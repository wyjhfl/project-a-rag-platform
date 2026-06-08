<template>
  <section class="stack" data-testid="page-jobs">
    <div class="toolbar">
      <el-button @click="refresh" :loading="loading">刷新列表</el-button>
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

    <el-alert v-if="listError" :title="listError" type="error" show-icon :closable="false" />

    <el-alert v-if="searchError" :title="searchError" type="error" show-icon :closable="false" />

    <el-alert v-if="searchResult && searchResult.status === 'FAILED'" type="error" :closable="false" show-icon>
      <template #title>Job {{ searchResult.job_id }} 失败: {{ truncate(searchResult.error || '未知错误', 300) }}</template>
    </el-alert>

    <el-card v-if="searchResult">
      <template #header>查询结果</template>
      <div class="stack">
        <div class="status-row">
          <el-tag :type="statusType(searchResult.status)" size="small">{{ searchResult.status }}</el-tag>
          <span class="muted">类型: {{ searchResult.job_type }}</span>
        </div>
        <el-alert v-if="searchResult.error" type="error" :title="truncate(searchResult.error, 300)" closable :show-icon="true" />
        <pre v-if="searchResult.status === 'SUCCEEDED'" class="mono section">{{ formatResult(searchResult) }}</pre>
      </div>
    </el-card>

    <el-card>
      <template #header>任务列表</template>
      <el-table :data="jobs" size="small" stripe v-loading="loading">
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
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && jobs.length === 0 && !listError" description="暂无任务" />
    </el-card>

    <div v-if="runningCount > 0" class="poll-bar">
      <span class="muted">{{ runningCount }} 个任务运行中，每 5 秒自动刷新</span>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'

import { ApiClientError, formatApiError } from '../api/client'
import { getJob, listJobs } from '../api/endpoints'
import type { JobRecord } from '../api/types'

const jobs = ref<JobRecord[]>([])
const loading = ref(false)
const listError = ref('')
const searchJobId = ref('')
const searchLoading = ref(false)
const searchResult = ref<JobRecord | null>(null)
const searchError = ref('')
let pollTimer: ReturnType<typeof setInterval> | null = null

const runningCount = computed(() => jobs.value.filter((j) => j.status === 'PENDING' || j.status === 'RUNNING').length)

function statusType(status: string): 'success' | 'warning' | 'danger' | 'info' {
  if (status === 'SUCCEEDED') return 'success'
  if (status === 'RUNNING') return 'warning'
  if (status === 'FAILED') return 'danger'
  return 'info'
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

async function refresh() {
  loading.value = true
  listError.value = ''
  try {
    jobs.value = await listJobs(100)
  } catch (e) {
    listError.value = formatApiError(e)
  } finally {
    loading.value = false
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
</style>
