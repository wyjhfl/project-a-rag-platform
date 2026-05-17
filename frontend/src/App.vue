<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="brand">Project A</div>
      <div class="subtitle">企业设备售后诊断 RAG 工作台</div>
      <nav class="nav">
        <button
          v-for="item in navItems"
          :key="item.key"
          :class="{ active: activeTab === item.key }"
          @click="activeTab = item.key"
        >
          {{ item.label }}
        </button>
      </nav>
    </aside>

    <main class="main">
      <div class="topbar">
        <h1 class="page-title">{{ currentTitle }}</h1>
        <el-button @click="refreshStatus">刷新状态</el-button>
      </div>

      <el-alert
        v-if="status && !status.llm_enabled"
        class="section"
        title="当前未接入真实大模型：请在 .env 中配置 LLM_API_KEY / LLM_BASE_URL / LLM_MODEL"
        type="warning"
        show-icon
      />

      <section v-if="activeTab === 'status'" class="grid">
        <el-card class="full">
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
              向量库 {{ status.vector_store_ready ? '已入库' : '未入库' }}
            </el-tag>
          </div>
        </el-card>
      </section>

      <section v-if="activeTab === 'documents'" class="grid">
        <el-card>
          <template #header>资料入库</template>
          <div class="toolbar">
            <el-select v-model="docsSource" style="width: 230px">
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

      <section v-if="activeTab === 'chat'" class="grid">
        <el-card class="full">
          <template #header>诊断问答</template>
          <el-input
            v-model="question"
            type="textarea"
            :rows="3"
            placeholder="例如：UPS-30K 电池冒烟或有异味，可以直接重启吗？"
          />
          <el-button class="section" type="primary" :loading="loading" @click="ask">
            发送
          </el-button>
          <div class="status-row section" v-if="chatResult">
            <el-tag :type="chatResult.llm_used ? 'success' : 'info'">
              {{ chatResult.llm_used ? 'LLM 生成' : '本地兜底' }}
            </el-tag>
            <el-tag v-if="chatResult.insufficient" type="warning">资料不足</el-tag>
            <el-tag v-if="chatResult.safety_warning" type="danger">安全后处理</el-tag>
          </div>
          <el-input v-if="chatResult" :model-value="chatResult.answer" type="textarea" :rows="8" readonly />
        </el-card>
        <el-card class="full" v-if="chatResult">
          <template #header>引用来源</template>
          <div v-for="citation in chatResult.citations" :key="citation.source + citation.chunk_index" class="citation">
            <strong>{{ citation.source }} / chunk {{ citation.chunk_index }}</strong>
            <div class="muted">{{ citation.content }}</div>
          </div>
        </el-card>
      </section>

      <section v-if="activeTab === 'session'" class="grid">
        <el-card class="full">
          <template #header>多轮会话</template>
          <el-input v-model="sessionId" class="section" placeholder="session id" />
          <el-input v-model="sessionQuestion" type="textarea" :rows="3" placeholder="它还能继续运行吗？" />
          <el-button class="section" type="primary" @click="askSession">发送</el-button>
          <pre class="mono">{{ sessionResult }}</pre>
        </el-card>
      </section>

      <section v-if="activeTab === 'tickets'" class="grid">
        <el-card>
          <template #header>启动工单</template>
          <el-input v-model="ticketQuestion" type="textarea" :rows="4" />
          <el-input v-model="idempotencyKey" class="section" placeholder="幂等 Key" />
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
        <el-card class="full">
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

      <section v-if="activeTab === 'eval'" class="grid">
        <el-card class="full">
          <template #header>评测中心</template>
          <div class="toolbar">
            <el-select v-model="evaluationType" style="width: 180px">
              <el-option label="RAGAS" value="ragas" />
              <el-option label="回归" value="regression" />
              <el-option label="对抗" value="adversarial" />
            </el-select>
            <el-input v-model="casesPath" style="width: 420px" />
            <el-select v-model="docsSource" style="width: 230px">
              <el-option label="seed_docs" value="seed_docs" />
              <el-option label="real_manuals_sanitized" value="real_manuals_sanitized" />
              <el-option label="uploaded_docs" value="uploaded_docs" />
            </el-select>
            <el-button type="primary" @click="evaluate">运行评测</el-button>
          </div>
          <pre class="mono">{{ evaluationResult }}</pre>
        </el-card>
      </section>

      <section v-if="activeTab === 'badcases'" class="grid">
        <el-card class="full">
          <template #header>Bad Case</template>
          <p class="muted">当前版本通过文档文件记录 bad case，后续可升级为数据库管理。</p>
          <pre class="mono">
docs/A-real-data_bad_cases.md
bad_cases/v0.5_evaluation_deploy.md
          </pre>
        </el-card>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import {
  chat,
  ChatResponse,
  closeTicket,
  ingestDocuments,
  listTickets,
  loadSystemStatus,
  resumeTicket,
  runEvaluation,
  sessionChat,
  startTicket,
  TicketRecord,
  uploadDocument
} from './api'

const navItems = [
  { key: 'status', label: '系统状态' },
  { key: 'documents', label: '资料管理' },
  { key: 'chat', label: '诊断问答' },
  { key: 'session', label: '多轮会话' },
  { key: 'tickets', label: '工单闭环' },
  { key: 'eval', label: '评测中心' },
  { key: 'badcases', label: 'Bad Case' }
]

const activeTab = ref('status')
const currentTitle = computed(() => navItems.find((item) => item.key === activeTab.value)?.label)
const status = ref<any>(null)
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

async function refreshStatus() {
  status.value = await loadSystemStatus()
  tickets.value = await listTickets()
}

async function ingest() {
  loading.value = true
  try {
    ingestResult.value = JSON.stringify(await ingestDocuments(docsSource.value), null, 2)
    await refreshStatus()
  } finally {
    loading.value = false
  }
}

function onFileChange(file: any) {
  uploadFile.value = file.raw
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
  await refreshStatus()
}

async function resumeSelectedTicket() {
  if (!selectedTicketId.value) return
  ticketResult.value = JSON.stringify(
    await resumeTicket(selectedTicketId.value, reviewer.value, decision.value),
    null,
    2
  )
  await refreshStatus()
}

async function closeSelectedTicket() {
  if (!selectedTicketId.value) return
  ticketResult.value = JSON.stringify(await closeTicket(selectedTicketId.value, closedBy.value), null, 2)
  await refreshStatus()
}

async function evaluate() {
  evaluationResult.value = JSON.stringify(
    await runEvaluation(evaluationType.value, casesPath.value, docsSource.value),
    null,
    2
  )
}

onMounted(refreshStatus)
</script>
