import React, { useState, useEffect, useCallback } from 'react'
import LoginScreen from './components/LoginScreen'
import ClaudeCodeMode from './components/ClaudeCodeMode'
import OrchestrationMode from './components/OrchestrationMode'
import ModeToggle from './components/ModeToggle'
import StatusBar from './components/StatusBar'

// ─── Auth Helpers ─────────────────────────────────────────────────────────────
const TOKEN_KEY = 'dual_claude_ui_token'

function getStoredToken() {
  try { return localStorage.getItem(TOKEN_KEY) } catch { return null }
}
function storeToken(t) {
  try { localStorage.setItem(TOKEN_KEY, t) } catch { }
}
function clearToken() {
  try { localStorage.removeItem(TOKEN_KEY) } catch { }
}

// ─── App ──────────────────────────────────────────────────────────────────────
export default function App() {
  const [mode, setMode] = useState('claude')          // 'claude' | 'orch'
  const [token, setToken] = useState(getStoredToken)
  const [authenticated, setAuthenticated] = useState(false)
  const [checking, setChecking] = useState(true)
  const [orchStatus, setOrchStatus] = useState(null)  // null | 'online' | 'offline'

  // Check if auth is required and validate stored token
  useEffect(() => {
    async function init() {
      try {
        const res = await fetch('/api/health')
        const data = await res.json()

        if (!data.passwordRequired) {
          // No password - auto auth
          const loginRes = await fetch('/api/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) })
          const loginData = await loginRes.json()
          if (loginData.token) {
            storeToken(loginData.token)
            setToken(loginData.token)
            setAuthenticated(true)
          }
        } else if (token) {
          // Validate stored token
          const testRes = await fetch('/api/claude/projects', { headers: { Authorization: `Bearer ${token}` } })
          if (testRes.ok) setAuthenticated(true)
          else { clearToken(); setToken(null) }
        }
      } catch (err) {
        console.warn('Init check failed:', err)
      } finally {
        setChecking(false)
      }
    }
    init()
  }, [])

  // Check PCT 100 orchestration status
  useEffect(() => {
    if (!authenticated) return
    async function checkOrch() {
      try {
        const res = await fetch('/api/orch/health', { headers: { Authorization: `Bearer ${token}` }, signal: AbortSignal.timeout(5000) })
        setOrchStatus(res.ok ? 'online' : 'offline')
      } catch {
        setOrchStatus('offline')
      }
    }
    checkOrch()
    const interval = setInterval(checkOrch, 30000)
    return () => clearInterval(interval)
  }, [authenticated, token])

  const handleLogin = useCallback((newToken) => {
    storeToken(newToken)
    setToken(newToken)
    setAuthenticated(true)
  }, [])

  const handleLogout = useCallback(() => {
    clearToken()
    setToken(null)
    setAuthenticated(false)
  }, [])

  const modeClass = mode === 'claude' ? 'mode-claude' : 'mode-orch'

  if (checking) {
    return (
      <div className="h-full flex items-center justify-center bg-claude-dark">
        <div className="flex gap-2">
          <div className="typing-dot" style={{ '--accent': '#D97757' }} />
          <div className="typing-dot" style={{ '--accent': '#D97757' }} />
          <div className="typing-dot" style={{ '--accent': '#D97757' }} />
        </div>
      </div>
    )
  }

  if (!authenticated) {
    return <LoginScreen onLogin={handleLogin} />
  }

  return (
    <div className={`h-full flex flex-col ${modeClass}`} style={{ background: 'var(--bg)', color: 'var(--text)' }}>
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-2 border-b shrink-0"
        style={{ borderColor: 'var(--border)', background: 'var(--bg-surface)' }}>
        <div className="flex items-center gap-3">
          <h1 className="font-semibold text-sm tracking-wide" style={{ color: 'var(--accent)' }}>
            {mode === 'claude' ? '⚡ Claude Code UI' : '⛩️ 武士団 Orchestration'}
          </h1>
        </div>
        <div className="flex items-center gap-3">
          <ModeToggle mode={mode} onChange={setMode} orchStatus={orchStatus} />
          <button onClick={handleLogout} className="btn-ghost text-xs px-2 py-1">
            ログアウト
          </button>
        </div>
      </header>

      {/* Status Bar */}
      <StatusBar mode={mode} token={token} orchStatus={orchStatus} />

      {/* Main Content */}
      <main className="flex-1 overflow-hidden">
        {mode === 'claude' ? (
          <ClaudeCodeMode token={token} />
        ) : (
          <OrchestrationMode token={token} orchStatus={orchStatus} />
        )}
      </main>
    </div>
  )
}
