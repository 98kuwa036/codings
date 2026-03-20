import React, { useState } from 'react'

// Simple markdown-like renderer (no external deps)
function renderMarkdown(text) {
  if (!text) return ''
  // Escape HTML
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  // Code blocks
  html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) =>
    `<pre><code class="language-${lang}">${code.trim()}</code></pre>`)

  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>')

  // Bold
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/__([^_]+)__/g, '<strong>$1</strong>')

  // Italic
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>')

  // Headers
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>')
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>')
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>')

  // Lists
  html = html.replace(/^[-*] (.+)$/gm, '<li>$1</li>')
  html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')

  // Line breaks (not inside pre)
  html = html.replace(/\n(?!<)/g, '<br />')

  return html
}

export default function ChatMessage({ msg, mode }) {
  const [expanded, setExpanded] = useState(false)

  switch (msg.type) {
    case 'user':
      return (
        <div className="flex justify-end">
          <div className="msg-user">
            <p className="whitespace-pre-wrap text-sm">{msg.content}</p>
          </div>
        </div>
      )

    case 'assistant':
    case 'message':
      return (
        <div className="flex flex-col gap-1">
          {msg.role && (
            <div className="flex items-center gap-2 ml-1">
              <span className="role-badge">{getRoleIcon(msg.role)} {msg.role}</span>
              {msg.durationMs && (
                <span className="text-xs" style={{ color: 'var(--muted)' }}>
                  {(msg.durationMs / 1000).toFixed(1)}s
                </span>
              )}
            </div>
          )}
          <div className="msg-assistant prose-custom"
            dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }} />
        </div>
      )

    case 'tool_use':
      return (
        <div className="flex flex-col gap-1">
          <button
            onClick={() => setExpanded(!expanded)}
            className="msg-tool flex items-center gap-2 cursor-pointer"
            style={{ background: 'color-mix(in srgb, var(--accent) 8%, transparent)' }}>
            <span>🔧 {msg.toolName}</span>
            <span className="ml-auto opacity-60">{expanded ? '▼' : '▶'}</span>
          </button>
          {expanded && msg.toolInput && (
            <pre className="text-xs px-3 py-2 rounded-lg overflow-x-auto"
              style={{ background: 'rgba(0,0,0,0.4)', color: 'var(--muted)' }}>
              {JSON.stringify(msg.toolInput, null, 2)}
            </pre>
          )}
        </div>
      )

    case 'tool_result':
      return (
        <button onClick={() => setExpanded(!expanded)}
          className="self-start text-xs px-3 py-1.5 rounded-lg"
          style={{ background: 'rgba(0,0,0,0.3)', color: 'var(--muted)', border: '1px solid var(--border)' }}>
          {expanded ? '▼ 結果を隠す' : '▶ ツール結果を表示'}
          {expanded && (
            <pre className="mt-2 text-left whitespace-pre-wrap max-h-40 overflow-y-auto">
              {msg.content?.slice(0, 2000)}{msg.content?.length > 2000 ? '...' : ''}
            </pre>
          )}
        </button>
      )

    case 'system':
      return (
        <div className="flex justify-center">
          <span className="msg-system">{msg.content}</span>
        </div>
      )

    case 'error':
      return (
        <div className="self-start max-w-[85%] rounded-lg px-3 py-2 text-xs"
          style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', color: '#f87171' }}>
          ⚠ {msg.content}
        </div>
      )

    default:
      return null
  }
}

function getRoleIcon(role) {
  const icons = {
    '大元帥': '👑', '将軍': '⚔️', '軍師': '🧠', '参謀': '💻',
    '外事': '🌐', '受付': '📋', '斥候': '🔍', '検校': '👁️',
    '右筆': '✍️', '隠密': '🥷',
  }
  return icons[role] || '🤖'
}
