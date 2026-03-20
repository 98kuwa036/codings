import React from 'react'

export default function ModeToggle({ mode, onChange, orchStatus }) {
  return (
    <div className="flex items-center rounded-lg p-0.5 gap-0.5"
      style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border)' }}>
      <button
        onClick={() => onChange('claude')}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all"
        style={{
          background: mode === 'claude' ? '#D97757' : 'transparent',
          color: mode === 'claude' ? 'white' : 'var(--muted)',
        }}>
        ⚡ Claude Code
      </button>
      <button
        onClick={() => onChange('orch')}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all"
        style={{
          background: mode === 'orch' ? '#C9A84C' : 'transparent',
          color: mode === 'orch' ? 'white' : 'var(--muted)',
        }}>
        ⛩️ 武士団
        {orchStatus === 'online' && (
          <span className="w-1.5 h-1.5 rounded-full bg-green-400 inline-block" />
        )}
        {orchStatus === 'offline' && (
          <span className="w-1.5 h-1.5 rounded-full bg-red-400 inline-block" />
        )}
      </button>
    </div>
  )
}
