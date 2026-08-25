import React, { useCallback, useEffect, useMemo, useState } from 'react'
import 'bootstrap/dist/css/bootstrap.min.css'
import { Button, Col, Container, Form, Modal, Row, Spinner, Table } from 'react-bootstrap'
import ElectricBorder from './ElectricBorder'
import LoginModal from './components/LoginModal'
import MemberHistoryModal from './components/MemberHistoryModal'
import StatsBar from './components/StatsBar'
import { ToastStack, useToasts } from './components/Toasts'
import { AuthProvider, useAuth } from './context/AuthContext'
import api, { API_BASE_URL, errorMessage } from './api'
import './App.css'

const ACTION_TYPES = [
  { value: 'attend_event', label: 'Attend Event', points: 10 },
  { value: 'volunteer_task', label: 'Volunteer Task', points: 20 },
  { value: 'lead_event', label: 'Lead Event', points: 50 },
  { value: 'upload_docs', label: 'Upload Docs', points: 15 },
  { value: 'bring_sponsorship', label: 'Bring Sponsorship', points: 100 },
]

const LEVEL_STYLE = {
  Bronze: 'level-bronze',
  Silver: 'level-silver',
  Gold: 'level-gold',
  Platinum: 'level-platinum',
}

const TIME_FRAMES = [
  { value: 'all', label: 'All Time' },
  { value: 'week', label: 'This Week' },
  { value: 'month', label: 'This Month' },
  { value: 'year', label: 'This Year' },
  { value: 'custom', label: 'Custom Range' },
]

function Dashboard() {
  const { user, loading: authLoading, logout, clearUser } = useAuth()
  const { toasts, push, remove } = useToasts()

  const [leaderboard, setLeaderboard] = useState([])
  const [stats, setStats] = useState(null)
  const [timeFrame, setTimeFrame] = useState('year')
  const [startDate, setStartDate] = useState(`${new Date().getFullYear()}-01-01`)
  const [endDate, setEndDate] = useState(`${new Date().getFullYear()}-12-31`)
  const [search, setSearch] = useState('')
  const [showLogin, setShowLogin] = useState(false)
  const [playTitleAnim, setPlayTitleAnim] = useState(false)

  const [loadingLb, setLoadingLb] = useState(true)
  const [loadingStats, setLoadingStats] = useState(true)
  const [isAdding, setIsAdding] = useState(false)

  const [viewMember, setViewMember] = useState(null)
  const [editingMember, setEditingMember] = useState(null)
  const [editPoints, setEditPoints] = useState('')
  const [editReason, setEditReason] = useState('')
  const [isUpdating, setIsUpdating] = useState(false)

  // ---------------------------------------------------------------- fetching
  const fetchLeaderboard = useCallback(async () => {
    setLoadingLb(true)
    try {
      const params = { time_frame: timeFrame }
      if (timeFrame === 'custom') {
        params.start_date = startDate
        params.end_date = endDate
      }
      const res = await api.get('/leaderboard', { params })
      setLeaderboard(res.data?.data?.leaderboard || [])
    } catch (err) {
      push(errorMessage(err, 'Failed to load leaderboard'), 'error')
    } finally {
      setLoadingLb(false)
    }
  }, [timeFrame, startDate, endDate, push])

  const fetchStats = useCallback(async () => {
    try {
      const res = await api.get('/stats')
      setStats(res.data?.data || null)
    } catch (err) {
      push(errorMessage(err, 'Failed to load stats'), 'error')
    } finally {
      setLoadingStats(false)
    }
  }, [push])

  const refreshAll = useCallback(async () => {
    await Promise.all([fetchLeaderboard(), fetchStats()])
  }, [fetchLeaderboard, fetchStats])

  useEffect(() => {
    fetchLeaderboard()
  }, [fetchLeaderboard])

  useEffect(() => {
    fetchStats()
  }, [fetchStats])

  useEffect(() => {
    const t = setTimeout(() => setPlayTitleAnim(true), 200)
    return () => clearTimeout(t)
  }, [])

  useEffect(() => {
    const onExpired = () => {
      clearUser()
      push('Session expired — please sign in again', 'warning')
    }
    window.addEventListener('auth:expired', onExpired)
    return () => window.removeEventListener('auth:expired', onExpired)
  }, [clearUser, push])

  // ---------------------------------------------------------------- actions
  const addPoints = async (name, action, description) => {
    if (!user) {
      push('Please sign in as an admin to award points', 'warning')
      setShowLogin(true)
      return
    }
    if (!name.trim()) {
      push('Please enter a member name', 'warning')
      return
    }
    setIsAdding(true)
    try {
      const res = await api.post('/points', { name: name.trim(), action, description })
      push(res.data.message, 'success')
      setName('')
      setAction('attend_event')
      setDescription('')
      await refreshAll()
    } catch (err) {
      push(errorMessage(err, 'Failed to add points'), 'error')
    } finally {
      setIsAdding(false)
    }
  }

  const handleEdit = (member) => {
    setEditingMember(member)
    setEditPoints(String(member.total_points ?? member.points ?? 0))
    setEditReason('')
  }

  const saveEdit = async (e) => {
    e.preventDefault()
    if (!editingMember) return
    const points = parseInt(editPoints, 10)
    if (Number.isNaN(points) || points < 0) {
      push('Please enter a valid non-negative number', 'warning')
      return
    }
    setIsUpdating(true)
    try {
      const res = await api.put(`/members/${editingMember.id}`, {
        points,
        reason: editReason.trim() || null,
      })
      push(res.data.message || 'Points updated', 'success')
      setEditingMember(null)
      await refreshAll()
    } catch (err) {
      push(errorMessage(err, 'Failed to update points'), 'error')
    } finally {
      setIsUpdating(false)
    }
  }

  const handleDelete = async (member) => {
    if (!window.confirm(`Delete "${member.name}" permanently?`)) return
    try {
      const res = await api.delete(`/members/${member.id}`)
      push(res.data.message || 'Member deleted', 'success')
      await refreshAll()
    } catch (err) {
      push(errorMessage(err, 'Failed to delete member'), 'error')
    }
  }

  const handleLogout = async () => {
    await logout()
    push('Signed out', 'info')
  }

  const exportCsv = () => {
    const params = new URLSearchParams({ time_frame: timeFrame })
    if (timeFrame === 'custom') {
      params.set('start_date', startDate)
      params.set('end_date', endDate)
    }
    window.open(`${API_BASE_URL}/leaderboard/export?${params.toString()}`, '_blank')
  }

  // ---------------------------------------------------------------- derived
  const filtered = useMemo(() => {
    if (!search.trim()) return leaderboard
    const q = search.trim().toLowerCase()
    return leaderboard.filter((m) => m.name.toLowerCase().includes(q))
  }, [leaderboard, search])

  const [name, setName] = useState('')
  const [action, setAction] = useState('attend_event')
  const [description, setDescription] = useState('')

  const getMedalClass = (rank) =>
    rank === 1 ? 'medal medal-gold' : rank === 2 ? 'medal medal-silver' : rank === 3 ? 'medal medal-bronze' : 'medal'

  const isAuthenticated = !!user

  return (
    <div className="app-container">
      <div className="bg-grid" />
      <svg className="eb-svg" aria-hidden="true" focusable="false">
        <defs>
          <linearGradient id="eb-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#00e5ff" />
            <stop offset="100%" stopColor="#8a2be2" />
          </linearGradient>
        </defs>
      </svg>

      <Container className="main-content" style={{ maxWidth: '1240px' }}>
        {/* ---------------------------------------------------------- header */}
        <div className="d-flex justify-content-between align-items-center w-100 header-row">
          <header className="app-header">
            <div className={`title-hero d-flex align-items-center ${playTitleAnim ? 'play' : ''}`}>
              <div className="logo-container me-3">
                <img src="/FAVICON.png" alt="Logo" className="header-logo" />
              </div>
              <div className="title-text-block">
                <h1 className="panel-title m-0">Gamified Ranking System</h1>
                <div className="title-sub">Contribute · Level Up · Lead the Board</div>
              </div>
            </div>
          </header>
          <div className="auth-panel d-flex align-items-center gap-2">
            {isAuthenticated ? (
              <>
                <span className="user-chip" title={user.email}>
                  👑 {user.name || user.email}
                </span>
                <Button variant="outline-info" size="sm" onClick={handleLogout}>
                  Sign out
                </Button>
              </>
            ) : (
              <Button variant="outline-info" size="sm" onClick={() => setShowLogin(true)}>
                🔐 Admin Sign In
              </Button>
            )}
          </div>
        </div>

        {/* ----------------------------------------------------------- stats */}
        <StatsBar stats={stats} loading={loadingStats} />

        {/* ------------------------------------------------------------ forms */}
        <div className="mb-5">
          <Row className="g-4 align-items-stretch">
            <Col md={6} className="d-flex">
              <ElectricBorder color="#d21349ff" speed={1} chaos={0.5} thickness={2} style={{ borderRadius: 16, width: '100%' }}>
                <div className="p-3 panel-card fade-slide-in h-100">
                  <h4 className="mb-3">⚡ Add Contribution</h4>
                  <Form
                    onSubmit={(e) => {
                      e.preventDefault()
                      addPoints(name, action, description)
                    }}
                  >
                    <Form.Group className="mb-3">
                      <Form.Label>Member Name</Form.Label>
                      <Form.Control
                        className="control-neon"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="Enter name"
                        maxLength={120}
                      />
                    </Form.Group>
                    <Form.Group className="mb-3">
                      <Form.Label>Action</Form.Label>
                      <div className="select-caret">
                        <Form.Select className="control-neon" value={action} onChange={(e) => setAction(e.target.value)} aria-label="Select action type">
                          {ACTION_TYPES.map((a) => (
                            <option key={a.value} value={a.value}>
                              {a.label} (+{a.points})
                            </option>
                          ))}
                        </Form.Select>
                      </div>
                    </Form.Group>
                    <Form.Group className="mb-3">
                      <Form.Label>Note (optional)</Form.Label>
                      <Form.Control
                        className="control-neon"
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                        placeholder="e.g. GDG DevFest 2026"
                        maxLength={500}
                      />
                    </Form.Group>
                    <Button type="submit" className="w-100 mb-2 btn-neon" disabled={isAdding || authLoading}>
                      {isAdding ? 'Awarding…' : 'Award Points'}
                    </Button>
                    {!isAuthenticated && (
                      <div className="auth-hint">🔒 Admin sign-in required to award points</div>
                    )}
                  </Form>
                </div>
              </ElectricBorder>
            </Col>

            <Col md={6} className="d-flex">
              <ElectricBorder color="#f74f0dff" speed={1} chaos={0.5} thickness={2} style={{ borderRadius: 16, width: '100%' }}>
                <div className="p-3 panel-card fade-slide-in h-100">
                  <h4 className="mb-3">📅 Filter Period</h4>
                  <Form>
                    <Form.Group className="mb-3">
                      <Form.Label>Time Frame</Form.Label>
                      <div className="select-caret">
                        <Form.Select className="control-neon" value={timeFrame} onChange={(e) => setTimeFrame(e.target.value)} aria-label="Time frame">
                          {TIME_FRAMES.map((t) => (
                            <option key={t.value} value={t.value}>
                              {t.label}
                            </option>
                          ))}
                        </Form.Select>
                      </div>
                    </Form.Group>
                    {timeFrame === 'custom' && (
                      <Row>
                        <Col>
                          <Form.Group className="mb-3">
                            <Form.Label>Start Date</Form.Label>
                            <Form.Control className="control-neon" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
                          </Form.Group>
                        </Col>
                        <Col>
                          <Form.Group className="mb-3">
                            <Form.Label>End Date</Form.Label>
                            <Form.Control className="control-neon" type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
                          </Form.Group>
                        </Col>
                      </Row>
                    )}
                    {timeFrame !== 'custom' && (
                      <div className="range-preview">
                        Showing contributions for{' '}
                        <strong>{TIME_FRAMES.find((t) => t.value === timeFrame)?.label.toLowerCase()}</strong>
                      </div>
                    )}
                    <Button variant="outline-info" onClick={exportCsv} className="w-100 mb-1">
                      📥 Export Leaderboard (CSV)
                    </Button>
                  </Form>
                </div>
              </ElectricBorder>
            </Col>
          </Row>
        </div>

        {/* ------------------------------------------------------ leaderboard */}
        <main className="app-main">
          <div className="dashboard-section">
            <div className="p-3 panel-card fade-slide-in">
              <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
                <h4 className="mb-0">🏆 Leaderboard</h4>
                <Form.Control
                  className="control-neon search-input"
                  placeholder="Search member…"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  aria-label="Search members"
                />
              </div>
              <div className="table-responsive">
                <Table striped hover className="lb-table">
                  <thead>
                    <tr>
                      <th>Rank</th>
                      <th>Name</th>
                      <th>Level</th>
                      <th>Badges</th>
                      <th>Points</th>
                      <th>Next Level</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {loadingLb ? (
                      <tr>
                        <td colSpan={7} className="text-center py-4">
                          <Spinner animation="border" variant="info" size="sm" /> Loading…
                        </td>
                      </tr>
                    ) : filtered.length > 0 ? (
                      filtered.map((member) => (
                        <tr className="lb-row" key={member.id || member.member_id}>
                          <td>
                            <span className={getMedalClass(member.rank)}>#{member.rank}</span>
                          </td>
                          <td className="member-name-cell">
                            <span className="member-name">{member.name}</span>
                            <button className="view-link" onClick={() => setViewMember(member)}>
                              view profile
                            </button>
                          </td>
                          <td>
                            <span className={`level-chip ${LEVEL_STYLE[member.level] || ''}`}>{member.level}</span>
                          </td>
                          <td>
                            {member.badges?.length ? (
                              <div className="badge-wrap">
                                {member.badges.slice(0, 3).map((b) => (
                                  <span key={b} className="badge-chip">{b}</span>
                                ))}
                                {member.badges.length > 3 && (
                                  <span className="badge-chip">+{member.badges.length - 3}</span>
                                )}
                              </div>
                            ) : (
                              <span className="badge-chip">Bronze Member</span>
                            )}
                          </td>
                          <td className="points-cell">{member.total_points ?? member.points}</td>
                          <td style={{ minWidth: 170 }}>
                            <div className="xp-bar">
                              <div className="xp-fill" style={{ width: `${member.progress ?? 0}%` }} />
                            </div>
                            <div className="xp-meta">
                              {member.maxed ? 'MAX LEVEL' : `${member.points_to_next} to ${member.next_level_points}`}
                            </div>
                          </td>
                          <td>
                            <div className="d-flex gap-1">
                              <Button variant="outline-info" size="sm" onClick={() => setViewMember(member)}>
                                View
                              </Button>
                              {isAuthenticated && (
                                <>
                                  <Button variant="warning" size="sm" onClick={() => handleEdit(member)}>
                                    Edit
                                  </Button>
                                  <Button variant="danger" size="sm" onClick={() => handleDelete(member)}>
                                    Delete
                                  </Button>
                                </>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={7} className="text-center">
                          {search ? 'No members match your search.' : 'No members yet. Add some!'}
                        </td>
                      </tr>
                    )}
                  </tbody>
                </Table>
              </div>
              <div className="table-footer">
                {filtered.length} member{filtered.length === 1 ? '' : 's'} · {leaderboard.length} ranked · period:{' '}
                {TIME_FRAMES.find((t) => t.value === timeFrame)?.label}
                {timeFrame === 'custom' && ` (${startDate} → ${endDate})`}
              </div>
            </div>
          </div>
        </main>
      </Container>

      {/* ------------------------------------------------------------ modals */}
      <LoginModal
        show={showLogin}
        onHide={() => setShowLogin(false)}
        onSuccess={() => push('Welcome back!', 'success')}
        onError={() => {}}
      />

      {viewMember && (
        <MemberHistoryModal
          member={viewMember}
          show={!!viewMember}
          onHide={() => setViewMember(null)}
          onDeleted={refreshAll}
          onError={() => { /* toasted inside */ }}
        />
      )}

      <Modal show={!!editingMember} onHide={() => !isUpdating && setEditingMember(null)} centered contentClassName="neon-modal">
        <Modal.Header closeButton closeVariant="white">
          <Modal.Title>Edit Points</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {editingMember && (
            <Form onSubmit={saveEdit}>
              <Form.Group className="mb-3">
                <Form.Label>Member</Form.Label>
                <Form.Control type="text" value={editingMember.name} disabled className="control-neon" />
              </Form.Group>
              <Form.Group className="mb-3">
                <Form.Label>Total Points (override)</Form.Label>
                <Form.Control
                  type="number"
                  min="0"
                  step="1"
                  value={editPoints}
                  onChange={(e) => setEditPoints(e.target.value)}
                  className="control-neon"
                  disabled={isUpdating}
                  required
                />
                <Form.Text className="text-muted-soft">The difference is logged as a manual adjustment.</Form.Text>
              </Form.Group>
              <Form.Group className="mb-3">
                <Form.Label>Reason (optional)</Form.Label>
                <Form.Control
                  type="text"
                  value={editReason}
                  onChange={(e) => setEditReason(e.target.value)}
                  className="control-neon"
                  placeholder="e.g. correction, campaign bonus"
                  maxLength={300}
                  disabled={isUpdating}
                />
              </Form.Group>
              <div className="d-flex justify-content-end gap-2">
                <Button variant="secondary" onClick={() => setEditingMember(null)} disabled={isUpdating}>
                  Cancel
                </Button>
                <Button variant="primary" type="submit" className="btn-neon" disabled={isUpdating}>
                  {isUpdating ? 'Saving…' : 'Save Changes'}
                </Button>
              </div>
            </Form>
          )}
        </Modal.Body>
      </Modal>

      <ToastStack toasts={toasts} onClose={remove} />
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <Dashboard />
    </AuthProvider>
  )
}
