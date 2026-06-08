import axios from 'axios'

import { useAuthStore } from '../stores/auth'
import type { ErrorResponse } from './types'

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

function stringOrEmpty(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

function formatValidationDetail(detail: unknown): string {
  if (!Array.isArray(detail)) return ''
  const messages = detail
    .map((item) => {
      if (!item || typeof item !== 'object') return ''
      const record = item as Record<string, unknown>
      const loc = Array.isArray(record.loc) ? record.loc.join('.') : ''
      const msg = stringOrEmpty(record.msg)
      if (!msg) return ''
      return loc ? `${loc}: ${msg}` : msg
    })
    .filter(Boolean)
  return messages.length > 0 ? `Validation failed: ${messages.join('; ')}` : 'Validation failed'
}

function extractApiErrorPayload(
  data: ErrorResponse | undefined,
  fallbackMessage: string,
  headers: Record<string, unknown> | undefined,
): { message: string; code: string; requestId: string } {
  const nested = data?.error
  const validationMessage = formatValidationDetail(data?.detail)
  const message =
    stringOrEmpty(nested?.message) ||
    validationMessage ||
    stringOrEmpty(data?.detail) ||
    stringOrEmpty(data?.message) ||
    fallbackMessage
  const code =
    stringOrEmpty(nested?.code) ||
    stringOrEmpty(data?.code) ||
    (validationMessage ? 'validation_error' : 'unknown')
  const requestId =
    stringOrEmpty(nested?.request_id) ||
    stringOrEmpty(data?.request_id) ||
    stringOrEmpty(headers?.['x-request-id'])
  return { message, code, requestId }
}

http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      const data = error.response.data as ErrorResponse | undefined
      const { message, code, requestId } = extractApiErrorPayload(
        data,
        error.message,
        error.response.headers as Record<string, unknown>,
      )
      throw new ApiClientError(error.response.status, code, message, requestId)
    }
    throw new ApiClientError(0, 'network_error', error.message, '')
  },
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
