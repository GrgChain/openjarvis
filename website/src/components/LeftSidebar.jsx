import { useState, useEffect } from 'react'
import { api } from '../api.js'
import { SpinnerCenter } from './shared/Spinner.jsx'
import '../styles/left-sidebar.css'

function fmtDate(iso) {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    const now = new Date()
    const diff = Math.floor((now - d) / 86400000)
    if (diff === 0) return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    if (diff === 1) return '昨天'
    if (diff < 7) return `${diff}天前`
    return d.toLocaleDateString([], { month: 'numeric', day: 'numeric' })
  } catch { return '' }
}

function WsNode({ node, depth = 0 }) {
  const isDir = node.type === 'directory'
  const [open, setOpen] = useState(false)
  return (
    <div className="ws-node-wrap">
      <div
        className="ws-node-row"
        style={{ paddingLeft: 8 + depth * 14 }}
        onClick={() => isDir && setOpen(v => !v)}
      >
        {isDir && <span className="ws-node-chevron" style={{ transform: open ? 'rotate(90deg)' : '' }}>▶</span>}
        <span className="ws-node-icon">{isDir ? '📁' : '📄'}</span>
        <span className="ws-node-name">{node.name}</span>
      </div>
      {isDir && open && node.children?.map((c, i) => (
        <WsNode key={i} node={c} depth={depth + 1} />
      ))}
    </div>
  )
}

export function LeftSidebar({ selectedKey, onSelect, onNewChat, online, refreshSig }) {
  const [sessions, setSessions] = useState([])
  const [wsOpen, setWsOpen] = useState(false)
  const [tree, setTree] = useState(null)
  const [wsLoading, setWsLoading] = useState(false)

  useEffect(() => {
    api.sessions().then(d => setSessions(d.sessions)).catch(() => {})
  }, [refreshSig])

  const toggleWs = async () => {
    setWsOpen(v => !v)
    if (!wsOpen && !tree) {
      setWsLoading(true)
      try { const d = await api.workspaceTree(3); setTree(d) } catch {}
      finally { setWsLoading(false) }
    }
  }

  const dotCls = online === true ? 'online' : online === false ? 'offline' : ''

  return (
    <aside className="left-sidebar">
      <div className="left-logo">
        <svg width="20" height="20" viewBox="0 0 32 32" fill="none">
          <rect width="32" height="32" rx="8" fill="#6366f1"/>
          <circle cx="16" cy="13" r="5" fill="white" opacity="0.9"/>
          <path d="M8 26c0-4.418 3.582-8 8-8s8 3.582 8 8" stroke="white" strokeWidth="2" strokeLinecap="round" opacity="0.9"/>
        </svg>
        <span className="left-logo-text">openjarvis</span>
        <span className={`left-status-dot ${dotCls}`} />
      </div>

      <div className="left-top">
        <button className="new-chat-btn" onClick={onNewChat}>＋ 新建对话</button>
      </div>

      <div className="left-sessions">
        {sessions.map(s => (
          <button
            key={s.key}
            className={`sess-item${selectedKey === s.key ? ' active' : ''}`}
            onClick={() => onSelect(s.key)}
          >
            <span className="sess-title">{s.key}</span>
            <span className="sess-date">{fmtDate(s.updated_at)}</span>
          </button>
        ))}
      </div>

      <div className="left-workspace">
        <button className="ws-toggle-btn" onClick={toggleWs}>
          <span className="ws-chevron" style={{ transform: wsOpen ? 'rotate(90deg)' : '' }}>▶</span>
          <span>🗂</span>
          <span>工作区</span>
        </button>
        {wsOpen && (
          <div className="ws-tree">
            {wsLoading && <SpinnerCenter size="sm" />}
            {tree && (tree.children ?? []).map((c, i) => <WsNode key={i} node={c} />)}
          </div>
        )}
      </div>
    </aside>
  )
}
