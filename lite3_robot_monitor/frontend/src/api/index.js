/**
 * 后端接口封装层。
 *
 * 约定：
 * - REST 走同源 /api（Vite dev 由 proxy 转发到后端 8000 端口）；
 * - WebSocket 走 /ws/state，由服务端以 10Hz 主动推送；
 * - 若设置环境变量 VITE_BACKEND_URL，则直接跨域访问后端，方便单端口/分离部署。
 */

const BACKEND = import.meta.env.VITE_BACKEND_URL || ''

/** REST 基础地址 */
export const apiBase = BACKEND

/** WebSocket 基础地址 */
export const wsBase = BACKEND ? BACKEND.replace(/^http/, 'ws') : `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}`

/** GET 请求封装，统一错误处理 */
async function httpGet(path, params = {}) {
  const url = new URL(`${apiBase}${path}`, location.origin)
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null) url.searchParams.set(k, v)
  })
  const resp = await fetch(url.toString())
  if (!resp.ok) {
    throw new Error(`${path} 请求失败: HTTP ${resp.status}`)
  }
  return resp.json()
}

/** 获取当前状态快照 */
export function fetchState() {
  return httpGet('/api/state')
}

/** 获取服务与链路状态 */
export function fetchStatus() {
  return httpGet('/api/status')
}

/** 获取最近 N 条原始报文 */
export function fetchRaw(limit = 20) {
  return httpGet('/api/raw', { limit })
}

/** 清空原始报文缓存 */
export async function clearRaw() {
  const url = new URL(`${apiBase}/api/raw/clear`, location.origin)
  const resp = await fetch(url.toString(), { method: 'POST' })
  if (!resp.ok) throw new Error(`清空失败: HTTP ${resp.status}`)
  return resp.json()
}

/**
 * 状态 WebSocket 客户端。
 *
 * 负责：
 * - 建立连接、断线自动重连（指数退避上限 5s）；
 * - 把服务端快照分发给回调；
 * - 维护 UI 侧的链路状态（connecting / open / closed）。
 */
export class StateSocket {
  /**
   * @param {Object} options
   * @param {(snapshot: any) => void} options.onSnapshot 收到快照时的回调
   * @param {(state: 'connecting'|'open'|'closed', detail?: string) => void} options.onStatus 连接状态变化回调
   * @param {number} options.retryInterval 重连基础间隔（毫秒）
   */
  constructor({ onSnapshot, onStatus, retryInterval = 1500 }) {
    this.onSnapshot = onSnapshot
    this.onStatus = onStatus
    this.retryInterval = retryInterval
    this.socket = null
    this.retryTimer = null
    this.retryCount = 0
    this.manualClosed = false
  }

  /** 建立连接（若已连接则忽略） */
  connect() {
    if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
      return
    }
    this.manualClosed = false
    this.onStatus?.('connecting')

    const ws = new WebSocket(`${wsBase}/ws/state`)
    this.socket = ws

    ws.onopen = () => {
      this.retryCount = 0
      this.onStatus?.('open')
    }

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data)
        this.onSnapshot?.(payload)
      } catch (err) {
        console.error('[StateSocket] 快照解析失败', err)
      }
    }

    ws.onerror = () => {
      // 具体的错误信息浏览器不暴露，统一按断连处理
      this.onStatus?.('closed', '连接异常')
    }

    ws.onclose = () => {
      this.onStatus?.('closed')
      if (!this.manualClosed) this._scheduleRetry()
    }
  }

  /** 安排一次重连（退避策略） */
  _scheduleRetry() {
    if (this.retryTimer) return
    const delay = Math.min(this.retryInterval * Math.pow(1.5, this.retryCount), 5000)
    this.retryCount += 1
    this.retryTimer = setTimeout(() => {
      this.retryTimer = null
      this.connect()
    }, delay)
  }

  /** 主动请求一次即时快照（服务端收到任意文本即回推一帧） */
  ping() {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send('ping')
    }
  }

  /** 关闭连接并停止重连 */
  close() {
    this.manualClosed = true
    if (this.retryTimer) {
      clearTimeout(this.retryTimer)
      this.retryTimer = null
    }
    if (this.socket) {
      this.socket.close()
      this.socket = null
    }
  }
}
