/**
 * Mode 1: Claude Code Handler
 * Manages Claude CLI processes, PTY terminals, and session state.
 * Supports Pro subscription (claude auth login) → Anthropic API key fallback.
 */

import { spawn, execSync } from 'child_process'
import { existsSync, readdirSync, readFileSync, statSync } from 'fs'
import { homedir } from 'os'
import { join, basename } from 'path'
import { v4 as uuidv4 } from 'uuid'

// ─── Active Sessions ──────────────────────────────────────────────────────────
// Map<sessionId, { process, ws, buffer: string[], cwd, abortController }>
const activeSessions = new Map()

// ─── Claude Auth: Pro → API Key Fallback ─────────────────────────────────────
export async function checkClaudeAuth() {
  const result = {
    claudeCliAvailable: false,
    proAuthActive: false,
    apiKeyAvailable: false,
    activeMethod: null,
    claudeVersion: null,
  }

  // Check if claude CLI is installed
  try {
    const version = execSync('claude --version 2>/dev/null', { timeout: 5000 }).toString().trim()
    result.claudeCliAvailable = true
    result.claudeVersion = version
  } catch {
    return result
  }

  // Check Pro auth (claude auth status)
  try {
    const authOut = execSync('claude auth status 2>&1', { timeout: 5000 }).toString()
    if (authOut.includes('Logged in') || authOut.includes('authenticated') || authOut.includes('@')) {
      result.proAuthActive = true
      result.activeMethod = 'pro'
    }
  } catch { /* not logged in */ }

  // Check API key fallback
  if (process.env.ANTHROPIC_API_KEY) {
    result.apiKeyAvailable = true
    if (!result.proAuthActive) result.activeMethod = 'api-key'
  }

  return result
}

function buildClaudeEnv() {
  const env = { ...process.env }
  // If API key is set and Pro auth isn't active, force API key mode
  if (!env.ANTHROPIC_API_KEY && process.env.ANTHROPIC_API_KEY) {
    env.ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY
  }
  return env
}

// ─── Projects ─────────────────────────────────────────────────────────────────
export async function getProjects() {
  const claudeDir = join(homedir(), '.claude')
  const projects = []

  // Load projects from ~/.claude/projects if present
  const projectsDir = join(claudeDir, 'projects')
  if (existsSync(projectsDir)) {
    try {
      const dirs = readdirSync(projectsDir)
      for (const dir of dirs) {
        const full = join(projectsDir, dir)
        const stat = statSync(full)
        if (stat.isDirectory()) {
          projects.push({
            id: dir,
            name: decodeURIComponent(dir.replace(/-/g, '/')),
            path: decodeURIComponent(dir.replace(/-/g, '/')),
            lastModified: stat.mtime.toISOString(),
          })
        }
      }
    } catch { /* ignore */ }
  }

  // Also check current working directory as fallback project
  if (projects.length === 0) {
    projects.push({
      id: 'current',
      name: basename(process.cwd()),
      path: process.cwd(),
      lastModified: new Date().toISOString(),
    })
  }

  return projects.sort((a, b) => new Date(b.lastModified) - new Date(a.lastModified))
}

export async function getSessionHistory(projectPath) {
  try {
    const claudeDir = join(homedir(), '.claude')
    const sessionDir = join(claudeDir, 'projects', encodeURIComponent(projectPath))
    if (!existsSync(sessionDir)) return []

    const files = readdirSync(sessionDir)
      .filter(f => f.endsWith('.jsonl'))
      .map(f => ({
        id: f.replace('.jsonl', ''),
        path: join(sessionDir, f),
        mtime: statSync(join(sessionDir, f)).mtime
      }))
      .sort((a, b) => b.mtime - a.mtime)

    return files.slice(0, 20).map(f => ({
      id: f.id,
      lastModified: f.mtime.toISOString(),
    }))
  } catch { return [] }
}

// ─── WebSocket: Claude Code Chat ──────────────────────────────────────────────
export function handleClaudeWebSocket(ws, req) {
  const url = new URL(req.url, 'http://localhost')
  const sessionId = url.searchParams.get('sessionId') || uuidv4()
  const projectPath = url.searchParams.get('project') || process.cwd()

  console.log(`[claude-mode] WS connected: session=${sessionId}`)

  ws.send(JSON.stringify({
    type: 'system',
    content: `セッション開始: ${sessionId}`,
    sessionId
  }))

  ws.on('message', async (raw) => {
    let msg
    try { msg = JSON.parse(raw) } catch { return }

    switch (msg.type) {
      case 'chat':
        await runClaudeChat(ws, sessionId, projectPath, msg.content, msg.resumeSessionId)
        break
      case 'abort':
        abortSession(sessionId)
        break
      case 'ping':
        ws.send(JSON.stringify({ type: 'pong' }))
        break
      default:
        ws.send(JSON.stringify({ type: 'error', content: `Unknown message type: ${msg.type}` }))
    }
  })

  ws.on('close', () => {
    console.log(`[claude-mode] WS disconnected: session=${sessionId}`)
    // Don't kill process on disconnect - allow resume
  })
}

async function runClaudeChat(ws, sessionId, projectPath, prompt, resumeSessionId) {
  // Kill any existing process for this session
  abortSession(sessionId)

  const authStatus = await checkClaudeAuth()
  if (!authStatus.claudeCliAvailable) {
    ws.send(JSON.stringify({
      type: 'error',
      content: 'Claude CLI not found. Run: npm run install:cli'
    }))
    return
  }

  const args = ['--output-format', 'stream-json', '--verbose', '-p', prompt]
  if (resumeSessionId) {
    args.push('--resume', resumeSessionId)
  }

  const env = buildClaudeEnv()
  const cwd = existsSync(projectPath) ? projectPath : process.cwd()

  ws.send(JSON.stringify({
    type: 'status',
    content: 'thinking',
    authMethod: authStatus.activeMethod,
  }))

  const proc = spawn('claude', args, { env, cwd })
  const controller = { aborted: false }
  activeSessions.set(sessionId, { process: proc, ws, cwd, controller })

  let responseSessionId = null

  proc.stdout.on('data', (chunk) => {
    if (controller.aborted) return
    const lines = chunk.toString().split('\n').filter(Boolean)
    for (const line of lines) {
      try {
        const event = JSON.parse(line)
        handleClaudeStreamEvent(ws, sessionId, event, (sid) => { responseSessionId = sid })
      } catch {
        // Plain text fallback
        ws.send(JSON.stringify({ type: 'text', content: line }))
      }
    }
  })

  proc.stderr.on('data', (chunk) => {
    if (controller.aborted) return
    const text = chunk.toString()
    // Filter auth-related messages
    if (text.includes('ANTHROPIC_API_KEY') || text.includes('auth')) {
      ws.send(JSON.stringify({ type: 'system', content: `[Auth] ${text.trim()}` }))
    } else {
      ws.send(JSON.stringify({ type: 'error', content: text.trim() }))
    }
  })

  proc.on('close', (code) => {
    if (controller.aborted) return
    activeSessions.delete(sessionId)
    ws.send(JSON.stringify({
      type: 'done',
      sessionId: responseSessionId || sessionId,
      exitCode: code,
    }))
  })

  proc.on('error', (err) => {
    activeSessions.delete(sessionId)
    ws.send(JSON.stringify({ type: 'error', content: err.message }))
  })
}

function handleClaudeStreamEvent(ws, sessionId, event, setSessionId) {
  // Claude CLI stream-json format events
  switch (event.type) {
    case 'system':
      if (event.session_id) setSessionId(event.session_id)
      ws.send(JSON.stringify({ type: 'system', content: event.message || '' }))
      break
    case 'assistant':
      for (const block of event.message?.content || []) {
        if (block.type === 'text') {
          ws.send(JSON.stringify({ type: 'text', content: block.text }))
        } else if (block.type === 'tool_use') {
          ws.send(JSON.stringify({
            type: 'tool_use',
            toolName: block.name,
            toolInput: block.input,
          }))
        }
      }
      break
    case 'tool_result':
      ws.send(JSON.stringify({
        type: 'tool_result',
        content: typeof event.content === 'string' ? event.content : JSON.stringify(event.content),
      }))
      break
    case 'result':
      ws.send(JSON.stringify({
        type: 'result',
        content: event.result || '',
        cost: event.cost_usd,
        durationMs: event.duration_ms,
        sessionId: event.session_id,
      }))
      if (event.session_id) setSessionId(event.session_id)
      break
    default:
      // Pass through unknown events
      ws.send(JSON.stringify({ type: 'raw', event }))
  }
}

function abortSession(sessionId) {
  const session = activeSessions.get(sessionId)
  if (session) {
    session.controller.aborted = true
    try { session.process.kill('SIGTERM') } catch { }
    activeSessions.delete(sessionId)
  }
}

// ─── WebSocket: Shell / PTY ───────────────────────────────────────────────────
// Map<sessionId, { pty, ws, buffer }>
const ptyMap = new Map()
const PTY_TIMEOUT_MS = 30 * 60 * 1000 // 30min

export function handleShellWebSocket(ws, req) {
  const url = new URL(req.url, 'http://localhost')
  const sessionId = url.searchParams.get('sessionId') || uuidv4()
  const cwd = url.searchParams.get('cwd') || process.env.HOME || '/'

  // Lazy import node-pty (optional dep - graceful degrade)
  import('node-pty').then(({ default: pty }) => {
    const shell = process.env.SHELL || '/bin/bash'
    const term = pty.spawn(shell, [], {
      name: 'xterm-256color',
      cols: 120,
      rows: 30,
      cwd,
      env: process.env,
    })

    let timeout = setTimeout(() => { term.kill(); ws.close() }, PTY_TIMEOUT_MS)
    const resetTimeout = () => { clearTimeout(timeout); timeout = setTimeout(() => { term.kill(); ws.close() }, PTY_TIMEOUT_MS) }

    ptyMap.set(sessionId, { pty: term, ws })

    term.onData((data) => {
      if (ws.readyState === ws.OPEN) ws.send(JSON.stringify({ type: 'output', data }))
    })

    ws.send(JSON.stringify({ type: 'ready', sessionId, cwd }))

    ws.on('message', (raw) => {
      resetTimeout()
      try {
        const msg = JSON.parse(raw)
        if (msg.type === 'input') term.write(msg.data)
        else if (msg.type === 'resize') term.resize(msg.cols || 120, msg.rows || 30)
      } catch { term.write(raw.toString()) }
    })

    ws.on('close', () => {
      clearTimeout(timeout)
      ptyMap.delete(sessionId)
      term.kill()
    })
  }).catch(() => {
    ws.send(JSON.stringify({ type: 'error', content: 'PTY not available (install node-pty)' }))
    ws.close()
  })
}
