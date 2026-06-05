export interface ErrorResponse {
  detail: string
  code?: string
  request_id?: string
}

export interface ChatRequest {
  question: string
}

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

export interface SessionChatRequest {
  session_id: string
  question: string
}

export interface SessionChatResponse extends ChatResponse {
  session_id: string
  resolved_question: string
}

export interface IngestResponse {
  document_count: number
  chunk_count: number
}

export interface UploadResponse {
  filename: string
  path: string
}

export interface SystemStatusResponse {
  status: string
  version: string
  llm_provider: string
  llm_model: string
  llm_enabled: boolean
  vector_store_ready: boolean
  docs_sources: string[]
}

export interface EvaluationRunResponse {
  summary: Record<string, unknown>
  report_path: string | null
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
  status: string
  risk_level: string
  device_model: string
  question: string
  [key: string]: unknown
}

export interface TicketWorkflowResult {
  ticket: TicketRecord
  [key: string]: unknown
}

export interface AuditEventResponse {
  event_id: string
  action: string
  actor_role: string
  resource_type: string
  resource_id: string | null
  summary: string
  metadata: Record<string, unknown>
  request_id: string
  created_at: string
}

export interface JobRecord {
  job_id: string
  job_type: string
  status: string
  payload: Record<string, unknown>
  result: Record<string, unknown>
  error: string | null
  retry_count: number
  max_retries: number
  locked_by: string | null
  locked_at: string | null
  heartbeat_at: string | null
  timeout_seconds: number
  cancel_requested: boolean
  created_at: string
  updated_at: string
  started_at: string | null
  finished_at: string | null
}

export interface JobCancelRequest {
  reason?: string
}

export interface JobCreateResponse {
  job: JobRecord
}

export interface HealthzResponse {
  status: string
  service: string
  version: string
}

export interface ReadyzResponse {
  status: string
  version: string
  checks: Record<string, unknown>
}

export interface HealthResponse {
  status: string
  version: string
}
