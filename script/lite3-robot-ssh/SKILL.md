---
name: lite3-robot-ssh
description: 用本地 SSH 连接并运维特种机器狗项目的局域网主机（lite3-f20-1-103 感知导航主机、lite3-f20-1-120 运动控制主机）。当用户要连 103/120、远程执行命令、查服务状态、拉日志、管理 RTSP→RTMP 推流（rtmp-forward / rtsp_stream / stream key lite3）、查 ROS 桥接或监控服务时使用。含沙箱放行、sudo 免交互、引号转义、常驻判定等必备前置知识。
agent_created: true
---

# Lite3 机器人主机 SSH 远程运维

从本机（运行 WorkBuddy 的 PC）用 SSH 直连局域网内的机器人主机并远程操作。
**先连上机器拿到真实状态，再交给领域专家分析**——不要用文档里的旧结论代替实测。

## 前置条件（不满足会白跑）

1. **本机必须接入目标网段**
   103/120 位于 `192.168.1.x`；120 另挂 `192.168.0.197`（与部分办公网同段）。
   自检本机地址：`hostname -I`（Windows 用 ipconfig）。
   若本机不在 `192.168.1.x` 且无路由，SSH 一律 `Connection timed out`。
   快速探活：`timeout 3 bash -c "cat < /dev/null > /dev/tcp/<IP>/22"`。

2. **Bash 出网默认被沙箱拦截**
   每条 ssh 命令都必须带 `dangerouslyDisableSandbox: true`，
   否则表现为静默超时或**空输出**（很容易误判为"命令没跑"）。

3. **SSH 走密钥，日常无需密码**
   `~/.ssh/config` 已配置 103/120/0-197，User 均为 `ysc`（103/120）。
   若某台报 `Permission denied (publickey,password)`，说明该机未部署本机公钥 → 见「密码引导」。

4. **引号铁律**
   远程命令用单引号包裹时，**命令体内不能出现字面单引号**，否则提前闭合并报
   `syntax error near unexpected token`。需要单引号请用八进制：`printf "\047\n"`。

## 主机清单

| 别名 | IP | 用户 | 定位 | 要点 |
| --- | --- | --- | --- | --- |
| `lite3-f20-1-103` | 192.168.1.103 | ysc | 感知/导航主机 | hostname=`lite`，Jetson/Tegra，内核 5.10.120-tegra，aarch64，6 核 / 6.7G；跑监控与 ROS 桥接 |
| `lite3-f20-1-120` | 192.168.1.120（另 192.168.0.197 / 192.168.137.120） | ysc | 运动控制主机 | hostname=`ysc`，内核 5.10.198，8 核 / 3.8G，多网卡；跑摄像头采集 + RTMP 推流 |

## 标准命令模板

```bash
# 系统级操作
ssh -o BatchMode=yes -o ConnectTimeout=10 <别名> '<命令>'

# 用户级 systemd（120 的推流属于此类）必须先导出运行时目录
export XDG_RUNTIME_DIR=/run/user/$(id -u)
systemctl --user ...
```

## 常用场景

### 连通性自检（每次开工先跑）

```bash
for h in lite3-f20-1-103 lite3-f20-1-120; do
  echo "=== $h ==="
  ssh -o BatchMode=yes -o ConnectTimeout=10 $h 'hostname; whoami; uname -r; uptime -p'
done
```

### 120：RTSP → RTMP 推流

链路：
`/dev/video0` → `rtsp_stream.service`(MediaMTX) → `rtsp://127.0.0.1:8554/test`
→ `rtmp-forward.service`(GStreamer) → `rtmp://172.31.68.227:1936/live/lite3`

关键文件：
- `/home/ysc/rtsp_stream/rtmp_forward.sh`（转发脚本）
- `/home/ysc/.config/systemd/user/rtmp-forward.service`（用户级单元）
- `/home/ysc/rtsp_stream/logs/rtmp_forward.log`（运行与诊断日志）

核验三件套：
```bash
systemctl --user show rtmp-forward.service -p ActiveState -p MainPID -p NRestarts -p ActiveEnterTimestamp
ss -tnp | grep 172.31.68.227:1936
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8888/test/index.m3u8
```

- **常驻判定**：`loginctl show-user ysc` 需为 `Linger=yes`。
  判据是新 SSH 会话里 `ActiveEnterTimestamp` **不刷新**；若每次都变新值，说明没开 linger，
  SSH 一断推流就停（`sudo loginctl enable-linger ysc`）。
- **自动关闭**：连续 `MAX_CONNECT_FAILURES`（默认 3）次连不上 `172.31.68.227:1936`
  → 写诊断日志 → 退出码 3 → `RestartPreventExitStatus=3` 使 systemd 不再重启。
  网络恢复后 `systemctl --user start rtmp-forward.service` 即可（单元是 inactive，无需 reset-failed）。
- **改流名**：改脚本 `target_url` 一行 → `bash -n` 检查 → `systemctl --user restart`；
   **不要把 `live=1` 写进变量值**（脚本会自动附加）。

### 103 出网 NAT（103 → 外网 / 172.31.68.227 全靠 120 转发）

- 103 默认路由 `via 192.168.1.120`，出网流量必须由 120 做 MASQUERADE。
- **120 的 NAT 规则是易失的**，开机由 `host.service → /home/ysc/host/host_start2.sh` 追加。
  截至 2026-09-23，脚本里只有 `192.168.2.0/24`（eth1）与 `192.168.137.0/24`（wlan0），
  **没有 103 的 192.168.1.0/24** → **120 一重启，103 就断网**
  （表现为 103 ping/TCP 全不通、RTMP 推流卡 SYN-SENT、`live/lite3_yolo` 从 SRS 消失）。
  `/etc/iptables/rules.v4` 里虽有该规则，但机器上**没有 netfilter-persistent，没人恢复它**。
- **判定特征**：120 `ping 172.31.68.227` 通、103 不通 → 九成是这条 NAT 没了。
  先查再排查别的：103 `ping 172.31.68.227`；120 上 `sudo iptables -t nat -S POSTROUTING | grep 192.168.1.0/24`。
- 修复（120 上执行，立即生效）：
  ```bash
  printf "\047\n" | sudo -S iptables -t nat -A POSTROUTING -s 192.168.1.0/24 -o wlan0 -j MASQUERADE
  ```
- **持久化**：2026-09-23 已把该行追加进 `/home/ysc/host/host_start2.sh`
  （备份 `host_start2.sh.bak-20260923`），开机随 host.service 自动恢复。
  若未来又出现 103 断网，优先检查该脚本是否被改动/还原。
- 注意 120 的 `host_start2.sh` 开头有等待 `p2p0` 的循环 → 规则在开机后**延迟一段时间**才生效。

### 120：无线（WiFi / 热点）

- 芯片 **Realtek RTL8822CE**（PCIe `0002:21:00.0`），驱动 `rtl88x2ce`（模块名 `8822ce`，
  版本 `5.14.0.3-...20230207`，**厂商 out-of-tree，非主线 rtw88**）。
- **单射频并发 AP+STA**：`wlan0`=STA、`p2p0`=AP，**同属 phy#0 且被强制同信道**。
  热点 profile `myap50G` 配 `band=a/ch36`，但因 STA 在 2.4G，**实际跑 ch13(2472MHz)**。
  热点是 **NetworkManager 内置共享**（NM 拉起 dnsmasq 监听 `192.168.2.1`），**不是独立 hostapd**。
- 排障文档：`docs/hosts/120-运动控制主机/网络与连接/热点消失与WiFi断连排查说明.md`。

### 103：监控与 ROS 桥接

相关服务：`lite3-monitor*.service`、`lite3-ros-bridge*.service`（TAG 机制，多实例端口 43900+TAG / HTTP 8002 等）。
详细背景与历史变更见项目 `docs/hosts/120-运动控制主机/`、`docs/ros_bridge.md`、`docs/ros_troubleshooting.md`。

## 密码与 sudo

- SSH 已密钥化，**日常不需要密码**。
- 需要 sudo 时（如 `loginctl enable-linger`、重启系统级服务）：
  ```bash
  printf "\047\n" | sudo -S <命令>
  ```
  `\047` 即单引号字符（当前 ysc 密码就是该字符；也是规避引号铁律的写法）。
- 环境里**没有** `sshpass` / `plink` / `expect`。若必须用密码做 SSH 登录，
  用 askpass 方案：写脚本 `printf "\047\n"` → `chmod +x` →
  `SSH_ASKPASS=<脚本> SSH_ASKPASS_REQUIRE=force DISPLAY=:0 ssh ...`，用完即删。
- ⚠️ 该密码极弱。建议改强密码，或配 sudoers 的 `NOPASSWD` 白名单；
  **不要把密码写进仓库或交付文档**。

## 坑位清单（都是实测踩过的）

1. **沙箱**：不放行 → 超时/空输出，最容易被误判成"机器没开"。
2. **引号**：单引号包裹的远程命令体内禁止出现字面单引号。
3. **gst 双管线**：`pgrep -f gst-launch-1.0` 在 120 上会同时命中
   **摄像头采集**（v4l2src→RTSP）和 **RTMP 转发** 两条管线，
   判断推流是否存活必须先看完整命令行再取 PID，别只取第一个。
4. **HLS 探测**：必须带 `index.m3u8`，只探 `/test/` 会返回 404，别误判源流挂了。
5. **用户级 systemd 依赖会话**：无 linger 时服务随 SSH 会话生灭，
   表现为 `ActiveEnterTimestamp` 每次刷新、`NRestarts` 却始终 0（不是重启，是全新启动）。
6. **改 unit 后**必须 `systemctl --user daemon-reload` + restart 才生效。
7. **别只信文档**：当前推的流名以进程命令行/脚本为准。
   历史上 `robotdog` → `lite3` 的变更导致文档滞后了十几天。
8. **写远端文件**：优先本地 `Write` 落盘再 `scp` 上去（规避引号问题），
   覆盖前先 `cp` 备份；随后 `bash -n` 做语法检查。
9. **长任务别跑前台**：前台 ssh 超过几十秒可能被掐断（返回空输出，极易误判成"命令没跑"），
   且 **`/tmp` 下的日志会被清**。用
   `setsid nohup <cmd> > <工程内 logs/>/x.log 2>&1 < /dev/null &` 脱离会话后分批轮询。
10. **ROS2 CLI 输出会缓冲**：`ros2 ... > file` 后被 `timeout`/SIGTERM 杀掉会丢缓冲区→文件空白。
    用 `python3 -u /opt/ros/foxy/bin/ros2 topic hz <topic>`（`stdbuf -oL` 亦可）。
    另注意 Foxy 的 `ros2 topic hz` 无 `--qos-*` 参数、固定 RELIABLE 订阅，
    BEST_EFFORT 发布端的话题会"可见但收不到"。
11. **本机 known_hosts 报 `hostfile_replace_entries ... Permission denied`** 不影响登录，忽略即可。
12. **103/120 的 journald 是 volatile**：`/var/log/journal` 不存在，journald 默认 `auto` 退化为内存盘，
    **重启即全部清空**。查历史只能靠 rsyslog 落盘的 `/var/log/syslog*`、`/var/log/kern.log*`、
    `/var/log/dmesg*`（有轮转、跨重启保留）。凡是"重启就好了"的故障，**先开持久化再等复现**，
    否则恢复动作本身会删掉证据（已踩）。
13. **ysc 不在 `adm` 组**：`/var/log/syslog` 是 `640 root:adm`，直接 `cat`/`grep` 会被拒绝，
    **读日志一律 sudo**；`journalctl --list-boots` 同样报权限不足。
    远程命令形如 `printf "\047\n" | sudo -S bash -c "..."`（命令体内避免字面单引号）。

## 与其他专家配合的方式

1. 用本 skill 连上 103/120，取**真实**状态、配置、日志（不要凭记忆或旧文档）；
2. 把原始数据（进程列表、服务状态、ss 连接、日志片段、配置文件内容）交给对应领域专家分析；
3. 专家给出结论后，再由本 skill 执行改动，并**立即实测核验**；
4. 改动落定后同步更新 `docs/` 下对应文档，保证文档与实际一致。

更详细的命令速查见 `references/hosts-ops.md`。
