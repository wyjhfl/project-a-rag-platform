<template>
  <div class="layout-shell">
    <aside class="sidebar">
      <div class="brand-block">
        <div class="eyebrow">Project A</div>
        <div class="brand">企业设备售后诊断与工单闭环 RAG 平台</div>
        <p class="subtitle">
          把真实 LLM 主链、多模态验收、评测结果和 bad case 做成一个可直接演示的前端中心。
        </p>
      </div>

      <nav class="nav">
        <button
          v-for="item in navItems"
          :key="item.key"
          :class="['nav-item', { active: activeTab === item.key }]"
          @click="activeTab = item.key"
        >
          <span class="nav-label">{{ item.label }}</span>
          <span class="nav-hint">{{ item.hint }}</span>
        </button>
      </nav>
    </aside>

    <main class="main">
      <header class="hero">
        <div>
          <p class="hero-kicker">A-v2.0 演示中心</p>
          <h1 class="page-title">{{ currentNav?.label }}</h1>
          <p class="hero-text">{{ currentNav?.hint }}</p>
        </div>
        <div class="hero-actions">
          <el-button @click="refreshAll" :loading="loading">刷新状态</el-button>
        </div>
      </header>

      <el-alert
        v-if="status && !status.llm_enabled"
        class="section"
        title="当前未接入真实文本 LLM，请检查 .env 中的 LLM_API_KEY、LLM_BASE_URL、LLM_MODEL。"
        type="warning"
        show-icon
      />

      <section v-if="activeTab === 'acceptance'" class="stack">
        <div class="overview-banner">
          <div>
            <div class="eyebrow">演示总览</div>
            <div class="overview-title">直接讲清主链是否稳定、哪些增强链路已转绿、哪些坏例子仍需面对。</div>
          </div>
          <el-tag :type="statusTagType(acceptanceOverview?.status)">
            {{ acceptanceOverview?.status || 'unknown' }}
          </el-tag>
        </div>

        <div class="hero-metrics">
          <div class="hero-metric">
            <span class="hero-metric-label">面板数</span>
            <strong>{{ acceptancePanels.length }}</strong>
          </div>
          <div class="hero-metric">
            <span class="hero-metric-label">证据文件</span>
            <strong>{{ acceptanceOverview?.generated_from.length || 0 }}</strong>
          </div>
          <div class="hero-metric">
            <span class="hero-metric-label">文本主链</span>
            <strong>{{ providerPanel?.metrics.default_candidate || '未确定' }}</strong>
          </div>
          <div class="hero-metric">
            <span class="hero-metric-label">多模态转绿</span>
            <strong>{{ multimodalPanel?.metrics.passed || '0' }}</strong>
          </div>
        </div>

        <div class="acceptance-grid">
          <article v-for="panel in acceptancePanels" :key="panel.key" class="acceptance-card">
            <div class="card-head">
              <div>
                <div class="card-title">{{ panel.title }}</div>
                <p class="card-summary">{{ panel.summary }}</p>
              </div>
              <el-tag :type="statusTagType(panel.status)">{{ panel.status }}</el-tag>
            </div>

            <div class="metric-grid">
              <div v-for="(value, key) in panel.metrics" :key="`${panel.key}-${key}`" class="metric-item">
                <span class="metric-label">{{ key }}</span>
                <strong class="metric-value">{{ value }}</strong>
              </div>
            </div>

            <div v-if="panel.chart.length" class="chart-block">
              <div class="section-label">可视化指标</div>
              <div v-for="bar in panel.chart" :key="`${panel.key}-${bar.label}`" class="chart-row">
                <div class="chart-meta">
                  <span>{{ bar.label }}</span>
                  <strong>{{ percentText(bar.value, bar.total) }}</strong>
                </div>
                <div class="chart-rail">
                  <div class="chart-fill" :class="toneClass(bar.tone)" :style="{ width: percentWidth(bar.value, bar.total) }" />
                </div>
              </div>
            </div>

            <div v-if="panel.breakdown.length" class="section-stack">
              <div class="section-label">状态明细</div>
              <div class="breakdown-list">
                <div v-for="item in panel.breakdown" :key="`${panel.key}-${item.label}`" class="breakdown-item">
                  <div class="breakdown-head">
                    <strong>{{ item.label }}</strong>
                    <el-tag size="small" :type="statusTagType(item.status)">{{ item.status }}</el-tag>
                  </div>
                  <p class="breakdown-summary">{{ item.summary }}</p>
                  <div v-if="Object.keys(item.metrics).length" class="mini-metrics">
                    <span v-for="(value, key) in item.metrics" :key="`${item.label}-${key}`">
                      {{ key }}: {{ value }}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <div v-if="panel.highlights.length" class="section-stack">
              <div class="section-label">重点样例</div>
              <div class="highlight-list">
                <div v-for="item in panel.highlights" :key="`${panel.key}-${item.title}`" class="highlight-item">
                  <div class="breakdown-head">
                    <strong>{{ item.title }}</strong>
                    <el-tag size="small" :type="statusTagType(item.status)">{{ item.status }}</el-tag>
                  </div>
                  <p class="breakdown-summary">{{ item.summary }}</p>
                  <div class="tag-list">
                    <span v-for="tag in item.tags" :key="tag" class="mini-tag">{{ tag }}</span>
                  </div>
                </div>
              </div>
            </div>

            <div v-if="panel.trace_cases.length" class="section-stack">
              <div class="section-label">Trace 入口</div>
              <div v-if="panel.key === 'evaluation'" class="toolbar trace-toolbar">
                <el-select v-model="selectedTraceIssue" clearable placeholder="按问题类型筛选" style="width: 220px">
                  <el-option
                    v-for="issue in traceIssueOptions"
                    :key="issue"
                    :label="issue"
                    :value="issue"
                  />
                </el-select>
                <span class="muted">当前显示 {{ filteredTraceCases(panel).length }} / {{ panel.trace_cases.length }} 个低分 case</span>
              </div>
              <div class="trace-case-list">
                <div v-for="traceCase in filteredTraceCases(panel)" :key="`${panel.key}-${traceCase.case_id}`" class="trace-case">
                  <div class="breakdown-head">
                    <strong>{{ traceCase.case_id }}</strong>
                    <div class="trace-head-actions">
                      <el-tag size="small" type="warning">{{ traceCase.issue }}</el-tag>
                      <el-button text type="primary" @click="openTraceJson(traceCase)">查看原始 trace</el-button>
                    </div>
                  </div>
                  <p class="breakdown-summary">{{ traceCase.title }}</p>
                  <el-button
                    text
                    type="primary"
                    class="trace-toggle"
                    @click="toggleTraceCase(traceCase.case_id)"
                  >
                    {{ expandedTraceCases[traceCase.case_id] ? '收起详情' : '展开详情' }}
                  </el-button>
                  <div class="trace-timeline">
                    <div v-for="event in traceCase.events" :key="`${traceCase.case_id}-${event.name}`" class="trace-step">
                      <div class="trace-dot"></div>
                      <div class="trace-content">
                        <div class="trace-name">{{ event.name }}</div>
                        <div class="trace-summary">{{ event.summary }}</div>
                        <div v-if="expandedTraceCases[traceCase.case_id]" class="trace-details">
                          <div v-if="Object.keys(event.inputs).length" class="trace-detail-group">
                            <div class="trace-detail-title">inputs</div>
                            <div v-for="(value, key) in event.inputs" :key="`${traceCase.case_id}-${event.name}-in-${key}`" class="trace-detail-row">
                              <span class="trace-detail-key">{{ key }}</span>
                              <span class="trace-detail-value">{{ value }}</span>
                            </div>
                          </div>
                          <div v-if="Object.keys(event.outputs).length" class="trace-detail-group">
                            <div class="trace-detail-title">outputs</div>
                            <div v-for="(value, key) in event.outputs" :key="`${traceCase.case_id}-${event.name}-out-${key}`" class="trace-detail-row">
                              <span class="trace-detail-key">{{ key }}</span>
                              <span class="trace-detail-value">{{ value }}</span>
                            </div>
                          </div>
                          <div v-if="Object.keys(event.metadata).length" class="trace-detail-group">
                            <div class="trace-detail-title">metadata</div>
                            <div v-for="(value, key) in event.metadata" :key="`${traceCase.case_id}-${event.name}-meta-${key}`" class="trace-detail-row">
                              <span class="trace-detail-key">{{ key }}</span>
                              <span class="trace-detail-value">{{ value }}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div v-if="panel.evidence.length" class="section-stack">
              <div class="section-label">证据文件</div>
              <ul class="evidence-list">
                <li v-for="item in panel.evidence" :key="item.path">
                  <span class="evidence-label">{{ item.label }}</span>
                  <code class="mono">{{ item.path }}</code>
                </li>
              </ul>
            </div>
          </article>
        </div>
      </section>

      <section v-if="activeTab === 'status'" class="stack">
        <el-card>
          <template #header>系统状态</template>
          <div v-if="status" class="status-row">
            <el-tag type="success">API {{ status.status }}</el-tag>
            <el-tag>版本 {{ status.version }}</el-tag>
            <el-tag :type="status.llm_enabled ? 'success' : 'warning'">
              LLM {{ status.llm_enabled ? '已启用' : '未启用' }}
            </el-tag>
            <el-tag>{{ status.llm_provider || 'unknown' }}</el-tag>
            <el-tag>{{ status.llm_model || '未配置模型' }}</el-tag>
            <el-tag :type="status.vector_store_ready ? 'success' : 'info'">
              向量库 {{ status.vector_store_ready ? '已就绪' : '未就绪' }}
            </el-tag>
          </div>
        </el-card>
      </section>

      <section v-if="activeTab === 'documents'" class="grid-2">
        <el-card>
          <template #header>资料入库</template>
          <div class="toolbar">
            <el-select v-model="docsSource" style="width: 240px">
              <el-option label="seed_docs" value="seed_docs" />
              <el-option label="real_manuals_sanitized" value="real_manuals_sanitized" />
              <el-option label="uploaded_docs" value="uploaded_docs" />
            </el-select>
            <el-button type="primary" :loading="loading" @click="ingest">执行入库</el-button>
          </div>
          <pre class="mono">{{ ingestResult }}</pre>
        </el-card>

        <el-card>
          <template #header>上传资料</template>
          <el-upload :auto-upload="false" :on-change="onFileChange" :limit="1">
            <el-button>选择文件</el-button>
          </el-upload>
          <el-button class="section" type="primary" :disabled="!uploadFile" @click="upload">
            上传到 uploaded_docs
          </el-button>
          <pre class="mono">{{ uploadResult }}</pre>
        </el-card>
      </section>

      <section v-if="activeTab === 'chat'" class="stack">
        <el-card>
          <template #header>诊断问答</template>
          <el-input
            v-model="question"
            type="textarea"
            :rows="4"
            placeholder="例如：UPS-30K 电池冒烟或有异味，可以直接重启吗？"
          />
          <el-button class="section" type="primary" :loading="loading" @click="ask">提交问答</el-button>
          <div v-if="chatResult" class="status-row section">
            <el-tag :type="chatResult.llm_used ? 'success' : 'info'">
              {{ chatResult.llm_used ? 'LLM 生成' : '本地兜底' }}
            </el-tag>
            <el-tag v-if="chatResult.insufficient" type="warning">资料不足</el-tag>
            <el-tag v-if="chatResult.safety_warning" type="danger">触发安全后处理</el-tag>
          </div>
          <el-input v-if="chatResult" :model-value="chatResult.answer" type="textarea" :rows="8" readonly />
        </el-card>

        <el-card v-if="chatResult">
          <template #header>引用来源</template>
          <div v-for="citation in chatResult.citations" :key="citation.source + citation.chunk_index" class="citation">
            <strong>{{ citation.source }} / chunk {{ citation.chunk_index }}</strong>
            <div class="muted">{{ citation.content }}</div>
          </div>
        </el-card>
      </section>

      <section v-if="activeTab === 'session'" class="stack">
        <el-card>
          <template #header>多轮会话</template>
          <el-input v-model="sessionId" class="section" placeholder="session id" />
          <el-input v-model="sessionQuestion" type="textarea" :rows="3" placeholder="例如：它还能继续运行吗？" />
          <el-button class="section" type="primary" @click="askSession">继续提问</el-button>
          <pre class="mono">{{ sessionResult }}</pre>
        </el-card>
      </section>

      <section v-if="activeTab === 'tickets'" class="grid-2">
        <el-card>
          <template #header>启动工单</template>
          <el-input v-model="ticketQuestion" type="textarea" :rows="4" />
          <el-input v-model="idempotencyKey" class="section" placeholder="幂等 key" />
          <el-button type="primary" @click="createTicket">启动工单</el-button>
          <pre class="mono">{{ ticketResult }}</pre>
        </el-card>

        <el-card>
          <template #header>人工确认 / 关闭</template>
          <el-select v-model="selectedTicketId" class="section" placeholder="选择工单" style="width: 100%">
            <el-option
              v-for="ticket in tickets"
              :key="ticket.ticket_id"
              :label="`${ticket.ticket_id} / ${ticket.status}`"
              :value="ticket.ticket_id"
            />
          </el-select>
          <div class="toolbar section">
            <el-input v-model="reviewer" placeholder="确认人" style="width: 140px" />
            <el-input v-model="decision" placeholder="decision" style="width: 140px" />
            <el-button @click="resumeSelectedTicket">人工确认</el-button>
          </div>
          <div class="toolbar">
            <el-input v-model="closedBy" placeholder="关闭人" style="width: 140px" />
            <el-button type="danger" @click="closeSelectedTicket">关闭工单</el-button>
          </div>
        </el-card>

        <el-card class="full-span">
          <template #header>工单列表</template>
          <el-table :data="tickets" size="small">
            <el-table-column prop="ticket_id" label="Ticket ID" width="180" />
            <el-table-column prop="status" label="状态" width="130" />
            <el-table-column prop="risk_level" label="风险" width="120" />
            <el-table-column prop="device_model" label="设备" width="140" />
            <el-table-column prop="question" label="问题" />
          </el-table>
        </el-card>
      </section>

      <section v-if="activeTab === 'eval'" class="stack">
        <el-card>
          <template #header>评测中心</template>
          <div class="toolbar">
            <el-select v-model="evaluationType" style="width: 180px">
              <el-option label="RAGAS" value="ragas" />
              <el-option label="回归" value="regression" />
              <el-option label="对抗" value="adversarial" />
            </el-select>
            <el-input v-model="casesPath" style="width: 420px" />
            <el-select v-model="docsSource" style="width: 240px">
              <el-option label="seed_docs" value="seed_docs" />
              <el-option label="real_manuals_sanitized" value="real_manuals_sanitized" />
              <el-option label="uploaded_docs" value="uploaded_docs" />
            </el-select>
            <el-button type="primary" @click="evaluate">运行评测</el-button>
          </div>
          <pre class="mono">{{ evaluationResult }}</pre>
        </el-card>
      </section>

      <section v-if="activeTab === 'badcases'" class="stack">
        <el-card>
          <template #header>Bad Case</template>
          <p class="muted">
            当前版本已把真实数据 bad case 与 A-v1.5 多模态 bad case 收进验收中心，可直接用于面试讲边界与失败模式。
          </p>
          <pre class="mono">docs/A-real-data_bad_cases.md
docs/A-v1.5_bad_cases.md</pre>
        </el-card>
      </section>
    </main>
  </div>

  <el-dialog
    v-model="traceDialogVisible"
    title="原始 Trace JSON"
    width="880px"
    top="6vh"
  >
    <div class="trace-dialog-head" v-if="selectedTraceCase">
      <strong>{{ selectedTraceCase.case_id }}</strong>
      <span class="muted">{{ selectedTraceCase.title }}</span>
    </div>
    <pre class="mono trace-json">{{ selectedTraceJson }}</pre>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import {
  AcceptanceOverviewResponse,
  AcceptancePanel,
  AcceptanceTraceCase,
  ChatResponse,
  TicketRecord,
  chat,
  closeTicket,
  ingestDocuments,
  listTickets,
  loadAcceptanceOverview,
  loadSystemStatus,
  resumeTicket,
  runEvaluation,
  sessionChat,
  startTicket,
  uploadDocument
} from './api'

const navItems = [
  { key: 'acceptance', label: '演示中心', hint: '展示文本主链、多模态、评测与 bad case 的统一证据面板。' },
  { key: 'status', label: '系统状态', hint: '查看 API、LLM 与向量库当前状态。' },
  { key: 'documents', label: '资料管理', hint: '上传资料、切换 docs source 并执行入库。' },
  { key: 'chat', label: '诊断问答', hint: '验证 grounded 回答、引用与安全后处理。' },
  { key: 'session', label: '多轮会话', hint: '演示会话上下文解析与追问。' },
  { key: 'tickets', label: '工单闭环', hint: '启动、人工确认并关闭售后工单。' },
  { key: 'eval', label: '评测中心', hint: '快速触发 regression、RAGAS 与 adversarial 入口。' },
  { key: 'badcases', label: 'Bad Case', hint: '集中查看当前版本已知边界。' }
]

const activeTab = ref('acceptance')
const currentNav = computed(() => navItems.find((item) => item.key === activeTab.value))
const status = ref<any>(null)
const acceptanceOverview = ref<AcceptanceOverviewResponse | null>(null)
const loading = ref(false)
const docsSource = ref('real_manuals_sanitized')
const ingestResult = ref('')
const uploadResult = ref('')
const uploadFile = ref<File | null>(null)
const question = ref('UPS-30K 电池冒烟或有异味，可以直接重启吗？')
const chatResult = ref<ChatResponse | null>(null)
const sessionId = ref('enterprise-session')
const sessionQuestion = ref('A100 出现 E-17 报警怎么排查？')
const sessionResult = ref('')
const ticketQuestion = ref('UPS-30K 电池有异味并冒烟，现场想重启。')
const idempotencyKey = ref(`web-${Date.now()}`)
const ticketResult = ref('')
const tickets = ref<TicketRecord[]>([])
const selectedTicketId = ref('')
const reviewer = ref('王工')
const decision = ref('approved')
const closedBy = ref('李工')
const evaluationType = ref('regression')
const casesPath = ref('data/eval/real_regression_cases_v1.json')
const evaluationResult = ref('')
const expandedTraceCases = ref<Record<string, boolean>>({})
const selectedTraceIssue = ref('')
const traceDialogVisible = ref(false)
const selectedTraceCase = ref<AcceptanceTraceCase | null>(null)

const acceptancePanels = computed(() => acceptanceOverview.value?.panels || [])
const providerPanel = computed(() => acceptancePanels.value.find((panel) => panel.key === 'provider'))
const multimodalPanel = computed(() => acceptancePanels.value.find((panel) => panel.key === 'multimodal'))
const evaluationPanel = computed(() => acceptancePanels.value.find((panel) => panel.key === 'evaluation'))
const traceIssueOptions = computed(() => {
  const issues = new Set((evaluationPanel.value?.trace_cases || []).map((item) => item.issue))
  return Array.from(issues)
})
const selectedTraceJson = computed(() =>
  selectedTraceCase.value ? JSON.stringify(selectedTraceCase.value.raw_trace, null, 2) : ''
)

function statusTagType(statusValue?: string) {
  if (statusValue === 'passed' || statusValue === 'ok') return 'success'
  if (statusValue === 'warning' || statusValue === 'blocked_dependency') return 'warning'
  if (statusValue === 'runtime_incompatible' || statusValue === 'runtime_resource_blocked' || statusValue === 'danger') {
    return 'danger'
  }
  if (statusValue === 'missing') return 'info'
  return 'info'
}

function toneClass(tone: string) {
  if (tone === 'success') return 'tone-success'
  if (tone === 'danger') return 'tone-danger'
  return 'tone-warning'
}

function percentWidth(value: number, total: number) {
  const denominator = total > 0 ? total : 1
  return `${Math.max(8, Math.min(100, (value / denominator) * 100))}%`
}

function percentText(value: number, total: number) {
  if (total <= 1) return value.toFixed(2)
  return `${Math.round((value / total) * 100)}%`
}

function toggleTraceCase(caseId: string) {
  expandedTraceCases.value = {
    ...expandedTraceCases.value,
    [caseId]: !expandedTraceCases.value[caseId]
  }
}

function filteredTraceCases(panel: AcceptancePanel) {
  if (panel.key !== 'evaluation' || !selectedTraceIssue.value) return panel.trace_cases
  return panel.trace_cases.filter((item) => item.issue === selectedTraceIssue.value)
}

function openTraceJson(traceCase: AcceptanceTraceCase) {
  selectedTraceCase.value = traceCase
  traceDialogVisible.value = true
}

async function refreshAll() {
  loading.value = true
  try {
    const [statusData, ticketsData, acceptanceData] = await Promise.all([
      loadSystemStatus(),
      listTickets(),
      loadAcceptanceOverview()
    ])
    status.value = statusData
    tickets.value = ticketsData
    acceptanceOverview.value = acceptanceData
  } finally {
    loading.value = false
  }
}

async function ingest() {
  loading.value = true
  try {
    ingestResult.value = JSON.stringify(await ingestDocuments(docsSource.value), null, 2)
    await refreshAll()
  } finally {
    loading.value = false
  }
}

function onFileChange(file: { raw?: File }) {
  uploadFile.value = file.raw || null
}

async function upload() {
  if (!uploadFile.value) return
  uploadResult.value = JSON.stringify(await uploadDocument(uploadFile.value), null, 2)
}

async function ask() {
  loading.value = true
  try {
    chatResult.value = await chat(question.value)
  } finally {
    loading.value = false
  }
}

async function askSession() {
  sessionResult.value = JSON.stringify(await sessionChat(sessionId.value, sessionQuestion.value), null, 2)
}

async function createTicket() {
  const result = await startTicket(ticketQuestion.value, idempotencyKey.value)
  ticketResult.value = JSON.stringify(result, null, 2)
  selectedTicketId.value = result.ticket.ticket_id
  await refreshAll()
}

async function resumeSelectedTicket() {
  if (!selectedTicketId.value) return
  ticketResult.value = JSON.stringify(
    await resumeTicket(selectedTicketId.value, reviewer.value, decision.value),
    null,
    2
  )
  await refreshAll()
}

async function closeSelectedTicket() {
  if (!selectedTicketId.value) return
  ticketResult.value = JSON.stringify(await closeTicket(selectedTicketId.value, closedBy.value), null, 2)
  await refreshAll()
}

async function evaluate() {
  evaluationResult.value = JSON.stringify(
    await runEvaluation(evaluationType.value, casesPath.value, docsSource.value),
    null,
    2
  )
}

onMounted(refreshAll)
</script>
