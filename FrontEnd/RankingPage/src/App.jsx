import React, { useState, useEffect } from 'react';
import axios from 'axios';
import 'bootstrap/dist/css/bootstrap.min.css';
import { Container, Form, Button, Table, Row, Col, Modal, ProgressBar, Badge } from 'react-bootstrap';
import ElectricBorder from './ElectricBorder';







const App = () => {
  const [leaderboard, setLeaderboard] = useState({ leaderboard: [] });
  const [name, setName] = useState('');
  const [action, setAction] = useState('attend_event');
  const [startDate, setStartDate] = useState('2025-01-01');
  const [endDate, setEndDate] = useState('2025-12-31');
  const [editingMember, setEditingMember] = useState(null);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editPoints, setEditPoints] = useState(0);
  const [playTitleAnim, setPlayTitleAnim] = useState(false);

  useEffect(() => {
    fetchLeaderboard();
  }, [startDate, endDate]);

  useEffect(() => {
    const t = setTimeout(() => setPlayTitleAnim(true), 200);
    return () => { clearTimeout(t); };
  }, []);

  const fetchLeaderboard = async () => {
    try {
      const res = await axios.get(`http://localhost:8000/api/leaderboard?start_date=${startDate}&end_date=${endDate}`);
      if (res.data.status === "success") {
        setLeaderboard(res.data.data || { leaderboard: [] });
      } else {
        setLeaderboard({ leaderboard: [{ name: "Error", total_points: 0, level: "N/A", badges: [] }] });
      }
    } catch (err) {
      console.error("Fetch error:", err);
      setLeaderboard({ leaderboard: [{ name: "Server Error", total_points: 0, level: "N/A", badges: [] }] });
    }
  };

  const addPoints = async () => {
    if (!name.trim()) {
      alert("Please enter a name.");
      return;
    }
    try {
      const res = await axios.post('http://localhost:8000/api/points', { name: name.trim(), action });
      if (res.data.status === "success") {
        fetchLeaderboard();
        setName('');
      } else {
        alert("Add failed: " + res.data.message);
      }
    } catch (err) {
      console.error("Add error:", err);
      alert("Add failed: Check server.");
    }
  };

  const handleEdit = (member) => {
    setEditingMember(member);
    setEditPoints(member.total_points);
    setShowEditModal(true);
  };

  const handleUpdatePoints = async () => {
    if (!editingMember) return;
    
    try {
      const res = await axios.put(`http://localhost:8000/api/members/${editingMember.member_id}`, {
        points: parseInt(editPoints)
      });
      
      if (res.data.status === "success") {
        setShowEditModal(false);
        fetchLeaderboard();
      } else {
        alert("Update failed: " + res.data.message);
      }
    } catch (err) {
      console.error("Update error:", err);
      alert("Update failed: Check server.");
    }
  };

  const handleDelete = async (memberId) => {
    if (!window.confirm("Are you sure you want to delete this member?")) return;
    
    try {
      const res = await axios.delete(`http://localhost:8000/api/members/${memberId}`);
      
      if (res.data.status === "success") {
        fetchLeaderboard();
      } else {
        alert("Delete failed: " + res.data.message);
      }
    } catch (err) {
      console.error("Delete error:", err);
      alert("Delete failed: Check server.");
    }
  };

  const getMedalClass = (rank) => {
    if (rank === 1) return 'medal medal-gold';
    if (rank === 2) return 'medal medal-silver';
    if (rank === 3) return 'medal medal-bronze';
    return 'medal medal-std';
  };

  const xpPercent = (points) => {
    const maxForBar = Math.max(100, points || 0);
    const pct = Math.min(100, Math.round(((points || 0) % maxForBar) / maxForBar * 100));
    return Number.isFinite(pct) ? pct : 0;
  };

  return (<>
    <div className="bg-grid" />
    <Container className="my-5 p-4" style={{ maxWidth: '900px' }}>
      {/* Hidden SVG defs for potential gradients (placeholder for future use) */}
      <svg className="eb-svg" aria-hidden="true" focusable="false">
        <defs>
          <linearGradient id="eb-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#00e5ff" />
            <stop offset="100%" stopColor="#8a2be2" />
          </linearGradient>
        </defs>
      </svg>
      <div className={`mb-4 title-hero ${playTitleAnim ? 'play' : ''}`}>
        <span className="intro-img" style={{ backgroundImage: 'url(/FAVICON.png)' }} />
        <h1 className="panel-title text">Gamified Ranking System</h1>
      </div>

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
                  <Form.Select className="control-neon" value={action} onChange={(e) => setAction(e.target.value)}>
                    <option value="attend_event">Attend Event (+10)</option>
                    <option value="volunteer_task">Volunteer Task (+20)</option>
                    <option value="lead_event">Lead Event (+50)</option>
                    <option value="upload_docs">Upload Docs (+15)</option>
                    <option value="bring_sponsorship">Bring Sponsorship (+100)</option>
                  </Form.Select>
                  </div>
                </Form.Group>
                <Button className="w-100 mb-2 btn-neon" onClick={addPoints}>Add Points</Button>
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

      <div className="mt-4 p-3 panel-card fade-slide-in">
        <h4 className="mb-3">Leaderboard</h4>
        <Table striped hover responsive className="lb-table">
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
                      <span className={getMedalClass(rank)}>
                        #{rank}
                      </span>
                    </td>
                    <td>{member.name}</td>
                    <td>{points}</td>
                    <td>{member.level || 'Bronze Member'}</td>
                    <td>
                      {badges.length > 0 ? badges.map((b, i) => (
                        <span className="badge-chip" key={i}>{b}</span>
                      )) : <span className="badge-chip">Bronze Member</span>}
                    </td>
                    <td style={{ minWidth: 150 }}>
                      <div className="xp-bar">
                        <div className="xp-fill" style={{ width: `${xpPercent(points)}%` }} />
                      </div>
                    </td>
                    <td>
                      <Button variant="warning" size="sm" onClick={() => handleEdit(member)} className="me-2">Edit</Button>
                      <Button variant="danger" size="sm" onClick={() => handleDelete(member.member_id)}>Delete</Button>
                    </td>
                  </tr>
                );
              })
            ) : (
              <tr><td colSpan="7" className="text-center">No members yet. Add some!</td></tr>
            )}
          </tbody>
        </Table>
      </div>

      {/* Single Edit Modal */}
      <Modal show={showEditModal} onHide={() => setShowEditModal(false)}>
        <Modal.Header closeButton>
          <Modal.Title>Edit Points</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {editingMember && (
            <Form>
              <Form.Group className="mb-3">
                <Form.Label>Member Name</Form.Label>
                <Form.Control type="text" value={editingMember?.name || ''} disabled />
              </Form.Group>
              <Form.Group className="mb-3">
                <Form.Label>Points</Form.Label>
                <Form.Control 
                  type="number" 
                  value={editPoints} 
                  onChange={(e) => setEditPoints(e.target.value)}
                />
              </Form.Group>
            </Form>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowEditModal(false)}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handleUpdatePoints}>
            Save Changes
          </Button>
        </Modal.Footer>
      </Modal>
    </Container>
  </> );
};

export default App;