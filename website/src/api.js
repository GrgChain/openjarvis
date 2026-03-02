/**
 * API client for nanobot HTTP API channel.
 * In dev mode all requests go through Vite proxy /api/* → localhost:18790.
 * In production set VITE_API_BASE to the backend URL.
 */

const PROD_BASE = import.meta.env.VITE_API_BASE || ''
const BASE = import.meta.env.DEV ? '/api' : PROD_BASE

async function request(method, path, body) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  }
  if (body !== undefined) {
    opts.body = JSON.stringify(body)
  }
  const res = await fetch(BASE + path, opts)
  if (!res.ok) {
    let msg = `HTTP ${res.status}`
    try {
      const j = await res.json()
      msg = j.error || msg
    } catch (_) {}
    throw new Error(msg)
  }
  return res.json()
}

export const api = {
  health: () => request('GET', '/health'),

  chat: (content, chatId = 'web', senderId = 'webuser') =>
    request('POST', '/chat', { content, chat_id: chatId, sender_id: senderId }),

  sessions: () => request('GET', '/sessions'),

  session: (key) => request('GET', `/sessions/${encodeURIComponent(key)}`),

  workspaceTree: (depth = 4) => request('GET', `/workspace/tree?depth=${depth}`),

  skills: () => request('GET', '/skills'),

  crons: () => request('GET', '/crons'),
}
