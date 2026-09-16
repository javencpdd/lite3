# Lite3 火灾巡检系统 v1.0：103 主机部署可行性评估

评估时间：2026-09-16 20:47（Asia/Shanghai）。状态：**有条件可行，当前远程连接阻塞；不是部署批准或硬件性能验收**。

## 1. 结论与证据边界

已完整读取[工程实施计划](Lite3%20火灾巡检系统%20v1.0%20工程实施计划.md)全部 18 节及最终判断，文件 SHA-256：`3C3EB139BE93FDFA579447C87A169B29720C6C4F71AD31B722B784F083773FB3`。

方案的软件分工可沿现有 Foxy 导航平台渐进实施，但目前不能确认“主机资源足够、依赖齐全、端口空闲、可直接部署”。主要原因：

1. 本轮 MCP 未能连接 103，CPU 核数、内存、磁盘、内核、服务与权限等要求的实时信息均未采集成功。
2. 历史源码显示原始速度可绕过 VOA；与计划 F7“VOA 最终安全层”不一致，必须先闭合安全链。
3. 现有导航配置控制频率为 5 Hz，与计划“导航频率 ≥10 Hz”至少存在口径/配置差异；调高参数不能替代性能测试。
4. 火焰模型、事件接口、告警停车、取证及巡检状态机属于新增工程，不是现有人体跟踪换个模型就完成。
5. 已有 GUI 依赖、地图/航点缺项和系统目录定制需整改或复核；不能直接套用全部现有启动脚本。

本文证据分三级：**本轮实测**、**历史已核验但本轮未复核**、**建议/待验证**。绝不将历史源码配置当作实时运行状态。未修改远端文件、安装软件、调整网络或启动机器人；新建本评估文件，未覆盖实施计划。

## 2. 本轮连接与实际条件采集结果

### 2.1 连接证据

| 检查 | 本轮结果 | 可得结论 |
| --- | --- | --- |
| MCP hostAlias=ysc-f20-103 | Unknown hostAlias，未在当前 SSH 配置/known_hosts 定义 | 该名称当前不能直接使用 |
| MCP hostAlias=lite3-f20-1-103 | 初次两次连接超时；用户确认此别名后再次重试，仍为 192.168.1.103:22 超时，退出码 255 | 别名已获用户确认；未建立 SSH，远端命令未执行 |
| 本机 IPv4/路由 | WLAN 192.168.0.200/24，默认网关 192.168.0.1；未见到 192.168.1.0/24 的专用路由 | 目标走默认路由；不同子网本身不等于不可达 |
| ping 103/120 | 两目标各 2 次请求均超时 | ICMP 没收到响应，不足以单独证明关机 |
| 沙箱外网络复核 | 经批准读取网卡并 Test-NetConnection 103:22，仍报告 TCP 失败及 ping 超时 | 不能仅归因于工具沙箱；具体故障点未知 |

可能原因包括机器人未通电、未接入目标网络、路由/防火墙隔离、IP 改变或 SSH 未监听。没有证据区分这些原因；不应盲目改静态 IP、删除路由或放开防火墙。此前批准的当前电脑 7897 加速代理仅帮助出网下载，不能自动解决 SSH 跨网段可达性。

### 2.2 主机条件：逐项标明缺失

| 项目 | 本轮实测 | 可参考历史证据 | 本轮判断 |
| --- | --- | --- | --- |
| OS | 未采到 | Ubuntu 20.04.6 | 待复核 |
| 内核 | 未采到 | 仅有 L4T R35.4.1 信息，不能代替 uname 内核版本 | 未知 |
| CPU 架构/核数/型号 | 未采到 | aarch64、Jetson 平台；具体型号与核数未知 | 无法定算力预算 |
| 内存/Swap | 未采到 | 无可靠容量/余量数据 | 无法判断并发内存与 OOM 风险 |
| 磁盘/挂载/可用空间/inode | 未采到 | 仅确认过源码路径可读 | 不足以批准构建、模型与取证落盘 |
| GPU/功耗/温度 | 未采到 | 源码依赖 CUDA/TensorRT | 无法承诺 10 FPS 或长时间不降频 |
| 网卡/103→120/互联网 | 未采到 | 固定 IP 与 RTSP URL 配置 | 不能认定视频或 DDS 可用 |
| 端口占用/进程 | 未采到 | 见第 5 节配置端口 | 配置值不是监听状态 |
| 已有系统/用户服务 | 未采到 | App 代码调用 realsense_ros2、voa_ros2 | 不证明 unit 存在或 active |
| 工作区写权限/设备权限 | 未采到 | ysc 曾能读取工作区 | 读权限不等于写权限或 USB 访问权 |
| sudo | 未采到 | 本轮 sudo -n -l 未在远端执行 | 不知道是否需密码、可执行哪些命令 |

历史证据入口：[103 源码总览](../hosts/103-感知导航主机/lite_cog_ros2/README.md)、[驱动](../hosts/103-感知导航主机/lite_cog_ros2/driver.md)、[导航](../hosts/103-感知导航主机/lite_cog_ros2/nav.md)、[Transfer](../hosts/103-感知导航主机/lite_cog_ros2/transfer.md)、[VOA](../hosts/103-感知导航主机/lite_cog_ros2/voa.md)。

## 3. 方案需求与部署架构梳理

### 3.1 主机职责

| 位置 | 计划部署 | 输入/输出与硬件要求 |
| --- | --- | --- |
| 控制笔记本 | Foxglove 客户端、布局、SSH 运维 | 能访问 bridge；不要求直接运行机器人 DDS 节点 |
| 103 感知主机 | Foxy、HDL/Nav2、VOA、transfer、fire_detector、patrol_manager、fire_event_manager、safe_cmd_mux、lite3_interfaces、bridge | 雷达/深度相机/IMU/里程计；RTSP 解码与 GPU 推理；磁盘取证 |
| 120 运动主机 | 视频 RTSP、语音、运动执行 | 摄像头、音频输出、UDP 控制、急停/断指令保护 |
| 训练环境 | 数据标注、YOLOv8n 训练、验证和导出 | 建议独立 GPU 开发机；103 以推理为主 |

原文将 120 标为 RK3588，但本轮未访问 120 验证，不能当作本轮硬件检测结果。

目录图存在歧义：src 与五个新包画成同级，ops 的根路径也不明确。建议在既有根目录下新增独立 `fire_patrol_ws/src/{fire_detector,patrol_manager,fire_event_manager,safe_cmd_mux,lite3_interfaces}`，把 ops 明确定义为 `/home/ysc/lite_cog_ros2/ops`，或封装成可安装的 bringup 包。不要在顶层直接 colcon build 扫描整组已有工作区，避免重复包/overlay 污染。此为建议，尚未创建。

### 3.2 逐项功能对照

| 计划目标 | 历史基础/本轮信息 | 判断与必须动作 |
| --- | --- | --- |
| F1 无头运行 | dr_nav2 启动 RViz，建图脚本用 gnome-terminal，记录器/track 使用 Qt/imshow | 需新建 headless 启动入口，隔离 GUI；不必卸载桌面 |
| F2 Foxglove | 未核验 bridge、端口、布局及安装候选 | 条件可行；先做版本兼容与只读遥测验证 |
| F3 固定路线 | Nav2/HDL 已有源码；历史 PCD/PGM 缺失、航点目录为空 | 重新核验地图，再开发 patrol_manager；不能直接执行示例坐标 |
| F4 火焰检测 | 有 RTSP/YOLO 人体跟踪基础；无已核验火焰权重 | 新增检测节点及火焰数据集；现有 COCO person 模型不满足 |
| F5 停止/语音 | 取消任务、零速锁存、语音协议未闭合 | P0 安全与接口设计阻塞，不以发 Bool 代替制动 |
| F6 图像/时间/位置 | 未核验取证目录、磁盘、时钟、位置关联 | 新增事件 ID、时间同步、原子写入与保留策略 |
| F7 VOA 最终安全层 | Transfer 同时收 /cmd_vel 与 /cmd_vel_corrected；pipeline 另有直连 UDP | 必须消除旁路并验证断流停车 |
| ≥2 小时巡检/8 小时测试 | 无本轮运行样本 | 待实测，两个时长分别是验收与耐久测试 |
| 检测 ≤500 ms | 计划 10 FPS、连续 5 帧 | 光确认窗口首帧到第五帧约 400 ms，尚有采集等待/解码/推理/调度延迟，余量很小 |
| 导航 ≥10 Hz | 历史 controller_frequency=5 Hz | 先定义测 controller 输出还是 planner；不是所有导航模块都应 10 Hz |
| CPU <80% | 无核数/负载统计 | 先规定整机归一化口径、采样窗口和峰值/P95；不能拿单进程 top 数值直接对比 |

## 4. 软件依赖、接口和兼容风险

| 依赖层 | 已有证据 | 待查/建议 |
| --- | --- | --- |
| Foxy/ament/colcon/rclpy/rclcpp | 历史存在 Foxy，也安装 Noetic | 每个服务明确 source 顺序，禁止混合两套 ROS 环境 |
| Nav2/HDL/STVL/TF | 历史 Nav2 0.4.7、PCL 1.10.0、Eigen 3.3.7 | 核对安装 prefix 与实际进程，迁移 /opt/ros 下定制启动文件 |
| RealSense/Livox/C16 | 定制相机 launch 已补齐、静态求值通过 | 不再以“launch 为空”阻塞；设备在线、USB/TF/数据仍需验收 |
| CUDA/TensorRT/PyTorch/Ultralytics | 仅有模型/源码依赖证据 | 采精确版本、Python 导入来源、engine 加载；不要直接升级全部 pip 包 |
| GStreamer/OpenCV | 历史 Jetson 解码路径；系统 OpenCV 4.2.0 | 检查 nvv4l2decoder/nvvidconv、Python OpenCV GStreamer 编译支持 |
| vision_msgs/lite3_interfaces | 方案需要，安装状态未知 | 在目标 Foxy 检查 ros2 interface show 并编译新消息 |
| foxglove_bridge | 安装状态未知 | 确认适配 Foxy/aarch64 的版本与构建依赖；不假定最新二进制可直接装 |
| tmux/systemd/音频接口 | 方案要求，现状未知 | 开发期 tmux，长期运行用受控服务；语音执行器/协议需要定义 |

Foxy 已被官方列为停止支持发行版，应冻结可复现依赖并评估补丁来源；不建议为本阶段任务直接原地升级机器人操作系统。[ROS 官方 EOL 列表](https://docs.ros.org/en/rolling/Releases/End-of-Life.html)

### 4.1 计划中需先修正的接口

- /fire_alert 在第 4 节为 std_msgs/Bool，第 8 节又建议 FireAlert；同名 Topic 不应承担两种类型。建议统一自定义类型，另设简化 Bool 状态话题。
- /fire_bbox 写 geometry_msgs 只是包名，缺具体消息类型。可复用 Detection2DArray 的 bbox，或定义明确类型。
- FireAlert 中 `string class` 涉及目标语言关键字风险，建议改为 class_name 并用 rosidl 编译确认；不以草案文本认定可构建。
- /robot_pose、/image、/mission_cancel、/voice_alert、/event_record、/patrol_status 和 battery/cpu 缺类型、发布者、QoS、超时及错误语义。
- Nav2 的停止任务应使用 Action cancel 并处理确认/超时，同时由独立安全通道持续输出停车；仅发 /mission_cancel 不会自动取消服务器目标。
- 单目检测框不能直接给出可信三维 fire_pose。v1.0 先记录检测时机器人位姿与 frame/stamp，火源坐标用明确 unknown 标记；后续定位再引入深度/标定/多视角。
- 数据配置文件名 dataset.yaml/fire.yaml 不一致；类别示例不是完整合法映射，应采用 `names: {0: candle, 1: flame, 2: light_reflection}` 等有效结构。数据集与 ROS 参数 YAML 是不同格式。
- 召回率 >90%、误报率 <5% 缺统计单位/测试集定义；需按事件或时间窗固定口径，训练/验证按场景或视频分组，防止相邻帧泄漏。

## 5. 网络与端口预算

下表是**计划/历史配置**，全部占用与连通性仍待远端复核。除 SSH 失败外，本轮没有端口监听结论。

| 流向/用途 | 端口/协议 | 依据与注意 |
| --- | --- | --- |
| 笔记本→103 SSH | TCP 22 | 本轮连接超时 |
| 笔记本→103 bridge | 建议 TCP 8765 WebSocket | 计划没写端口，按官方默认补充；不要与 rosbridge 9090 混淆 |
| 103→120 视频 | RTSP TCP 8554 | 原计划 /test；媒体若用 UDP 还需协商 RTP/RTCP，优先测试 RTSP interleaved TCP 简化端口 |
| 103→120 运动 | UDP 43893 | 历史 Transfer 目标 |
| 103 接收运动/App | UDP 43897、43899 | 历史源码 local_port，不是本轮 ss 结果 |
| pipeline 直接控制 | UDP 本地 20001→120:43893 | 历史旁路，生产任务需禁用或受统一控制 |
| C16 雷达→103 | UDP 2368/2369 | 历史雷达配置，设备 IP 192.168.1.201 |
| Livox 雷达↔103 | 配置设备 56100～56500、主机 56101～56501（每 100 间隔） | 与 C16 二选一，按 SDK/实际型号验证 |
| ROS2 DDS | 按 RMW、Domain ID、参与者派生 | 不按固定单端口放行；采集 Cyclone 配置/网卡绑定/多播与实际 UDP socket |
| 103→当前电脑代理 | TCP 7897（可选） | 需监听可达接口、ACL 和回程路由；不修改电脑代理绑定作为本轮操作 |
| 120 语音 | 未定义 | 必须先明确协议/端口/确认消息，不猜测 |
| 软件源/时间同步 | DNS、HTTPS/HTTP、时间服务按部署选择 | 代理不保证 UDP/DDS 或时钟同步可用 |

Foxglove 到 bridge 是 WebSocket；bridge 在机器人侧订阅 ROS2，不要求笔记本跨网段直接参与 DDS。官方给出的默认连接为 ws://localhost:8765。[Foxglove ROS2 文档](https://docs.foxglove.dev/docs/getting-started/frameworks/ros2)

建议先绑定 bridge 到受控接口并通过 SSH 隧道访问，不把可发命令/调参接口无鉴权暴露给整个网络；点云降采样、图像压缩、Topic 白名单与限频须计入带宽预算。

## 6. 安全链与权限整改

### 6.1 优先修正的控制结构

建议：Nav2/遥控等独立输入 → safe_cmd_mux → /cmd_vel_safe → VOA → /cmd_vel_corrected → 唯一运动发送器。需要同步调整 VOA 的输入和 Transfer 的订阅，不能仅新增一个 mux 后保留原 /cmd_vel 旁路。

人工急停、火灾锁存停止、输入超时必须对最终发送器持续有效。即便 VOA 崩溃、卡死或输入陈旧，也要由末端 watchdog 或运动主机断指令机制停车；人工硬件急停不应依赖 ROS/DDS/GPU。计划中遥控低于导航的优先级需区分“普通遥控”和“人工接管/急停”，后者不能被导航压住。

验收至少覆盖：mux/VOA/Transfer 任一进程退出、RTSP 断开、IMU/点云过期、网络中断、取消目标失败、旧命令重放、重启后锁存状态与人工复位。此处是整改要求，未实施或测试。

### 6.2 哪些动作需要权限

| 操作 | 通常权限要求 | 本机是否具备 |
| --- | --- | --- |
| 读取源码/日志、列进程 | 普通用户，部分日志/进程细节受限 | 本轮未知 |
| 在工作区构建、新建包/取证目录 | 目标和所有父目录的可写/可遍历权限 | 本轮未知 |
| apt、udev、/etc/systemd/system、系统服务管理 | 通常 sudo/相应策略授权 | 本轮未知；不能把历史密码当作 sudo 授权范围 |
| systemctl --user | 用户会话管理器；开机无人登录运行还涉及 linger | 本轮未知，enable-linger 可能需管理员 |
| 访问 USB/串口/音频 | 设备 ACL、udev 与 video/render/dialout/audio 等适用组 | 须以实际设备权限核对，不建议一律 sudo 跑节点 |
| ss 完整 PID、防火墙、系统日志 | 某些细节需 sudo | 先普通用户；缺项单列，不强制提权 |

计划目录在 /home/ysc 下也不能自动认定可写。只读 test -w 能检查访问判断，仍不能证明无磁盘配额、只读挂载或运行时写盘故障。取证服务应以最小权限运行，失败有告警，不授予任意 sudo。

## 7. 分阶段可行性与整改优先级

| 阶段 | 当前可直接做（不依赖在线机器人） | 阻塞/风险与通过条件 |
| --- | --- | --- |
| Phase 0 基础平台 | 设计 headless launch、服务依赖、监控字段、冻结清单 | P0 恢复连接并补采资源；去 GUI；bridge 兼容；记录 /opt/ros 定制 |
| Phase 1 巡检 | 编写状态机/Action 超时取消逻辑与模拟测试 | P0 地图、TF、传感器与安全链；P1 5→10 Hz 性能验证；真实路线验收 |
| Phase 2 检测 | 离线标注、训练、录像测试，定义模型契约 | P1 目标机 TRT/GStreamer、火焰权重、端到端延迟及 RTSP 恢复 |
| Phase 3 闭环 | 定义事件数据、停止锁存、语音适配和记录协议 | P0 最终停车机制；P1 120 语音与时钟/磁盘；先隔离运动测试 |
| Phase 4 优化 | 设计日志轮转、故障矩阵、性能记录模板 | P2 连续 2 h 与 8 h 热稳态/泄漏/丢帧统计 |

优先队列：

1. **P0 连通与基线**：确认 103/120 通电及实际 IP，接入机器人网络或由管理员配置路由；统一 SSH 别名，不盲目改网络。
2. **P0 运动安全**：移除双订阅/直连 UDP 旁路，末端过期停车、人工急停与火灾停止锁存；通过故障注入后才允许自主巡检。
3. **P0 输入就绪**：复核地图 PCD/PGM/YAML、航点、TF 和 IMU/雷达/相机；历史缺项不能视为当前仍缺，也不能假定已补齐。
4. **P1 可复现无头平台**：独立 overlay、明确 service WorkingDirectory/Environment/启动依赖/重启限速，保存现有系统目录改动。
5. **P1 接口和时延**：统一消息、Action 取消、语音确认、事件关联；固定“检测延迟”的起终点及 P95/P99。
6. **P1 算力与存储**：训练外移；实测并发 CPU/GPU/内存、功耗与磁盘写入，再确定频率/保留天数。
7. **P2 可维护性**：监控、磁盘水位、日志轮转、版本锁定、升级回滚和 8 小时耐久测试。

原文时间估计约 5～6 周加持续优化，只能当作目标计划；未计入硬件恢复、缺图、模型效果与旧版本兼容成本，不应据此承诺交付日期。

## 8. 硬件预算和替代方案

目前不能给出可信“至少空闲几 GB 就够”的设备专属结论。应分别测 ROS 基线、导航+VOA、加解码推理、再加 bridge/取证四组峰值。

- 内存：记录总量、MemAvailable、Swap、各进程 RSS/PSS、GPU 共享内存与峰值；不以 swap 掩盖持续内存不足。
- 磁盘：需求 = 源码/构建/依赖缓存 + 模型 + 峰值日志 + 取证保留量 + 回滚空间。连续录像约为码率(Mbit/s)×0.45 GB/小时；4 Mbit/s×8 h 约 14.4 GB，仅为估算，不含日志。
- 解码/推理：测预处理、推理、时序确认、发布与停车各段延迟。10 FPS 五帧确认留下的时延余量很少，可评估时间窗/置信度分级，但不能为了过指标随意牺牲误报抑制。
- 热/电：满载 8 h 温度、降频、供电与电池续航；“软件能跑 2 h”不等于整机电池能巡检 2 h。

替代路线：

1. 保留 Foxy 主栈，冻结兼容依赖，新功能独立 overlay；后续单独规划系统升级，避免同时换 ROS/JetPack/导航算法。
2. 先用离线录像或控制端完成火焰算法测试，103 只做导航与事件接口；若正式推理外置，必须把网络断连作为安全状态，且不能把外置算力视为板载验收通过。
3. 无可用 Foxy bridge 二进制时，评估固定兼容源码版本构建，或先用录制数据离线可视化；不保证现代 bridge 可直接装在 Foxy。
4. HSV+Motion 可用于低负载预筛选或影子模式，不能因资源受限直接替代火灾检测验收；静止火焰不应被运动门控永久过滤。
5. v1.0 保留“机器人位置+图像”取证，暂不输出未经验证的火源三维坐标；不引入 SCAN-Planner、热成像或大模型扩展。

## 9. 恢复连接后的必采指标和只读命令

以下为**待执行清单**，不是已获得结果。通过 MCP 确认目标 host/IP 后分批执行；不启动节点，不执行安装、重启、压测或发运动命令。命令不存在/权限不足应记录原始错误。

### 9.1 系统、资源、权限

```bash
hostname
date -Is
id
cat /etc/os-release
uname -a
lscpu
nproc
free -h
swapon --show
df -hT
df -i
lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT
cat /etc/nv_tegra_release
cat /proc/device-tree/model
findmnt -T /home/ysc/lite_cog_ros2
namei -l /home/ysc/lite_cog_ros2
stat -c '%A %U:%G %n' /home/ysc /home/ysc/lite_cog_ros2 /etc/systemd/system
test -w /home/ysc/lite_cog_ros2; printf 'workspace_write_check=%s\n' "$?"
sudo -n -l
```

sudo -n 不交互请求密码；失败只说明本次非交互授权未获确认，不等于用户完全没有 sudo。当前不存在的新目录还要检查其最近存在的父目录。

### 9.2 网络、服务、设备

```bash
ip -br address
ip route
ss -lntup
systemctl --failed --no-pager
systemctl list-units --type=service --state=running --no-pager
systemctl list-unit-files --type=service --no-pager
systemctl --user --failed --no-pager
systemctl --user list-units --type=service --no-pager
loginctl show-user ysc -p Linger
timedatectl status
lsusb
ls -l /dev/video* /dev/snd /dev/ttyUSB* /dev/ttyACM*
```

补查匹配到的 transfer/realsense/voa/Nav2/RTSP unit 的 systemctl cat/show、运行用户和 journal 错误；通配符无匹配不代表全部硬件缺失。防火墙规则、完整 socket PID 如需提权，另行确认。从 103 测 120:8554 TCP、RTSP OPTIONS/DESCRIBE（不发控制），再测 DNS/HTTPS 下载源；TCP 成功仍不等于视频帧可解码。不要发送运动 UDP 探测包。

### 9.3 软件与源码输入

```bash
dpkg-query -W 'ros-foxy-*' 'nvidia-l4t-*' 'libnvinfer*' 'cuda-*' 'librealsense*'
python3 --version
python3 -m pip show torch torchvision ultralytics tensorrt numpy opencv-python
command -v colcon tmux gst-inspect-1.0 tegrastats
gst-inspect-1.0 nvv4l2decoder
gst-inspect-1.0 nvvidconv
source /opt/ros/foxy/setup.bash
ros2 pkg prefix nav2_bringup
ros2 pkg prefix foxglove_bridge
ros2 pkg prefix vision_msgs
ros2 interface show vision_msgs/msg/Detection2DArray
ls -lh /home/ysc/lite_cog_ros2/system/map
ls -la /home/ysc/lite_cog_ros2/pipeline/src/data
```

还需核对 Python 实际模块路径/OpenCV 编译信息、GPU/功耗模式、CUDA/TRT 版本、engine 元数据、相机 USB 速率、地图是否匹配现场、业务新增包是否已存在。pip/dpkg 清单不能代替 engine 加载与业务测试。

### 9.4 性能数据（另行批准后测试）

至少补采：整机型号/核数/内存、CPU/GPU 热稳态负载、进程 PSS、磁盘剩余/写速/增长量、视频分辨率码率与断线恢复、ROS 输入频率与时间戳延迟、控制输出周期/抖动、端到端检测/取消/停车延迟、网络丢包/带宽、2 h 路线与8 h耐久日志。动态采样工具如 tegrastats 需限时；真实运动和故障注入必须另设安全条件。

## 10. 交付判断

当前可直接推进的是离线设计、接口修订、数据集和测试准备；**不能批准在 103 上直接执行完整部署或宣称达到性能指标**。恢复可达性并补齐第 9 节数据后，应更新第 2 节、逐行解除第 3/7 节阻塞，再进入受控联调。当前最需要用户确认的是机器人是否在线、电脑应连接的网络，以及 103 是否仍使用 192.168.1.103。
