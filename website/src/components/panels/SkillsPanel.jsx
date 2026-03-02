import { useState, useEffect } from 'react'
import { api } from '../../api.js'
import { SpinnerCenter } from '../shared/Spinner.jsx'
import { ErrorBanner } from '../shared/ErrorBanner.jsx'
import { Badge } from '../shared/Badge.jsx'
import '../../styles/skills.css'

export function SkillsPanel() {
  const [skills, setSkills] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api.skills()
      .then((d) => setSkills(d.skills))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">🔧 技能</span>
        {!loading && !error && (
          <span style={{ fontSize: 12, color: 'var(--muted)' }}>
            {skills.filter((s) => s.available).length} / {skills.length} 可用
          </span>
        )}
      </div>
      <div className="panel-body">
        {loading && <SpinnerCenter />}
        {error && <ErrorBanner message={error} />}
        {!loading && !error && skills.length === 0 && (
          <p className="skills-empty">暂无技能。</p>
        )}
        {!loading && !error && skills.length > 0 && (
          <div className="skills-grid">
            {skills.map((skill) => (
              <div
                key={skill.name}
                className={`skill-card${skill.available ? '' : ' unavailable'}`}
              >
                <div className="skill-card-header">
                  <span className="skill-emoji">{skill.emoji || '🔌'}</span>
                  <span className="skill-name">{skill.name}</span>
                </div>

                <div className="skill-badges">
                  <Badge color={skill.available ? 'green' : 'red'}>
                    {skill.available ? '可用' : '不可用'}
                  </Badge>
                  {skill.source && (
                    <Badge color="blue">{skill.source}</Badge>
                  )}
                  {skill.always && (
                    <Badge color="gray">常驻</Badge>
                  )}
                </div>

                {skill.description && (
                  <p className="skill-description">{skill.description}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
