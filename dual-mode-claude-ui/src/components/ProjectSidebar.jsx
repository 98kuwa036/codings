import React, { useState, useEffect } from 'react'

export default function ProjectSidebar({ token, selectedProject, onSelect, onClose }) {
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  useEffect(() => {
    fetch('/api/claude/projects', { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json())
      .then(d => setProjects(d.projects || []))
      .catch(() => { })
      .finally(() => setLoading(false))
  }, [token])

  const filtered = projects.filter(p =>
    p.name.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="w-64 flex flex-col h-full border-r shrink-0"
      style={{ background: 'var(--bg-surface)', borderColor: 'var(--border)' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2.5 border-b"
        style={{ borderColor: 'var(--border)' }}>
        <span className="text-xs font-semibold tracking-wide" style={{ color: 'var(--text)' }}>
          PROJECTS
        </span>
        <button onClick={onClose} className="text-xs" style={{ color: 'var(--muted)' }}>✕</button>
      </div>

      {/* Search */}
      <div className="px-3 py-2 border-b" style={{ borderColor: 'var(--border)' }}>
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="プロジェクトを検索..."
          className="w-full text-xs px-2 py-1.5 rounded outline-none"
          style={{ background: 'var(--bg)', border: '1px solid var(--border)', color: 'var(--text)' }}
        />
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto py-1">
        {loading && (
          <div className="px-3 py-4 text-xs text-center" style={{ color: 'var(--muted)' }}>読込中...</div>
        )}
        {!loading && filtered.length === 0 && (
          <div className="px-3 py-4 text-xs text-center" style={{ color: 'var(--muted)' }}>
            プロジェクトが見つかりません
          </div>
        )}
        {filtered.map(project => (
          <button
            key={project.id}
            onClick={() => onSelect(project)}
            className="w-full text-left px-3 py-2 text-xs transition-colors"
            style={{
              background: selectedProject?.id === project.id ? 'color-mix(in srgb, var(--accent) 15%, transparent)' : 'transparent',
              color: selectedProject?.id === project.id ? 'var(--accent)' : 'var(--text)',
            }}>
            <div className="font-medium truncate">📁 {project.name}</div>
            <div className="text-xs mt-0.5 truncate" style={{ color: 'var(--muted)', fontSize: '10px' }}>
              {new Date(project.lastModified).toLocaleDateString('ja-JP')}
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
