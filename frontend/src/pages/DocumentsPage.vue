<template>
  <section class="grid-2">
    <el-card>
      <template #header>
        <div class="card-header-row">
          <span>资料入库（异步 Job）</span>
          <el-tag v-if="auth.hasKey && !auth.canOperate" type="info" size="small">需 operator 权限</el-tag>
        </div>
      </template>
      <div class="toolbar">
        <el-select v-model="docsSource" style="width: 240px">
          <el-option label="seed_docs" value="seed_docs" />
          <el-option label="real_manuals_sanitized" value="real_manuals_sanitized" />
          <el-option label="uploaded_docs" value="uploaded_docs" />
        </el-select>
        <el-button type="primary" data-testid="ingest-async-button" :loading="ingestLoading" @click="confirmIngestAsync">
          异步入库
        </el-button>
      </div>
      <div v-if="ingestJobResult" class="result-block">
        <el-alert type="success" :closable="false" show-icon>
          <template #title>
            Job 已创建: {{ ingestJobResult.job.job_id }}（状态: {{ ingestJobResult.job.status }}）
          </template>
        </el-alert>
        <p class="muted section">请前往「异步任务」页面查看执行状态。</p>
      </div>
      <div v-if="ingestError" class="section">
        <ApiErrorAlert :error="ingestError" />
      </div>
    </el-card>

    <el-card>
      <template #header>
        <div class="card-header-row">
          <span>上传资料</span>
          <el-tag v-if="auth.hasKey && !auth.canOperate" type="info" size="small">需 operator 权限</el-tag>
        </div>
      </template>
      <el-upload :auto-upload="false" :on-change="onFileChange" :limit="1">
        <el-button>选择文件</el-button>
      </el-upload>
      <el-button class="section" type="primary" :disabled="!uploadFile" :loading="uploadLoading" @click="confirmUpload">
        上传到 uploaded_docs
      </el-button>
      <div v-if="uploadResult" class="result-block section">
        <el-alert type="success" :closable="false" show-icon>
          <template #title>上传成功: {{ uploadResult.filename }}</template>
        </el-alert>
      </div>
      <div v-if="uploadError" class="section">
        <ApiErrorAlert :error="uploadError" />
      </div>
    </el-card>

    <el-card class="full-span">
      <template #header>
        <div class="card-header-row">
          <span>同步入库（兼容旧接口，可能阻塞）</span>
          <el-tag type="warning" size="small">同步</el-tag>
        </div>
      </template>
      <div class="toolbar">
        <el-select v-model="syncDocsSource" style="width: 240px">
          <el-option label="seed_docs" value="seed_docs" />
          <el-option label="real_manuals_sanitized" value="real_manuals_sanitized" />
          <el-option label="uploaded_docs" value="uploaded_docs" />
        </el-select>
        <el-button :loading="syncLoading" @click="confirmIngestSync">
          同步入库
        </el-button>
      </div>
      <pre v-if="syncResult" class="mono section">{{ syncResult }}</pre>
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
import { createIngestJob, ingestDocuments, uploadDocument } from '../api/endpoints'
import type { JobCreateResponse, UploadResponse } from '../api/types'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()

const docsSource = ref('real_manuals_sanitized')
const syncDocsSource = ref('real_manuals_sanitized')
const ingestLoading = ref(false)
const ingestJobResult = ref<JobCreateResponse | null>(null)
const ingestError = ref('')

const uploadFile = ref<File | null>(null)
const uploadLoading = ref(false)
const uploadResult = ref<UploadResponse | null>(null)
const uploadError = ref('')

const syncLoading = ref(false)
const syncResult = ref('')
const syncError = ref('')

async function confirmIngestAsync() {
  try {
    await ElMessageBox.confirm(
      `确认对「${docsSource.value}」执行异步入库？任务将在后台执行，可在「异步任务」页面查看状态。`,
      '确认异步入库',
      { confirmButtonText: '确认', cancelButtonText: '取消', type: 'info' }
    )
  } catch {
    return
  }
  ingestLoading.value = true
  ingestError.value = ''
  ingestJobResult.value = null
  try {
    ingestJobResult.value = await createIngestJob(docsSource.value)
  } catch (e) {
    ingestError.value = formatApiError(e)
  } finally {
    ingestLoading.value = false
  }
}

function onFileChange(file: { raw?: File }) {
  uploadFile.value = file.raw || null
}

async function confirmUpload() {
  if (!uploadFile.value) return
  try {
    await ElMessageBox.confirm(
      `确认上传文件「${uploadFile.value.name}」到 uploaded_docs？`,
      '确认上传',
      { confirmButtonText: '确认', cancelButtonText: '取消', type: 'info' }
    )
  } catch {
    return
  }
  uploadLoading.value = true
  uploadError.value = ''
  uploadResult.value = null
  try {
    uploadResult.value = await uploadDocument(uploadFile.value)
  } catch (e) {
    uploadError.value = formatApiError(e)
  } finally {
    uploadLoading.value = false
  }
}

async function confirmIngestSync() {
  try {
    await ElMessageBox.confirm(
      `确认对「${syncDocsSource.value}」执行同步入库？此操作可能阻塞较长时间。`,
      '确认同步入库',
      { confirmButtonText: '确认', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  syncLoading.value = true
  syncError.value = ''
  syncResult.value = ''
  try {
    const result = await ingestDocuments(syncDocsSource.value)
    syncResult.value = JSON.stringify(result, null, 2)
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
  margin-top: 10px;
}
</style>
