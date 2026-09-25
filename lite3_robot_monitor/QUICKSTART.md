# QUICKSTART：克隆后直接部署（10 分钟版）

> 面向**第一次接触本项目**的人：从 `git clone` 到浏览器看到机器人状态。
> 完整背景与配置项见 [README.md](README.md)；踩坑与排错见 [note/](note/README.md)。

---

## 0. 你要部署的是什么

在 **103**（Jetson 感知导航主机）上跑一个 Web 服务，读取机器人运动主机 120 发来的
UDP 遥测报文（目的端口 **43897**），解析后推给浏览器面板。

- 安装目录：`/home/test/monitor`
- 对外端口：仅 **8000**（HTTP + WebSocket）
- 关键约束：**只读**，不能干扰 103 上已有的 `transfer_ros2` / ROS / Nav2

---

## 1. 前置条件

| 项 | 要求 |
| --- | --- |
| 笔记本 | 能 `ssh ysc@192.168.1.103`；装有 Node.js（构建前端用） |
| 103 | Ubuntu 20.04 / Python 3.8 / 用户 `ysc`；与 120 网络连通 |
| 机器人 | 已上电并下发状态（**没上电也能先跑通**，见第 5 节模拟器） |

先确认 103 可达：

```bash
ssh ysc@192.168.1.103 "hostname; python3 -V"
```

---

## 2. 笔记本侧：构建 + 打包 + 上传

```bash
git clone <本仓库地址>
cd lite3_robot_monitor

# 构建前端（Jetson 上 npm build 很慢，务必在本地构建）
cd frontend && npm install && npm run build && cd ..

# 打包（自动剔除 node_modules，几百 MB → 几十 KB）
bash deploy/pack.sh

# 上传（/tmp 只是上传中转站，不是安装位置）
scp lite3-monitor-deploy.tar.gz ysc@192.168.1.103:/tmp/
```

> **为什么上传到 `/tmp`？** 它只是**一次性的上传中转站**，不是安装目录 ——
> 真正的安装位置是下一节 `install.sh` 的参数 `/home/test/monitor`。
> 选 `/tmp` 是因为：所有用户都可写（`drwxrwxrwt`，scp 以 `ysc` 身份必成功）、
> 挂在磁盘而非内存盘（103 上为 `/dev/mmcblk1p1`，放大包不占内存）、
> 且装完即可丢弃，不会把每次的压缩包堆进 `/home/test` 工作区。
> 想换成 `/home/test/` 也完全可以（该目录属主就是 `ysc`），
> 但要注意**别覆盖 `/home/test/lite3_robot_monitor`** —— 那是 103 上的源码树，
> 日常增量更新就是直接从它 rsync 到 `/home/test/monitor`（见第 7 节）。

> 如果 `frontend/` 下没有 `dist`，`pack.sh` 会警告"未发现 frontend/dist"——
> 此时装完只有 API、没有页面。**先 `npm run build` 再打包**，顺序不能反。

---

## 3. 103 侧：安装（一条命令）

```bash
ssh ysc@192.168.1.103
cd /tmp && tar xzf lite3-monitor-deploy.tar.gz
sudo bash lite3_robot_monitor/deploy/install.sh /home/test/monitor
```

脚本会自动：建虚拟环境 → 装依赖 → 拷贝后端与前端产物 → **抓包自检** → 注册 systemd 并启动。
它**不会**改动 `transfer_ros2`、`jy_exe` 及任何现有配置。

内网 pip 源较慢时：

```bash
PIP_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple sudo -E bash lite3_robot_monitor/deploy/install.sh /home/test/monitor
```

---

## 4. 验证

```bash
curl -s http://127.0.0.1:8000/api/status | python3 -m json.tool
```

看三个字段：

| 字段 | 期望 | 不对怎么办 |
| --- | --- | --- |
| `udp_mode` | `sniff` | 是 `bind` 说明抓包降级了 → 见下方"常见问题" |
| `connected` | `true` | 一直 false → 见下方"常见问题" |
| `packets_parsed` | 持续增长 | 不涨说明没收到或没解析出报文 |

然后笔记本浏览器打开 **http://192.168.1.103:8000**。

---

## 5. 机器人没上电？用模拟器先跑通

```bash
cd /home/test/monitor
/home/test/monitor/.venv/bin/python tools/mock_sender.py     # 向 127.0.0.1:43897 发 10Hz 数据
```

模拟器能跑通 ⇒ 解析链路 OK；连真机还不行 ⇒ 问题在链路或网卡，不在解析。

---

## 6. 三个最常见的"装完不对"

按顺序排查，**第一步一定是 tcpdump**（它能一句话把问题切成两半）：

```bash
sudo tcpdump -i any -nn udp dst port 43897 -c 5
```

- **有输出** → 数据到了 103，问题在 Monitor
- **无输出** → 数据没到 103，去查 120 侧 `jy_exe/conf/network.toml`

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| `udp_mode` 是 `bind` | 抓包降级（多为权限） | 确认 unit 有 `AmbientCapabilities=CAP_NET_RAW`；`journalctl -u lite3-monitor -n 50` |
| `connected` 一直 false | 抓错网卡 / 机器人没开机 / 数据没到 | 设 `LITE3_UDP_IFACE` 为连 `192.168.1.120` 的那张网卡 |
| 浏览器打不开 | 防火墙 / 服务没起 | `systemctl status lite3-monitor`；`sudo ufw allow 8000/tcp` |

完整排错见 [note/04-运行调试与常见报错.md](note/04-运行调试与常见报错.md)。

---

## 7. 改完代码怎么更新（别重跑 install.sh）

日常改后端**不要**用 `install.sh`（会重建 venv、重装依赖，还可能删掉前端）：

```bash
# 103 本机
sudo rsync -av --exclude '__pycache__' --exclude '*.pyc' \
  /home/test/lite3_robot_monitor/backend/ /home/test/monitor/backend/
sudo find /home/test/monitor/backend -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null
sudo systemctl restart lite3-monitor        # config 是 frozen dataclass，不重启不生效
```

只有这 4 种情况才重跑 `install.sh`：改了 `requirements.txt`、改了 `deploy/*.service`、
要部署新构建的 `frontend/dist`、首次安装或换目录。

---

## 8. 卸载 / 回滚

```bash
sudo systemctl stop lite3-monitor
sudo systemctl disable lite3-monitor
sudo rm /etc/systemd/system/lite3-monitor.service
sudo systemctl daemon-reload
sudo rm -rf /home/test/monitor
```

现有 ROS 服务与 120 侧配置全程未被修改，回滚后回到部署前状态。

---

## 9. 两条安全底线

1. **绝不 bind 43897**。该端口已被 `transfer_ros2` 占用，抢走会导致
   `/imu/data`、`/leg_odom2` 断流、Nav2 丢失本体里程计。监听一律走 `sniff`。
2. **控制通道默认关闭**（`LITE3_CTRL_ENABLED=false`）。它直连 120 的闭源 `jy_exe`，
   **绕过 VOA 安全层**（限速、避障、防撞均不生效）。启用前务必读
   [README.md 第十二章](README.md)，并在开阔场地、机器人架空或有人持遥控器待命时使用。
