import React, { useState, useEffect } from 'react'

export default function StatusBar({ mode, token, orchStatus }) {
  const [claudeAuth, setClaudeAuth] = useState(null)

  useEffect(() => {
    if (mode !== 'claude') return
    fetch('/api/claude/auth-status', { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json())
      .then(setClaudeAuth)
      .catch(() => { })
  }, [mode, token])

  return (
    <div className="flex items-center gap-4 px-4 py-1 text-xs border-b shrink-0"
      style={{ background: 'var(--bg)', borderColor: 'var(--border)', color: 'var(--muted)' }}>
      {mode === 'claude' && claudeAuth && (
        <>
          <span className="flex items-center gap-1">
            <span className={`w-1.5 h-1.5 rounded-full ${claudeAuth.claudeCliAvailable ? 'bg-green-400' : 'bg-red-400'}`} />
            Claude CLI {claudeAuth.claudeVersion ? `(${claudeAuth.claudeVersion.split(' ')[2] || claudeAuth.claudeVersion})` : ''}
          </span>
          {claudeAuth.proAuthActive && (
            <span className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
              Pro認証済み
            </span>
          )}
          {!claudeAuth.proAuthActive && claudeAuth.apiKeyAvailable && (
            <span className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-yellow-400" />
              API Key (フォールバック)
            </span>
          )}
          {!claudeAuth.proAuthActive && !claudeAuth.apiKeyAvailable && claudeAuth.claudeCliAvailable && (
            <span className="text-red-400">⚠ 認証なし (claude auth login を実行してください)</span>
          )}
        </>
      )}
      {mode === 'orch' && (
        <span className="flex items-center gap-1">
          <span className={`w-1.5 h-1.5 rounded-full ${orchStatus === 'online' ? 'bg-green-400' : orchStatus === 'offline' ? 'bg-red-400' : 'bg-yellow-400'}`} />
          PCT 100 武士団: {orchStatus === 'online' ? 'オンライン' : orchStatus === 'offline' ? 'オフライン' : '確認中...'}
        </span>
      )}
      <span className="ml-auto opacity-50">Dual Mode Claude UI v1.0</span>
    </div>
  )
}
