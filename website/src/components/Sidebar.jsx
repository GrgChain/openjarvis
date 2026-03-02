const NAV = [
  { id: 'chat',      icon: '💬', label: '对话' },
  { id: 'workspace', icon: '📁', label: '工作区' },
  { id: 'skills',    icon: '🔧', label: '技能' },
  { id: 'crons',     icon: '⏰', label: '定时任务' },
]

export function Sidebar({ active, onNav }) {
  return (
    <nav className="sidebar">
      <div className="sidebar-logo">
        <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect width="32" height="32" rx="8" fill="#6366f1"/>
          <circle cx="16" cy="13" r="5" fill="white" opacity="0.9"/>
          <path d="M8 26c0-4.418 3.582-8 8-8s8 3.582 8 8" stroke="white" strokeWidth="2" strokeLinecap="round" opacity="0.9"/>
        </svg>
        nanobot
      </div>

      {NAV.map(({ id, icon, label }) => (
        <button
          key={id}
          className={`nav-item${active === id ? ' active' : ''}`}
          onClick={() => onNav(id)}
        >
          <span className="nav-icon">{icon}</span>
          {label}
        </button>
      ))}
    </nav>
  )
}
