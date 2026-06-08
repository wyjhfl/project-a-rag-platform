<template>
  <section class="stack">
    <el-card>
      <template #header>
        <div class="card-header-row">
          <span>评测中心（异步 Job）</span>
          <el-tag v-if="auth.hasKey && !auth.canAdmin" type="info" size="small">需 admin 权限</el-tag>
        </div>
      </template>
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
        <el-button type="primary" data-testid="eval-async-button" :loading="asyncLoading" @click="confirmEvaluateAsync">
          异步评测
        </el-button>
      </div>
      <div v-if="evalJobResult" class="result-block section">
        <el-alert type="success" :closable="false" show-icon>
          <template #title>
            Job 已创建: {{ evalJobResult.job.job_id }}（状态: {{ evalJobResult.job.status }}）
          </template>
        </el-alert>
        <p class="muted">请前往「异步任务」页面查看执行状态。</p>
      </div>
      <div v-if="asyncError" class="section">
        <ApiErrorAlert :error="asyncError" />
      </div>
    </el-card>

    <el-card>
      <template #header>
        <div class="card-header-row">
          <span>同步评测（兼容旧接口，可能阻塞）</span>
          <el-tag type="warning" size="small">同步</el-tag>
        </div>
      </template>
      <div class="toolbar">
        <el-select v-model="syncEvalType" style="width: 180px">
          <el-option label="RAGAS" value="ragas" />
          <el-option label="回归" value="regression" />
          <el-option label="对抗" value="adversarial" />
        </el-select>
        <el-input v-model="syncCasesPath" style="width: 420px" />
        <el-select v-model="syncDocsSource" style="width: 240px">
          <el-option label="seed_docs" value="seed_docs" />
          <el-option label="real_manuals_sanitized" value="real_manuals_sanitized" />
          <el-option label="uploaded_docs" value="uploaded_docs" />
        </el-select>
        <el-button :loading="syncLoading" @click="confirmEvaluateSync">
          同步评测
        </el-button>
      </div>
      <div v-if="syncResult" class="section">
        <el-descriptions title="评测结果" :column="2" border size="small">
          <el-descriptions-item v-for="(value, key) in syncResult.summary" :key="String(key)" :label="String(key)">
            {{ value }}
          </el-descriptions-item>
        </el-descriptions>
      </div>
      <div v-if="syncError" class="section">
        <ApiErrorAlert :error="syncError" />
      </div>
    </el-card>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessageBox } from '../plugins/element-plus'

import { formatApiError } from '../api/client'
import ApiErrorAlert from '../components/ApiErrorAlert.vue'
import { createEvaluationJob, runEvaluation } from '../api/endpoints'
import type { EvaluationRunResponse, JobCreateResponse } from '../api/types'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()

const evaluationType = ref('regression')
const casesPath = ref('data/eval/real_regression_cases_v1.json')
const docsSource = ref('real_manuals_sanitized')
const asyncLoading = ref(false)
const evalJobResult = ref<JobCreateResponse | null>(null)
const asyncError = ref('')

const syncEvalType = ref('regression')
const syncCasesPath = ref('data/eval/real_regression_cases_v1.json')
const syncDocsSource = ref('real_manuals_sanitized')
const syncLoading = ref(false)
const syncResult = ref<EvaluationRunResponse | null>(null)
const syncError = ref('')

async function confirmEvaluateAsync() {
  try {
    await ElMessageBox.confirm(
      `确认执行异步评测？类型: ${evaluationType.value}，需要 admin 权限。任务将在后台执行。`,
      '确认异步评测',
      { confirmButtonText: '确认', cancelButtonText: '取消', type: 'info' }
    )
  } catch {
    return
  }
  asyncLoading.value = true
  asyncError.value = ''
  evalJobResult.value = null
  try {
    evalJobResult.value = await createEvaluationJob(evaluationType.value, casesPath.value, docsSource.value)
  } catch (e) {
    asyncError.value = formatApiError(e)
  } finally {
    asyncLoading.value = false
  }
}

async function confirmEvaluateSync() {
  try {
    await ElMessageBox.confirm(
      `确认执行同步评测？类型: ${syncEvalType.value}，此操作可能阻塞较长时间，需要 admin 权限。`,
      '确认同步评测',
      { confirmButtonText: '确认', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  syncLoading.value = true
  syncError.value = ''
  syncResult.value = null
  try {
    syncResult.value = await runEvaluation(syncEvalType.value, syncCasesPath.value, syncDocsSource.value)
  } catch (e) {
    syncError.value = formatApiError(e)
  } finally {
    syncLoading.value = false
  }
}
</script>

<style scoped>
.card-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.result-block {
  margin-top: 4px;
}
</style>
