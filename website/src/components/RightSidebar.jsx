import { useState, useEffect } from 'react'
import { api } from '../api.js'
import '../styles/right-sidebar.css'

function scheduleLabel(schedule) {
  if (!schedule) return '—'
  const { kind, expr, every_ms, at_ms } = schedule
  if (kind === 'cron' && expr) return expr
  if (kind === 'every' && every_ms) {
    const s = Math.round(every_ms / 1000)
    if (s < 60) return `每${s}秒`
    const m = Math.round(s / 60)
    if (m < 60) return `每${m}分钟`
    return `每${Math.round(m / 60)}小时`
  }
  if (kind === 'at' && at_ms) return `于 ${new Date(at_ms).toLocaleString()}`
  return kind || '—'
}

export function RightSidebar() {
  const [skills, setSkills] = useState([])
  const [jobs, setJobs] = useState([])

  useEffect(() => {
    api.skills().then(d => setSkills(d.skills)).catch(() => {})
    api.crons().then(d => setJobs(d.jobs)).catch(() => {})
  }, [])

  return (
    <aside className="right-sidebar">
      <section className="right-sect">
        <div className="right-sect-title">
          <span className="right-sect-icon">🔧</span> 能力
        </div>
        <div className="right-skill-grid">
          {skills.map(s => (
            <div key={s.name} className={`right-skill-card${s.available ? '' : ' dim'}`} title={s.description || s.name}>
              <span className="right-skill-card-icon">{s.emoji || '🔧'}</span>
              <span className="right-skill-card-name">{s.name}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="right-sect">
        <div className="right-sect-title">
          <span className="cron-red-dot">●</span> 自主任务
        </div>
        {jobs.length === 0 ? (
          <div className="right-empty">暂无定时任务</div>
        ) : (
          <div className="right-cron-list">
            {jobs.map(j => {
              const status = j.state?.last_status
              return (
                <div key={j.id} className={`right-cron-item${j.enabled ? '' : ' disabled'}`}>
                  <div className="right-cron-row">
                    <span className={`right-cron-dot ${j.enabled ? 'enabled' : 'off'}`}>●</span>
                    <span className="right-cron-name">{j.name || j.id}</span>
                  </div>
                  <div className="right-cron-meta">
                    <span className="right-cron-sched">{scheduleLabel(j.schedule)}</span>
                    {status && (
                      <span className={`right-cron-status ${status}`}>{status}</span>
                    )}
                  </div>
                  {j.state?.last_run_at_ms && (
                    <div className="right-cron-last">
                      上次：{new Date(j.state.last_run_at_ms).toLocaleString([], {
                        month: 'numeric', day: 'numeric',
                        hour: '2-digit', minute: '2-digit'
                      })}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </section>
    </aside>
  )
}
