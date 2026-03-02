import { useState, useEffect } from 'react'
import { api } from '../../api.js'
import { SpinnerCenter } from '../shared/Spinner.jsx'
import { ErrorBanner } from '../shared/ErrorBanner.jsx'
import { Badge } from '../shared/Badge.jsx'
import '../../styles/crons.css'

function scheduleLabel(schedule) {
  if (!schedule) return '—'
  const { kind, expr, every_ms, at_ms } = schedule

  if (kind === 'cron' && expr) return expr

  if (kind === 'every' && every_ms) {
    const s = Math.round(every_ms / 1000)
    if (s < 60) return `每 ${s} 秒`
    const m = Math.round(s / 60)
    if (m < 60) return `每 ${m} 分钟`
    const h = Math.round(m / 60)
    return `每 ${h} 小时`
  }

  if (kind === 'at' && at_ms) {
    return `于 ${new Date(at_ms).toLocaleString()}`
  }

  return kind || '—'
}

function fmtTs(ms) {
  if (!ms) return '—'
  return new Date(ms).toLocaleString()
}

export function CronsPanel() {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api.crons()
      .then((d) => setJobs(d.jobs))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">⏰ 定时任务</span>
        {!loading && !error && (
          <span style={{ fontSize: 12, color: 'var(--muted)' }}>
            {jobs.filter((j) => j.enabled).length} / {jobs.length} 已启用
          </span>
        )}
      </div>
      <div className="panel-body">
        {loading && <SpinnerCenter />}
        {error && <ErrorBanner message={error} />}
        {!loading && !error && jobs.length === 0 && (
          <p className="crons-empty">暂无定时任务。</p>
        )}
        {!loading && !error && jobs.length > 0 && (
          <div className="crons-table-wrap">
            <table className="crons-table">
              <thead>
                <tr>
                  <th>名称</th>
                  <th>计划</th>
                  <th>启用</th>
                  <th>上次执行</th>
                  <th>状态</th>
                  <th>下次执行</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => {
                  const lastStatus = job.state?.last_status
                  const statusClass =
                    lastStatus === 'ok' ? 'ok'
                    : lastStatus === 'error' ? 'error'
                    : 'pending'

                  return (
                    <tr key={job.id}>
                      <td className="cron-name">{job.name || job.id}</td>
                      <td className="cron-schedule">{scheduleLabel(job.schedule)}</td>
                      <td>
                        <Badge color={job.enabled ? 'green' : 'gray'}>
                          {job.enabled ? '是' : '否'}
                        </Badge>
                      </td>
                      <td className="cron-time">{fmtTs(job.state?.last_run_at_ms)}</td>
                      <td>
                        {lastStatus ? (
                          <span className={`cron-status ${statusClass}`}>
                            {lastStatus}
                          </span>
                        ) : (
                          <span style={{ color: 'var(--muted)', fontSize: 12 }}>—</span>
                        )}
                      </td>
                      <td className="cron-time">{fmtTs(job.state?.next_run_at_ms)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
