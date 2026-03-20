import React, { useState, useEffect, useRef, useCallback } from 'react'
import ChatMessage from './ChatMessage'
import ProjectSidebar from './ProjectSidebar'

// ─── WebSocket Hook ────────────────────────────────────────────────────────────
function useClaudeWS(token, sessionId, projectPath) {
  const wsRef = useRef(null)
  const [messages, setMessages] = useState([])
  const [status, setStatus] = useState('idle') // idle | thinking | streaming | done
  const [currentSessionId, setCurrentSessionId] = useState(null)

  const connect = useCallback(() => {
    const protocol = location.protocol === 'https:' ? 'wss' : 'ws'
    const params = new URLSearchParams({ token, sessionId, project: projectPath || '' })
    const url = `${protocol}://${location.host}/ws?${params}`

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data)
      handleEvent(msg)
    }
    ws.onclose = () => setStatus('idle')
    ws.onerror = () => setStatus('idle')
  }, [token, sessionId, projectPath])

  function handleEvent(event) {
    switch (event.type) {
      case 'system':
        setMessages(prev => [...prev, { id: Date.now(), type: 'system', content: event.content }])
        break
      case 'status':
        setStatus(event.content === 'thinking' ? 'thinking' : 'streaming')
        break
      case 'text':
        setMessages(prev => {
          const last = prev[prev.length - 1]
          if (last?.type === 'assistant') {
            return [...prev.slice(0, -1), { ...last, content: last.content + event.content }]
          }
          return [...prev, { id: Date.now(), type: 'assistant', content: event.content }]
        })
        setStatus('streaming')
        break
      case 'tool_use':
        setMessages(prev => [...prev, {
          id: Date.now(), type: 'tool_use',
          toolName: event.toolName, toolInput: event.toolInput
        }])
        break
      case 'tool_result':
        setMessages(prev => [...prev, { id: Date.now(), type: 'tool_result', content: event.content }])
        break
      case 'result':
        if (event.sessionId) setCurrentSessionId(event.sessionId)
        setStatus('done')
        setTimeout(() => setStatus('idle'), 1500)
        break
      case 'done':
        if (event.sessionId) setCurrentSessionId(event.sessionId)
        setStatus('idle')
        break
      case 'error':
        setMessages(prev => [...prev, { id: Date.now(), type: 'error', content: event.content }])
        setStatus('idle')
        break
    }
  }

  function send(content, resumeSessionId) {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      connect()
      // Queue message after reconnect
      setTimeout(() => {
        wsRef.current?.send(JSON.stringify({ type: 'chat', content, resumeSessionId }))
      }, 500)
      return
    }
    setStatus('thinking')
    setMessages(prev => [...prev, { id: Date.now(), type: 'user', content }])
    wsRef.current.send(JSON.stringify({ type: 'chat', content, resumeSessionId }))
  }

  function abort() {
    wsRef.current?.send(JSON.stringify({ type: 'abort' }))
    setStatus('idle')
  }

  function clear() {
    setMessages([])
    setCurrentSessionId(null)
    setStatus('idle')
  }

  useEffect(() => {
    connect()
    return () => wsRef.current?.close()
  }, [connect])

  return { messages, status, currentSessionId, send, abort, clear }
}

// ─── Claude Code Mode ─────────────────────────────────────────────────────────
export default function ClaudeCodeMode({ token }) {
  const [selectedProject, setSelectedProject] = useState(null)
  const [showSidebar, setShowSidebar] = useState(true)
  const [input, setInput] = useState('')
  const sessionId = useRef(`claude-${Date.now()}`).current
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)

  const { messages, status, currentSessionId, send, abort, clear } = useClaudeWS(
    token, sessionId, selectedProject?.path
  )

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function handleSend() {
    if (!input.trim() || status === 'thinking' || status === 'streaming') return
    send(input.trim(), currentSessionId)
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
    <div className="h-full flex">
      {/* Sidebar */}
      {showSidebar && (
        <ProjectSidebar
          token={token}
          selectedProject={selectedProject}
          onSelect={setSelectedProject}
          onClose={() => setShowSidebar(false)}
        />
      )}

      {/* Main Chat */}
      <div className="flex-1 flex flex-col h-full min-w-0">
        {/* Toolbar */}
        <div className="flex items-center gap-2 px-4 py-2 border-b shrink-0"
          style={{ borderColor: 'var(--border)' }}>
          {!showSidebar && (
            <button onClick={() => setShowSidebar(true)} className="btn-ghost text-xs px-2 py-1">
              ☰ Projects
            </button>
          )}
          <span className="text-xs" style={{ color: 'var(--muted)' }}>
            {selectedProject ? `📁 ${selectedProject.name}` : '📁 プロジェクト未選択'}
          </span>
          <div className="flex-1" />
          {currentSessionId && (
            <span className="text-xs font-mono" style={{ color: 'var(--muted)' }}>
              session: {currentSessionId.slice(-8)}
            </span>
          )}
          <button onClick={clear} className="btn-ghost text-xs px-2 py-1">
            クリア
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center gap-4"
              style={{ color: 'var(--muted)' }}>
              <div className="text-6xl opacity-30">⚡</div>
              <div>
                <p className="text-sm font-medium" style={{ color: 'var(--text)' }}>Claude Code モード</p>
                <p className="text-xs mt-1">左のサイドバーでプロジェクトを選択して、タスクを入力してください</p>
              </div>
              <div className="grid grid-cols-2 gap-2 mt-4 w-full max-w-sm">
                {['コードをレビューして', 'バグを修正して', '新機能を追加して', 'テストを書いて'].map(hint => (
                  <button key={hint} onClick={() => setInput(hint)}
                    className="text-xs px-3 py-2 rounded-lg border text-left transition-all"
                    style={{ borderColor: 'var(--border)', color: 'var(--muted)' }}>
                    {hint}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map(msg => <ChatMessage key={msg.id} msg={msg} mode="claude" />)}
          {status === 'thinking' && (
            <div className="flex items-center gap-2 px-4 py-3 rounded-2xl rounded-bl-md self-start max-w-[200px]"
              style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
              <div className="flex gap-1">
                <div className="typing-dot" /><div className="typing-dot" /><div className="typing-dot" />
              </div>
              <span className="text-xs" style={{ color: 'var(--muted)' }}>思考中...</span>
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
              placeholder={isProcessing ? 'Claude が処理中...' : 'メッセージを入力 (Shift+Enter で改行)'}
              disabled={isProcessing}
              rows={1}
              className="chat-input"
              style={{ height: 'auto' }}
              onInput={e => { e.target.style.height = 'auto'; e.target.style.height = Math.min(e.target.scrollHeight, 200) + 'px' }}
            />
            {isProcessing ? (
              <button onClick={abort} className="btn-ghost shrink-0"
                style={{ color: '#ef4444', borderColor: '#ef4444' }}>
                ⏹
              </button>
            ) : (
              <button onClick={handleSend} disabled={!input.trim()} className="btn-primary shrink-0">
                送信
              </button>
            )}
          </div>
          <p className="text-xs mt-1.5" style={{ color: 'var(--muted)' }}>
            Enter で送信 · Shift+Enter で改行
            {currentSessionId && ' · セッション継続中'}
          </p>
        </div>
      </div>
    </div>
  )
}
