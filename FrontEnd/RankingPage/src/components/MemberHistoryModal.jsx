import { useEffect, useState } from 'react'
import { Badge, Button, Modal, Spinner, Table } from 'react-bootstrap'
import api, { errorMessage } from '../api'
import { useToasts } from './Toasts'

const LEVEL_BADGE = {
  Bronze: 'background-color: #8d6e63; color: #fff;',
  Silver: 'background-color: #b0bec5; color: #102027;',
  Gold: 'background-color: #ffb300; color: #3e2723;',
  Platinum: 'background-color: linear-gradient(90deg,#26c6da,#7e57c2); color: #fff;',
}

function fmtDate(value) {
  if (!value) return '—'
  try {
    return new Date(value).toLocaleString()
  } catch {
    return String(value)
  }
}

export default function MemberHistoryModal({ member, show, onHide, onDeleted, onError }) {
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const { push } = useToasts()

  useEffect(() => {
    if (!show || !member?.id) return
    let cancelled = false
    setLoading(true)
    setError('')
    api
      .get(`/members/${member.id}`)
      .then((res) => {
        if (cancelled) return
        setProfile(res.data.data)
      })
      .catch((err) => {
        if (cancelled) return
        setError(errorMessage(err, 'Failed to load member'))
      })
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [show, member?.id])

  const removeContribution = async (contribId) => {
    if (!window.confirm('Remove this contribution? Points will be recalculated.')) return
    try {
      const res = await api.delete(`/members/${member.id}/contributions/${contribId}`)
      push(res.data.message || 'Contribution removed', 'success')
      setProfile((p) => (p ? { ...p, points: res.data.data.total_points, level: res.data.data.level, badges: res.data.data.badges } : p))
      onDeleted?.()
    } catch (err) {
      push(errorMessage(err, 'Failed to remove contribution'), 'error')
      onError?.(err)
    }
  }

  const badges = profile?.badges || []
  return (
    <Modal show={show} onHide={onHide} size="lg" centered contentClassName="neon-modal">
      <Modal.Header closeButton closeVariant="white">
        <Modal.Title>
          {profile?.name || member?.name} <span className="modal-sub">· Rank #{profile?.rank ?? '—'}</span>
        </Modal.Title>
      </Modal.Header>
      <Modal.Body>
        {loading && (
          <div className="text-center py-4">
            <Spinner animation="border" variant="info" />
          </div>
        )}
        {error && <div className="alert alert-danger">{error}</div>}
        {profile && (
          <>
            <div className="member-summary mb-4">
              <div className="member-summary-item">
                <span className="ms-label">Points</span>
                <span className="ms-value">{profile.points}</span>
              </div>
              <div className="member-summary-item">
                <span className="ms-label">Level</span>
                <span className="ms-value">
                  <span className="level-chip" style={LEVEL_BADGE[profile.level] || {}}>{profile.level}</span>
                </span>
              </div>
              <div className="member-summary-item">
                <span className="ms-label">Next level at</span>
                <span className="ms-value">{profile.maxed ? 'MAX' : `${profile.next_level_points} pts (${profile.progress}%)`}</span>
              </div>
              <div className="member-summary-item">
                <span className="ms-label">Contributions</span>
                <span className="ms-value">{profile.total_contributions}</span>
              </div>
            </div>

            {badges.length > 0 && (
              <div className="mb-4">
                <h6 className="section-title">Badges</h6>
                <div className="d-flex flex-wrap gap-2">
                  {badges.map((b) => (
                    <span key={b} className="badge-chip">{b}</span>
                  ))}
                </div>
              </div>
            )}

            {Object.keys(profile.contributions_by_type || {}).length > 0 && (
              <div className="mb-4">
                <h6 className="section-title">Contribution Breakdown</h6>
                <Table size="sm" className="lb-table" responsive>
                  <tbody>
                    {Object.entries(profile.contributions_by_type).map(([key, v]) => (
                      <tr key={key}>
                        <td>{v.label}</td>
                        <td className="text-end">{v.count}×</td>
                        <td className="text-end">{v.total_points} pts</td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </div>
            )}

            <h6 className="section-title">Recent Contributions</h6>
            {profile.recent_contributions?.length ? (
              <div className="contrib-list">
                {profile.recent_contributions.map((c, i) => (
                  <div className="contrib-item" key={`${c.id || c.timestamp}-${i}`}>
                    <div className="contrib-main">
                      <span className="contrib-label">{c.label}</span>
                      <span className="contrib-desc">{c.description || ''}</span>
                      <span className="contrib-date">{fmtDate(c.timestamp)}</span>
                    </div>
                    <div className="contrib-right">
                      <span className={`contrib-points ${c.points < 0 ? 'neg' : ''}`}>
                        {c.points > 0 ? '+' : ''}{c.points} pts
                      </span>
                      <Badge
                        bg="outline-danger"
                        className="contrib-del"
                        onClick={() => removeContribution(c.id)}
                        title="Remove contribution"
                      >
                        ×
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-muted-soft">No contributions yet.</p>
            )}
          </>
        )}
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={onHide}>Close</Button>
      </Modal.Footer>
    </Modal>
  )
}
