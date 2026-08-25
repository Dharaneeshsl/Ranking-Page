import { Col, Row } from 'react-bootstrap'

export default function StatsBar({ stats, loading }) {
  const items = [
    {
      label: 'Total Members',
      value: stats?.total_members ?? '—',
      icon: '👥',
      accent: 'accent-cyan',
    },
    {
      label: 'Total Points Awarded',
      value: (stats?.total_points ?? '—').toLocaleString?.() ?? '—',
      icon: '⚡',
      accent: 'accent-purple',
    },
    {
      label: 'Active (7 days)',
      value: stats?.active_last_7_days ?? '—',
      icon: '🔥',
      accent: 'accent-pink',
    },
    {
      label: 'Top Contributor',
      value: stats?.top_member?.name ?? '—',
      sub: stats?.top_member ? `${stats.top_member.points} pts · ${stats.top_member.level}` : null,
      icon: '🏆',
      accent: 'accent-gold',
    },
  ]

  return (
    <Row className={`g-3 mb-4 stats-row ${loading ? 'is-loading' : ''}`}>
      {items.map((it) => (
        <Col key={it.label} xs={6} lg={3}>
          <div className={`stat-card ${it.accent}`}>
            <div className="stat-icon">{it.icon}</div>
            <div className="stat-body">
              <div className="stat-label">{it.label}</div>
              <div className="stat-value" title={String(it.value)}>
                {it.value}
              </div>
              {it.sub && <div className="stat-sub">{it.sub}</div>}
            </div>
          </div>
        </Col>
      ))}
    </Row>
  )
}
