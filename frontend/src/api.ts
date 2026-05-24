import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || ''
})

export interface Citation {
  source: string
  chunk_index: number
  content: string
}

export interface ChatResponse {
  answer: string
  citations: Citation[]
  llm_used: boolean
  insufficient: boolean
  safety_warning: boolean
}

export interface AcceptanceEvidenceItem {
  label: string
  path: string
}

export interface AcceptanceBreakdownItem {
  label: string
  status: string
  summary: string
  metrics: Record<string, string>
}

export interface AcceptanceChartBar {
  label: string
  value: number
  total: number
  tone: string
}

export interface AcceptanceHighlightItem {
  title: string
  summary: string
  status: string
  tags: string[]
}

export interface AcceptanceTraceEvent {
  name: string
  summary: string
  inputs: Record<string, string>
  outputs: Record<string, string>
  metadata: Record<string, string>
}

export interface AcceptanceTraceCase {
  case_id: string
  title: string
  issue: string
  events: AcceptanceTraceEvent[]
  raw_trace: Record<string, unknown>
}

export interface AcceptancePanel {
  key: string
  title: string
  status: string
  summary: string
  metrics: Record<string, string>
  evidence: AcceptanceEvidenceItem[]
  breakdown: AcceptanceBreakdownItem[]
  chart: AcceptanceChartBar[]
  highlights: AcceptanceHighlightItem[]
  trace_cases: AcceptanceTraceCase[]
}

export interface AcceptanceOverviewResponse {
  status: string
  version: string
  generated_from: string[]
  panels: AcceptancePanel[]
}

export interface TicketRecord {
  ticket_id: string
  question: string
  diagnosis: string
  device_model?: string
  fault_code?: string
  risk_level: string
  status: string
  human_required: boolean
  human_decision?: string
  human_reviewer?: string
  closed_by?: string
  created_at: string
  updated_at: string
  closed_at?: string
}

export async function loadSystemStatus() {
  const { data } = await api.get('/api/v1/system/status')
  return data
}

export async function loadAcceptanceOverview(): Promise<AcceptanceOverviewResponse> {
  const { data } = await api.get('/api/v1/acceptance/overview')
  return data
}

export async function ingestDocuments(docsSource: string) {
  const { data } = await api.post('/api/v1/documents/ingest', { docs_source: docsSource })
  return data
}

export async function uploadDocument(file: File) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post('/api/v1/documents/upload', form)
  return data
}

export async function chat(question: string): Promise<ChatResponse> {
  const { data } = await api.post('/api/v1/chat', { question })
  return data
}

export async function sessionChat(sessionId: string, question: string) {
  const { data } = await api.post('/api/v1/chat/session', {
    session_id: sessionId,
    question
  })
  return data
}

export async function startTicket(question: string, idempotencyKey: string) {
  const { data } = await api.post('/api/v1/tickets/start', {
    question,
    idempotency_key: idempotencyKey
  })
  return data
}

export async function resumeTicket(ticketId: string, reviewer: string, decision: string) {
  const { data } = await api.post(`/api/v1/tickets/${ticketId}/resume`, { reviewer, decision })
  return data
}

export async function closeTicket(ticketId: string, closedBy: string) {
  const { data } = await api.post(`/api/v1/tickets/${ticketId}/close`, { closed_by: closedBy })
  return data
}

export async function listTickets(): Promise<TicketRecord[]> {
  const { data } = await api.get('/api/v1/tickets')
  return data
}

export async function runEvaluation(
  evaluationType: string,
  casesPath: string,
  docsSource: string
) {
  const { data } = await api.post('/api/v1/evaluations/run', {
    evaluation_type: evaluationType,
    cases_path: casesPath,
    docs_source: docsSource
  })
  return data
}
