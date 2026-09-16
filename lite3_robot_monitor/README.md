# Lite3 Robot Monitor

把原先基于 **Python Tkinter** 的 Lite3 状态接收工具（`script/lite3_robot_state_receiver.py`）改造成 **前后端分离的 Web 监控系统**。

> 通过浏览器访问监控页面，即可实时查看 Lite3 四足机器人通过 UDP 上报的状态数据。

---

## 一、架构总览

```text
Lite3 机器人本体
      │  UDP 二进制报文 (0x0901 / 0x0902 / 0x0903)
      ▼
┌──────────────────────── Backend (FastAPI) ────────────────────────┐
│  udp_receiver.py   后台线程收发，写入线程安全队列                   │
│        ▼                                                           │
│  parser.py         bytes → 结构化 dict（协议逻辑与原脚本一致）       │
│        ▼                                                           │
│  state_manager.py  保存最新状态 + 原始报文环形缓存 + 在线判定        │
│        ▼                                                           │
│  main.py           REST (/api/*) + WebSocket (/ws/state, 10Hz)     │
└────────────────────────────────────────────────────────────────────┘
      │  WebSocket JSON 推送
      ▼
┌──────────────────────── Frontend (Vue3) ──────────────────────────┐
│  RobotStatus.vue   状态 / 步态 / 电池 / 连接                        │
│  IMUChart.vue      Roll / Pitch / Yaw 实时曲线（ECharts）           │
│  JointPanel.vue    12 个关节角度与角速度                            │
│  RawPacket.vue     原始 UDP 报文十六进制预览                        │
└────────────────────────────────────────────────────────────────────┘
```

设计要点：

| 项 | 说明 |
| --- | --- |
| 协议不变 | 完全沿用原脚本的消息码、struct 格式与字段顺序，未删减任何字段 |
| 去 GUI | 不再依赖 Tkinter，UDP 线程与 Web 事件循环彻底解耦 |
| 单一职责 | 接收、解析、状态管理、接口、展示分别独立成模块 |
| 可扩展 | 预留视频、AI 检测、ROS2 桥接的接入位置 |

---

## 二、目录结构

```text
lite3_robot_monitor/
├── backend/
│   ├── main.py            # FastAPI 入口：REST + WebSocket
│   ├── udp_receiver.py    # UDP 接收线程 + 队列（含丢包统计）
│   ├── parser.py          # 0x0901 / 0x0902 / 0x0903 协议解析
│   ├── state_manager.py   # 最新状态仓库 + 原始报文缓存 + 在线判定
│   ├── models.py          # Pydantic 响应模型
│   ├── config.py          # 集中配置，支持环境变量覆盖
│   └── requirements.txt
├── frontend/
│   ├── package.json
│   ├── vite.config.js     # 内置 /api、/ws 代理
│   ├── index.html
│   └── src/
│       ├── main.js
│       ├── App.vue        # 主面板布局
│       ├── api/index.js   # REST 封装 + WebSocket 客户端（自动重连）
│       ├── composables/useRobotState.js
│       ├── components/
│       │   ├── RobotStatus.vue
│       │   ├── IMUChart.vue
│       │   ├── JointPanel.vue
│       │   └── RawPacket.vue
│       └── style.css
├── tools/
│   ├── mock_sender.py               # 本地联调用的 Lite3 数据模拟器
│   ├── smoke_test.py                # 端到端冒烟测试：UDP → 解析 → WS → REST → 离线判定
│   └── inspect_control_packets.py   # 控制通道侦查：pcap 解析 + 逐字节差分 + 受控重放
├── start-backend.bat                # 后端一键启动（自动建 .venv + 装依赖）
├── start-backend.ps1                # 同上，PowerShell 版
├── start-frontend.bat               # 前端一键启动（自动 npm install）
├── .gitignore                       # 忽略 .venv / node_modules / dist
├── requirements.txt
└── README.md
```

> `.venv/` 由启动脚本首次运行时自动创建，不需要提交到仓库。

---

## 三、支持的协议

| 消息码 | 内容 | 报文长度 |
| --- | --- | --- |
| `0x0901` | 机器人综合状态：基本状态 / 步态 / AI 步态 / IMU（姿态、角速度、加速度）/ 世界系位姿与速度 / 机体系速度 / 电池 / 错误码 / 标志位 / 前后超声波 | 头 12B + 负载 208B |
| `0x0902` | 12 个关节角度（rad） | 头 12B + 负载 96B |
| `0x0903` | 12 个关节角速度（rad/s） | 头 12B + 负载 96B |

消息头统一为 3 个 `uint32`（`<3I`）：消息码、长度、序号。

---

## 四、快速开始

### 1. 启动后端（Windows 推荐用脚本）

在项目根目录 **双击 `start-backend.bat`** 即可，脚本会自动完成：
创建 `.venv` → 安装 `backend/requirements.txt` → 启动 `uvicorn`。

| 文件 | 适用场景 |
| --- | --- |
| `start-backend.bat` | 推荐，双击即可，无执行策略限制 |
| `start-backend.ps1` | PowerShell 用户；若提示禁止运行脚本，用 `powershell -ExecutionPolicy Bypass -File start-backend.ps1` |

换端口：`set PORT=9000` 后再运行（PowerShell 用 `$env:PORT=9000`）。

<details>
<summary>手动启动方式（Linux / macOS / 想自己掌控时）</summary>

```bash
cd lite3_robot_monitor
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r backend/requirements.txt   # Windows
# source .venv/bin/activate && pip install -r backend/requirements.txt  # Linux / macOS

cd backend
../.venv/Scripts/python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
```

</details>

浏览器打开 <http://localhost:8000/docs> 可查看自动生成的接口文档。

> 若 UDP 端口被占用，服务仍会启动，可通过 `/api/status` 查看原因。

#### 常见报错：`uvicorn 不是内部或外部命令`

```
uvicorn : The term 'uvicorn' is not recognized as the name of a cmdlet...
```

**原因**：没有激活虚拟环境，或依赖装在了别的 Python 里。全局 `uvicorn` 不在 PATH 中。

**三种解法**（任选其一）：

1. 用上面的 `start-backend.bat`（最省事，脚本内部绝对路径调用 `.venv` 里的 Python）；
2. 先激活再运行：
   ```powershell
   .\.venv\Scripts\Activate.ps1
   cd backend
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```
3. 不激活也可以，直接用 venv 的解释器：
   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
   ```

若需确认依赖到底装在哪：

```powershell
.\.venv\Scripts\python.exe -c "import fastapi, uvicorn; print('ok')"
```

### 2. 启动前端

双击 `start-frontend.bat`（首次自动 `npm install`），或手动执行：

访问 <http://localhost:5173> 即可看到监控面板。

生产模式下也可先 `npm run build`，后端会自动托管 `frontend/dist`，直接用 `http://localhost:8000` 单端口访问。

---

## 五、接口说明

### WebSocket

`ws://<host>:8000/ws/state`

服务端以 **10Hz** 主动推送完整快照：

```json
{
  "type": "snapshot",
  "server_time": 1726400000.123,
  "connected": true,
  "robot_state": {
    "type": "robot_state",
    "code": "0x0901",
    "basic_state": "力控状态",
    "basic_state_code": 6,
    "gait_state": "平地高速",
    "imu": { "roll": 1.02, "pitch": -0.31, "yaw": 8.4 },
    "position": { "x": 1.2, "y": -0.4, "yaw": 0.15 },
    "velocity": { "x": 0.3, "y": 0.0, "yaw": 0.02 },
    "battery": 78.0,
    "ultrasound": { "forward": 1.25, "backward": 0.86 }
  },
  "joint_angle": { "type": "joint_angle", "joint": [0.01, -0.02] },
  "joint_velocity": { "type": "joint_velocity", "velocity": [0.0, 0.01] },
  "others": []
}
```

客户端发送任意文本，服务端立即回推一帧最新快照（可用于降频探测）。

### REST

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/state` | 当前完整状态快照（HTTP 轮询备用） |
| GET | `/api/status` | 服务与链路状态：是否在线、收发包计数、WS 连接数 |
| GET | `/api/raw?limit=20` | 最近 N 条原始报文摘要（时间、消息码、长度、来源、hex 预览） |
| POST | `/api/raw/clear` | 清空原始报文缓存 |
| GET | `/api/health` | 轻量健康检查 |

---

## 六、配置项

所有参数集中在 `backend/config.py`，可用环境变量覆盖：

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `LITE3_UDP_HOST` | `0.0.0.0` | UDP 监听地址 |
| `LITE3_UDP_PORT` | `43897` | UDP 监听端口（需与 Lite3 发送目标端口一致） |
| `LITE3_UDP_BUFFER` | `2048` | 单次接收缓冲区大小 |
| `LITE3_UDP_QUEUE` | `1024` | 接收队列容量，满时丢弃最旧数据 |
| `LITE3_HTTP_HOST` | `0.0.0.0` | HTTP 监听地址 |
| `LITE3_HTTP_PORT` | `8000` | HTTP 监听端口 |
| `LITE3_PUSH_HZ` | `10` | WebSocket 推送频率 |
| `LITE3_LINK_TIMEOUT` | `3.0` | 超过该秒数未收到数据判定离线 |
| `LITE3_RAW_HISTORY` | `30` | 原始报文环形缓存条数 |
| `LITE3_LOG_LEVEL` | `INFO` | 日志级别 |
| `LITE3_SERVE_FRONTEND` | `true` | 是否挂载 `frontend/dist` |

前端可通过 `VITE_BACKEND_URL` 指定后端地址（跨域直连模式）。

---

## 七、本机无机器人时的联调

使用内置模拟器向本机发送符合协议的数据：

```bash
# 默认向 127.0.0.1:43897 以 10Hz 发送
python tools/mock_sender.py

# 只发一轮用于协议校验
python tools/mock_sender.py --once
```

随后刷新页面，应能看到：状态卡片显示「力控状态 / 平地高速 / 78.0%」，IMU 曲线随时间摆动，12 个关节数值滚动更新。停止模拟器 3 秒后（默认超时），页面自动切换为 **Disconnected**。

也可直接在命令行做一次完整链路自检（UDP → 解析 → WebSocket → REST → 离线判定）：

```bash
python tools/smoke_test.py
```

测试会临时占用本机 8000 端口，通过后打印「全部冒烟测试通过」。

---

## 八、验收对照

| 验收项 | 结果 |
| --- | --- |
| 启动后端后可收到 Lite3 UDP 数据 | ✅ 通过 `/api/status` 的接收包计数验证 |
| 浏览器显示 Battery / Mode / IMU / Position | ✅ `RobotStatus.vue` + `IMUChart.vue` + 位置速度面板 |
| 机器人状态变化时网页同步变化 | ✅ WebSocket 10Hz 推送 |
| 关闭机器人后显示 Disconnected | ✅ 超过 `LITE3_LINK_TIMEOUT` 未收到数据即判定离线 |

---

## 九、后续扩展预留

| 方向 | 建议接入位置 |
| --- | --- |
| 视频（RealSense / RTSP） | 新增 `backend/video_stream.py`，接口 `GET /api/video` 或 `WS /ws/video` |
| AI 检测（YOLO 火焰检测） | 新增 `backend/detector.py`，接口 `GET /api/detection`，前端增加 `DetectionPanel.vue` |
| ROS2 桥接 | 新增 `backend/ros_bridge.py`，把 `/ws/state` 的 dict 转成 ROS2 Topic，或反向订阅 |

新增能力只需：在 `parser.py` 增加消息码分支 → 在 `models.py` 增加模型 → 在前端增加组件，
不需要改动 UDP 接收与 WebSocket 推送骨架。

---

## 十、注意事项

1. 本系统**只读**，不会向机器人发送任何运动控制指令；
2. 关节名称默认按 `FR / FL / RR / RL` 四腿、每腿 `hip / thigh / calf` 排列，若与实际 SDK 顺序不符，修改 `backend/config.py` 中的 `DisplayConfig` 即可；
3. `0x0901` 中的 `touch_down_and_stair_trot`、`is_charging`、`error_state`、`task_state` 在部分固件版本上为无效值，界面已做弱化处理但仍完整透传。

---

## 十一、控制通道（写方向）：为什么现在没有，以及该怎么做

### 11.1 读写是两条完全不同的链路

| 方向 | 端口 | 谁监听 | 协议 | 本项目状态 |
| --- | --- | --- | --- | --- |
| **读**（状态上报） | UDP **43897** | 103（`transfer_ros2`） | 半公开：`0x0901/0x0902/0x0903` | 已实现 |
| **写**（运动控制） | UDP **43893** | 120（`jy_exe`，闭源） | 私有，未公开 | **刻意未实现** |

监控面板上的按钮只能切页面，不可能"顺便"让狗动起来——后端根本没有打开写方向的 socket。

⚠️ 注意：120 上 `43899`、`43901` 也在监听，属于私有扩展端口，不要试探。

### 11.2 三条可选路径（按风险从低到高）

| 路径 | 做法 | 安全层 | 风险 |
| --- | --- | --- | --- |
| **A. 走 ROS 2（推荐）** | 后端 publish `/cmd_vel` → 103 上现有 `transfer_ros2` / `jetson2motion` 转成 43893 发给 120 | ✅ 经 **VOA SafetyController**，会限速、避障、防撞 | 需与 Nav2 争 `/cmd_vel`，要用 mux 做模式互斥 |
| **B. 复用 103 侧的组包逻辑** | 读 103 上 `transfer_ros2` 自己的源码（不是逆向闭源 `jy_exe`），把那几行组包代码搬到后端 | ❌ 绕过 VOA | 错误速度无人兜底，直接驱动关节 |
| **C. 抓包逆向 43893** | 用 `tools/inspect_control_packets.py` 差分推断字段 | ❌ 绕过 VOA | 最慢；可能带校验/时间戳，重放失败 |

**结论：只有路径 A 不会拆掉已有的安全防线。** 你们自己的笔记也写了不建议对 `jy_exe` 做协议级联动。

### 11.3 侦查流程（无论走哪条路，都建议先看清报文）

```bash
# 1) 在 103 上抓自己发出的控制包（103 → 120:43893 出向包，零侵入）
sudo tcpdump -i any -nn udp dst port 43893 -w /tmp/ctrl.pcap -c 300
#    抓的同时，让机器人缓慢改变速度，制造可比较的报文序列

# 2) 列出报文，观察长度与头部
python tools/inspect_control_packets.py list /tmp/ctrl.pcap --port 43893

# 3) 相邻帧逐字节差分，自动定位"哪几个偏移随速度变化"
python tools/inspect_control_packets.py diff /tmp/ctrl.pcap --port 43893
```

`diff` 会按偏移区间给出变化频率，并直接用多种数值格式试解（float32/float64/整型，大小端），例如：

```text
  区间          帧数占比   候选解码（取最后一帧）
  0008           100.0%   i32_le=+29.0000      ← 每帧必变，序号
  0012-0015      100.0%   f32_le=+2.9000       ← 随操作有界变化，速度
  0020-0027       96.6%   f64_le=+1.4500       ← 角速度
```

拿到结果后**必须与实际操作对照确认**，确认无误才能写进 `parser.py`。

如需验证某个猜想，可用 `send` 子命令，默认 dry-run：

```bash
python tools/inspect_control_packets.py send "010a0000 dc000000 05000000 cccc3d40" --port 43893
```

### 11.4 万一将来要加控制，必须先具备的安全约束

按重要性排序，缺一项都不建议开放写通道：

1. **默认禁用**：配置项显式开启才下发，默认 `CONTROL_ENABLED=false`；
2. **强制 deadman**：前端必须持续按住才发速度，松手立即下发零速（不能只靠超时兜底）；
3. **心跳超时归零**：超过 200~300ms 没收到前端心跳，后端自动持续下发零速；
4. **速度硬限幅**：在**后端**再夹一次上下限（不能只信前端），建议初始 ±0.3 m/s、±0.5 rad/s；
5. **独立急停**：一个不经常规指令路径的急停端点，直接广播零速并锁死；
6. **模式互斥**：手动控制与 Nav2 自动导航互斥，禁止同时写 `/cmd_vel`；
7. **审计日志**：每条下发的速度指令带时间戳落盘，便于事后复盘；
8. **现场有人**：首轮测试在开阔场地、有人持遥控器准备接管，机器人先架空或垫起。

在此之前，本工程保持只读是**特性，不是缺陷**。
