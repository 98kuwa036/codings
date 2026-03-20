import React, { useState, useEffect, useRef, useCallback } from 'react'
import ChatMessage from './ChatMessage'

// ─── Agent Roles (matches server/orchestration.js) ───────────────────────────
const AGENT_ROLES = [
  { id: 'auto',   name: '自動選択', icon: '⚡', model: 'auto',             color: '#C9A84C' },
  { id: '大元帥', name: '大元帥',  icon: '👑', model: 'Claude Opus 4.6',  color: '#8B6914' },
  { id: '将軍',   name: '将軍',   icon: '⚔️', model: 'Claude Sonnet 4.6', color: '#6B4E9B' },
  { id: '軍師',   name: '軍師',   icon: '🧠', model: 'o3-mini (high)',     color: '#1A5276' },
  { id: '参謀',   name: '参謀',   icon: '💻', model: 'Mistral Large',     color: '#117A65' },
  { id: '外事',   name: '外事',   icon: '🌐', model: 'Command R+',         color: '#7D6608' },
  { id: '受付',   name: '受付',   icon: '📋', model: 'Command R',          color: '#6E2F1A' },
  { id: '斥候',   name: '斥候',   icon: '🔍', model: 'Llama 3.3 (Groq)',  color: '#1B4F72' },
  { id: '検校',   name: '検校',   icon: '👁️', model: 'Gemini Flash',      color: '#4A235A' },
  { id: '右筆',   name: '右筆',   icon: '✍️', model: 'ELYZA (local)',      color: '#2E4057' },
  { id: '隠密',   name: '隠密',   icon: '🥷', model: 'Nemotron (local)',   color: '#212121' },
]

// ─── WebSocket Hook ───────────────────────────────────────────────────────────
function useOrchWS(token) {
  const wsRef = useRef(null)
  const [messages, setMessages] = useState([])
  const [status, setStatus] = useState('idle')
  const [connected, setConnected] = useState(false)
  const threadId = useRef(`thread-${Date.now()}`).current

  const connect = useCallback(() => {
    const protocol = location.protocol === 'https:' ? 'wss' : 'ws'
    const params = new URLSearchParams({ token, threadId })
    const url = `${protocol}://${location.host}/orch?${params}`
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => setConnected(true)
    ws.onclose = () => { setConnected(false); setStatus('idle') }
    ws.onerror = () => { setConnected(false); setStatus('idle') }

    ws.onmessage = (e) => {
      const event = JSON.parse(e.data)
      switch (event.type) {
        case 'system':
          setMessages(prev => [...prev, { id: Date.now(), type: 'system', content: event.content }])
          if (event.status === 'connected') setConnected(true)
          if (event.status === 'disconnected') setConnected(false)
          break
        case 'status':
          setStatus(event.content)
          break
        case 'message':
          setMessages(prev => [...prev, {
            id: Date.now(), type: 'message',
            content: event.content,
            role: event.role,
            handler: event.handler,
            path: event.path,
            durationMs: event.durationMs,
            threadId: event.threadId,
          }])
          setStatus('idle')
          break
        case 'error':
          setMessages(prev => [...prev, { id: Date.now(), type: 'error', content: event.content }])
          setStatus('idle')
          break
        case 'pong':
          break
      }
    }
  }, [token, threadId])

  function send(content, role = 'auto') {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    setStatus('thinking')
    setMessages(prev => [...prev, { id: Date.now(), type: 'user', content }])
    wsRef.current.send(JSON.stringify({ type: 'chat', content, role }))
  }

  function ping() {
    wsRef.current?.send(JSON.stringify({ type: 'ping' }))
  }

  function clear() {
    setMessages([])
    setStatus('idle')
  }

  useEffect(() => {
    connect()
    const pingInterval = setInterval(ping, 25000)
    return () => { clearInterval(pingInterval); wsRef.current?.close() }
  }, [connect])

  return { messages, status, connected, send, clear, threadId }
}

// ─── Orchestration Mode ───────────────────────────────────────────────────────
export default function OrchestrationMode({ token, orchStatus }) {
  const [selectedRole, setSelectedRole] = useState(AGENT_ROLES[0])
  const [input, setInput] = useState('')
  const [showRolePanel, setShowRolePanel] = useState(true)
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)

  const { messages, status, connected, send, clear, threadId } = useOrchWS(token)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function handleSend() {
    if (!input.trim() || status === 'thinking' || !connected) return
    send(input.trim(), selectedRole.id)
    setInput('')
    textareaRef.current?.focus()
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const isProcessing = status === 'thinking' || status === 'streaming'

  return (
    <div className="h-full flex" style={{ background: 'var(--bg)' }}>

      {/* Role Panel */}
      {showRolePanel && (
        <div className="w-52 flex flex-col h-full border-r shrink-0"
          style={{ background: 'var(--bg-surface)', borderColor: 'var(--border)' }}>
          <div className="flex items-center justify-between px-3 py-2.5 border-b"
            style={{ borderColor: 'var(--border)' }}>
            <span className="text-xs font-semibold tracking-wide" style={{ color: 'var(--text)' }}>
              役職選択
            </span>
            <button onClick={() => setShowRolePanel(false)} className="text-xs" style={{ color: 'var(--muted)' }}>✕</button>
          </div>
          <div className="flex-1 overflow-y-auto py-1">
            {AGENT_ROLES.map(role => (
              <button
                key={role.id}
                onClick={() => setSelectedRole(role)}
                className="w-full text-left px-3 py-2 transition-colors"
                style={{
                  background: selectedRole.id === role.id
                    ? 'color-mix(in srgb, var(--accent) 15%, transparent)'
                    : 'transparent',
                }}>
                <div className="flex items-center gap-2">
                  <span className="text-base">{role.icon}</span>
                  <div>
                    <div className="text-xs font-medium" style={{
                      color: selectedRole.id === role.id ? 'var(--accent)' : 'var(--text)'
                    }}>
                      {role.name}
                    </div>
                    <div className="text-xs" style={{ color: 'var(--muted)', fontSize: '10px' }}>
                      {role.model}
                    </div>
                  </div>
                </div>
              </button>
            ))}
          </div>
          {/* Connection status */}
          <div className="px-3 py-2 border-t text-xs" style={{ borderColor: 'var(--border)', color: 'var(--muted)' }}>
            <div className="flex items-center gap-1.5">
              <span className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-green-400' : 'bg-red-400'}`} />
              {connected ? 'PCT 100 接続済み' : 'PCT 100 未接続'}
            </div>
          </div>
        </div>
      )}

      {/* Main Chat */}
      <div className="flex-1 flex flex-col h-full min-w-0">
        {/* Toolbar */}
        <div className="flex items-center gap-2 px-4 py-2 border-b shrink-0"
          style={{ borderColor: 'var(--border)' }}>
          {!showRolePanel && (
            <button onClick={() => setShowRolePanel(true)} className="btn-ghost text-xs px-2 py-1">
              ☰ 役職
            </button>
          )}
          <span className="text-xs flex items-center gap-1.5" style={{ color: 'var(--text)' }}>
            {selectedRole.icon}
            <span style={{ color: 'var(--accent)' }}>{selectedRole.name}</span>
            <span style={{ color: 'var(--muted)' }}>({selectedRole.model})</span>
          </span>
          <div className="flex-1" />
          <span className="text-xs font-mono" style={{ color: 'var(--muted)', fontSize: '10px' }}>
            thread: {threadId.slice(-8)}
          </span>
          <button onClick={clear} className="btn-ghost text-xs px-2 py-1">クリア</button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center gap-4"
              style={{ color: 'var(--muted)' }}>
              <div className="text-6xl opacity-30">⛩️</div>
              <div>
                <p className="text-sm font-medium" style={{ color: 'var(--text)', fontFamily: 'Noto Sans JP, sans-serif' }}>
                  武士団 マルチエージェント システム
                </p>
                <p className="text-xs mt-1">PCT 100 の LLM オーケストレーションに接続</p>
                <p className="text-xs mt-0.5">10役職体制による知的ルーティング</p>
              </div>
              {orchStatus === 'offline' && (
                <div className="px-4 py-3 rounded-lg text-xs max-w-sm"
                  style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', color: '#f87171' }}>
                  ⚠ PCT 100 がオフラインです。<br />
                  Proxmox で PCT 100 が起動しているか確認してください。
                </div>
              )}
              <div className="grid grid-cols-1 gap-2 mt-2 w-full max-w-xs">
                {['最新のAI技術を教えて', 'コードをデバッグして', '戦略的な計画を立てて', '日本語で報告書を作成して'].map(hint => (
                  <button key={hint} onClick={() => setInput(hint)}
                    className="text-xs px-3 py-2 rounded-lg border text-left"
                    style={{ borderColor: 'var(--border)', color: 'var(--muted)' }}>
                    {hint}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map(msg => <ChatMessage key={msg.id} msg={msg} mode="orch" />)}
          {isProcessing && (
            <div className="flex items-center gap-3 px-4 py-3 rounded-xl self-start"
              style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
              <div className="flex gap-1">
                <div className="typing-dot" /><div className="typing-dot" /><div className="typing-dot" />
              </div>
              <span className="text-xs" style={{ color: 'var(--muted)', fontFamily: 'Noto Sans JP, sans-serif' }}>
                {selectedRole.icon} {selectedRole.name} が処理中...
              </span>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="px-4 py-3 border-t shrink-0" style={{ borderColor: 'var(--border)' }}>
          <div className="flex gap-2 items-end">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                !connected ? 'PCT 100 に接続中...' :
                isProcessing ? `${selectedRole.name} が処理中...` :
                `${selectedRole.icon} ${selectedRole.name} へメッセージを送信`
              }
              disabled={isProcessing || !connected}
              rows={1}
              className="chat-input"
              onInput={e => { e.target.style.height = 'auto'; e.target.style.height = Math.min(e.target.scrollHeight, 200) + 'px' }}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isProcessing || !connected}
              className="btn-primary shrink-0"
              style={{ background: 'var(--accent)' }}>
              出陣
            </button>
          </div>
          <p className="text-xs mt-1.5" style={{ color: 'var(--muted)' }}>
            Enter で送信 · 役職: {selectedRole.name} ({selectedRole.model})
          </p>
        </div>
      </div>
    </div>
  )
}
