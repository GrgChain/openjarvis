import { useState, useRef, useEffect, useCallback } from 'react'
import { api } from '../../api.js'
import { SpinnerCenter } from '../shared/Spinner.jsx'
import { ErrorBanner } from '../shared/ErrorBanner.jsx'
import { ErrorBoundary } from '../shared/ErrorBoundary.jsx'
import { Markdown } from '../shared/Markdown.jsx'
import '../../styles/chat.css'

const WEB_KEY = 'web'
const HTTP_API_PREFIX = 'http_api:'

// Extract chat_id from session key. Returns null for non-httpapi sessions (read-only).
function getChatId(key) {
  if (key === WEB_KEY) return WEB_KEY
  if (key.startsWith(HTTP_API_PREFIX)) return key.slice(HTTP_API_PREFIX.length)
  return null
}

function msgText(content) {
  if (typeof content === 'string') return content
  if (Array.isArray(content))
    return content.map(c => typeof c === 'string' ? c : c?.text ?? JSON.stringify(c)).join('')
  return JSON.stringify(content)
}

function Avatar({ role }) {
  return (
    <div className={`msg-avatar msg-avatar-${role}`}>
      {role === 'assistant' ? 'J' : '你'}
    </div>
  )
}

function ToolCallBlock({ toolCalls }) {
  const [open, setOpen] = useState(false)
  if (!toolCalls?.length) return null
  return (
    <div className="tool-calls">
      <button className="tool-calls-toggle" onClick={() => setOpen(v => !v)}>
        <span className="tool-calls-chevron" style={{ transform: open ? 'rotate(90deg)' : '' }}>▶</span>
        <span className="tool-calls-icon">⚙</span>
        <span>使用了 {toolCalls.length} 个工具</span>
      </button>
      {open && (
        <div className="tool-calls-list">
          {toolCalls.map((tc, i) => {
            let args = tc.arguments
            try { args = JSON.stringify(JSON.parse(tc.arguments), null, 2) } catch {}
            return (
              <div key={i} className="tool-call-item">
                <div className="tool-call-name">⚙ {tc.name}</div>
                {args && <pre className="tool-call-args">{args}</pre>}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function ToolResultBlock({ msg }) {
  const [open, setOpen] = useState(false)
  const text = msgText(msg.content)
  const lines = text.split('\n').length
  const preview = lines > 4 ? text.split('\n').slice(0, 3).join('\n') + '\n...' : text
  return (
    <div className="tool-result">
      <button className="tool-result-toggle" onClick={() => setOpen(v => !v)}>
        <span className="tool-result-chevron" style={{ transform: open ? 'rotate(90deg)' : '' }}>▶</span>
        <span className="tool-result-icon">📤</span>
        <span className="tool-result-name">{msg.name}</span>
        <span className="tool-result-lines">{lines} 行</span>
      </button>
      {open
        ? <pre className="tool-result-content">{text}</pre>
        : <pre className="tool-result-content tool-result-preview">{preview}</pre>
      }
    </div>
  )
}

function MessageCard({ msg }) {
  const { role, content, ts, tool_calls } = msg
  const text = msgText(content)

  if (role === 'tool') {
    return <ToolResultBlock msg={msg} />
  }

  return (
    <div className={`msg-group msg-group-${role}`}>
      <div className="msg-meta">
        <Avatar role={role} />
        <span className="msg-role-label">{role === 'assistant' ? 'ASSISTANT' : 'YOU'}</span>
        {ts && (
          <span className="msg-ts">
            {new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        )}
      </div>
      <div className="msg-card">
        {tool_calls && <ToolCallBlock toolCalls={tool_calls} />}
        {text && (
          role === 'assistant'
            ? <ErrorBoundary><Markdown>{text}</Markdown></ErrorBoundary>
            : <div className="msg-plain">{text}</div>
        )}
      </div>
    </div>
  )
}

function TypingCard() {
  return (
    <div className="msg-group msg-group-assistant">
      <div className="msg-meta">
        <Avatar role="assistant" />
        <span className="msg-role-label">ASSISTANT</span>
      </div>
      <div className="msg-card">
        <div className="typing-indicator">
          <div className="typing-dot" />
          <div className="typing-dot" />
          <div className="typing-dot" />
        </div>
      </div>
    </div>
  )
}

export function ChatPanel({ selectedKey, onSessionsRefresh }) {
  const chatId = getChatId(selectedKey)
  const canChat = chatId !== null
  const isWeb = selectedKey === WEB_KEY
  const [webMessages, setWebMessages] = useState([])
  const [historyMsgs, setHistoryMsgs] = useState([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyError, setHistoryError] = useState('')
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [sendError, setSendError] = useState('')
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)

  // Load history when non-web session selected
  useEffect(() => {
    if (isWeb) return
    setHistoryMsgs([])
    setHistoryError('')
    setHistoryLoading(true)
    api.session(selectedKey)
      .then(d => setHistoryMsgs(d.messages.map(m => ({ ...m, ts: m.timestamp }))))
      .catch(err => setHistoryError(err.message))
      .finally(() => setHistoryLoading(false))
  }, [selectedKey, isWeb])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [webMessages, historyMsgs, sending])

  const send = useCallback(async () => {
    const content = input.trim()
    if (!content || sending) return
    setInput('')
    setSendError('')
    const userMsg = { role: 'user', content, ts: new Date() }
    if (isWeb) {
      setWebMessages(prev => [...prev, userMsg])
    } else {
      setHistoryMsgs(prev => [...prev, userMsg])
    }
    setSending(true)
    try {
      await api.chat(content, chatId)
      // Reload full session to get all tool call messages
      const sessionKey = isWeb ? HTTP_API_PREFIX + chatId : selectedKey
      const d = await api.session(sessionKey)
      const msgs = d.messages.map(m => ({ ...m, ts: m.timestamp }))
      if (isWeb) {
        setWebMessages(msgs)
      } else {
        setHistoryMsgs(msgs)
      }
      onSessionsRefresh?.()
    } catch (err) {
      setSendError(err.message)
    } finally {
      setSending(false)
      textareaRef.current?.focus()
    }
  }, [input, sending, chatId, isWeb, selectedKey, onSessionsRefresh])

  const handleKeyDown = e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }

  const displayMsgs = isWeb ? webMessages : historyMsgs

  return (
    <div className="chat-col">
      {!isWeb && (
        <div className="chat-history-header">
          <span className="chat-history-key">{selectedKey}</span>
        </div>
      )}

      <div
        className="chat-messages"
        onClick={e => {
          if (window.getSelection()?.toString()) return
          if (['A','BUTTON','INPUT','TEXTAREA','CODE','PRE'].includes(e.target.tagName)) return
          textareaRef.current?.focus()
        }}
      >
        {historyLoading && <SpinnerCenter />}
        {historyError && <div style={{padding:'0 8px'}}><ErrorBanner message={historyError} /></div>}

        {!historyLoading && displayMsgs.length === 0 && (
          <div className="chat-empty">
            <span className="chat-empty-icon">🤖</span>
            <span>发送消息开始对话</span>
          </div>
        )}

        {!historyLoading && displayMsgs.map((m, i) => (
          <MessageCard key={i} msg={m} />
        ))}

        {sending && <TypingCard />}
        <div ref={bottomRef} />
      </div>

      <div className="chat-input-wrap">
        {sendError && <div style={{padding:'0 0 8px'}}><ErrorBanner message={sendError}/></div>}
        {canChat ? (
          <>
            <div className="chat-input-row">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="输入消息... (Enter 发送, Shift+Enter 换行)"
                rows={1}
                disabled={sending}
              />
              <button className="send-btn" onClick={send} disabled={sending || !input.trim()}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="22" y1="2" x2="11" y2="13"/>
                  <polygon points="22 2 15 22 11 13 2 9 22 2"/>
                </svg>
              </button>
            </div>
            <div className="chat-input-hint">按 Enter 发送 · Shift+Enter 换行</div>
          </>
        ) : (
          <div className="chat-readonly-hint">此对话来自其他渠道，网页端仅供查看</div>
        )}
      </div>
    </div>
  )
}
