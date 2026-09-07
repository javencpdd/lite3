# host-120：运动控制、视频与网络侧

本目录保存 IP 后缀为 120 的 Lite3 运动主机审计材料。文档实测时的实际 hostname 为 `ysc`，设备树标识为 Rockchip RK3588 WEB-S3588-YSC-V10；与 103 的感知/ROS 主机通过 `192.168.1.0/24` 业务网关联。

## 文件清单

| 文件 | 内容 | 使用方式 |
| --- | --- | --- |
| `YSC_HOME_MODULES_OVERVIEW.md` | `/home/ysc` 总体模块、运行入口和风险总览 | 首次了解本机时优先阅读。 |
| `YSC_JY_EXE_ANALYSIS.md` | `jy_exe` 运动控制部署、脚本和配置边界 | 维护运动控制服务前阅读；其中脚本可能影响实体设备。 |
| `YSC_RTSP_STREAM_ANALYSIS.md` | 当前 RTSP 发布链、脚本和 MediaMTX 配置 | 排查摄像头、推流或端口时阅读。 |
| `RTSP_CODE_ANALYSIS.md` | RTSP 协议、MediaMTX 运行与配置细节 | 需要协议级排障时阅读。 |
| `LITE3_SLAM_NAVIGATION_CODE_ANALYSIS.md` | 运动侧 SDK、闭源导航接入边界与感知主机线索 | 区分运动控制与 SLAM/导航职责时阅读。 |
| `USER_F20_NETWORK_HOTSPOT_ANALYSIS.md` | Wi-Fi 上行、NetworkManager shared/NAT 热点和路由 | 修改网络前必须阅读，并准备本地回退通道。 |
| `USER_YSC_ACCOUNT_AND_FILESYSTEM_ANALYSIS.md` | `user` 与 `ysc` 账户、家目录和运行目录关系 | 清理或迁移文件前阅读。 |
| `YSC_MODULE_ANALYSIS.md` | Wi-Fi 模块、设备树和部署脚本 | 含 boot 分区写入风险，仅在受控维护时阅读。 |
| `YSC_SLAVE_ANALYSIS.md` | 从机 Wi-Fi 管理脚本 | 调整 `p2p0` 前阅读。 |
| `YSC_QIRUI_ANALYSIS.md` | 离线依赖库集合 | 判断库目录是否可清理时阅读。 |

## 使用方式

1. 日常状态先看 `YSC_HOME_MODULES_OVERVIEW.md` 和上级跨主机维护说明；
2. 变更服务、网络、CAN、策略、boot 分区或热点前，阅读对应专题并记录现状；
3. 本目录记录的二进制、模型、SDK、密钥和厂商制品边界不构成修改或重新分发授权。
