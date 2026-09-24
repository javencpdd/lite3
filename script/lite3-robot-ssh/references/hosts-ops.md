# 103 / 120 运维命令速查

> 所有命令都需在 **放开沙箱** 的 Bash 中执行（否则超时/空输出）。

## 1. 连通性

```bash
# 探活（TCP 22）
for ip in 192.168.1.103 192.168.1.120 192.168.0.197; do
  timeout 3 bash -c "cat < /dev/null > /dev/tcp/$ip/22" 2>/dev/null \
    && echo "$ip OPEN" || echo "$ip TIMEOUT"
done

# 本机网段自检（确认自己是否在 192.168.1.x）
hostname -I
```

## 2. 120 推流全量核验（一次跑完）

```bash
ssh -o BatchMode=yes -o ConnectTimeout=10 lite3-f20-1-120 '
export XDG_RUNTIME_DIR=/run/user/$(id -u)
echo "--- 转发服务 ---"
systemctl --user show rtmp-forward.service -p ActiveState -p MainPID -p NRestarts -p ActiveEnterTimestamp
echo "--- 实际推的流名(以命令行为准) ---"
ps -eo pid,cmd | grep "[g]st-launch-1.0.*rtmpsink" | cut -c1-220
echo "--- RTMP 连接 ---"
ss -tnp | grep "172.31.68.227:1936"
echo "--- 采集服务与源流 ---"
systemctl is-active rtsp_stream.service
ss -lntp | grep -E ":8554|:1935|:8888"
curl -s -o /dev/null -w "HLS=%{http_code}\n" http://127.0.0.1:8888/test/index.m3u8
echo "--- 常驻 ---"
loginctl show-user ysc | grep -i Linger
systemctl --user is-enabled rtmp-forward.service
' 2>&1 | grep -v "post-quantum\|openssh.com\|upgraded"
```

## 3. 120 推流：日志与自停

```bash
# 运行/诊断日志
tail -50 /home/ysc/rtsp_stream/logs/rtmp_forward.log

# 自动关闭触发条件：连续 MAX_CONNECT_FAILURES(默认3) 次 TCP 探测失败 → 退出码 3
# systemd 不再重启（RestartPreventExitStatus=3），单元变 inactive
# 恢复：
systemctl --user start rtmp-forward.service

# 可调参数（用 drop-in，不要直接改单元文件）
systemctl --user edit rtmp-forward.service
# [Service]
# Environment=MAX_CONNECT_FAILURES=5
```

## 4. 120 常用文件

| 路径 | 说明 |
| --- | --- |
| `/home/ysc/rtsp_stream/rtmp_forward.sh` | 转发脚本（含网络不可达保护） |
| `/home/ysc/.config/systemd/user/rtmp-forward.service` | 用户级单元 |
| `/home/ysc/rtsp_stream/logs/rtmp_forward.log` | 运行/诊断日志 |
| `/home/ysc/rtsp_stream/start_stream.sh` | `rtsp_stream.service` 入口 |
| `/home/ysc/rtsp_stream/push_video.sh` | 摄像头 → RTSP |
| `/home/ysc/rtsp_stream/mediamtx` + `mediamtx.yml` | MediaMTX v1.4.2 |
| `*.bak-20260921` | 2026-09-21 改造前的备份 |
| `/var/lib/systemd/linger/ysc` | 常驻标志（root 创建，重启后有效） |

次要/遗留（不参与当前 `/test` 流）：`/home/ysc/rtsp_stream/ZLMediaKit/MediaServer`、
`/home/ysc/.zetton/rtsp_server/`（`streaming.service` 已 disabled）。

## 5. 103 监控 / ROS

```bash
ssh -o BatchMode=yes -o ConnectTimeout=10 lite3-f20-1-103 '
systemctl is-active lite3-monitor2.service lite3-ros-bridge2.service 2>&1
ps -eo pid,cmd | grep "[u]vicorn\|[r]os_bridge" | cut -c1-160
ss -lntup | grep -E ":8002|:43902|:43900"
'
```

多实例靠 TAG 隔离：服务名 `lite3-monitor2`、HTTP `8002`、桥接端口 `43900+TAG`。
ROS 数据源有 `ros_bridge`（独立桥接进程）与 `ros_direct`（内嵌 rclpy）两种实现，
由 `LITE3_ROS_IMPL` 选择；推荐 `LITE3_DATA_SOURCE=auto`。

## 6. 排障决策树（推流不出画面）

1. `systemctl is-active rtsp_stream.service` → 不是 active 就先修采集；
2. HLS `.../test/index.m3u8` 是否 200 → 不是 200 说明源流断了；
3. `systemctl --user show rtmp-forward.service` → 是否 active、`NRestarts` 是否飙升；
4. `ss -tnp | grep 172.31.68.227:1936` → 无 ESTAB 说明没连上服务器；
5. 查日志 `/home/ysc/rtsp_stream/logs/rtmp_forward.log` → 是否触发了自动关闭；
6. `ip route get 172.31.68.227` → 路由是否还走预期上行（历史走 wlan0 / 192.168.0.1）；
7. 最后到 `172.31.68.227` 服务端确认 stream key `live/lite3` 的入流状态。

## 7. 改远端文件的稳妥姿势

1. 本地 `Write` 落盘（避免引号嵌套问题）；
2. `scp` 到远端 `/tmp/`；
3. `cp` 备份原文件；
4. `install -m <权限> /tmp/x.new <目标路径>`；
5. `bash -n` 语法检查；
6. `daemon-reload`（改 unit 时）+ `restart`；
7. 实测核验，再更新 `docs/`。

## 8. 密码 / sudo 速记

```bash
# sudo（密码为单引号字符，用八进制规避引号铁律）
printf "\047\n" | sudo -S loginctl enable-linger ysc

# 无 sshpass/plink/expect 时的 SSH 密码引导
cat > /tmp/wb_askpass.sh <<"XEOF"
#!/bin/sh
printf "\047\n"
XEOF
chmod +x /tmp/wb_askpass.sh
SSH_ASKPASS=/tmp/wb_askpass.sh SSH_ASKPASS_REQUIRE=force DISPLAY=:0 \
  ssh -o StrictHostKeyChecking=accept-new <user>@<host> '<cmd>'
rm -f /tmp/wb_askpass.sh
```
