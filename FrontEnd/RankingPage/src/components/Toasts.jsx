/* eslint-disable react-refresh/only-export-components */
import { useCallback, useRef, useState } from 'react'

const ICONS = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' }

export function useToasts() {
  const [toasts, setToasts] = useState([])
  const idRef = useRef(0)

  const remove = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const push = useCallback(
    (message, type = 'info', duration = 4000) => {
      const id = ++idRef.current
      setToasts((prev) => [...prev.slice(-4), { id, message, type }])
      if (duration > 0) {
        setTimeout(() => remove(id), duration)
      }
      return id
    },
    [remove],
  )

  return { toasts, push, remove }
}

export function ToastStack({ toasts, onClose }) {
  if (!toasts.length) return null
  return (
    <div className="toast-stack" role="status" aria-live="polite">
      {toasts.map((t) => (
        <div key={t.id} className={`app-toast toast-${t.type || 'info'}`} onClick={() => onClose(t.id)}>
          <span className="toast-icon">{ICONS[t.type] || ICONS.info}</span>
          <span className="toast-msg">{t.message}</span>
          <button className="toast-close" aria-label="Dismiss" onClick={(e) => { e.stopPropagation(); onClose(t.id) }}>
            ×
          </button>
        </div>
      ))}
    </div>
  )
}

export default ToastStack
