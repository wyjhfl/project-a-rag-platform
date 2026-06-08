<template>
  <section class="stack">
    <div class="toolbar">
      <el-button @click="refreshAll" :loading="loading">刷新状态</el-button>
    </div>

    <div class="health-grid">
      <el-card data-testid="healthz-card">
        <template #header>健康检查</template>
        <div v-if="healthzLoading" v-loading="true" style="min-height: 60px" />
        <template v-else-if="healthzData">
          <el-tag :type="healthzData.status === 'ok' ? 'success' : 'danger'" size="small">{{ healthzData.status }}</el-tag>
          <p class="muted section">
            service: <span data-testid="healthz-service">{{ displayValue(healthzData.service) }}</span>
            / version: <span data-testid="healthz-version">{{ displayValue(healthzData.version) }}</span>
          </p>
        </template>
        <el-empty v-else-if="!healthzError" description="暂无健康检查数据" />
        <ApiErrorAlert v-if="healthzError" :error="healthzError" />
      </el-card>

      <el-card data-testid="readyz-card">
        <template #header>就绪检查</template>
        <div v-if="readyzLoading" v-loading="true" style="min-height: 60px" />
        <template v-else-if="readyzData">
          <el-tag :type="readyzStatusType" size="small">{{ readyzData.status }}</el-tag>
          <p class="muted section">version: <span data-testid="readyz-version">{{ displayValue(readyzData.version) }}</span></p>
          <el-collapse v-if="readyzData.checks" class="section">
            <el-collapse-item title="详细检查项">
              <pre class="mono">{{ formatChecks(readyzData.checks) }}</pre>
            </el-collapse-item>
          </el-collapse>
        </template>
        <el-empty v-else-if="!readyzError" description="暂无就绪检查数据" />
        <ApiErrorAlert v-if="readyzError" :error="readyzError" />
      </el-card>

      <el-card data-testid="legacy-health-card">
        <template #header>Legacy Health</template>
        <div v-if="healthLoading" v-loading="true" style="min-height: 60px" />
        <template v-else-if="healthData">
          <el-tag :type="healthData.status === 'ok' ? 'success' : 'danger'" size="small">{{ healthData.status }}</el-tag>
          <p class="muted section">version: <span data-testid="legacy-health-version">{{ displayValue(healthData.version) }}</span></p>
        </template>
        <el-empty v-else-if="!healthError" description="暂无 legacy health 数据" />
        <ApiErrorAlert v-if="healthError" :error="healthError" />
      </el-card>
    </div>

    <el-card data-testid="system-status-panel">
      <template #header>系统详情</template>
      <div v-if="statusLoading" v-loading="true" style="min-height: 60px" />
      <template v-else-if="statusData">
        <div data-testid="system-status-loaded">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="状态">{{ displayValue(statusData.status) }}</el-descriptions-item>
          <el-descriptions-item label="版本">
            <span data-testid="system-status-version">{{ displayValue(statusData.version) }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="发布入口" :span="2">
            <a
              class="release-link"
              data-testid="system-release-link"
              :href="systemReleaseUrl"
              target="_blank"
              rel="noreferrer"
            >
              {{ systemReleaseUrl }}
            </a>
          </el-descriptions-item>
          <el-descriptions-item label="LLM Provider">{{ displayValue(statusData.llm_provider) }}</el-descriptions-item>
          <el-descriptions-item label="LLM Model">{{ displayValue(statusData.llm_model) }}</el-descriptions-item>
          <el-descriptions-item label="LLM 已启用">
            <el-tag :type="statusData.llm_enabled ? 'success' : 'info'" size="small">{{ statusData.llm_enabled ? '是' : '否' }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="向量库就绪">
            <el-tag :type="statusData.vector_store_ready ? 'success' : 'warning'" size="small">{{ statusData.vector_store_ready ? '是' : '否' }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="文档来源" :span="2">{{ displayList(statusData.docs_sources) }}</el-descriptions-item>
        </el-descriptions>
        </div>
      </template>
      <el-empty v-else-if="!statusError" description="暂无系统详情数据" />
      <ApiErrorAlert v-if="statusError" data-testid="system-status-error" :error="statusError" />
    </el-card>

    <el-card data-testid="metrics-card">
      <template #header>Metrics</template>
      <div v-if="metricsLoading" v-loading="true" style="min-height: 80px" />
      <template v-else-if="metricsData">
        <div class="metrics-grid">
          <div class="metric-tile">
            <span class="metric-label">HTTP requests</span>
            <strong data-testid="metrics-request-total">{{ metricsData.requestTotal }}</strong>
          </div>
          <div class="metric-tile">
            <span class="metric-label">HTTP errors</span>
            <strong data-testid="metrics-error-total">{{ metricsData.errorTotal }}</strong>
          </div>
          <div class="metric-tile">
            <span class="metric-label">Jobs processed</span>
            <strong data-testid="metrics-job-total">{{ metricsData.jobTotal }}</strong>
          </div>
          <div class="metric-tile">
            <span class="metric-label">Uptime seconds</span>
            <strong data-testid="metrics-uptime-seconds">{{ displayMetricNumber(metricsData.uptimeSeconds) }}</strong>
          </div>
        </div>
        <p class="muted section">Parsed from /metrics ({{ metricsData.rawLineCount }} non-empty lines).</p>
      </template>
      <el-empty v-else-if="!metricsError" description="暂无 metrics 数据" />
      <ApiErrorAlert v-if="metricsError" :error="metricsError" />
    </el-card>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { formatApiError } from '../api/client'
import ApiErrorAlert from '../components/ApiErrorAlert.vue'
import { getHealth, getHealthz, getMetricsText, getReadyz, getSystemStatus } from '../api/endpoints'
import type { HealthResponse, HealthzResponse, ReadyzResponse, SystemStatusResponse } from '../api/types'
import { RELEASE_URL } from '../release'

interface MetricsSnapshot {
  requestTotal: number
  errorTotal: number
  jobTotal: number
  uptimeSeconds: number | null
  rawLineCount: number
}

const loading = ref(false)

const healthzData = ref<HealthzResponse | null>(null)
const healthzLoading = ref(false)
const healthzError = ref('')

const readyzData = ref<ReadyzResponse | null>(null)
const readyzLoading = ref(false)
const readyzError = ref('')

const healthData = ref<HealthResponse | null>(null)
const healthLoading = ref(false)
const healthError = ref('')

const statusData = ref<SystemStatusResponse | null>(null)
const statusLoading = ref(false)
const statusError = ref('')

const metricsData = ref<MetricsSnapshot | null>(null)
const metricsLoading = ref(false)
const metricsError = ref('')

const readyzStatusType = computed(() => {
  if (!readyzData.value) return 'info'
  const s = readyzData.value.status
  if (s === 'ok') return 'success'
  if (s === 'degraded') return 'warning'
  return 'danger'
})

const systemReleaseUrl = computed(() => {
  const value = displayValue(statusData.value?.release_url)
  return value === '—' ? RELEASE_URL : value
})

function formatChecks(checks: Record<string, unknown>): string {
  return JSON.stringify(checks, null, 2)
}

function displayValue(value: unknown): string {
  if (typeof value === 'string') {
    const trimmed = value.trim()
    return trimmed.length > 0 ? trimmed : '—'
  }
  if (value === null || value === undefined) return '—'
  return String(value)
}

function displayList(values: string[] | null | undefined): string {
  if (!values || values.length === 0) return '—'
  const visible = values.map((value) => value.trim()).filter(Boolean)
  return visible.length > 0 ? visible.join(', ') : '—'
}

function metricValues(text: string, name: string): number[] {
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.startsWith(name))
    .map((line) => Number(line.match(/\s+([0-9.]+)$/)?.[1] ?? 0))
    .filter((value) => Number.isFinite(value))
}

function sumMetric(text: string, name: string): number {
  return metricValues(text, name).reduce((total, value) => total + value, 0)
}

function parseMetricsSnapshot(text: string): MetricsSnapshot {
  const uptime = metricValues(text, 'project_a_uptime_seconds')[0]
  return {
    requestTotal: sumMetric(text, 'project_a_request_total'),
    errorTotal: sumMetric(text, 'project_a_error_total'),
    jobTotal: sumMetric(text, 'project_a_job_total'),
    uptimeSeconds: Number.isFinite(uptime) ? uptime : null,
    rawLineCount: text.split('\n').filter((line) => line.trim().length > 0).length,
  }
}

function displayMetricNumber(value: number | null): string {
  if (value === null) return '—'
  return Number.isInteger(value) ? String(value) : value.toFixed(2)
}

async function refreshAll() {
  loading.value = true
  healthzError.value = ''
  readyzError.value = ''
  healthError.value = ''
  statusError.value = ''
  metricsError.value = ''

  healthzLoading.value = true
  readyzLoading.value = true
  healthLoading.value = true
  statusLoading.value = true
  metricsLoading.value = true

  await Promise.allSettled([
    (async () => {
      try { healthzData.value = await getHealthz() } catch (e) { healthzError.value = formatApiError(e) }
      finally { healthzLoading.value = false }
    })(),
    (async () => {
      try { readyzData.value = await getReadyz() } catch (e) { readyzError.value = formatApiError(e) }
      finally { readyzLoading.value = false }
    })(),
    (async () => {
      try { healthData.value = await getHealth() } catch (e) { healthError.value = formatApiError(e) }
      finally { healthLoading.value = false }
    })(),
    (async () => {
      try { statusData.value = await getSystemStatus() } catch (e) { statusError.value = formatApiError(e) }
      finally { statusLoading.value = false }
    })(),
    (async () => {
      try { metricsData.value = parseMetricsSnapshot(await getMetricsText()) } catch (e) { metricsError.value = formatApiError(e) }
      finally { metricsLoading.value = false }
    })(),
  ])

  loading.value = false
}

onMounted(refreshAll)

defineExpose({ refresh: refreshAll })
</script>

<style scoped>
.health-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

@media (max-width: 900px) {
  .health-grid {
    grid-template-columns: 1fr;
  }
}

.release-link {
  color: var(--el-color-primary);
  font-weight: 600;
  text-decoration: none;
  word-break: break-all;
}

.release-link:hover {
  text-decoration: underline;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.metric-tile {
  padding: 12px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  background: var(--el-fill-color-lighter);
}

.metric-label {
  display: block;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.metric-tile strong {
  display: block;
  margin-top: 6px;
  color: var(--el-text-color-primary);
  font-size: 24px;
}

@media (max-width: 900px) {
  .metrics-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
