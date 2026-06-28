<template>
  <section class="grid-2">
    <el-card>
      <template #header>Agentic RAG 诊断</template>
      <el-input
        v-model="question"
        data-testid="agentic-question"
        type="textarea"
        :rows="4"
        placeholder="输入设备型号、故障码或现场现象"
      />
      <div class="section actions">
        <el-input-number v-model="topK" :min="1" :max="10" size="small" />
        <el-switch v-model="createTicket" active-text="高风险自动建工单" />
        <el-button data-testid="agentic-run" type="primary" :loading="loading" @click="runDiagnosis">
          运行诊断
        </el-button>
      </div>
      <div v-if="error" class="section">
        <ApiErrorAlert :error="error" />
      </div>

      <template v-if="result">
        <div class="section result-panel">
          <el-tag data-testid="agentic-decision" :type="decisionType(result.decision)">
            {{ result.decision }}
          </el-tag>
          <el-tag v-if="result.ticket_id" type="warning">ticket {{ result.ticket_id }}</el-tag>
          <el-tag data-testid="agentic-trace-id" type="info">{{ result.trace_id }}</el-tag>
        </div>
        <p>{{ result.answer }}</p>
        <div class="metric-row">
          <div>
            <span class="muted">retrieval_score</span>
            <strong>{{ result.quality.retrieval_score }}</strong>
          </div>
          <div>
            <span class="muted">risk_level</span>
            <strong>{{ result.quality.risk_level }}</strong>
          </div>
          <div>
            <span class="muted">citations</span>
            <strong>{{ result.quality.citation_count }}</strong>
          </div>
        </div>
      </template>
    </el-card>

    <el-card data-testid="agentic-adaptive">
      <template #header>Adaptive Retrieval</template>
      <el-empty v-if="!knowledgeCall" description="运行诊断后展示检索控制决策" />
      <template v-else>
        <p><strong>retrieval_attempts:</strong> {{ knowledgeCall.outputs?.retrieval_attempts || 1 }}</p>
        <p><strong>retry_reason:</strong> {{ knowledgeCall.outputs?.retry_reason || '-' }}</p>
        <p><strong>rewritten_query:</strong> {{ knowledgeCall.outputs?.rewritten_query || '-' }}</p>
        <p><strong>context_sufficient:</strong> {{ knowledgeCall.outputs?.context_sufficient }}</p>
      </template>
    </el-card>

    <el-card data-testid="agentic-tool-calls">
      <template #header>工具调用时间线</template>
      <el-empty v-if="!result" description="暂无工具调用" />
      <el-timeline v-else>
        <el-timeline-item v-for="call in result.tool_calls" :key="call.tool" :timestamp="call.tool">
          <el-tag size="small">{{ call.status }}</el-tag>
          <span class="tool-summary">{{ call.summary }}</span>
        </el-timeline-item>
      </el-timeline>
    </el-card>

    <el-card data-testid="agentic-graph-relations">
      <template #header>GraphRAG 关系</template>
      <el-table :data="relations" size="small" empty-text="暂无图关系；入库后或启用 Neo4j 后展示">
        <el-table-column prop="source" label="source" />
        <el-table-column prop="relation" label="relation" />
        <el-table-column prop="target" label="target" />
        <el-table-column prop="evidence_source" label="evidence" />
      </el-table>
    </el-card>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { formatApiError } from '../api/client'
import { agentDiagnose, listGraphRelations } from '../api/endpoints'
import type { AgentDiagnoseResponse, AgentToolCall, GraphRelationRecord } from '../api/types'
import ApiErrorAlert from '../components/ApiErrorAlert.vue'

const question = ref('UPS-30K battery has smoke and odor. Can I restart it?')
const topK = ref(4)
const createTicket = ref(true)
const loading = ref(false)
const error = ref('')
const result = ref<AgentDiagnoseResponse | null>(null)
const relations = ref<GraphRelationRecord[]>([])

const knowledgeCall = computed<AgentToolCall | undefined>(() =>
  result.value?.tool_calls.find((call) => call.tool === 'knowledge_search'),
)

function decisionType(decision: string): 'success' | 'warning' | 'info' | 'danger' {
  if (decision === 'answer') return 'success'
  if (decision === 'escalate') return 'warning'
  if (decision === 'refuse') return 'danger'
  return 'info'
}

async function runDiagnosis() {
  loading.value = true
  error.value = ''
  result.value = null
  try {
    result.value = await agentDiagnose(question.value, topK.value, createTicket.value)
    await refreshRelations()
  } catch (e) {
    error.value = formatApiError(e)
  } finally {
    loading.value = false
  }
}

async function refreshRelations() {
  try {
    relations.value = await listGraphRelations()
  } catch {
    relations.value = []
  }
}

onMounted(refreshRelations)
</script>

<style scoped>
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.result-panel,
.metric-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.metric-row > div {
  min-width: 120px;
  padding: 8px;
  border-radius: 6px;
  background: #f8fafc;
}

.metric-row span,
.metric-row strong {
  display: block;
}

.tool-summary {
  margin-left: 8px;
}
</style>
