"""Lite3 Robot Monitor 后端服务入口。

提供：
    GET  /api/state     当前机器人状态快照
    GET  /api/status    服务与链路运行状态
    GET  /api/raw       最近若干条原始 UDP 报文
    WS   /ws/state      10Hz 实时推送机器人状态

设计约束：
1. UDP 接收在独立线程；解析在 asyncio 消费任务中完成，两者都不会阻塞事件循环；
2. 每个 WebSocket 连接独立心跳；断连自动清理；
3. 所有对外数据经由 models.py 中的 Pydantic 模型序列化。
"""

from __future__ import annotations

import asyncio
import contextlib
import functools
import json
import logging
import os
import sys
import time
from typing import Any, Dict, Set

# 保证既支持 `uvicorn main:app`，也支持从其他工作目录脚本方式启动
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from config import service_config, udp_config  # noqa: E402
from models import MonitorState, RawPacketResponse, ServiceStatus  # noqa: E402
from parser import parse_packet  # noqa: E402
from state_manager import StateManager  # noqa: E402
from udp_receiver import UDPReceiver  # noqa: E402

# ----------------------------------------------------------------------
# 日志
# ----------------------------------------------------------------------
logging.basicConfig(
    level=os.getenv("LITE3_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("lite3.monitor")


class WebSocketManager:
    """WebSocket 连接池：负责注册、注销与广播。"""

    def __init__(self) -> None:
        self._clients: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        """接受连接并加入广播列表。"""
        await websocket.accept()
        self._clients.add(websocket)
        logger.info("WebSocket 客户端接入，当前连接数 %d", len(self._clients))

    def disconnect(self, websocket: WebSocket) -> None:
        """移除连接（幂等）。"""
        if websocket in self._clients:
            self._clients.discard(websocket)
            logger.info("WebSocket 客户端断开，当前连接数 %d", len(self._clients))

    @property
    def count(self) -> int:
        """当前在线客户端数。"""
        return len(self._clients)

    async def broadcast(self, message: str) -> None:
        """向所有在线客户端广播文本消息，异常连接自动清理。"""
        dead: list[WebSocket] = []
        for client in list(self._clients):
            try:
                await client.send_text(message)
            except Exception as exc:  # noqa: BLE001 - 连接可能随时断开
                logger.debug("广播失败，移除客户端: %s", exc)
                dead.append(client)
        for client in dead:
            self.disconnect(client)


class MonitorService:
    """组合 UDP 接收器、状态管理器与 WebSocket 广播的核心服务。"""

    def __init__(self) -> None:
        # UDP 接收器（后台线程）
        self.receiver = UDPReceiver()
        # 状态仓库（线程安全）
        self.state = StateManager()
        # WebSocket 连接池
        self.ws = WebSocketManager()
        # 消费任务与广播任务句柄
        self._consumer_task: asyncio.Task | None = None
        self._broadcast_task: asyncio.Task | None = None
        # UDP 是否已成功绑定
        self.udp_ready: bool = False

    # ------------------------------------------------------------------
    async def start(self) -> None:
        """启动 UDP 接收、消费任务与广播任务。"""
        try:
            self.receiver.start()
            self.udp_ready = True
        except OSError:
            logger.error(
                "UDP 端口 %s 绑定失败，服务继续启动以便查看状态页，请检查端口占用后重试",
                udp_config.port,
            )
            self.udp_ready = False

        self._consumer_task = asyncio.create_task(self._consume_loop(), name="udp-consumer")
        self._broadcast_task = asyncio.create_task(self._broadcast_loop(), name="ws-broadcast")

    async def stop(self) -> None:
        """停止所有后台任务与 UDP 接收线程。"""
        for task in (self._consumer_task, self._broadcast_task):
            if task is not None:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
        self._consumer_task = None
        self._broadcast_task = None
        self.receiver.stop()

    # ------------------------------------------------------------------
    async def _consume_loop(self) -> None:
        """消费 UDP 队列：取帧 -> 解析 -> 更新状态仓库。

        队列读取是阻塞调用，放入线程池执行，避免阻塞 asyncio 事件循环。
        """
        loop = asyncio.get_running_loop()
        get_packet = functools.partial(self.receiver.get_packet, 0.1)

        while True:
            try:
                frame = await loop.run_in_executor(None, get_packet)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - 消费线程不应因异常退出
                logger.error("UDP 队列读取异常: %s", exc)
                await asyncio.sleep(0.2)
                continue

            if frame is None:
                continue

            data, addr = frame
            try:
                payload: Dict[str, Any] = parse_packet(data, addr)
                self.state.update(payload, raw=data)
            except Exception as exc:  # noqa: BLE001 - 单包异常不能终止整个服务
                logger.exception("处理 UDP 数据包失败: %s", exc)

    async def _broadcast_loop(self) -> None:
        """按固定频率向所有 WebSocket 客户端推送最新状态快照。"""
        interval = 1.0 / max(1, service_config.push_hz)
        while True:
            await asyncio.sleep(interval)
            if self.ws.count == 0:
                # 没有客户端时跳过序列化开销，仅更新连接数
                self.state.set_ws_clients(0)
                continue

            try:
                snapshot = self.state.snapshot()
                self.state.set_ws_clients(self.ws.count)
                message = json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"))
            except Exception as exc:  # noqa: BLE001
                logger.exception("状态序列化失败: %s", exc)
                continue

            await self.ws.broadcast(message)

    # ------------------------------------------------------------------
    def status(self) -> ServiceStatus:
        """返回服务运行状态。"""
        return self.state.get_status(self.receiver.stats(), service_config.push_hz)


service = MonitorService()


# ----------------------------------------------------------------------
# FastAPI 应用
# ----------------------------------------------------------------------
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN201 - FastAPI 生命周期钩子
    """应用生命周期：启动时拉起监控服务，关闭时释放资源。"""
    logger.info(
        "Lite3 Robot Monitor 启动: UDP %s:%s, HTTP %s:%s",
        udp_config.host, udp_config.port, service_config.host, service_config.port,
    )
    await service.start()
    try:
        yield
    finally:
        await service.stop()
        logger.info("Lite3 Robot Monitor 已停止")


app = FastAPI(
    title="Lite3 Robot Monitor",
    description="Lite3 四足机器人 UDP 状态实时监控后端",
    version="1.0.0",
    lifespan=lifespan,
)

# 开发环境允许 Vite 直连后端，生产环境也保留以便跨域部署
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------------------------------------------------
# REST 接口
# ----------------------------------------------------------------------
@app.get("/api/state", response_model=MonitorState, tags=["state"])
async def get_state() -> MonitorState:
    """获取当前机器人状态快照（HTTP 轮询备用接口）。"""
    return service.state.get_state()


@app.get("/api/status", response_model=ServiceStatus, tags=["state"])
async def get_status() -> ServiceStatus:
    """获取服务与链路运行状态。"""
    return service.status()


@app.get("/api/raw", response_model=RawPacketResponse, tags=["debug"])
async def get_raw(limit: int = 20) -> RawPacketResponse:
    """获取最近 `limit` 条原始 UDP 报文的摘要信息。"""
    limit = max(1, min(limit, 200))
    return service.state.get_raw_response(limit)


@app.get("/api/health", tags=["ops"])
async def health() -> Dict[str, Any]:
    """轻量健康检查，供容器 / supervisor 使用。"""
    status = service.status()
    counters = service.state.counters()
    return {
        "ok": True,
        "udp_running": status.udp_running,
        "connected": status.connected,
        "uptime_seconds": counters["uptime"],
    }


@app.post("/api/raw/clear", tags=["debug"])
async def clear_raw() -> Dict[str, Any]:
    """清空原始报文缓存。"""
    service.state.clear_raw()
    return {"ok": True}


# ----------------------------------------------------------------------
# WebSocket 接口
# ----------------------------------------------------------------------
@app.websocket("/ws/state")
async def websocket_state(websocket: WebSocket) -> None:
    """实时推送机器人状态。

    服务端以 10Hz 主动推送；客户端发送任意文本均可触发一次即时快照；
    连接断开自动清理。
    """
    await service.ws.connect(websocket)
    service.state.set_ws_clients(service.ws.count)
    try:
        # 建立连接后立即推送一次，避免页面空白等待
        snapshot = service.state.snapshot()
        await websocket.send_text(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")))

        while True:
            # 接收客户端消息以感知断连；收到任意消息立即回推一帧
            await websocket.receive_text()
            snapshot = service.state.snapshot()
            await websocket.send_text(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")))
    except WebSocketDisconnect:
        service.ws.disconnect(websocket)
    except Exception as exc:  # noqa: BLE001 - 未知异常同样需要清理连接
        logger.debug("WebSocket 异常: %s", exc)
        service.ws.disconnect(websocket)
    finally:
        service.ws.disconnect(websocket)
        service.state.set_ws_clients(service.ws.count)


# ----------------------------------------------------------------------
# 静态资源（可选）：若前端已构建，则由本服务直接托管
# ----------------------------------------------------------------------
def _mount_frontend() -> None:
    """把 frontend/dist 挂载到根路径，实现单端口部署。"""
    if not service_config.serve_frontend:
        return
    dist = os.path.abspath(os.path.join(_BACKEND_DIR, service_config.frontend_dist))
    index = os.path.join(dist, "index.html")
    if os.path.isfile(index):
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
        logger.info("已挂载前端静态资源: %s", dist)
    else:
        logger.info("未发现前端构建产物，跳过静态挂载（开发模式请使用 npm run dev）")


_mount_frontend()


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):  # noqa: ANN001, ANN201
    """统一异常处理，避免内部错误直接暴露堆栈。"""
    logger.exception("未处理异常: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "服务器内部错误", "error": str(exc)})


def main() -> None:
    """命令行入口：python main.py。

    等价于 `uvicorn main:app --host ... --port ...`
    """
    import uvicorn

    uvicorn.run(
        "main:app",
        host=service_config.host,
        port=service_config.port,
        reload=os.getenv("LITE3_RELOAD", "false").lower() == "true",
        log_level=os.getenv("LITE3_LOG_LEVEL", "info").lower(),
    )


if __name__ == "__main__":
    main()
