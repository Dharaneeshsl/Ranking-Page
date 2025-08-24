import React, { useState, useEffect } from 'react';
import axios from 'axios';
import 'bootstrap/dist/css/bootstrap.min.css';
import { Container, Form, Button, Table, Row, Col } from 'react-bootstrap';

const App = () => {
  const [leaderboard, setLeaderboard] = useState([]);
  const [name, setName] = useState('');
  const [action, setAction] = useState('attend_event');
  const [startDate, setStartDate] = useState('2025-01-01');
  const [endDate, setEndDate] = useState('2025-12-31');
  const [ws, setWs] = useState(null);

  const fetchLeaderboard = async () => {
    try {
      const res = await axios.get(`http://localhost:8000/leaderboard?start_date=${startDate}&end_date=${endDate}`);
      if (res.data.error) throw new Error(res.data.error);
      setLeaderboard(res.data);
    } catch (err) {
      console.error("Leaderboard fetch error:", err);
    }
  };

  const addPoints = async () => {
    if (!name.trim()) {
      alert("Please enter a member name.");
      return;
    }
    try {
      await axios.post('http://localhost:8000/add_points', { name: name.trim(), action });
      setName('');
    } catch (err) {
      console.error("Detailed error:", err);
      alert("Failed to add points: " + (err.response?.data?.error || err.message));
    }
  };

  useEffect(() => {
    const websocket = new WebSocket('ws://localhost:8000/ws');
    websocket.onopen = () => console.log('WebSocket Connected');
    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'update_leaderboard') fetchLeaderboard();
    };
    websocket.onclose = () => console.log('WebSocket Disconnected');
    setWs(websocket);

    fetchLeaderboard();

    return () => websocket.close();
  }, [startDate, endDate]);

  return (
    <Container className="my-5 p-4" style={{ maxWidth: '600px', backgroundColor: '#ffffff', borderRadius: '10px', boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)' }}>
      <h1 className="text-center mb-4" style={{ color: '#2c3e50' }}>Club Ranking Page</h1>

      <h4 className="mb-3" style={{ color: '#34495e' }}>Add Contribution</h4>
      <Form>
        <Form.Group className="mb-3" controlId="formMemberName">
          <Form.Label style={{ color: '#34495e' }}>Member Name</Form.Label>
          <Form.Control
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Enter member name"
            style={{ borderColor: '#3498db', borderWidth: '2px' }}
          />
        </Form.Group>
        <Form.Group className="mb-3" controlId="formAction">
          <Form.Label style={{ color: '#34495e' }}>Action</Form.Label>
          <Form.Select
            value={action}
            onChange={(e) => setAction(e.target.value)}
            style={{ borderColor: '#3498db', borderWidth: '2px' }}
          >
            <option value="attend_event">Attend Event (+10)</option>
            <option value="volunteer_task">Volunteer Task (+20)</option>
            <option value="lead_event">Lead Event (+50)</option>
            <option value="upload_docs">Upload Docs (+15)</option>
            <option value="bring_sponsorship">Bring Sponsorship (+100)</option>
          </Form.Select>
        </Form.Group>
        <Button
          variant="primary"
          onClick={addPoints}
          className="w-100 mb-4"
          style={{ backgroundColor: '#3498db', borderColor: '#3498db', fontWeight: 'bold' }}
        >
          Add Points
        </Button>
      </Form>

      <h4 className="mb-3" style={{ color: '#34495e' }}>Filter Period</h4>
      <Form>
        <Row>
          <Col>
            <Form.Group className="mb-3" controlId="formStartDate">
              <Form.Label style={{ color: '#34495e' }}>Start Date</Form.Label>
              <Form.Control
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                style={{ borderColor: '#3498db', borderWidth: '2px' }}
              />
            </Form.Group>
          </Col>
          <Col>
            <Form.Group className="mb-3" controlId="formEndDate">
              <Form.Label style={{ color: '#34495e' }}>End Date</Form.Label>
              <Form.Control
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                style={{ borderColor: '#3498db', borderWidth: '2px' }}
              />
            </Form.Group>
          </Col>
        </Row>
      </Form>

      <h4 className="mb-3" style={{ color: '#34495e' }}>Leaderboard</h4>
      <Table striped bordered hover variant="light" style={{ borderColor: '#3498db' }}>
        <thead style={{ backgroundColor: '#3498db', color: '#ffffff' }}>
          <tr>
            <th style={{ width: '10%' }}>Rank</th>
            <th style={{ width: '30%' }}>Name</th>
            <th style={{ width: '30%' }}>Period Points</th>
            <th style={{ width: '30%' }}>Badge (Total Points)</th>
          </tr>
        </thead>
        <tbody>
          {leaderboard.map((entry, index) => (
            <tr key={index}>
              <td>{index + 1}</td>
              <td>{entry.name}</td>
              <td>{entry.period_points}</td>
              <td>{entry.badge} ({entry.total_points})</td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Container>
  );
};

export default App;