#!/bin/bash
# ============================================================
# 120主机 无线状态巡检 & 断连自动抓证 看门狗
# 用途：每分钟采样一次 AP(p2p0) 与 STA(wlan0) 状态；
#       一旦检测到热点消失或上联 WiFi 断连，立即抓取前后证据存档。
# 配套：systemd timer（见排查文档 4.6.2）
# ============================================================

LOGDIR=/var/log/wifi_watchdog
mkdir -p "$LOGDIR"
LOG="$LOGDIR/wifi_watch.log"
TS=$(date '+%F %T')

AP_IF=p2p0
STA_IF=wlan0
AP_CON=myap50G
STA_CON=Tenda_FCFA20

# ---------- 状态采集 ----------
ap_state=$(iw dev "$AP_IF" info 2>/dev/null | awk '/type AP/{print "AP_UP"}')
ap_chan=$(iw dev "$AP_IF" info 2>/dev/null | grep -oE 'channel [0-9]+' | head -1)
sta_link=$(iw dev "$STA_IF" link 2>/dev/null | grep -c 'Connected to')
ap_sta_num=$(iw dev "$AP_IF" station dump 2>/dev/null | grep -c '^Station')

echo "$TS ap=${ap_state:-AP_DOWN} ${ap_chan} ap_clients=$ap_sta_num sta_connected=$sta_link \
mem_avail=$(awk '/MemAvailable/{printf "%dMiB",$2/1024}' /proc/meminfo) \
load=$(cut -d' ' -f1 /proc/loadavg) \
temp=$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null)" >> "$LOG"

# ---------- 异常判定：AP 消失 或 STA 断连 ----------
if [ -z "$ap_state" ] || [ "$sta_link" -eq 0 ]; then
    INC="$LOGDIR/incident_$(date '+%Y%m%d_%H%M%S').log"
    {
        echo "===== 无线异常事件 $TS ====="
        echo "ap_state=${ap_state:-AP_DOWN} sta_connected=$sta_link"
        echo "--- iw dev ---";        iw dev
        echo "--- iw link ---";       iw dev "$STA_IF" link
        echo "--- nmcli dev ---";     nmcli -t -f DEVICE,TYPE,STATE,CONNECTION dev status
        echo "--- 近10分钟内核日志 ---"
        journalctl -k --since "10 min ago" --no-pager 2>/dev/null \
            | grep -iE "RTW|HALMAC|8822ce|wlan0|p2p0|pcie|AER" | tail -40
        echo "--- 近10分钟系统日志 ---"
        journalctl --since "10 min ago" --no-pager 2>/dev/null \
            | grep -iE "wpa_supplicant|NetworkManager|dnsmasq" | tail -40
        echo "--- 资源 ---";           free -h; uptime
        echo "--- dnsmasq ---";        ps aux | grep -E "[d]nsmasq"
        echo "--- 温度 ---"
        for f in /sys/class/thermal/thermal_zone*/temp; do echo "$f $(cat $f)"; done
    } >> "$INC" 2>&1
    logger -t wifi_watchdog "WIFI_INCIDENT captured: $INC"

    # ---------- 软件层自愈尝试 ----------
    nmcli con up "$AP_CON"  >/dev/null 2>&1
    nmcli con up "$STA_CON" >/dev/null 2>&1
    sleep 15

    if [ -z "$(iw dev "$AP_IF" info 2>/dev/null | grep 'type AP')" ] \
       || [ "$(iw dev "$STA_IF" link 2>/dev/null | grep -c 'Connected to')" -eq 0 ]; then
        logger -t wifi_watchdog "SOFT_RECOVERY_FAILED: 软件层自愈无效，需人工重启"
        echo "$TS SOFT_RECOVERY_FAILED" >> "$INC"
    else
        logger -t wifi_watchdog "SOFT_RECOVERY_OK"
        echo "$TS SOFT_RECOVERY_OK" >> "$INC"
    fi
fi

# ---------- 日志体积保护（超过 20MB 则轮转） ----------
if [ -f "$LOG" ] && [ "$(stat -c %s "$LOG")" -gt 20971520 ]; then
    STAMP=$(date '+%Y%m%d_%H%M%S')
    mv "$LOG" "$LOG.$STAMP"
    gzip -f "$LOG.$STAMP" 2>/dev/null
fi
