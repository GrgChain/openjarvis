import { useState, useEffect, useRef } from 'react'
import { api } from '../../api.js'
import { Spinner, SpinnerCenter } from '../shared/Spinner.jsx'
import { ErrorBanner } from '../shared/ErrorBanner.jsx'
import '../../styles/sessions.css'

function fmtDate(iso) {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch {
    return iso
  }
}

function msgText(content) {
  if (typeof content === 'string') return content
  // litellm sometimes wraps content in an array of parts
  if (Array.isArray(content)) {
    return content
      .map((c) => (typeof c === 'string' ? c : c?.text ?? JSON.stringify(c)))
      .join('')
  }
  return JSON.stringify(content)
}

export function SessionsPanel() {
  const [sessions, setSessions] = useState([])
  const [listLoading, setListLoading] = useState(true)
  const [listError, setListError] = useState('')

  const [selected, setSelected] = useState(null)   // session key
  const [msgs, setMsgs] = useState([])
  const [detail, setDetail] = useState(null)        // full session detail
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState('')

  const bottomRef = useRef(null)

  useEffect(() => {
    api.sessions()
      .then((d) => setSessions(d.sessions))
      .catch((err) => setListError(err.message))
      .finally(() => setListLoading(false))
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [msgs])

  const selectSession = async (key) => {
    if (key === selected) return
    setSelected(key)
    setMsgs([])
    setDetail(null)
    setDetailError('')
    setDetailLoading(true)
    try {
      const data = await api.session(key)
      setDetail(data)
      setMsgs(data.messages)
    } catch (err) {
      setDetailError(err.message)
    } finally {
      setDetailLoading(false)
    }
  }

  return (
    <div className="sessions-layout">
      {/* ── Session list ── */}
      <aside className="sessions-sidebar">
        <div className="sessions-sidebar-header">
          <span className="panel-title" style={{ fontSize: 13 }}>📋 Sessions</span>
          {!listLoading && (
            <span style={{ fontSize: 11, color: 'var(--muted)' }}>{sessions.length}</span>
          )}
        </div>

        {listLoading && <SpinnerCenter size="sm" />}
        {listError && <div style={{ padding: '8px 12px' }}><ErrorBanner message={listError} /></div>}

        <div className="sessions-list">
          {sessions.map((s) => (
            <button
              key={s.key}
              className={`session-list-item${selected === s.key ? ' active' : ''}`}
              onClick={() => selectSession(s.key)}
            >
              <span className="session-list-key">{s.key}</span>
              <span className="session-list-meta">
                <span>{s.message_count} msgs</span>
                <span>{fmtDate(s.updated_at)}</span>
              </span>
            </button>
          ))}
          {!listLoading && sessions.length === 0 && (
            <p className="sessions-empty">No sessions found.</p>
          )}
        </div>
      </aside>

      {/* ── Conversation history ── */}
      <section className="sessions-history">
        {!selected && (
          <div className="sessions-placeholder">
            <span style={{ fontSize: 28 }}>💬</span>
            <span>Select a session to view history</span>
          </div>
        )}

        {selected && (
          <>
            <div className="sessions-history-header">
              <span className="session-history-key">{selected}</span>
              {detail && (
                <span style={{ fontSize: 11, color: 'var(--muted)' }}>
                  {detail.message_count} messages · updated {fmtDate(detail.updated_at)}
                </span>
              )}
              {detailLoading && <Spinner size="sm" />}
            </div>

            <div className="sessions-history-body">
              {detailError && <ErrorBanner message={detailError} />}

              {msgs.map((m, i) => (
                <div key={i} className={`sh-message ${m.role}`}>
                  <div className="sh-bubble">{msgText(m.content)}</div>
                  {m.timestamp && (
                    <span className="sh-time">
                      {new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  )}
                </div>
              ))}

              <div ref={bottomRef} />
            </div>
          </>
        )}
      </section>
    </div>
  )
}
