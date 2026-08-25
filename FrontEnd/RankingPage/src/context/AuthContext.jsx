/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import api, { setCsrfToken } from '../api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    api
      .get('/auth/check')
      .then((res) => {
        if (cancelled) return
        if (res.data?.authenticated) {
          setUser(res.data.user)
          setCsrfToken(res.data.csrf_token)
        }
      })
      .catch(() => {})
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [])

  const login = useCallback(async (email, password, rememberMe) => {
    const res = await api.post('/auth/login', {
      email,
      password,
      remember_me: rememberMe,
    })
    setUser(res.data.user)
    setCsrfToken(res.data.csrf_token)
    return res.data
  }, [])

  const logout = useCallback(async () => {
    try {
      await api.post('/auth/logout')
    } catch {
      /* session may already be gone - clear locally anyway */
    }
    setUser(null)
    setCsrfToken(null)
  }, [])

  const clearUser = useCallback(() => {
    setUser(null)
    setCsrfToken(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, clearUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)

export default AuthContext
