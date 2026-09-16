"""Lite3 Robot Monitor 后端全局配置。

设计要点：
1. 所有可调参数集中在本文件，避免散落到业务模块中；
2. 全部参数支持通过环境变量覆盖，方便在机器人本体 / 边缘主机上部署；
3. 使用冻结（frozen）的数据类，运行期不允许被意外修改。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Tuple


def _get_str(name: str, default: str) -> str:
    """读取字符串型环境变量，未设置时返回默认值。"""
    value = os.getenv(name)
    return value if value else default


def _get_int(name: str, default: int) -> int:
    """读取整型环境变量，解析失败时回退到默认值。"""
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    """读取浮点型环境变量，解析失败时回退到默认值。"""
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class UDPConfig:
    """UDP 接收相关配置。

    默认值与原 Tkinter 脚本保持一致：监听本机所有网卡的 43897 端口。
    """

    # 监听地址：0.0.0.0 表示接收所有网卡上的数据
    host: str = _get_str("LITE3_UDP_HOST", "0.0.0.0")
    # Lite3 状态数据默认目标端口
    port: int = _get_int("LITE3_UDP_PORT", 43897)
    # 单次 recvfrom 的最大字节数，需大于最长报文（0x0901 共 220 字节）
    buffer_size: int = _get_int("LITE3_UDP_BUFFER", 2048)
    # Socket 超时时间（秒），保证后台线程可以被及时停止
    timeout: float = _get_float("LITE3_UDP_TIMEOUT", 0.1)
    # 接收队列最大长度，超限时丢弃最旧的数据包，防止长时间断网后堆积
    max_queue_size: int = _get_int("LITE3_UDP_QUEUE", 1024)


@dataclass(frozen=True)
class ServiceConfig:
    """Web 服务相关配置。"""

    host: str = _get_str("LITE3_HTTP_HOST", "0.0.0.0")
    port: int = _get_int("LITE3_HTTP_PORT", 8000)
    # WebSocket 推送频率（Hz），计划书要求 10Hz
    push_hz: int = _get_int("LITE3_PUSH_HZ", 10)
    # 超过该时间（秒）没有收到任何 UDP 数据，即判定机器人离线
    link_timeout: float = _get_float("LITE3_LINK_TIMEOUT", 3.0)
    # 原始报文环形缓存条数，供前端 RawPacket 组件展示
    raw_history_size: int = _get_int("LITE3_RAW_HISTORY", 30)
    # 原始报文十六进制预览的最大字节数
    raw_preview_bytes: int = _get_int("LITE3_RAW_PREVIEW", 64)
    # 是否挂载已构建的前端静态资源（frontend/dist）
    serve_frontend: bool = _get_str("LITE3_SERVE_FRONTEND", "true").lower() == "true"
    # 前端静态资源目录（相对 backend 目录）
    frontend_dist: str = _get_str("LITE3_FRONTEND_DIST", "../frontend/dist")


@dataclass(frozen=True)
class DisplayConfig:
    """数值展示相关的辅助配置。"""

    # 12 个关节的显示名称。
    # Lite3 关节顺序以 SDK 版本为准，默认按 FR / FL / RR / RL 四腿、
    # 每腿 hip / thigh / calf 三关节排列；如与实际不符，在此处调整即可。
    joint_legs: Tuple[str, ...] = ("FR", "FL", "RR", "RL")
    joint_parts: Tuple[str, ...] = ("hip", "thigh", "calf")


# 全局单例配置对象
udp_config = UDPConfig()
service_config = ServiceConfig()
display_config = DisplayConfig()


def get_joint_names() -> list[str]:
    """生成 12 个关节的显示名称，例如 FR_hip、FR_thigh ...。"""
    names: list[str] = []
    for leg in display_config.joint_legs:
        for part in display_config.joint_parts:
            names.append(f"{leg}_{part}")
    # SDK 关节顺序若少于 12 个，使用通用名称兜底，保证下标不会越界。
    while len(names) < 12:
        names.append(f"joint_{len(names)}")
    return names[:12]
