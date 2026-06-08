<template>
  <section class="stack">
    <div class="toolbar">
      <el-select v-model="limitValue" style="width: 140px">
        <el-option :value="50" label="50 条" />
        <el-option :value="100" label="100 条" />
        <el-option :value="200" label="200 条" />
      </el-select>
      <el-button @click="refresh" :loading="loading">刷新审计日志</el-button>
    </div>

    <ApiErrorAlert v-if="error" :error="error" />

    <el-card>
      <template #header>
        <div class="card-header-row">
          <span>审计事件</span>
          <el-tag v-if="auth.hasKey && !auth.canAdmin" type="info" size="small">需 admin 权限</el-tag>
        </div>
      </template>
      <el-table :data="events" size="small" stripe v-loading="loading">
        <el-table-column prop="event_id" label="Event ID" width="160" />
        <el-table-column prop="action" label="操作" width="160" />
        <el-table-column prop="actor_role" label="角色" width="100" />
        <el-table-column prop="resource_type" label="资源类型" width="120" />
        <el-table-column prop="resource_id" label="资源 ID" width="140">
          <template #default="{ row }">{{ row.resource_id || '—' }}</template>
        </el-table-column>
        <el-table-column prop="summary" label="摘要" min-width="180" />
        <el-table-column prop="request_id" label="Request ID" width="140">
          <template #default="{ row }">{{ row.request_id || '—' }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="180">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="Metadata" width="100" fixed="right">
          <template #default="{ row }">
            <el-button v-if="Object.keys(row.metadata || {}).length > 0" size="small" text @click="showMetadata(row)">查看</el-button>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && events.length === 0 && !error" description="暂无审计事件" />
    </el-card>

    <el-dialog v-model="metadataVisible" title="Metadata" width="600px">
      <pre class="mono">{{ metadataContent }}</pre>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

import { formatApiError } from '../api/client'
import ApiErrorAlert from '../components/ApiErrorAlert.vue'
import { listAuditEvents } from '../api/endpoints'
import type { AuditEventResponse } from '../api/types'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()

const events = ref<AuditEventResponse[]>([])
const loading = ref(false)
const error = ref('')
const limitValue = ref(100)

const metadataVisible = ref(false)
const metadataContent = ref('')

function formatTime(iso: string | null): string {
  if (!iso) return '—'
  try { return new Date(iso).toLocaleString('zh-CN') } catch { return iso }
}

function showMetadata(row: AuditEventResponse) {
  metadataContent.value = JSON.stringify(row.metadata, null, 2)
  metadataVisible.value = true
}

async function refresh() {
  loading.value = true
  error.value = ''
  try {
    events.value = await listAuditEvents(limitValue.value)
  } catch (e) {
    error.value = formatApiError(e)
  } finally {
    loading.value = false
  }
}

watch(limitValue, () => refresh())

onMounted(refresh)
</script>

<style scoped>
.card-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
</style>
