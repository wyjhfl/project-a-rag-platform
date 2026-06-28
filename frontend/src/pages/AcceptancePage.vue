<template>
  <section class="stack">
    <el-card class="showcase-card" data-testid="interview-showcase-card">
      <template #header>
        <div class="card-header-row">
          <span>面试展示入口</span>
          <el-tag type="success" size="small">{{ RELEASE_VERSION }}</el-tag>
        </div>
      </template>

      <div class="showcase-hero">
        <div>
          <h2>企业设备售后诊断 RAG 平台</h2>
          <p class="showcase-pitch" data-testid="interview-pitch">{{ interviewPitch }}</p>
          <div class="tag-row">
            <el-tag v-for="tag in showcaseTags" :key="tag" size="small" type="info">{{ tag }}</el-tag>
          </div>
        </div>
        <div class="showcase-actions">
          <el-button data-testid="copy-interview-pitch" type="primary" @click="copyPitch">复制 30 秒讲法</el-button>
          <el-button data-testid="open-release-notes" tag="a" :href="RELEASE_URL" target="_blank" rel="noreferrer">
            查看 Release
          </el-button>
        </div>
      </div>

      <div class="showcase-grid section" data-testid="showcase-proof-grid">
        <div v-for="item in proofItems" :key="item.label" class="proof-tile">
          <span class="proof-label">{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
          <p class="muted">{{ item.summary }}</p>
        </div>
      </div>

      <div class="showcase-columns section">
        <div data-testid="showcase-architecture-pillars">
          <h4>技术亮点</h4>
          <ul class="compact-list">
            <li v-for="pillar in architecturePillars" :key="pillar">{{ pillar }}</li>
          </ul>
        </div>
        <div data-testid="showcase-demo-route">
          <h4>5 分钟 Demo 路线</h4>
          <ol class="compact-list">
            <li v-for="step in demoRoute" :key="step">{{ step }}</li>
          </ol>
        </div>
      </div>
    </el-card>

    <el-card class="quality-card" data-testid="rag-quality-card">
      <template #header>
        <div class="card-header-row">
          <span>RAG 质量证据</span>
          <el-tag :type="panelStatusType(qualityPanel?.status || 'info')" size="small">
            {{ qualityPanel?.status || 'pending' }}
          </el-tag>
        </div>
      </template>

      <p class="muted">{{ qualityPanel?.summary || '等待验收中心返回评测数据。' }}</p>
      <div class="quality-grid section">
        <div class="quality-tile" data-testid="rag-quality-metric-context-precision">
          <span class="proof-label">context_precision</span>
          <strong>{{ qualityMetricValue('context_precision') }}</strong>
          <p class="muted">检索到的上下文有多少真正支撑答案。</p>
        </div>
        <div class="quality-tile" data-testid="rag-quality-metric-faithfulness">
          <span class="proof-label">faithfulness</span>
          <strong>{{ qualityMetricValue('faithfulness') }}</strong>
          <p class="muted">回答是否忠实于检索上下文，避免编造。</p>
        </div>
        <div class="quality-tile" data-testid="rag-quality-metric-context-recall">
          <span class="proof-label">context_recall</span>
          <strong>{{ qualityMetricValue('context_recall') }}</strong>
          <p class="muted">关键证据是否被检索链路召回。</p>
        </div>
      </div>

      <div class="showcase-columns section">
        <div class="boundary-card" data-testid="bad-case-boundary-card">
          <h4>Bad Case 与边界</h4>
          <p>{{ badCasePanel?.summary || '暂无 bad case 汇总。' }}</p>
          <ul class="compact-list">
            <li>资料不足时拒答，而不是强行生成不可靠答案。</li>
            <li>高风险维修建议进入人工工单闭环。</li>
            <li>低分样本保留 trace，方便复盘检索、上下文和生成问题。</li>
          </ul>
        </div>
        <div class="boundary-card" data-testid="risk-tradeoff-card">
          <h4>面试可讲取舍</h4>
          <ul class="compact-list">
            <li v-for="item in riskTradeoffs" :key="item">{{ item }}</li>
          </ul>
        </div>
      </div>
    </el-card>

    <el-alert v-if="!overview" type="info" :closable="false" show-icon class="section">
      <template #title>正在加载验收概览数据…</template>
    </el-alert>

    <template v-if="overview">
      <div class="overview-header">
        <el-tag :type="overview.status === 'ok' ? 'success' : 'warning'" size="large">
          {{ overview.status === 'ok' ? '验收通过' : '部分待改进' }}
        </el-tag>
        <span class="muted">版本: {{ overview.version }}</span>
      </div>

      <div v-for="panel in overview.panels" :key="panel.key" class="panel-section">
        <el-card>
          <template #header>
            <div class="card-header-row">
              <span>{{ panel.title }}</span>
              <el-tag :type="panelStatusType(panel.status)" size="small">{{ panel.status }}</el-tag>
            </div>
          </template>

          <p>{{ panel.summary }}</p>

          <el-descriptions v-if="Object.keys(panel.metrics).length > 0" :column="2" border size="small" class="section">
            <el-descriptions-item v-for="(value, key) in panel.metrics" :key="String(key)" :label="String(key)">
              {{ value }}
            </el-descriptions-item>
          </el-descriptions>

          <div v-if="panel.breakdown.length > 0" class="section">
            <h4>分项明细</h4>
            <el-table :data="panel.breakdown" size="small" stripe>
              <el-table-column prop="label" label="项目" width="200" />
              <el-table-column prop="status" label="状态" width="120">
                <template #default="{ row }">
                  <el-tag :type="panelStatusType(row.status)" size="small">{{ row.status }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="summary" label="说明" min-width="200" />
            </el-table>
          </div>

          <div v-if="panel.chart.length > 0" class="section">
            <h4>指标图表</h4>
            <div class="chart-bars">
              <div v-for="bar in panel.chart" :key="bar.label" class="chart-bar-row">
                <span class="chart-label">{{ bar.label }}</span>
                <div class="chart-bar-track">
                  <div
                    class="chart-bar-fill"
                    :class="`tone-${bar.tone}`"
                    :style="{ width: `${(bar.value / bar.total) * 100}%` }"
                  />
                </div>
                <span class="chart-value">{{ bar.value }} / {{ bar.total }}</span>
              </div>
            </div>
          </div>

          <div v-if="panel.highlights.length > 0" class="section">
            <h4>关键发现</h4>
            <div v-for="hl in panel.highlights" :key="hl.title" class="highlight-item">
              <el-tag :type="panelStatusType(hl.status)" size="small">{{ hl.status }}</el-tag>
              <strong>{{ hl.title }}</strong>
              <p class="muted">{{ hl.summary }}</p>
              <div v-if="hl.tags.length > 0" class="tag-row">
                <el-tag v-for="tag in hl.tags" :key="tag" size="small" type="info">{{ tag }}</el-tag>
              </div>
            </div>
          </div>

          <div v-if="panel.trace_cases.length > 0" class="section">
            <h4>Trace 时间线</h4>
            <el-collapse>
              <el-collapse-item v-for="tc in panel.trace_cases" :key="tc.case_id" :title="`${tc.title} — ${tc.issue}`">
                <el-timeline>
                  <el-timeline-item v-for="(evt, idx) in tc.events" :key="idx" :timestamp="evt.name" placement="top">
                    <p>{{ evt.summary }}</p>
                    <el-descriptions v-if="Object.keys(evt.inputs).length > 0" :column="1" size="small" border>
                      <el-descriptions-item v-for="(v, k) in evt.inputs" :key="String(k)" :label="String(k)">{{ v }}</el-descriptions-item>
                    </el-descriptions>
                  </el-timeline-item>
                </el-timeline>
              </el-collapse-item>
            </el-collapse>
          </div>

          <div v-if="panel.evidence.length > 0" class="section">
            <h4>证据文件</h4>
            <ul class="evidence-list">
              <li v-for="ev in panel.evidence" :key="ev.path">
                <span class="muted">{{ ev.label }}: {{ ev.path }}</span>
              </li>
            </ul>
          </div>
        </el-card>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import type { AcceptanceOverviewResponse } from '../api/types'
import { ElMessage } from '../plugins/element-plus'
import { RELEASE_URL, RELEASE_VERSION } from '../release'

const props = defineProps<{ overview: AcceptanceOverviewResponse | null }>()

const interviewPitch = '我做的 Project A 不是普通聊天 demo，而是企业设备售后诊断 RAG 平台：它能把故障描述转成可引用答案，在资料不足或高风险时拒答/升级人工，并用评测、审计、Metrics、E2E 和生产验收脚本证明工程质量。'

const showcaseTags = ['FastAPI', 'Vue 3', 'RAG', 'Async Jobs', 'Audit', 'OpenAPI', 'E2E', 'Docker']

const proofItems = [
  { label: '后端测试', value: 'pytest suite', summary: '覆盖认证、RAG、安全、工单、Redis 限流与 Worker 并发' },
  { label: '前端验收', value: 'Playwright E2E', summary: '覆盖系统状态、资料、Jobs、审计、工单与评测主路径' },
  { label: '生产门禁', value: '13-step gate', summary: '统一执行测试、构建、OpenAPI drift、secret scan、Docker 与 smoke' },
  { label: '可观测性', value: '/metrics + audit', summary: 'Request ID、结构化错误、Prometheus 指标和审计事件可追踪' },
]

const architecturePillars = [
  'RAG 检索 + grounded 回答 + 引用证据，避免只包装聊天接口',
  '异步 Job/Worker 把入库与评测从同步请求中解耦',
  'X-API-Key 角色、统一错误体、Request ID 与审计日志支撑运维排障',
  'OpenAPI 生成前端类型并在 CI 中阻断 schema drift',
  'Redis 限流、PostgreSQL smoke、Docker Compose 与最终验收脚本面向生产落地',
]

const demoRoute = [
  'Acceptance：用这张卡说明业务目标、技术亮点和验收证据',
  'System Status：展示 health/readyz/release/metrics 与 Request ID 排障',
  'Documents + Jobs：演示资料入库如何进入后台任务并可取消/重试/查询',
  'Chat + Tickets：展示 grounded 回答、拒答边界和人工工单升级',
  'Evaluations + Audit：用评测结果和审计日志收束工程可信度',
]

const riskTradeoffs = [
  'SQLite + Chroma 降低面试 demo 成本，PostgreSQL + Redis + Milvus 保留生产增强路径',
  '内置 JobService 展示任务生命周期，外部队列是多实例规模化的下一步',
  'OpenAPI 生成前端类型并在 CI 阻断 drift，避免手写类型长期失真',
  'Prometheus /metrics 与 Grafana demo stack 已接入，OTel 是后续可观测性增强方向',
]

const qualityPanel = computed(() => findPanel('evaluation'))
const badCasePanel = computed(() => findPanel('badcases'))
const qualityMetrics = computed(() => qualityPanel.value?.chart || [])

function findPanel(key: string) {
  return props.overview?.panels.find((panel) => panel.key === key) || null
}

function qualityMetricValue(label: string): string {
  const metric = qualityMetrics.value.find((item) => item.label === label)
  if (!metric) return '见评测报告'
  if (metric.total === 1) return metric.value.toFixed(3)
  return `${metric.value}/${metric.total}`
}

async function copyPitch() {
  try {
    await navigator.clipboard.writeText(interviewPitch)
    ElMessage.success('已复制面试 30 秒讲法')
  } catch {
    ElMessage.warning('当前浏览器不支持自动复制，请手动选择文案')
  }
}

function panelStatusType(status: string): 'success' | 'warning' | 'danger' | 'info' {
  if (status === 'passed' || status === 'ok') return 'success'
  if (status === 'warning' || status === 'degraded') return 'warning'
  if (status === 'error' || status === 'danger') return 'danger'
  return 'info'
}
</script>

<style scoped>
.showcase-card {
  border: 1px solid #d9ecff;
  background: linear-gradient(135deg, #f8fbff 0%, #ffffff 48%, #f5fff8 100%);
}

.showcase-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 16px;
  align-items: start;
}

.showcase-hero h2 {
  margin: 0 0 8px;
  font-size: 22px;
}

.showcase-pitch {
  margin: 0 0 12px;
  color: #303133;
  line-height: 1.7;
}

.showcase-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.showcase-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.proof-tile {
  padding: 12px;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.82);
}

.proof-label {
  display: block;
  margin-bottom: 6px;
  color: #909399;
  font-size: 12px;
}

.proof-tile strong {
  color: #303133;
}

.proof-tile p {
  margin: 6px 0 0;
  line-height: 1.5;
}

.showcase-columns {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.quality-card {
  border: 1px solid #e1f3d8;
}

.quality-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.quality-tile,
.boundary-card {
  padding: 12px;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  background: #fff;
}

.quality-tile strong {
  display: block;
  color: #303133;
  font-size: 20px;
}

.quality-tile p,
.boundary-card p {
  margin: 6px 0 0;
  line-height: 1.5;
}

.compact-list {
  margin: 0;
  padding-left: 20px;
  color: #606266;
  line-height: 1.7;
}

.overview-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.panel-section {
  margin-bottom: 16px;
}

.card-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.chart-bars {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.chart-bar-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chart-label {
  width: 160px;
  font-size: 13px;
  text-align: right;
}

.chart-bar-track {
  flex: 1;
  height: 16px;
  border-radius: 4px;
  background: #f0f0f0;
  overflow: hidden;
}

.chart-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s;
}

.tone-success { background: #67c23a; }
.tone-warning { background: #e6a23c; }
.tone-danger { background: #f56c6c; }
.tone-info { background: #909399; }

.chart-value {
  width: 80px;
  font-size: 13px;
  color: #909399;
}

.highlight-item {
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.tag-row {
  display: flex;
  gap: 4px;
  margin-top: 4px;
}

.evidence-list {
  padding-left: 20px;
  margin: 0;
}

@media (max-width: 900px) {
  .showcase-hero,
  .showcase-columns,
  .showcase-grid,
  .quality-grid {
    grid-template-columns: 1fr;
  }

  .showcase-actions {
    justify-content: flex-start;
  }
}
</style>
