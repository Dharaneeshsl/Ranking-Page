import React, { useState, useEffect } from 'react';
import axios from 'axios';
import 'bootstrap/dist/css/bootstrap.min.css';
import { Container, Form, Button, Table, Row, Col, Modal } from 'react-bootstrap';

const App = () => {
  const [leaderboard, setLeaderboard] = useState({ leaderboard: [] });
  const [name, setName] = useState('');
  const [action, setAction] = useState('attend_event');
  const [startDate, setStartDate] = useState('2025-01-01');
  const [endDate, setEndDate] = useState('2025-12-31');
  const [editingMember, setEditingMember] = useState(null);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editPoints, setEditPoints] = useState(0);

  useEffect(() => {
    fetchLeaderboard();
  }, [startDate, endDate]);

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

  return (
    <Container className="my-5 p-4" style={{ maxWidth: '600px', backgroundColor: '#fff', borderRadius: '10px', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
      <h1 className="text-center mb-4" style={{ color: '#2c3e50' }}>Gamified Ranking System</h1>
      <h4 className="mb-3" style={{ color: '#34495e' }}>Add Contribution</h4>
      <Form>
        <Form.Group className="mb-3">
          <Form.Label style={{ color: '#34495e' }}>Member Name</Form.Label>
          <Form.Control value={name} onChange={(e) => setName(e.target.value)} placeholder="Enter name" style={{ borderColor: '#3498db', borderWidth: '2px' }} />
        </Form.Group>
        <Form.Group className="mb-3">
          <Form.Label style={{ color: '#34495e' }}>Action</Form.Label>
          <Form.Select value={action} onChange={(e) => setAction(e.target.value)} style={{ borderColor: '#3498db', borderWidth: '2px' }}>
            <option value="attend_event">Attend Event (+10)</option>
            <option value="volunteer_task">Volunteer Task (+20)</option>
            <option value="lead_event">Lead Event (+50)</option>
            <option value="upload_docs">Upload Docs (+15)</option>
            <option value="bring_sponsorship">Bring Sponsorship (+100)</option>
          </Form.Select>
        </Form.Group>
        <Button variant="primary" onClick={addPoints} className="w-100 mb-4" style={{ backgroundColor: '#3498db', borderColor: '#3498db', fontWeight: 'bold' }}>
          Add Points
        </Button>
      </Form>
      <h4 className="mb-3" style={{ color: '#34495e' }}>Filter Period</h4>
      <Form>
        <Row>
          <Col>
            <Form.Group className="mb-3">
              <Form.Label style={{ color: '#34495e' }}>Start Date</Form.Label>
              <Form.Control type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} style={{ borderColor: '#3498db', borderWidth: '2px' }} />
            </Form.Group>
          </Col>
          <Col>
            <Form.Group className="mb-3">
              <Form.Label style={{ color: '#34495e' }}>End Date</Form.Label>
              <Form.Control type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} style={{ borderColor: '#3498db', borderWidth: '2px' }} />
            </Form.Group>
          </Col>
        </Row>
      </Form>
      <h4 className="mb-3" style={{ color: '#34495e' }}>Leaderboard</h4>
      <Table striped bordered hover variant="light" style={{ borderColor: '#3498db' }}>
        <thead style={{ backgroundColor: '#3498db', color: '#fff' }}>
          <tr>
            <th>Rank</th>
            <th>Name</th>
            <th>Total Points</th>
            <th>Level</th>
            <th>Badges</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {leaderboard.leaderboard && leaderboard.leaderboard.length > 0 ? (
            leaderboard.leaderboard.map((member, index) => (
              <tr key={member.member_id || index}>
                <td>{member.rank || index + 1}</td>
                <td>{member.name}</td>
                <td>{member.total_points || 0}</td>
                <td>{member.level || 'Bronze Member'}</td>
                <td>{member.badges ? member.badges.join(', ') : 'Bronze Member'}</td>
                <td>
                  <Button variant="warning" size="sm" onClick={() => handleEdit(member)} className="me-2">
                    Edit
                  </Button>
                  <Button variant="danger" size="sm" onClick={() => handleDelete(member.member_id)}>
                    Delete
                  </Button>
                </td>
              </tr>
            ))
          ) : (
            <tr><td colSpan="6" className="text-center">No members yet. Add some!</td></tr>
          )}
        </tbody>
      </Table>

      {/* Edit Points Modal */}
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

    {/* Edit Points Modal */}
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
  );
};

export default App;