<template>
  <section class="stack" data-testid="page-jobs">
    <div class="job-summary-grid">
      <el-card shadow="never" data-testid="job-summary-total">
        <div class="summary-label">任务总数</div>
        <div class="summary-value">{{ safeJobs.length }}</div>
      </el-card>
      <el-card shadow="never" data-testid="job-summary-active">
        <div class="summary-label">活跃任务</div>
        <div class="summary-value">{{ activeCount }}</div>
      </el-card>
      <el-card shadow="never" data-testid="job-summary-failed">
        <div class="summary-label">失败任务</div>
        <div class="summary-value danger">{{ failedCount }}</div>
      </el-card>
      <el-card shadow="never" data-testid="job-summary-cancelled">
        <div class="summary-label">已取消</div>
        <div class="summary-value muted-value">{{ cancelledCount }}</div>
      </el-card>
    </div>

    <el-card class="worker-card" data-testid="job-worker-architecture-card">
      <template #header>
        <div class="card-header-row">
          <span>Worker / 队列架构</span>
          <el-tag size="small" type="success">production-ready semantics</el-tag>
        </div>
      </template>

      <div class="worker-grid">
        <div>
          <h4>状态流转</h4>
          <div class="lifecycle-flow" data-testid="job-lifecycle-flow">
            <span v-for="(step, index) in lifecycleSteps" :key="step" class="lifecycle-step">
              {{ step }}
              <span v-if="index < lifecycleSteps.length - 1" class="arrow">→</span>
            </span>
          </div>
          <p class="muted section">{{ workerArchitecture }}</p>
        </div>

        <div data-testid="job-worker-guarantees">
          <h4>生产保证</h4>
          <ul class="compact-list">
            <li v-for="item in workerGuarantees" :key="item">{{ item }}</li>
          </ul>
        </div>

        <div data-testid="job-queue-evolution">
          <h4>队列演进</h4>
          <ul class="compact-list">
            <li v-for="item in queueEvolution" :key="item">{{ item }}</li>
          </ul>
        </div>
      </div>

      <div class="stress-command section" data-testid="job-worker-stress-command">
        <code>{{ workerStressCommand }}</code>
        <el-button data-testid="job-copy-stress-command" size="small" text @click="copyWorkerStressCommand">
          复制压测命令
        </el-button>
      </div>
    </el-card>

    <div class="toolbar">
      <el-button @click="refresh" :loading="loading">刷新列表</el-button>
      <el-select
        v-model="statusFilter"
        data-testid="job-status-filter"
        placeholder="按状态筛选"
        style="width: 180px"
      >
        <el-option label="全部状态" value="ALL" />
        <el-option label="活跃中" value="ACTIVE" />
        <el-option label="PENDING" value="PENDING" />
        <el-option label="RUNNING" value="RUNNING" />
        <el-option label="RETRYING" value="RETRYING" />
        <el-option label="SUCCEEDED" value="SUCCEEDED" />
        <el-option label="FAILED" value="FAILED" />
        <el-option label="CANCELLED" value="CANCELLED" />
      </el-select>
      <el-input
        v-model="searchJobId"
        data-testid="job-search-input"
        placeholder="输入 job_id 查询"
        style="width: 320px"
        clearable
        @keyup.enter="searchJob"
      >
        <template #append>
          <el-button data-testid="job-search-button" @click="searchJob" :loading="searchLoading">查询</el-button>
        </template>
      </el-input>
    </div>

    <ApiErrorAlert v-if="listError" data-testid="jobs-list-error" :error="listError" />

    <ApiErrorAlert v-if="searchError" data-testid="job-search-error" :error="searchError" />

    <el-alert v-if="searchResult && searchResult.status === 'FAILED'" type="error" :closable="false" show-icon>
      <template #title>Job {{ searchResult.job_id }} 失败: {{ truncate(searchResult.error || '未知错误', 300) }}</template>
    </el-alert>

    <el-card v-if="searchResult">
      <template #header>查询结果</template>
      <div class="stack">
        <div class="status-row">
          <el-tag :type="statusType(searchResult.status)" size="small">{{ searchResult.status }}</el-tag>
          <span class="muted">类型: {{ searchResult.job_type }}</span>
          <el-tag v-if="searchResult.cancel_requested" type="warning" size="small">取消已请求</el-tag>
          <el-button
            v-if="canCancelJob(searchResult)"
            data-testid="job-cancel-button"
            size="small"
            type="danger"
            plain
            :loading="cancellingJobId === searchResult.job_id"
            @click="confirmCancel(searchResult)"
          >
            取消任务
          </el-button>
        </div>
        <el-alert v-if="searchResult.error" type="error" :title="truncate(searchResult.error, 300)" closable :show-icon="true" />
        <pre v-if="searchResult.status === 'SUCCEEDED'" class="mono section">{{ formatResult(searchResult) }}</pre>
      </div>
    </el-card>

    <el-card>
      <template #header>任务列表</template>
      <el-table :data="filteredJobs" size="small" stripe v-loading="loading">
        <el-table-column prop="job_id" label="Job ID" width="180" />
        <el-table-column prop="job_type" label="类型" width="160" />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="180">
          <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="结果摘要" min-width="200">
          <template #default="{ row }">
            <span v-if="row.status === 'SUCCEEDED' && row.result">{{ resultSummary(row) }}</span>
            <span v-else-if="row.status === 'FAILED' && row.error" class="error-text">{{ truncate(row.error, 80) }}</span>
            <span v-else-if="row.cancel_requested" class="warning-text">取消已请求</span>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="canCancelJob(row)"
              data-testid="job-cancel-button"
              size="small"
              type="danger"
              plain
              :loading="cancellingJobId === row.job_id"
              @click="confirmCancel(row)"
            >
              取消
            </el-button>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && safeJobs.length === 0 && !listError" description="暂无任务" />
      <el-empty v-else-if="!loading && filteredJobs.length === 0 && !listError" description="当前筛选条件下暂无任务" />
    </el-card>

    <div v-if="runningCount > 0" class="poll-bar">
      <span class="muted">{{ runningCount }} 个任务运行中，每 5 秒自动刷新</span>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'

import { ApiClientError, formatApiError } from '../api/client'
import ApiErrorAlert from '../components/ApiErrorAlert.vue'
import { cancelJob, getJob, listJobs } from '../api/endpoints'
import type { JobRecord } from '../api/types'
import { ElMessage, ElMessageBox } from '../plugins/element-plus'

const jobs = ref<JobRecord[]>([])
const loading = ref(false)
const listError = ref('')
const statusFilter = ref('ALL')
const searchJobId = ref('')
const searchLoading = ref(false)
const searchResult = ref<JobRecord | null>(null)
const searchError = ref('')
const cancellingJobId = ref('')
let pollTimer: ReturnType<typeof setInterval> | null = null

const activeStatuses = new Set(['PENDING', 'RUNNING', 'RETRYING'])
const lifecycleSteps = ['PENDING', 'RUNNING', 'SUCCEEDED / FAILED / CANCELLED']
const workerArchitecture = 'JobService 将入库与评测从同步请求中解耦；worker 通过 claim_next_job 获取任务，用 heartbeat 证明长任务仍然存活，并把结果、错误摘要、审计事件和 metrics 写回。'
const workerGuarantees = [
  'claim_next_job 保证同一时刻只有一个 worker 拥有 RUNNING job',
  'heartbeat 防止合法长任务被 timeout 误回收',
  'cancel_requested 由 worker 安全收口到 CANCELLED',
  'FAILED error 只保留安全摘要，不泄露 traceback 或绝对路径',
]
const queueEvolution = [
  '单机 demo：内置 JobService + SQLite，启动成本低',
  '生产增强：PostgreSQL 共享 job 状态，Redis 共享限流',
  '规模化下一步：外部队列 Celery / RQ / Redis Queue',
]
const workerStressCommand = 'python scripts/postgres_worker_stress.py --jobs 50 --workers 6'
const safeJobs = computed(() => (Array.isArray(jobs.value) ? jobs.value : []))
const runningCount = computed(() => safeJobs.value.filter((j) => activeStatuses.has(j.status)).length)
const activeCount = runningCount
const failedCount = computed(() => safeJobs.value.filter((j) => j.status === 'FAILED').length)
const cancelledCount = computed(() => safeJobs.value.filter((j) => j.status === 'CANCELLED').length)

const filteredJobs = computed(() => {
  if (statusFilter.value === 'ALL') return safeJobs.value
  if (statusFilter.value === 'ACTIVE') return safeJobs.value.filter((job) => activeStatuses.has(job.status))
  return safeJobs.value.filter((job) => job.status === statusFilter.value)
})

function statusType(status: string): 'success' | 'warning' | 'danger' | 'info' {
  if (status === 'SUCCEEDED') return 'success'
  if (status === 'RUNNING' || status === 'RETRYING') return 'warning'
  if (status === 'FAILED') return 'danger'
  return 'info'
}

function canCancelJob(job: JobRecord): boolean {
  return activeStatuses.has(job.status) && !job.cancel_requested
}

function formatTime(iso: string | null): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('zh-CN')
  } catch {
    return iso
  }
}

function resultSummary(job: JobRecord): string {
  const r = job.result
  if (job.job_type === 'document.ingest') {
    return `文档: ${r.document_count ?? '?'} / 分块: ${r.chunk_count ?? '?'} / 来源: ${r.docs_source ?? '?'}`
  }
  if (job.job_type === 'evaluation.run') {
    const summary = r.summary as Record<string, unknown> | undefined
    return `类型: ${r.evaluation_type ?? '?'} / 用例: ${summary?.case_count ?? '?'}`
  }
  return truncate(JSON.stringify(r), 80)
}

function formatResult(job: JobRecord): string {
  return JSON.stringify(job.result, null, 2)
}

function truncate(s: string, max: number): string {
  return s.length > max ? s.slice(0, max) + '...' : s
}

async function copyWorkerStressCommand() {
  try {
    await navigator.clipboard.writeText(workerStressCommand)
    ElMessage.success('已复制 worker stress 命令')
  } catch {
    ElMessage.warning('当前浏览器不支持自动复制，请手动选择命令')
  }
}

async function refresh() {
  loading.value = true
  listError.value = ''
  try {
    const data = await listJobs(100)
    if (!Array.isArray(data)) {
      jobs.value = []
      listError.value = 'Jobs API 返回格式异常：期望数组'
      return
    }
    jobs.value = data
  } catch (e) {
    listError.value = formatApiError(e)
  } finally {
    loading.value = false
  }
}

function replaceJob(updated: JobRecord) {
  const index = jobs.value.findIndex((job) => job.job_id === updated.job_id)
  if (index >= 0) {
    jobs.value.splice(index, 1, updated)
  } else {
    jobs.value.unshift(updated)
  }
  if (searchResult.value?.job_id === updated.job_id) {
    searchResult.value = updated
  }
}

async function confirmCancel(job: JobRecord) {
  try {
    await ElMessageBox.confirm(
      `确认取消任务 ${job.job_id}？RUNNING 任务会先标记取消请求，由 worker 安全收口。`,
      '取消任务',
      {
        type: 'warning',
        confirmButtonText: '确认取消',
        cancelButtonText: '保留任务',
      },
    )
  } catch {
    return
  }

  cancellingJobId.value = job.job_id
  try {
    const updated = await cancelJob(job.job_id, 'Cancelled from operations console')
    replaceJob(updated)
    ElMessage.success(`任务 ${job.job_id} 已提交取消`)
  } catch (e) {
    ElMessage.error(formatApiError(e))
  } finally {
    cancellingJobId.value = ''
  }
}

async function searchJob() {
  if (!searchJobId.value.trim()) return
  searchLoading.value = true
  searchResult.value = null
  searchError.value = ''
  try {
    searchResult.value = await getJob(searchJobId.value.trim())
  } catch (e) {
    if (e instanceof ApiClientError && e.status === 404) {
      searchError.value = `Job ${searchJobId.value.trim()} 不存在 (request_id: ${e.requestId || '-'})`
    } else {
      searchError.value = formatApiError(e)
    }
  } finally {
    searchLoading.value = false
  }
}

function startPoll() {
  if (pollTimer) return
  pollTimer = setInterval(() => {
    if (runningCount.value > 0) {
      refresh()
    }
  }, 5000)
}

onMounted(() => {
  refresh()
  startPoll()
})

onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
})
</script>

<style scoped>
.poll-bar {
  padding: 8px 0;
}

.error-text {
  color: #f56c6c;
  font-size: 13px;
}

.warning-text {
  color: #e6a23c;
  font-size: 13px;
}

.job-summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.summary-label {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.summary-value {
  margin-top: 6px;
  color: var(--el-text-color-primary);
  font-size: 28px;
  font-weight: 700;
}

.summary-value.danger {
  color: var(--el-color-danger);
}

.summary-value.muted-value {
  color: var(--el-text-color-secondary);
}

.worker-card {
  border: 1px solid #d9ecff;
  background: linear-gradient(135deg, #f8fbff 0%, #ffffff 50%, #f8fff5 100%);
}

.card-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.worker-grid {
  display: grid;
  grid-template-columns: 1.2fr 1fr 1fr;
  gap: 16px;
}

.worker-grid h4 {
  margin: 0 0 8px;
}

.lifecycle-flow {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.lifecycle-step {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border: 1px solid #d9ecff;
  border-radius: 999px;
  background: #ecf5ff;
  color: #303133;
  font-size: 12px;
  font-weight: 600;
}

.arrow {
  color: #909399;
}

.compact-list {
  margin: 0;
  padding-left: 18px;
  color: var(--el-text-color-regular);
  line-height: 1.7;
}

.stress-command {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  background: #fff;
}

.stress-command code {
  overflow-wrap: anywhere;
}

@media (max-width: 900px) {
  .job-summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .worker-grid {
    grid-template-columns: 1fr;
  }

  .stress-command {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
