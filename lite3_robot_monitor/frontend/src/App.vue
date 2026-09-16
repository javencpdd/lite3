<script setup>
/**
 * App.vue
 * Lite3 Robot Monitor 主面板。
 *
 * 布局自上而下：
 *   顶部标题栏 + 服务概要
 *   → RobotStatus  机器人综合状态
 *   → IMUChart / Position  姿态与位姿、速度
 *   → JointPanel   12 个关节
 *   → RawPacket    原始报文
 */
import { computed } from 'vue'
import RobotStatus from './components/RobotStatus.vue'
import IMUChart from './components/IMUChart.vue'
import JointPanel from './components/JointPanel.vue'
import RawPacket from './components/RawPacket.vue'
import { useRobotState } from './composables/useRobotState.js'
import { clearRaw } from './api/index.js'

const {
  robotState,
  jointAngle,
  jointVelocity,
  others,
  history,
  wsStatus,
  serviceStatus,
  rawPackets,
  connected,
  refreshRaw
} = useRobotState()

/** 顶部标题栏右侧的服务概要 */
const summary = computed(() => {
  const s = serviceStatus.value
  if (!s) return []
  return [
    { label: 'UDP', value: `${s.udp_host || '0.0.0.0'}:${s.udp_port}` },
    { label: '推送频率', value: `${s.push_hz} Hz` },
    { label: '已接收', value: s.packets_received },
    { label: 'WS 连接', value: s.ws_clients }
  ]
})

/** 世界坐标系位置（x, y, yaw） */
const position = computed(() => robotState.value?.position || { x: 0, y: 0, yaw: 0 })
/** 世界坐标系速度 */
const velocity = computed(() => robotState.value?.velocity || { x: 0, y: 0, yaw: 0 })
/** 机体系速度 */
const velocityBody = computed(() => robotState.value?.velocity_body || { x: 0, y: 0, yaw: 0 })
/** IMU 加速度 */
const acc = computed(() => robotState.value?.imu || {})

/** 通用数值格式化 */
const fmt = (v, digits = 3) => (typeof v === 'number' ? v.toFixed(digits) : '--')

async function handleClear() {
  try {
    await clearRaw()
    await refreshRaw()
  } catch (err) {
    console.warn('[App] 清空原始报文失败', err)
  }
}
</script>

<template>
  <div class="page">
    <header class="topbar">
      <div class="brand">
        <h1>Lite3 Robot Monitor</h1>
        <p>四足机器人 UDP 状态实时监控面板</p>
      </div>
      <div class="summary">
        <div v-for="item in summary" :key="item.label" class="summary-item">
          <span class="k">{{ item.label }}</span>
          <span class="v mono">{{ item.value }}</span>
        </div>
        <div class="conn" :class="connected() ? 'on' : 'off'">
          <span class="dot" />
          {{ connected() ? 'Online' : 'Offline' }}
        </div>
      </div>
    </header>

    <main class="layout">
      <RobotStatus :state="robotState" :status="serviceStatus" :ws-status="wsStatus" />

      <div class="row">
        <IMUChart :history="history" />

        <section class="card metrics">
          <div class="card-title">
            <span>Position &amp; Velocity</span>
            <span class="sub">世界系 / 机体系</span>
          </div>

          <div class="metric-group">
            <div class="group-title">Position (world)</div>
            <div class="metric-row">
              <div class="metric"><span>X</span><b class="mono">{{ fmt(position.x) }} m</b></div>
              <div class="metric"><span>Y</span><b class="mono">{{ fmt(position.y) }} m</b></div>
              <div class="metric"><span>Yaw</span><b class="mono">{{ fmt(position.yaw) }} rad</b></div>
            </div>
          </div>

          <div class="metric-group">
            <div class="group-title">Velocity (world)</div>
            <div class="metric-row">
              <div class="metric"><span>Vx</span><b class="mono">{{ fmt(velocity.x) }} m/s</b></div>
              <div class="metric"><span>Vy</span><b class="mono">{{ fmt(velocity.y) }} m/s</b></div>
              <div class="metric"><span>ω</span><b class="mono">{{ fmt(velocity.yaw) }} rad/s</b></div>
            </div>
          </div>

          <div class="metric-group">
            <div class="group-title">Velocity (body)</div>
            <div class="metric-row">
              <div class="metric"><span>Vx</span><b class="mono">{{ fmt(velocityBody.x) }} m/s</b></div>
              <div class="metric"><span>Vy</span><b class="mono">{{ fmt(velocityBody.y) }} m/s</b></div>
              <div class="metric"><span>ω</span><b class="mono">{{ fmt(velocityBody.yaw) }} rad/s</b></div>
            </div>
          </div>

          <div class="metric-group">
            <div class="group-title">IMU Acceleration</div>
            <div class="metric-row">
              <div class="metric"><span>Ax</span><b class="mono">{{ fmt(acc.x_acc) }} m/s²</b></div>
              <div class="metric"><span>Ay</span><b class="mono">{{ fmt(acc.y_acc) }} m/s²</b></div>
              <div class="metric"><span>Az</span><b class="mono">{{ fmt(acc.z_acc) }} m/s²</b></div>
            </div>
          </div>

          <div v-if="others && others.length" class="metric-group">
            <div class="group-title">其他消息码</div>
            <div class="others">
              <span v-for="item in others" :key="item.code" class="chip mono">
                {{ item.code }} · {{ item.length }} B
              </span>
            </div>
          </div>
        </section>
      </div>

      <JointPanel :angle="jointAngle" :velocity="jointVelocity" />

      <RawPacket :packets="rawPackets" @refresh="refreshRaw" @clear="handleClear" />
    </main>

    <footer class="footer">
      <span v-if="!connected()" class="warn">未检测到机器人数据，请确认 Lite3 已上电并指向本机 UDP 端口。</span>
      <span v-else class="ok">数据链路正常 · WebSocket {{ wsStatus }}</span>
    </footer>
  </div>
</template>

<style scoped>
.page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px 22px 40px;
}

.topbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 20px;
  margin-bottom: 16px;
  background: linear-gradient(135deg, #ffffff, #eff4ff);
  border: 1px solid var(--panel-border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
}

.brand h1 {
  margin: 0;
  font-size: 22px;
  letter-spacing: -0.01em;
}

.brand p {
  margin: 2px 0 0;
  font-size: 13px;
  color: var(--text-sub);
}

.summary {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 18px;
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.summary-item .k {
  font-size: 11px;
  color: #94a3b8;
}

.summary-item .v {
  font-size: 14px;
  font-weight: 600;
}

.conn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  font-size: 13px;
  font-weight: 600;
  border-radius: 999px;
}

.conn.on {
  color: #166534;
  background: #dcfce7;
}

.conn.off {
  color: #991b1b;
  background: #fee2e2;
}

.conn .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
}

.layout {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.row {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
  gap: 16px;
}

@media (max-width: 1080px) {
  .row {
    grid-template-columns: 1fr;
  }
}

.metrics {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.group-title {
  margin-bottom: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #94a3b8;
}

.metric-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.metric {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 10px;
  background: #f8fafc;
  border: 1px solid #e6ecf3;
  border-radius: 8px;
}

.metric span {
  font-size: 11px;
  color: #94a3b8;
}

.metric b {
  font-size: 13px;
  font-weight: 600;
}

.others {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.chip {
  padding: 3px 8px;
  font-size: 11px;
  color: #475569;
  background: var(--chip-bg);
  border-radius: 6px;
}

.footer {
  margin-top: 18px;
  font-size: 12px;
  color: var(--text-sub);
  text-align: center;
}

.footer .warn {
  color: #b45309;
}

.footer .ok {
  color: #166534;
}
</style>
