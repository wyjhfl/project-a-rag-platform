import type { components, paths } from './generated'

export type ApiSchema<Name extends keyof components['schemas']> = components['schemas'][Name]

type JsonContent<Response> = Response extends { content: { 'application/json': infer Body } } ? Body : never
type SuccessResponse<Path extends keyof paths> = paths[Path]['get'] extends { responses: { 200: infer Response } }
  ? JsonContent<Response>
  : never

export interface ErrorResponse {
  detail?: string
  message?: string
  code?: string
  request_id?: string
  error?: {
    code?: string
    message?: string
    request_id?: string
  }
}

export type ChatRequest = ApiSchema<'ChatRequest'>
export type Citation = ApiSchema<'Citation'>
export type ChatResponse = ApiSchema<'ChatResponse'>
export type SessionChatRequest = ApiSchema<'SessionChatRequest'>
export type SessionChatResponse = ApiSchema<'SessionChatResponse'>
export type IngestResponse = ApiSchema<'IngestResponse'>
export type UploadResponse = ApiSchema<'UploadResponse'>
export type SystemStatusResponse = ApiSchema<'SystemStatusResponse'>
export type EvaluationRunResponse = ApiSchema<'EvaluationRunResponse'>
export type AcceptanceEvidenceItem = ApiSchema<'AcceptanceEvidenceItem'>
export type AcceptanceBreakdownItem = ApiSchema<'AcceptanceBreakdownItem'> & {
  metrics: Record<string, string>
}
export type AcceptanceChartBar = ApiSchema<'AcceptanceChartBar'>
export type AcceptanceHighlightItem = ApiSchema<'AcceptanceHighlightItem'> & {
  tags: string[]
}
export type AcceptanceTraceEvent = ApiSchema<'AcceptanceTraceEvent'> & {
  inputs: Record<string, string>
  outputs: Record<string, string>
  metadata: Record<string, string>
}
export type AcceptanceTraceCase = Omit<ApiSchema<'AcceptanceTraceCase'>, 'events' | 'raw_trace'> & {
  events: AcceptanceTraceEvent[]
  raw_trace: Record<string, unknown>
}
export type AcceptancePanel = Omit<
  ApiSchema<'AcceptancePanel'>,
  'evidence' | 'breakdown' | 'chart' | 'highlights' | 'trace_cases'
> & {
  evidence: AcceptanceEvidenceItem[]
  breakdown: AcceptanceBreakdownItem[]
  chart: AcceptanceChartBar[]
  highlights: AcceptanceHighlightItem[]
  trace_cases: AcceptanceTraceCase[]
}
export type AcceptanceOverviewResponse = Omit<ApiSchema<'AcceptanceOverviewResponse'>, 'panels'> & {
  panels: AcceptancePanel[]
}
export type TicketRecord = ApiSchema<'TicketRecord'> & { [key: string]: unknown }
export type TicketWorkflowResult = ApiSchema<'TicketWorkflowResult'> & { [key: string]: unknown }
export type AuditEventResponse = ApiSchema<'AuditEventResponse'> & {
  id?: number
  event_id?: string
  request_id?: string
  created_at?: string
}
export type JobRecord = ApiSchema<'JobRecord'>
export type JobCancelRequest = Partial<ApiSchema<'JobCancelRequest'>>
export type JobCreateResponse = ApiSchema<'JobCreateResponse'>

export type HealthzResponse = SuccessResponse<'/healthz'> & {
  status: string
  service?: string
  version?: string
  release_url?: string
}
export type ReadyzResponse = {
  status: string
  version?: string
  release_url?: string
  checks?: Record<string, unknown>
  [key: string]: unknown
}
export type HealthResponse = SuccessResponse<'/health'> & {
  status: string
  version?: string
  release_url?: string
}
