/**
 * Dual Mode Claude UI - Backend Server
 * Mode 1: Claude Code (Claude CLI process management)
 * Mode 2: PCT 100 LLM Orchestration (Bushidan Multi-Agent proxy)
 */

import 'dotenv/config'
import express from 'express'
import { createServer } from 'http'
import { WebSocketServer, WebSocket } from 'ws'
import jwt from 'jsonwebtoken'
import bcrypt from 'bcrypt'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'
import { existsSync } from 'fs'
import { v4 as uuidv4 } from 'uuid'
import { handleClaudeWebSocket, handleShellWebSocket, getProjects, getSessionHistory } from './claude-mode.js'
import { handleOrchWebSocket, getOrchHealth, getOrchModels, proxyOrchChat } from './orchestration.js'

const __dirname = dirname(fileURLToPath(import.meta.url))
const PORT = parseInt(process.env.PORT || '4000')
const JWT_SECRET = process.env.JWT_SECRET || 'dual-claude-ui-secret-' + Math.random()
const UI_PASSWORD = process.env.UI_PASSWORD || ''
const PLATFORM_MODE = process.env.PLATFORM_MODE === 'true'

const app = express()
const server = createServer(app)

// ─── WebSocket Servers ───────────────────────────────────────────────────────
const wss = new WebSocketServer({ noServer: true })       // /ws  - Claude Code chat
const shellWss = new WebSocketServer({ noServer: true })  // /shell - PTY terminal
const orchWss = new WebSocketServer({ noServer: true })   // /orch - Orchestration proxy

// ─── Middleware ───────────────────────────────────────────────────────────────
app.use(express.json({ limit: '10mb' }))
app.use(express.urlencoded({ extended: true }))

// CORS for dev
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*')
  res.header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
  res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
  if (req.method === 'OPTIONS') return res.sendStatus(200)
  next()
})

// ─── Auth Helpers ─────────────────────────────────────────────────────────────
function signToken(payload) {
  return jwt.sign(payload, JWT_SECRET, { expiresIn: '24h' })
}

function verifyToken(token) {
  try { return jwt.verify(token, JWT_SECRET) } catch { return null }
}

function extractToken(req) {
  const auth = req.headers.authorization
  if (auth?.startsWith('Bearer ')) return auth.slice(7)
  return req.query.token
}

function authMiddleware(req, res, next) {
  if (PLATFORM_MODE) return next()
  if (!UI_PASSWORD) return next()          // No password set = open access
  const token = extractToken(req)
  if (!token || !verifyToken(token)) return res.status(401).json({ error: 'Unauthorized' })
  next()
}

function wsVerify(info, cb) {
  if (PLATFORM_MODE || !UI_PASSWORD) return cb(true)
  const url = new URL(info.req.url, 'http://localhost')
  const token = url.searchParams.get('token') ||
    info.req.headers.authorization?.replace('Bearer ', '')
  if (token && verifyToken(token)) return cb(true)
  cb(false, 401, 'Unauthorized')
}

// ─── Auth Routes ──────────────────────────────────────────────────────────────
app.get('/api/health', (req, res) => {
  res.json({
    status: 'ok',
    version: '1.0.0',
    modes: ['claude-code', 'orchestration'],
    passwordRequired: !PLATFORM_MODE && !!UI_PASSWORD,
    timestamp: new Date().toISOString()
  })
})

app.post('/api/auth/login', async (req, res) => {
  const { password } = req.body
  if (!UI_PASSWORD) {
    return res.json({ token: signToken({ user: 'admin', role: 'admin' }), user: 'admin' })
  }
  if (!password) return res.status(400).json({ error: 'Password required' })
  const valid = password === UI_PASSWORD || await bcrypt.compare(password, UI_PASSWORD).catch(() => false)
  if (!valid) return res.status(401).json({ error: 'Invalid password' })
  const token = signToken({ user: 'admin', role: 'admin' })
  res.json({ token, user: 'admin' })
})

// ─── Mode 1: Claude Code Routes ───────────────────────────────────────────────
app.get('/api/claude/projects', authMiddleware, async (req, res) => {
  try {
    const projects = await getProjects()
    res.json({ projects })
  } catch (err) {
    res.status(500).json({ error: err.message })
  }
})

app.get('/api/claude/sessions/:projectPath', authMiddleware, async (req, res) => {
  try {
    const history = await getSessionHistory(decodeURIComponent(req.params.projectPath))
    res.json({ history })
  } catch (err) {
    res.status(500).json({ error: err.message })
  }
})

app.get('/api/claude/auth-status', authMiddleware, async (req, res) => {
  try {
    const { checkClaudeAuth } = await import('./claude-mode.js')
    const status = await checkClaudeAuth()
    res.json(status)
  } catch (err) {
    res.status(500).json({ error: err.message })
  }
})

// ─── Mode 2: Orchestration Routes ────────────────────────────────────────────
app.get('/api/orch/health', authMiddleware, async (req, res) => {
  try {
    const health = await getOrchHealth()
    res.json(health)
  } catch (err) {
    res.status(503).json({ error: 'Orchestration system unavailable', detail: err.message })
  }
})

app.get('/api/orch/models', authMiddleware, async (req, res) => {
  try {
    const models = await getOrchModels()
    res.json(models)
  } catch (err) {
    res.status(503).json({ error: 'Orchestration system unavailable', detail: err.message })
  }
})

app.post('/api/orch/chat', authMiddleware, async (req, res) => {
  try {
    const result = await proxyOrchChat(req.body)
    res.json(result)
  } catch (err) {
    res.status(503).json({ error: 'Orchestration system unavailable', detail: err.message })
  }
})

// ─── Static Files ─────────────────────────────────────────────────────────────
const distPath = join(__dirname, '..', 'dist')
if (existsSync(distPath)) {
  app.use(express.static(distPath))
  app.get('*', (req, res) => res.sendFile(join(distPath, 'index.html')))
}

// ─── WebSocket Upgrade ────────────────────────────────────────────────────────
server.on('upgrade', (req, socket, head) => {
  const pathname = new URL(req.url, 'http://localhost').pathname

  if (pathname === '/ws') {
    wss.handleUpgrade(req, socket, head, (ws) => wss.emit('connection', ws, req))
  } else if (pathname === '/shell') {
    shellWss.handleUpgrade(req, socket, head, (ws) => shellWss.emit('connection', ws, req))
  } else if (pathname === '/orch') {
    orchWss.handleUpgrade(req, socket, head, (ws) => orchWss.emit('connection', ws, req))
  } else {
    socket.destroy()
  }
})

// ─── WebSocket Handlers ───────────────────────────────────────────────────────
wss.on('connection', (ws, req) => {
  if (!wsVerify({ req }, (ok, code, msg) => { if (!ok) { ws.close(code, msg) } })) return
  handleClaudeWebSocket(ws, req)
})

shellWss.on('connection', (ws, req) => {
  if (!wsVerify({ req }, (ok, code, msg) => { if (!ok) { ws.close(code, msg) } })) return
  handleShellWebSocket(ws, req)
})

orchWss.on('connection', (ws, req) => {
  if (!wsVerify({ req }, (ok, code, msg) => { if (!ok) { ws.close(code, msg) } })) return
  handleOrchWebSocket(ws, req)
})

// ─── Start ────────────────────────────────────────────────────────────────────
server.listen(PORT, '0.0.0.0', () => {
  console.log(`\n╔══════════════════════════════════════════╗`)
  console.log(`║      Dual Mode Claude UI - v1.0.0        ║`)
  console.log(`╠══════════════════════════════════════════╣`)
  console.log(`║  Server: http://0.0.0.0:${PORT}            ║`)
  console.log(`║  Mode 1: Claude Code  (ws://...:/ws)     ║`)
  console.log(`║  Mode 2: Orchestration(ws://...:/orch)   ║`)
  console.log(`╚══════════════════════════════════════════╝\n`)
})

export default server
