import React, { useState, useEffect } from 'react';
import axios from 'axios';
import 'bootstrap/dist/css/bootstrap.min.css';
import { Container, Form, Button, Table, Row, Col, Modal } from 'react-bootstrap';
import ElectricBorder from './ElectricBorder';

const API_BASE_URL = 'http://localhost:8000/api';

const App = () => {
  const [leaderboard, setLeaderboard] = useState({ leaderboard: [] });
  const [name, setName] = useState('');
  const [action, setAction] = useState('attend_event');
  const [startDate, setStartDate] = useState('2025-01-01');
  const [endDate, setEndDate] = useState('2025-12-31');
  const [playTitleAnim, setPlayTitleAnim] = useState(false);
  const [editingMember, setEditingMember] = useState(null);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editPoints, setEditPoints] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  
  // Action types with their point values
  const actionTypes = [
    { value: 'attend_event', label: 'Attend Event (+10)', points: 10 },
    { value: 'volunteer_task', label: 'Volunteer Task (+20)', points: 20 },
    { value: 'lead_event', label: 'Lead Event (+50)', points: 50 },
    { value: 'upload_docs', label: 'Upload Docs (+15)', points: 15 },
    { value: 'bring_sponsorship', label: 'Bring Sponsorship (+100)', points: 100 }
  ];

  const handleEdit = (member) => {
    setEditingMember(member);
    setEditPoints(member.total_points);
    setShowEditModal(true);
  };

  const [isUpdating, setIsUpdating] = useState(false);

  const handleUpdatePoints = async () => {
    if (!editingMember) return;
    
    try {
      setIsUpdating(true);
      const points = parseInt(editPoints, 10);
      if (isNaN(points) || points < 0) {
        alert('Please enter a valid positive number for points');
        return;
      }
      
      const res = await axios.put(`${API_BASE_URL}/members/${editingMember.member_id}`, {
        points: points
      });
      
      if (res.data.status === "success") {
        setShowEditModal(false);
        await fetchLeaderboard();
      }
    } catch (err) {
      console.error("Update error:", err);
      alert('Failed to update points. Please try again.');
    } finally {
      setIsUpdating(false);
    }
  };

  const handleDelete = async (memberId) => {
    if (!window.confirm("Are you sure you want to delete this member?")) return;
    
    try {
      const res = await axios.delete(`${API_BASE_URL}/members/${memberId}`);
      
      if (res.data.status === "success") {
        fetchLeaderboard();
      }
    } catch (err) {
      console.error("Delete error:", err);
      alert('Failed to delete member. Please try again.');
    }
  };

  useEffect(() => {
    fetchLeaderboard();
  }, [startDate, endDate]);

  useEffect(() => {
    const t = setTimeout(() => setPlayTitleAnim(true), 200);
    return () => { clearTimeout(t); };
  }, []);

  const fetchLeaderboard = async () => {
    setIsLoading(true);
    try {
      const res = await axios.get(`${API_BASE_URL}/leaderboard`, {
        params: { start_date: startDate, end_date: endDate }
      });
      if (res.data.status === "success") {
        setLeaderboard(res.data.data || { leaderboard: [] });
      }
    } catch (err) {
      console.error("Fetch error:", err);
      alert('Failed to load leaderboard. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const addPoints = async () => {
    if (!name.trim()) {
      alert("Please enter a name.");
      return;
    }
    try {
      const res = await axios.post(`${API_BASE_URL}/points`, { 
        name: name.trim(), 
        action 
      });
      if (res.data.status === "success") {
        fetchLeaderboard();
        setName('');
        setAction('attend_event');
      }
    } catch (err) {
      console.error("Add error:", err);
      alert('Failed to add points. Please try again.');
    }
  };

  const getMedalClass = (rank) => {
    if (rank === 1) return 'medal medal-gold';
    if (rank === 2) return 'medal medal-silver';
    if (rank === 3) return 'medal medal-bronze';
    return 'medal';
  };

  const xpPercent = (points) => {
    const maxForBar = Math.max(100, points || 0);
    const pct = Math.min(100, Math.round(((points || 0) % maxForBar) / maxForBar * 100));
    return Number.isFinite(pct) ? pct : 0;
  };

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
      
      <Container className="main-content" style={{ maxWidth: '1200px' }}>
        {/* Header Section */}
        <div className="d-flex justify-content-center w-100">
          <header className="app-header">
            <div className={`title-hero d-flex align-items-center ${playTitleAnim ? 'play' : ''}`}>
              <div className="logo-container me-3">
                <img 
                  src="/FAVICON.png" 
                  alt="Logo" 
                  className="header-logo"
                  style={{
                    width: '60px',
                    height: '60px',
                    objectFit: 'contain'
                  }}
                />
              </div>
              <h1 className="panel-title m-0">Gamified Ranking System</h1>
            </div>
          </header>
        </div>

        {/* Form Boxes Section */}
        <div className="mb-5">
          <Row className="g-4 align-items-stretch">
            <Col md={6} className="d-flex">
              <ElectricBorder
                color="#d21349ff"
                speed={1}
                chaos={0.5}
                thickness={2}
                style={{ borderRadius: 16, width: '100%' }}
              >
                <div className="p-3 panel-card fade-slide-in">
                  <h4 className="mb-3">Add Contribution</h4>
                  <Form>
                    <Form.Group className="mb-3">
                      <Form.Label>Member Name</Form.Label>
                      <Form.Control className="control-neon" value={name} onChange={(e) => setName(e.target.value)} placeholder="Enter name" />
                    </Form.Group>
                    <Form.Group className="mb-3">
                      <Form.Label>Action</Form.Label>
                      <div className="select-caret">
                      <Form.Select 
                        className="control-neon" 
                        value={action} 
                        onChange={(e) => setAction(e.target.value)}
                        aria-label="Select action type"
                      >
                        {actionTypes.map((actionType) => (
                          <option key={actionType.value} value={actionType.value}>
                            {actionType.label}
                          </option>
                        ))}
                      </Form.Select>
                      </div>
                    </Form.Group>
                    <Button 
                      className="w-100 mb-2 btn-neon" 
                      onClick={addPoints}
                      disabled={isLoading || !name.trim()}
                    >
                      {isLoading ? 'Adding...' : 'Add Points'}
                    </Button>
                  </Form>
                </div>
              </ElectricBorder>
            </Col>

            <Col md={6} className="d-flex">
              <ElectricBorder
                color="#f74f0dff"
                speed={1}
                chaos={0.5}
                thickness={2}
                style={{ borderRadius: 16, width: '100%' }}
              >
                <div className="p-3 panel-card fade-slide-in">
                  <h4 className="mb-3">Filter Period</h4>
                  <Form>
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
                  </Form>
                </div>
              </ElectricBorder>
            </Col>
          </Row>
        </div>

      {/* Main Content Section */}
      <main className="app-main">
        <div className="dashboard-section">
          <div className="p-3 panel-card fade-slide-in">
            <h4 className="mb-3">Leaderboard</h4>
            <div className="table-responsive">
              <Table striped hover className="lb-table">
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Name</th>
                    <th>Total Points</th>
                    <th>Level</th>
                    <th>Badges</th>
                    <th>XP</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {leaderboard.leaderboard && leaderboard.leaderboard.length > 0 ? (
                    leaderboard.leaderboard.map((member, index) => {
                      const rank = member.rank || index + 1;
                      const points = member.total_points || 0;
                      const badges = member.badges && Array.isArray(member.badges) ? member.badges : [];
                      return (
                        <tr className="lb-row" key={member.member_id || index}>
                          <td>
                            <span className={getMedalClass(rank)}>#{rank}</span>
                          </td>
                          <td>{member.name}</td>
                          <td>{points}</td>
                          <td>{member.level || 'Bronze Member'}</td>
                          <td>
                            {badges.length > 0 ? (
                              badges.map((b, i) => (
                                <span className="badge-chip" key={i}>{b}</span>
                              ))
                            ) : (
                              <span className="badge-chip">Bronze Member</span>
                            )}
                          </td>
                          <td style={{ minWidth: 150 }}>
                            <div className="xp-bar">
                              <div className="xp-fill" style={{ width: `${xpPercent(points)}%` }} />
                            </div>
                          </td>
                          <td>
                            <Button variant="warning" size="sm" onClick={() => handleEdit(member)} className="me-2">
                              Edit
                            </Button>
                            <Button variant="danger" size="sm" onClick={() => handleDelete(member.member_id)}>
                              Delete
                            </Button>
                          </td>
                        </tr>
                      );
                    })
                  ) : (
                    <tr>
                      <td colSpan="7" className="text-center">No members yet. Add some!</td>
                    </tr>
                  )}
                </tbody>
              </Table>
            </div>

            {/* Edit Modal */}
            <Modal show={showEditModal} onHide={() => !isUpdating && setShowEditModal(false)}>
              <Modal.Header closeButton closeVariant={isUpdating ? 'white' : undefined} closeButtonProps={{ disabled: isUpdating }}>
                <Modal.Title>Edit Points</Modal.Title>
              </Modal.Header>
              <Modal.Body>
                {editingMember && (
                  <Form onSubmit={(e) => { e.preventDefault(); handleUpdatePoints(); }}>
                    <Form.Group className="mb-3">
                      <Form.Label>Member Name</Form.Label>
                      <Form.Control 
                        type="text" 
                        value={editingMember?.name || ''} 
                        disabled 
                        className="control-neon"
                      />
                    </Form.Group>
                    <Form.Group className="mb-3">
                      <Form.Label>Points</Form.Label>
                      <Form.Control 
                        type="number" 
                        min="0"
                        value={editPoints} 
                        onChange={(e) => setEditPoints(e.target.value)}
                        className="control-neon"
                        disabled={isUpdating}
                        required
                      />
                    </Form.Group>
                    <div className="d-flex justify-content-end gap-2">
                      <Button 
                        variant="secondary" 
                        onClick={() => setShowEditModal(false)}
                        disabled={isUpdating}
                      >
                        Cancel
                      </Button>
                      <Button 
                        variant="primary" 
                        type="submit"
                        disabled={isUpdating}
                      >
                        {isUpdating ? 'Saving...' : 'Save Changes'}
                      </Button>
                    </div>
                  </Form>
                )}
              </Modal.Body>
            </Modal>
          </div>
        </div>
      </main>
    </Container>
  </div>
  );
};

export default App;