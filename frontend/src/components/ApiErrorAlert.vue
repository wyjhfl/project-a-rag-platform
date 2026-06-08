<template>
  <div class="api-error-alert" :data-testid="rootTestId">
    <span v-if="rootTestId !== 'api-error-alert'" class="sr-only" data-testid="api-error-alert">API error</span>
    <el-alert type="error" show-icon :closable="closable" :title="displayTitle" :description="displayDescription" />
    <div v-if="requestId" class="api-error-meta" data-testid="api-error-request-id">
      <span>Request ID: <code>{{ requestId }}</code></span>
      <el-button
        size="small"
        text
        data-testid="api-error-copy-request-id"
        @click="copyRequestId"
      >
        {{ copied ? 'Copied' : 'Copy' }}
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, useAttrs } from 'vue'

defineOptions({ inheritAttrs: false })

const props = withDefaults(defineProps<{
  error: string
  title?: string
  closable?: boolean
}>(), {
  title: '',
  closable: false,
})

const copied = ref(false)
const attrs = useAttrs()

const separator = ' — '
const rootTestId = computed(() => {
  const value = attrs['data-testid']
  return typeof value === 'string' && value ? value : 'api-error-alert'
})
const parts = computed(() => props.error.split(separator).map((part) => part.trim()).filter(Boolean))
const message = computed(() => parts.value[0] || props.error || 'Request failed')
const requestId = computed(() => {
  const found = parts.value.find((part) => part.toLowerCase().startsWith('request_id:'))
  return found?.replace(/^request_id:\s*/i, '').trim() || ''
})
const displayTitle = computed(() => props.title || message.value)
const displayDescription = computed(() => {
  const details = parts.value.slice(props.title ? 0 : 1).filter((part) => !part.toLowerCase().startsWith('request_id:'))
  return details.join(separator)
})

async function copyRequestId() {
  if (!requestId.value) return
  await navigator.clipboard.writeText(requestId.value)
  copied.value = true
  window.setTimeout(() => { copied.value = false }, 1200)
}
</script>

<style scoped>
.api-error-alert {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.api-error-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-left: 28px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.api-error-meta code {
  color: var(--el-color-danger);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', monospace;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
