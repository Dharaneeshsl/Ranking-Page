import { useState } from 'react'
import { Button, Form, Modal } from 'react-bootstrap'
import { useAuth } from '../context/AuthContext'
import { errorMessage } from '../api'

export default function LoginModal({ show, onHide, onSuccess, onError }) {
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [remember, setRemember] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      await login(email.trim(), password, remember)
      setPassword('')
      setEmail('')
      onSuccess?.()
      onHide()
    } catch (err) {
      setError(errorMessage(err, 'Login failed'))
      onError?.(errorMessage(err, 'Login failed'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal show={show} onHide={() => !busy && onHide()} centered contentClassName="neon-modal">
      <Modal.Header closeButton closeVariant="white">
        <Modal.Title>Admin Sign In</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <p className="text-muted-soft mb-3">
          Sign in to manage members, award points and edit the leaderboard.
        </p>
        <Form onSubmit={submit}>
          <Form.Group className="mb-3">
            <Form.Label>Email</Form.Label>
            <Form.Control
              type="email"
              required
              autoFocus
              className="control-neon"
              placeholder="admin@yourdomain.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={busy}
            />
          </Form.Group>
          <Form.Group className="mb-3">
            <Form.Label>Password</Form.Label>
            <Form.Control
              type="password"
              required
              className="control-neon"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={busy}
            />
          </Form.Group>
          <Form.Check
            type="switch"
            id="remember-me"
            label="Keep me signed in (30 days)"
            checked={remember}
            onChange={(e) => setRemember(e.target.checked)}
            disabled={busy}
            className="mb-3"
          />
          {error && <div className="alert alert-danger py-2">{error}</div>}
          <Button type="submit" className="w-100 btn-neon" disabled={busy}>
            {busy ? 'Signing in…' : 'Sign In'}
          </Button>
        </Form>
      </Modal.Body>
    </Modal>
  )
}
