/**
 * Mode 2: PCT 100 LLM Orchestration Proxy
 * Proxies requests to Bushidan Multi-Agent system (LangGraph + 10-role system)
 * running on PCT 100 (default port 8067).
 */

import { WebSocket } from 'ws'
import { v4 as uuidv4 } from 'uuid'

const ORCH_HOST = process.env.ORCHESTRATION_HOST || '192.168.1.100'
const ORCH_PORT = parseInt(process.env.ORCHESTRATION_PORT || '8067')
const ORCH_PASSWORD = process.env.ORCHESTRATION_PASSWORD || ''
const ORCH_BASE_URL = `http://${ORCH_HOST}:${ORCH_PORT}`
const ORCH_WS_URL = `ws://${ORCH_HOST}:${ORCH_PORT}`

// Cache the token from PCT 100 auth
let orchTokenCache = null
let orchTokenExpiry = 0

// ─── PCT 100 Auth ─────────────────────────────────────────────────────────────
async function getOrchToken() {
  if (orchTokenCache && Date.now() < orchTokenExpiry) return orchTokenCache
  try {
    const resp = await fetch(`${ORCH_BASE_URL}/api/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: ORCH_PASSWORD }),
      signal: AbortSignal.timeout(5000),
    })
    if (!resp.ok) throw new Error(`Auth failed: ${resp.status}`)
    const data = await resp.json()
    orchTokenCache = data.token || data.access_token
    orchTokenExpiry = Date.now() + 23 * 3600 * 1000 // 23h
    return orchTokenCache
  } catch (err) {
    throw new Error(`PCT 100 auth failed: ${err.message}`)
  }
}

// ─── Health & Models ──────────────────────────────────────────────────────────
export async function getOrchHealth() {
  const resp = await fetch(`${ORCH_BASE_URL}/api/health`, {
    signal: AbortSignal.timeout(5000),
  })
  if (!resp.ok) throw new Error(`Health check failed: ${resp.status}`)
  return resp.json()
}

export async function getOrchModels() {
  const token = await getOrchToken()
  const resp = await fetch(`${ORCH_BASE_URL}/api/models`, {
    headers: { Authorization: `Bearer ${token}` },
    signal: AbortSignal.timeout(5000),
  })
  if (!resp.ok) throw new Error(`Models fetch failed: ${resp.status}`)
  return resp.json()
}

// ─── Synchronous Chat Proxy ───────────────────────────────────────────────────
export async function proxyOrchChat(body) {
  const token = await getOrchToken()
  const resp = await fetch(`${ORCH_BASE_URL}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(120000),
  })
  if (!resp.ok) throw new Error(`Chat failed: ${resp.status}`)
  return resp.json()
}

// ─── WebSocket Proxy to PCT 100 ───────────────────────────────────────────────
export function handleOrchWebSocket(clientWs, req) {
  const url = new URL(req.url, 'http://localhost')
  const threadId = url.searchParams.get('threadId') || uuidv4()

  console.log(`[orch-mode] WS connected, thread=${threadId}`)

  let upstreamWs = null
  let connected = false
  const pendingMessages = []

  // Send initial status to client
  clientWs.send(JSON.stringify({
    type: 'system',
    content: `PCT 100 オーケストレーション接続中... (${ORCH_HOST}:${ORCH_PORT})`,
    host: ORCH_HOST,
    port: ORCH_PORT,
  }))

  // Connect to PCT 100's Bushidan WebSocket
  async function connectUpstream() {
    let token = ''
    try {
      token = await getOrchToken()
    } catch (err) {
      clientWs.send(JSON.stringify({
        type: 'error',
        content: `PCT 100 認証失敗: ${err.message}`,
      }))
      return
    }

    const wsUrl = `${ORCH_WS_URL}/ws/chat?token=${token}&thread_id=${threadId}`
    upstreamWs = new WebSocket(wsUrl)

    upstreamWs.on('open', () => {
      connected = true
      clientWs.send(JSON.stringify({
        type: 'system',
        content: '武士団マルチエージェントシステム接続完了',
        status: 'connected',
        threadId,
      }))
      // Flush pending messages
      for (const msg of pendingMessages) {
        upstreamWs.send(JSON.stringify(msg))
      }
      pendingMessages.length = 0
    })

    upstreamWs.on('message', (raw) => {
      try {
        const event = JSON.parse(raw.toString())
        // Transform Bushidan events to our format
        const transformed = transformOrchEvent(event)
        clientWs.send(JSON.stringify(transformed))
      } catch {
        // Forward raw if not JSON
        clientWs.send(raw.toString())
      }
    })

    upstreamWs.on('close', (code, reason) => {
      connected = false
      clientWs.send(JSON.stringify({
        type: 'system',
        content: `PCT 100 接続終了 (code: ${code})`,
        status: 'disconnected',
      }))
    })

    upstreamWs.on('error', (err) => {
      connected = false
      clientWs.send(JSON.stringify({
        type: 'error',
        content: `PCT 100 接続エラー: ${err.message}`,
        detail: `${ORCH_HOST}:${ORCH_PORT} が利用できません`,
      }))
    })
  }

  connectUpstream()

  // Forward client messages to PCT 100
  clientWs.on('message', (raw) => {
    try {
      const msg = JSON.parse(raw.toString())

      if (msg.type === 'ping') {
        clientWs.send(JSON.stringify({ type: 'pong' }))
        return
      }

      // Transform client message to Bushidan format
      const upstream = {
        message: msg.content || msg.message || '',
        model: msg.role || 'auto',  // agent role selection
        thread_id: threadId,
        source: 'dual_ui',
      }

      if (connected && upstreamWs?.readyState === WebSocket.OPEN) {
        upstreamWs.send(JSON.stringify(upstream))
      } else {
        pendingMessages.push(upstream)
      }
    } catch { /* ignore malformed */ }
  })

  clientWs.on('close', () => {
    console.log(`[orch-mode] Client disconnected, thread=${threadId}`)
    if (upstreamWs) {
      upstreamWs.close(1000, 'Client disconnected')
    }
  })
}

// ─── Event Transformer: Bushidan → UI format ──────────────────────────────────
function transformOrchEvent(event) {
  // Bushidan response format → our unified format
  if (event.response !== undefined) {
    return {
      type: 'message',
      content: event.response,
      role: event.role || event.agent_role,
      handler: event.handler,
      path: event.routing_path,
      durationMs: event.execution_time ? Math.round(event.execution_time * 1000) : null,
      threadId: event.thread_id,
    }
  }

  // Thinking/status events
  if (event.status || event.type === 'thinking') {
    return {
      type: 'status',
      content: event.status || 'thinking',
      role: event.role,
    }
  }

  // Error events
  if (event.error) {
    return {
      type: 'error',
      content: event.error,
    }
  }

  // Pass through unknown events
  return { type: 'raw', event }
}

// ─── Agent Roster (10-role system) ────────────────────────────────────────────
export const AGENT_ROLES = [
  { id: 'auto',     name: '自動選択',  nameEn: 'Auto Select',      icon: '⚡', model: 'auto',                   description: 'インテリジェントルーティング' },
  { id: '大元帥',   name: '大元帥',   nameEn: 'Supreme Commander', icon: '👑', model: 'claude-opus-4-6',         description: '戦略的意思決定' },
  { id: '将軍',     name: '将軍',     nameEn: 'General',           icon: '⚔️', model: 'claude-sonnet-4-6',       description: 'メイン作業実行' },
  { id: '軍師',     name: '軍師',     nameEn: 'Strategist',        icon: '🧠', model: 'o3-mini (high)',          description: '深い論理的推論' },
  { id: '参謀',     name: '参謀',     nameEn: 'Chief of Staff',    icon: '💻', model: 'Mistral Large 3',        description: 'コーディング専門' },
  { id: '外事',     name: '外事',     nameEn: 'Foreign Affairs',   icon: '🌐', model: 'Command R+',              description: 'RAG/情報取得' },
  { id: '受付',     name: '受付',     nameEn: 'Reception',         icon: '📋', model: 'Command R',              description: 'フォールバック処理' },
  { id: '斥候',     name: '斥候',     nameEn: 'Scout',             icon: '🔍', model: 'Llama 3.3 (Groq)',       description: '高速無料処理' },
  { id: '検校',     name: '検校',     nameEn: 'Inspector',         icon: '👁️', model: 'Gemini Flash',           description: 'マルチモーダル分析' },
  { id: '右筆',     name: '右筆',     nameEn: 'Scribe',            icon: '✍️', model: 'ELYZA (local)',           description: '日本語文書作成' },
  { id: '隠密',     name: '隠密',     nameEn: 'Shadow',            icon: '🥷', model: 'Nemotron (local)',        description: '機密処理' },
]
