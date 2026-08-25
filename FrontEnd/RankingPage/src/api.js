import axios from 'axios'

// Same-origin by default (Vite dev proxy / nginx in production).
// Set VITE_API_BASE_URL only if the API lives on a different origin.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

let csrfToken = null

export const setCsrfToken = (token) => {
  csrfToken = token || null
}

export const getCsrfToken = () => csrfToken

const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  timeout: 15000,
})

api.interceptors.request.use((config) => {
  const method = (config.method || 'get').toLowerCase()
  if (
    !['get', 'head', 'options'].includes(method) &&
    config.headers &&
    csrfToken
  ) {
    config.headers['X-CSRF-Token'] = csrfToken
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    const isAuthCall = (error.config?.url || '').includes('/auth/')
    if (status === 401 && !isAuthCall) {
      window.dispatchEvent(new CustomEvent('auth:expired'))
    }
    return Promise.reject(error)
  },
)

export const errorMessage = (error, fallback = 'Something went wrong') => {
  const data = error?.response?.data
  if (data?.error) return data.error
  if (Array.isArray(data?.details) && data.details[0]?.msg) return data.details[0].msg
  return error?.message || fallback
}

export default api
