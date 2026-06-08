<template>
  <section class="stack">
    <el-card class="quality-hero" data-testid="quality-overview-card">
      <template #header>
        <div class="card-header-row">
          <span>RAG 质量洞察</span>
          <el-tag :type="panelStatusType(evaluationPanel?.status || 'info')" size="small">
            {{ evaluationPanel?.status || 'pending' }}
          </el-tag>
        </div>
      </template>

      <p class="muted">
        {{ evaluationPanel?.summary || '等待验收中心返回评测数据；本页用于面试时集中讲 RAG 质量、Bad Case 和工程取舍。' }}
      </p>

      <div class="metric-grid section">
        <div class="metric-card primary" data-testid="quality-regression-pass-rate">
          <span class="metric-label">regression</span>
          <strong>{{ regressionPassRate }}</strong>
          <p>真实回归样本通过情况，用来证明主链不是只靠单条 demo。</p>
        </div>
        <div class="metric-card" data-testid="quality-context-precision">
          <span class="metric-label">context_precision</span>
          <strong>{{ metricValue('context_precision') }}</strong>
          <p>检索上下文是否真正支撑答案。</p>
        </div>
        <div class="metric-card" data-testid="quality-faithfulness">
          <span class="metric-label">faithfulness</span>
          <strong>{{ metricValue('faithfulness') }}</strong>
          <p>回答是否忠实于资料，避免幻觉。</p>
        </div>
        <div class="metric-card" data-testid="quality-context-recall">
          <span class="metric-label">context_recall</span>
          <strong>{{ metricValue('context_recall') }}</strong>
          <p>关键证据是否被召回。</p>
        </div>
      </div>
    </el-card>

    <div class="quality-columns">
      <el-card data-testid="quality-badcase-count">
        <template #header>
          <div class="card-header-row">
            <span>Bad Case 边界</span>
            <el-tag :type="panelStatusType(badCasePanel?.status || 'info')" size="small">
              {{ badCaseCount }}
            </el-tag>
          </div>
        </template>
        <p>{{ badCasePanel?.summary || '暂无 bad case 汇总。' }}</p>
        <div v-if="badCaseHighlights.length > 0" class="section">
          <div v-for="item in badCaseHighlights" :key="item.title" class="case-item">
            <el-tag :type="panelStatusType(item.status)" size="small">{{ item.status }}</el-tag>
            <strong>{{ item.title }}</strong>
            <p class="muted">{{ item.summary }}</p>
          </div>
        </div>
        <ul class="compact-list section">
          <li>资料不足时拒答，避免企业维修场景中编造结论。</li>
          <li>高风险动作升级人工工单，而不是直接给不可控建议。</li>
          <li>Bad case 保留为后续调参、检索改进和评测扩容样本。</li>
        </ul>
      </el-card>

      <el-card data-testid="quality-tradeoff-lane">
        <template #header>工程取舍路线</template>
        <div v-for="item in tradeoffs" :key="item.title" class="tradeoff-item">
          <div>
            <strong>{{ item.title }}</strong>
            <p class="muted">{{ item.summary }}</p>
          </div>
          <el-tag size="small" type="info">{{ item.next }}</el-tag>
        </div>
      </el-card>
    </div>

    <el-card data-testid="quality-trace-case-list">
      <template #header>低分 Trace 复盘</template>
      <el-empty v-if="traceCases.length === 0" description="暂无 trace case；可从评测报告继续沉淀低分样本。" />
      <el-collapse v-else>
        <el-collapse-item v-for="trace in traceCases" :key="trace.case_id" :title="`${trace.case_id} - ${trace.issue}`">
          <el-timeline>
            <el-timeline-item v-for="(event, idx) in trace.events" :key="idx" :timestamp="event.name" placement="top">
              <p>{{ event.summary }}</p>
            </el-timeline-item>
          </el-timeline>
        </el-collapse-item>
      </el-collapse>
    </el-card>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import type { AcceptanceOverviewResponse, AcceptancePanel } from '../api/types'

const props = defineProps<{ overview: AcceptanceOverviewResponse | null }>()

const evaluationPanel = computed(() => findPanel('evaluation'))
const badCasePanel = computed(() => findPanel('badcases'))
const qualityMetrics = computed(() => evaluationPanel.value?.chart || [])
const traceCases = computed(() => evaluationPanel.value?.trace_cases || [])
const badCaseHighlights = computed(() => badCasePanel.value?.highlights || [])

const tradeoffs = [
  {
    title: 'Demo 成本 vs 生产增强',
    summary: 'SQLite + Chroma 让面试现场可快速启动；PostgreSQL + Redis + Milvus 保留生产落地路径。',
    next: 'compose',
  },
  {
    title: '内置 JobService vs 外部队列',
    summary: '当前实现清晰展示 claim/cancel/retry/timeout/heartbeat；多实例规模化时演进到 Celery/RQ/Redis Queue。',
    next: '外部队列',
  },
  {
    title: '文本 metrics vs 可视化观测',
    summary: 'System Status 已解析 /metrics；下一步接 Grafana/OTel 做趋势和告警。',
    next: 'Grafana',
  },
]

const regressionPassRate = computed(() => {
  const regression = evaluationPanel.value?.metrics?.regression
  if (regression) return regression
  const passRate = qualityMetrics.value.find((item) => item.label === 'regression_pass_rate')
  return passRate ? `${passRate.value}/${passRate.total}` : '见评测报告'
})

const badCaseCount = computed(() => {
  const metrics = badCasePanel.value?.metrics || {}
  const real = Number(metrics.real_data_cases || 0)
  const multimodal = Number(metrics.multimodal_cases || 0)
  const total = real + multimodal
  return total > 0 ? `${total} cases` : 'pending'
})

function findPanel(key: string): AcceptancePanel | null {
  return props.overview?.panels.find((panel) => panel.key === key) || null
}

function metricValue(label: string): string {
  const metric = qualityMetrics.value.find((item) => item.label === label)
  if (!metric) return '见评测报告'
  if (metric.total === 1) return metric.value.toFixed(3)
  return `${metric.value}/${metric.total}`
}

function panelStatusType(status: string): 'success' | 'warning' | 'danger' | 'info' {
  if (status === 'passed' || status === 'ok') return 'success'
  if (status === 'warning' || status === 'degraded') return 'warning'
  if (status === 'error' || status === 'danger') return 'danger'
  return 'info'
}
</script>

<style scoped>
.quality-hero {
  border: 1px solid #d9ecff;
  background: linear-gradient(135deg, #f8fbff 0%, #ffffff 50%, #f8fff5 100%);
}

.card-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.metric-card {
  padding: 14px;
  border: 1px solid #ebeef5;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.86);
}

.metric-card.primary {
  background: linear-gradient(135deg, #ecf5ff 0%, #ffffff 100%);
}

.metric-label {
  display: block;
  margin-bottom: 6px;
  color: #909399;
  font-size: 12px;
}

.metric-card strong {
  display: block;
  color: #303133;
  font-size: 22px;
}

.metric-card p,
.case-item p,
.tradeoff-item p {
  margin: 6px 0 0;
  line-height: 1.5;
}

.quality-columns {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 16px;
}

.case-item {
  padding: 10px 0;
  border-bottom: 1px solid #ebeef5;
}

.tradeoff-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid #ebeef5;
}

.compact-list {
  margin: 0;
  padding-left: 20px;
  color: #606266;
  line-height: 1.7;
}

@media (max-width: 980px) {
  .metric-grid,
  .quality-columns {
    grid-template-columns: 1fr;
  }
}
</style>
