# Lite3 主机运维、审计与监控

本仓库包含两部分内容：

1. **主机运维与审计文档** —— 覆盖感知/导航侧主机 103 与运动控制/视频侧主机 120，
   目标是让维护人员能够快速定位职责、配置依据、服务入口和操作风险；
2. **`lite3_robot_monitor/`** —— Lite3 状态监控 Web 应用（FastAPI + Vue 3），
   部署在 103 上，同时提供只读状态监控与可选的控制通道。

## 核心特性

- 以主机为边界归档环境、脚本、服务、网络和模块分析；
- 将实测配置与既有审计笔记分开标注，避免把历史状态当作当前事实；
- 提供双主机的角色对比、端口关联和维护注意事项；
- 监控应用支持四种数据源（旁路抓包 / 绑定端口 / ROS 话题桥接 / ROS 内嵌订阅），
  可运行时切换并自动降级自愈；
- 不包含远端源码、密钥、Wi-Fi 凭据、私钥或自动化控制脚本。

## 目录结构

```text
.
├── docs/                       # 主机运维与审计文档
│   ├── hosts/                  # 按主机归档的审计报告
│   │   ├── 103-感知导航主机/    # 感知、定位、导航与 ROS 双栈分析
│   │   └── 120-运动控制主机/    # Lite3 运动控制、视频与网络分析
│   └── operations/             # 跨主机维护说明与跨主机方案
├── lite3_robot_monitor/        # Lite3 监控 Web 应用（可部署到 103）
│   ├── backend/                # FastAPI 后端：数据源 / 解析 / 状态 / REST+WS / 控制
│   ├── frontend/               # Vue 3 + Vite 前端
│   ├── deploy/                 # 103 部署脚本与 systemd 单元
│   ├── docs/                   # 应用侧文档（协议摘录、ROS 数据源部署与排查）
│   ├── tools/                  # 模拟器、冒烟测试、控制报文侦查
│   └── README.md               # 应用入口：架构、协议、部署、接口、配置项
├── script/                     # 早期 Python 状态接收脚本（监控应用的前身）
├── .gitignore                  # 本地编辑器与临时文件忽略规则
├── LICENSE                     # MIT 许可证
└── README.md                   # 仓库入口
```

`docs/` 为纯文档；可构建代码集中在 `lite3_robot_monitor/`，其自带的
`backend/`、`frontend/`、`deploy/`、`tools/` 已按职责分层，故根目录不再另建
`src/`、`tests/`、`config/` 等目录。

## 安装与快速开始

**只读文档**：无需安装运行时依赖，克隆后用任意 Markdown 阅读器即可。

**部署监控应用到 103**：

```bash
# 笔记本侧：构建前端后打包
cd lite3_robot_monitor/frontend && npm run build && cd ..
bash deploy/pack.sh
scp lite3-monitor-deploy.tar.gz ysc@192.168.1.103:/home/test/

# 103 侧：解压并安装（自动建 venv、装依赖、注册 systemd 并启动）
cd /home/test && tar xzf lite3-monitor-deploy.tar.gz
sudo bash lite3_robot_monitor/deploy/install.sh /home/test/monitor
```

完整部署、验证、排错与回滚见 [`lite3_robot_monitor/deploy/README.md`](lite3_robot_monitor/deploy/README.md)。

## 建议按以下顺序阅读

1. [跨主机维护说明](docs/operations/host-maintenance.md)了解当前角色、实测配置和风险；
2. [103 感知导航主机文档](docs/hosts/103-感知导航主机/README.md)了解 ROS、传感器、地图和导航链；
3. [120 运动控制主机文档](docs/hosts/120-运动控制主机/README.md)了解运动控制、RTSP、热点和 SDK 边界；
4. [监控应用 README](lite3_robot_monitor/README.md)了解架构、协议、接口与配置项；
5. [ROS 数据源部署](lite3_robot_monitor/docs/ros_bridge.md)了解话题订阅的两种实现与取舍；
6. [应急蜡烛/火焰检测方案](docs/operations/fire-candle-detection.md)在双主机上落地火焰检测时阅读。

## 使用示例

查看 103 的 ROS 2 传输、导航和地图关系：

```bash
sed -n '1,220p' 'docs/hosts/103-感知导航主机/概览与环境/总体分析.md'
sed -n '1,220p' 'docs/hosts/103-感知导航主机/ROS2软件栈/传输避障与跟踪.md'
```

查看 120 的运动、视频和热点维护边界：

```bash
sed -n '1,220p' 'docs/hosts/120-运动控制主机/运动控制与导航/运动控制部署分析.md'
sed -n '1,220p' 'docs/hosts/120-运动控制主机/网络与连接/网络与无线热点分析.md'
```

这些命令只读取仓库文档；它们不会连接或操作远端主机。

## 贡献指南

1. 新报告按对象归入 `docs/hosts/<IP后缀-中文角色>/` 的对应专题，或 `docs/operations/`；不要在根目录新增业务文档。
2. 每项“当前状态”注明采集时间、采集方式和主机标识；历史笔记需与新实测明确区分。
3. 不提交密码、令牌、私钥、Wi-Fi 密钥、客户数据、完整日志或可直接触发机器人运动的未审计脚本。
4. 新增或移动文件后同步更新所属目录的 `README.md` 和本文件的目录说明。
5. 提交前执行 `git diff --check`，确认链接、相对路径和 Markdown 表格可读。
6. **改动 `lite3_robot_monitor/` 后同步更新其 `README.md`**：新增模块要进目录树，
   新增环境变量要进配置项表，新增数据源/部署方式要在对应章节说明取舍与适用条件。
7. 后端代码保持 **Python 3.8** 兼容（103 为 Ubuntu 20.04），不使用 3.9+ 内置泛型
   与 3.10+ 的 `X | None` 语法，否则 103 上会启动失败。

## 许可证

本仓库采用 [MIT License](LICENSE)。提交内容即表示贡献者有权按该许可证授权其新增内容；涉及第三方软件、厂商二进制、设备固件或外部文档时，应保留其原有许可证和使用限制。



