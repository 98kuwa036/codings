import React, { useState } from 'react'

export default function LoginScreen({ onLogin }) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      })
      const data = await res.json()
      if (!res.ok) { setError(data.error || 'ログイン失敗'); return }
      onLogin(data.token)
    } catch {
      setError('サーバーに接続できません')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="h-full flex items-center justify-center bg-claude-dark">
      <div className="w-full max-w-sm p-8 rounded-2xl border"
        style={{ background: '#1e1e1e', borderColor: '#333' }}>
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="text-5xl mb-3">⚡</div>
          <h1 className="text-xl font-bold text-white">Dual Mode Claude UI</h1>
          <p className="text-sm mt-1" style={{ color: '#888' }}>
            Claude Code + 武士団 オーケストレーション
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs mb-2" style={{ color: '#888' }}>パスワード</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full rounded-lg px-3 py-2.5 text-sm outline-none"
              style={{
                background: '#2a2a2a',
                border: '1px solid #444',
                color: '#e5e5e5',
              }}
              placeholder="パスワードを入力"
              autoFocus
            />
          </div>
          {error && <p className="text-xs text-red-400">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 rounded-lg text-sm font-medium transition-opacity"
            style={{ background: '#D97757', color: 'white', opacity: loading ? 0.6 : 1 }}>
            {loading ? 'ログイン中...' : 'ログイン'}
          </button>
        </form>
      </div>
    </div>
  )
}
