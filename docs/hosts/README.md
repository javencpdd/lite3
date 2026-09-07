# 主机审计文档

本目录按受审计主机分组保存只读分析报告。目录名使用稳定的 `host-<IP 后缀>` 形式；文档内会同时记录实际 hostname 和 MCP 连接别名，避免把逻辑名称与机器名称混淆。

## 文件与子目录

| 路径 | 主机定位 | 使用方式 |
| --- | --- | --- |
| [`host-103/`](host-103/README.md) | 实际 hostname 为 `lite` 的 NVIDIA/ROS 感知、定位与导航侧 | 查询 ROS 1/ROS 2、传感器、地图、Transfer 或导航脚本。 |
| [`host-120/`](host-120/README.md) | 实际 hostname 为 `ysc` 的 Rockchip/Lite3 运动、视频与网络侧 | 查询 `jy_exe`、RTSP、视觉跟随、热点及底层部署资料。 |

## 使用方式

1. 先从目标主机的 `README.md` 选择专题报告；
2. 将报告中的采集时间与当前实测结果对照；
3. 涉及两机端口、地址或控制链时，再阅读 [`../operations/host-maintenance.md`](../operations/host-maintenance.md)。

不要把文档中的历史 service 状态、网络路由或硬编码值直接当作执行命令的依据。
