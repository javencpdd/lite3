# SCAN-Planner 部署到 103 主机：评估结论与方案

> 目标仓库：https://github.com/wuyi2121/SCAN-Planner （main 分支，ROS 1 版）
> 目标主机：103（lite3-f20-1-103 / 192.168.1.103，用户 ysc）
> 作业空间：`/home/test/scan_planner`
> 文档状态：**已执行**（已 clone、已编译通过、仿真闭环跑通、Lite3 参数适配已完成并通过双次复跑）
> 编写时间：2026-09-21　最后更新：2026-09-21 03:40

## 〇、当前进度（一眼看完）

| 阶段 | 状态 | 说明 |
|---|---|---|
| 环境准备（代理 / apt 源 / ROS1 隔离） | ✅ 完成 | 清华 403 源已换 `ports.ubuntu.com`；代理可用 |
| 拉取源码 | ✅ 完成 | 走代理 clone，commit `348e8a5` |
| 编译（`-j2`，约 14 min） | ✅ 通过 | 0 错误，9 个可执行文件 + 2 个自定义 msg |
| 仿真冒烟（navi_mode=1，lidar） | ✅ 通过 | 起点 (−19,1) → 目标 (5,0)，约 24 m，正常抵达 |
| ros1_bridge 安装 | ✅ 完成 | apt `ros-foxy-ros1-bridge 0.9.7-1focal`（arm64） |
| 桥接方案修正 | ✅ 完成 | **只需桥 1 个 `/cmd_vel`**，点云/里程计原生同域 |
| Lite3 模型替换（官方 URDF + 网格） | ✅ 完成 | 新增 `lite3_description` 包 |
| Lite3 参数适配 + A/B 回归 | ✅ 完成 | 见 `05-避坑事项.md` 第 8 章，双次复跑通过 |
| FAST-LIO 话题适配（`/LIO/*`） | ✅ 完成 | FAST-LIO 实际发 `/Odometry` + `/cloud_registered_body`，已用 `lio_relay.launch` 补齐（第 10 章），假数据源端到端验证通过 |
| 真机本体接入 | ⏳ 未开始 | 见 `05-避坑事项.md` 第 9 章，6 步清单 |
| **真机接入** | ⏳ 未开始 | 见 `05-避坑事项.md` 第 9 章待办清单 |

---

## 一、结论（先行）

**结论：可以部署，且兼容性风险低。建议按"先离线落地 + 仿真冒烟，再真机接入"两阶段推进。**

判定依据一句话概括：SCAN-Planner main 分支要求的运行环境是 **Ubuntu 20.04 + ROS Noetic + Eigen3/PCL/OpenCV/Armadillo**，而 103 实测恰好是 **Ubuntu 20.04.6 + ROS Noetic（347 个包）+ PCL 1.10 + Eigen 3.3.7 + OpenCV 4.2 + Armadillo 9.8**，编译工具链（gcc 9.4 / cmake 3.16）与全部 catkin 依赖均已就位，源码中也没有 x86 专属指令或 CUDA 硬依赖，aarch64 上不存在架构阻断项。

但有三条必须提前接受的现实约束：

| # | 约束 | 影响 | 处置 |
|---|---|---|---|
| C1 | **103 直连 GitHub 不通**（可解析但 TCP 超时），国内镜像/ROS/NVIDIA 源正常 | 裸 `git clone https://github.com/...` 会卡死 | 走本机代理 `http://192.168.2.47:7897`（**实测 clone 成功，4m29s**）；或 `gh-proxy.com` 镜像；离线 scp 仅作兜底 |
| C2 | **103 默认跑 ROS 2 Foxy**（`transfer_ros2.service` 常驻），而 SCAN-Planner 主分支是 ROS 1 | 环境串味、话题不通 | 编译/运行前用专用脚本只 source Noetic；真机数据用 `ros1_bridge` 跨栈桥接 |
| C3 | **SCAN-Planner 默认参数与执行器面向 Unitree Go2**，103 载的是 Lite3 | 尺寸/速度/步态接口不匹配 | 阶段二改 `advanced_param.xml` 的机体包络与速度参数，并用 `/cmd_vel` 对接 Lite3 控制口 |

分级建议：

- **阶段一（可行、低风险、建议立即做）**：离线落地源码 → `catkin_make` 编译 → 用自带仿真器（mockamap + pcl_render_node）跑通 navi_mode 1/2/3。此阶段**不碰真机、不改主机现有 ROS 2 服务**。
- **阶段二（可行、中风险）**：接真机。需要 ros1_bridge（foxy↔noetic）或等效中继，把 faster_lio 的里程计与雷达点云喂给规划器，并把 `/cmd_vel` 回传给 Lite3。
- **不建议**：使用 `ros2-community` 分支 —— 该分支明确要求 **Ubuntu 22.04 + ROS 2 Humble + C++17**，与 103 的 20.04/Foxy 不匹配。

---

## 二、文档索引

| 文件 | 内容 |
|---|---|
| `01-兼容性评估.md` | 项目依赖清单、103 实测环境、逐项对照表、风险登记与降级方案 |
| `02-部署执行方案.md` | 准备工作、作业空间目录设计、离线传输、编译、三级验证、真机接入方案、参数适配清单 |
| `03-命令清单与回滚.md` | 可直接复制执行的命令集（含代理配置 A0、打包/传输/编译/验证）、回滚与清理步骤 |
| `04-阶段一执行报告.md` | 阶段一落地结果：编译产物、仿真冒烟数据、ros1_bridge 需求修正说明 |
| **`05-避坑事项.md`** | ⭐ **踩坑手册**：网络/ ROS1 隔离/ 编译/ 桥接/ Shell 操作/ 仿真判读/ Lite3 参数 全链路坑点与对策，含 A/B 实测数据表。**开工前先看这一份** |

---

## 三、一页速览：关键实测数据

### 103 主机（实测，非文档推断）

```
hostname      : lite
型号          : NVIDIA Jetson Xavier NX Developer Kit
内核 / 架构   : 5.10.120-tegra / aarch64
JetPack       : R35.4.1（CUDA 11.4 在 /usr/local/cuda-11.4）
系统          : Ubuntu 20.04.6 LTS (focal)
CPU / 内存    : 6 核 / 约 6.7 GiB，swap 3 GiB
磁盘          : / 共 117G，已用 79G，可用 33G
编译链        : gcc/g++ 9.4.0，cmake 3.16.3，git 2.25.1，Python 3.8.10
ROS           : /opt/ros/noetic（347 个包）+ /opt/ros/foxy；~/.bashrc 默认 source foxy
库            : Eigen 3.3.7 / PCL 1.10.0 / OpenCV 4.2.0 / Armadillo 9.800.4 / Boost(filesystem,iostreams,program_options,serialization,system) / libglew-dev 2.1.0
网络          : IPv4 出网可用（默认路由 via 192.168.1.120）；GitHub 直连超时，
                国内镜像/ROS 源/NVIDIA 源正常；走 192.168.2.47:7897 代理可直连 GitHub
常驻服务      : transfer_ros2.service（ROS 2 Foxy）、lite3-monitor.service
现有资源      : /home/ysc/lite_cog_ros2/{driver(mid360_ws,leishen_ws,orbbec_ws,realsense_ws), slam(faster_lio,pcd2grid,octomap), nav(dr_nav2,hdl_*), transfer}
作业目录      : /home/test/scan_planner 已存在且为空，属主 ysc:ysc，可写
```

### SCAN-Planner（main 分支，源码实测）

```
许可证        : Apache-2.0
构建系统      : catkin_make（ROS 1，无顶层 CMakeLists，仓库根即工作空间根）
官方测试环境  : Ubuntu 20.04 + ROS Noetic
源码规模      : src 62 MB（.git 另 35 MB，525 个文件）
ROS 包数量    : 12 个
  规划器      : plan_manage / plan_env / path_searching / bspline_opt / traj_utils
  仿真        : local_sensing / map_generator / mockamap
  仿真工具    : go2_description / odom_visualization / pose_utils / waypoint_generator
硬依赖        : Eigen3 ≥3、PCL ≥1.7、OpenCV、catkin 组件
              （roscpp/rospy/std_msgs/geometry_msgs/nav_msgs/sensor_msgs/
                visualization_msgs/tf/message_filters/message_generation/
                cv_bridge/pcl_ros/pcl_conversions/cmake_modules/roslaunch）
仅仿真需要    : Armadillo（pose_utils）、OpenMP、Boost
仅 GPU 版需要 : GLEW + glfw3 + 桌面 OpenGL（默认 OFF）
架构相关      : 无 SSE/AVX 内联汇编；无 CUDA 代码；唯一 x86_64 资产是 third_party 预编译 GLFW（USE_GPU=ON 且系统无 glfw 时才可能用到）
运行期资源    : 纯 CPU 算法，无 GPU 推理
```

---

## 四、网络复测结论（2026-09-21 01:47–18:03 二次实测，推翻初次结论）

初次评估（01:24）判定"103 无外网"，复测发现**网络状态是波动的**，当前已恢复且明显更好：

| 测试项 | 结果 |
|---|---|
| 默认路由 | `default via 192.168.1.120 dev eth0`（103 的上联是 120 主机） |
| DNS | 正常（223.5.5.5 / 119.29.29.29），github.com 等均可解析 |
| IPv4 | **通**（ustc 镜像 0.16s、tuna 0.26s） |
| IPv6 | 不通（无全局 IPv6 地址、无 IPv6 默认路由） |
| GitHub 直连 | ❌ 超时（`20.205.243.166:443` 连不上） |
| GitHub 镜像 | ✅ `gh-proxy.com`、`ghproxy.net` 的 git 协议可用（返回正确 commit `348e8a5`） |
| **代理 192.168.2.47:7897** | ✅ **可用**。103→代理 ping 1.8ms，HTTP 代理访问 GitHub `200 / 1.8s`；**实测 clone 成功，4m29s，122M，commit `348e8a5` 校验一致** |
| apt | ROS 源(`packages.ros.org`)、NVIDIA(`repo.download.nvidia.com`)、`ports.ubuntu.com` 均 Hit；清华 `ubuntu-ports` 返回 403（该源异常，与代理无关） |
| **ros-foxy-ros1-bridge** | ✅ **可直接 apt 安装**（候选 `0.9.7-1focal`，arm64，来自 ROS 源）—— 阶段二桥接难点大幅降低 |

**结论：可以而且应该用代理加速。** 部署路径从"离线 scp"升级为"103 上直接走代理 clone"，省去本机打包传输环节。

---

## 五、下一步（阶段二：真机接入）

已完成：clone / apt 源 / 编译 / ros1_bridge / Lite3 尺寸参数 / FAST-LIO 话题适配。
当前只剩真机接入，**详细步骤见 `05-避坑事项.md` 第 9 章**，摘要：

```bash
# ① 雷达（注意: c16.yaml 是镭神 C16, 配 start_lslidar.sh, 不是 start_livox.sh）
cd /home/ysc/lite_cog/system/scripts/lidar && bash start_lslidar.sh
# ② SLAM（输出 /Odometry 与 /cloud_registered_body, 不是 /LIO/*）
bash /home/ysc/lite_cog/system/scripts/slam/start_slam.sh
# ③ 补出 /LIO/* 三话题
roslaunch scan_planner lio_relay.launch
# ④ SCAN-Planner 真机模式（先不接机器人）
roslaunch scan_planner run.launch is_real_world:=true navi_mode:=1 \
  sensor_type:=lidar need_extrinsic:=false
# ⑤ 只桥一个 Twist
ros2 run ros1_bridge parameter_bridge /scan_planner/cmd_vel@geometry_msgs/msg/Twist@geometry_msgs/Twist
# ⑥ 首次上电：四腿离地 + 限速，再落地
```

⚠️ 上述 6 步中的**真机部分尚未执行**；第 ①～④ 的数据链路已用假数据源端到端验证通过。

---

## 六、采纳的 Lite3 参数（回归通过）

```
double_cylinder_radius        0.18   # 包络 0.60 m × 0.36 m（源自官方 URDF 实测）
double_cylinder_offset        0.12
body_height                   0.30   # 仅 navi_mode=3 生效，navi_mode=1 下为空操作
max_vel                       0.75   # 开阔场地再显式覆盖到 1.0
closed_loop_controller/max_vy    0.50
closed_loop_controller/max_vyaw   1.00   # 受源码 kMaxVYawLimit 钳位，最高只能 1.0
```

对照组（`run.launch`）：`robot_pkg:=go2_description` 可随时切回 Go2 模型。
