import axios from 'axios'

import { useAuthStore } from '../stores/auth'

const API_BASE = import.meta.env.VITE_API_BASE || ''

const http = axios.create({
  baseURL: API_BASE,
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
})

http.interceptors.request.use((config) => {
  const auth = useAuthStore()
  if (auth.hasKey) {
    config.headers['X-API-Key'] = auth.apiKey
  }
  return config
})

export class ApiClientError extends Error {
  status: number
  code: string
  requestId: string

  constructor(status: number, code: string, message: string, requestId: string) {
    super(message)
    this.name = 'ApiClientError'
    this.status = status
    this.code = code
    this.requestId = requestId
  }
}

http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      const data = error.response.data
      const message = data?.detail || data?.message || error.message
      const code = data?.code || 'unknown'
      const requestId = data?.request_id || error.response.headers?.['x-request-id'] || ''
      throw new ApiClientError(error.response.status, code, message, requestId)
    }
    throw new ApiClientError(0, 'network_error', error.message, '')
  }
)

export { http }

export function formatApiError(e: unknown): string {
  if (e instanceof ApiClientError) {
    const parts = [e.message]
    if (e.requestId) parts.push(`request_id: ${e.requestId}`)
    if (e.status) parts.push(`HTTP ${e.status}`)
    return parts.join(' — ')
  }
  if (e instanceof Error) return e.message
  return String(e)
}
