import { http } from './client'
import type {
  AcceptanceOverviewResponse,
  AuditEventResponse,
  ChatResponse,
  EvaluationRunResponse,
  HealthResponse,
  HealthzResponse,
  IngestResponse,
  JobCreateResponse,
  JobRecord,
  ReadyzResponse,
  SessionChatResponse,
  SystemStatusResponse,
  TicketRecord,
  TicketWorkflowResult,
  UploadResponse,
} from './types'

export async function loadAcceptanceOverview(): Promise<AcceptanceOverviewResponse> {
  const { data } = await http.get<AcceptanceOverviewResponse>('/api/v1/acceptance/overview')
  return data
}

export async function getSystemStatus(): Promise<SystemStatusResponse> {
  const { data } = await http.get<SystemStatusResponse>('/api/v1/system/status')
  return data
}

export async function getHealthz(): Promise<HealthzResponse> {
  const { data } = await http.get<HealthzResponse>('/healthz')
  return data
}

export async function getReadyz(): Promise<ReadyzResponse> {
  const { data } = await http.get<ReadyzResponse>('/readyz')
  return data
}

export async function getHealth(): Promise<HealthResponse> {
  const { data } = await http.get<HealthResponse>('/health')
  return data
}

export async function getMetricsText(): Promise<string> {
  const { data } = await http.get<string>('/metrics', {
    responseType: 'text',
  })
  return data
}

export async function ingestDocuments(docsSource: string): Promise<IngestResponse> {
  const { data } = await http.post<IngestResponse>('/api/v1/documents/ingest', { docs_source: docsSource })
  return data
}

export async function uploadDocument(file: File): Promise<UploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await http.post<UploadResponse>('/api/v1/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function chat(question: string): Promise<ChatResponse> {
  const { data } = await http.post<ChatResponse>('/api/v1/chat', { question })
  return data
}

export async function sessionChat(sessionId: string, question: string): Promise<SessionChatResponse> {
  const { data } = await http.post<SessionChatResponse>('/api/v1/chat/session', {
    session_id: sessionId,
    question,
  })
  return data
}

export async function startTicket(question: string, idempotencyKey: string): Promise<TicketWorkflowResult> {
  const { data } = await http.post<TicketWorkflowResult>('/api/v1/tickets/start', {
    question,
    idempotency_key: idempotencyKey,
  })
  return data
}

export async function resumeTicket(ticketId: string, reviewer: string, decision: string): Promise<TicketWorkflowResult> {
  const { data } = await http.post<TicketWorkflowResult>(`/api/v1/tickets/${ticketId}/resume`, {
    reviewer,
    decision,
  })
  return data
}

export async function closeTicket(ticketId: string, closedBy: string): Promise<unknown> {
  const { data } = await http.post(`/api/v1/tickets/${ticketId}/close`, { closed_by: closedBy })
  return data
}

export async function listTickets(): Promise<TicketRecord[]> {
  const { data } = await http.get<TicketRecord[]>('/api/v1/tickets')
  return data
}

export async function runEvaluation(evaluationType: string, casesPath: string, docsSource: string): Promise<EvaluationRunResponse> {
  const { data } = await http.post<EvaluationRunResponse>('/api/v1/evaluations/run', {
    evaluation_type: evaluationType,
    cases_path: casesPath,
    docs_source: docsSource,
  })
  return data
}

export async function listAuditEvents(limit: number = 100): Promise<AuditEventResponse[]> {
  const { data } = await http.get<AuditEventResponse[]>('/api/v1/admin/audit/events', {
    params: { limit },
  })
  return data
}

export async function createIngestJob(docsSource: string): Promise<JobCreateResponse> {
  const { data } = await http.post<JobCreateResponse>('/api/v1/jobs/ingest', {
    docs_source: docsSource,
  })
  return data
}

export async function createEvaluationJob(evaluationType: string, casesPath: string, docsSource: string): Promise<JobCreateResponse> {
  const { data } = await http.post<JobCreateResponse>('/api/v1/jobs/evaluations', {
    evaluation_type: evaluationType,
    cases_path: casesPath,
    docs_source: docsSource,
  })
  return data
}

export async function getJob(jobId: string): Promise<JobRecord> {
  const { data } = await http.get<JobRecord>(`/api/v1/jobs/${jobId}`)
  return data
}

export async function listJobs(limit: number = 100): Promise<JobRecord[]> {
  const { data } = await http.get<JobRecord[]>('/api/v1/jobs', {
    params: { limit },
  })
  return data
}

export async function cancelJob(jobId: string, reason?: string): Promise<JobRecord> {
  const { data } = await http.post<JobRecord>(`/api/v1/jobs/${jobId}/cancel`, { reason: reason || '' })
  return data
}
