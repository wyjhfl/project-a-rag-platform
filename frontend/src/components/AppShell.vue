<template>
  <div class="layout-shell">
    <aside class="sidebar">
      <div class="brand-block">
        <div class="eyebrow">Project A</div>
        <div class="brand">企业设备售后诊断与工单闭环 RAG 平台</div>
        <p class="subtitle">
          把真实 LLM 主链、多模态验收、评测结果和 bad case 做成一个可直接演示的前端中心。
        </p>
      </div>

      <div class="release-card" data-testid="release-badge">
        <div>
          <div class="release-label">Production release</div>
          <div class="release-version">{{ RELEASE_VERSION }}</div>
        </div>
        <a
          class="release-link"
          data-testid="release-link"
          :href="RELEASE_URL"
          target="_blank"
          rel="noreferrer"
        >
          GitHub Release
        </a>
      </div>

      <nav class="nav">
        <button
          v-for="item in navItems"
          :key="item.key"
          :data-testid="`nav-${item.key}`"
          :class="['nav-item', { active: activeTab === item.key }]"
          @click="activeTab = item.key"
        >
          <span class="nav-label">{{ item.label }}</span>
          <span class="nav-hint">{{ item.hint }}</span>
        </button>
      </nav>

      <div class="sidebar-footer">
        <div v-if="auth.hasKey" class="key-status">
          <el-tag size="small" type="success">API Key 已配置</el-tag>
          <el-tag size="small">{{ auth.role }}</el-tag>
        </div>
        <div v-else class="key-status">
          <el-tag size="small" type="info">未配置 API Key</el-tag>
        </div>
        <el-button size="small" text data-testid="api-key-config-button" @click="showKeyDialog = true">
          {{ auth.hasKey ? '修改密钥' : '配置密钥' }}
        </el-button>
      </div>
    </aside>

    <main class="main">
      <header class="hero">
        <div>
          <p class="hero-kicker">A-v2.0 运维控制台</p>
          <h1 class="page-title">{{ currentNav?.label }}</h1>
          <p class="hero-text">{{ currentNav?.hint }}</p>
        </div>
        <div class="hero-actions">
          <el-button @click="$emit('refresh')" :loading="loading">刷新状态</el-button>
        </div>
      </header>

      <el-alert
        v-if="!auth.hasKey"
        class="section"
        title="未配置 API Key（demo 模式）。如后端 AUTH_ENABLED=false，可直接使用所有功能；如 AUTH_ENABLED=true，请求会返回 401，需配置 API Key。"
        type="info"
        show-icon
        :closable="false"
      />

      <slot />
    </main>

    <ApiKeyConfig v-model:visible="showKeyDialog" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

import { RELEASE_URL, RELEASE_VERSION } from '../release'
import { useAuthStore } from '../stores/auth'
import ApiKeyConfig from './ApiKeyConfig.vue'

defineProps<{ loading: boolean }>()
defineEmits<{ refresh: [] }>()

const auth = useAuthStore()
const showKeyDialog = ref(false)

const navItems = [
  { key: 'acceptance', label: '验收中心', hint: '展示文本主链、多模态、评测与 bad case 的统一证据面板。' },
  { key: 'status', label: '系统状态', hint: '查看 API、LLM 与向量库当前状态及健康检查。' },
  { key: 'documents', label: '资料管理', hint: '上传资料、切换 docs source 并执行入库。' },
  { key: 'jobs', label: '异步任务', hint: '查看和管理异步入库与评测任务。' },
  { key: 'audit', label: '审计日志', hint: '查看系统操作审计记录（需 admin 权限）。' },
  { key: 'chat', label: '诊断问答', hint: '验证 grounded 回答、引用与安全后处理。' },
  { key: 'tickets', label: '工单闭环', hint: '启动、人工确认并关闭售后工单。' },
  { key: 'eval', label: '评测中心', hint: '快速触发 regression、RAGAS 与 adversarial 入口。' },
]

const activeTab = defineModel<string>('activeTab', { default: 'acceptance' })
const currentNav = computed(() => navItems.find((item) => item.key === activeTab.value))
</script>

<style scoped>
.sidebar-footer {
  margin-top: auto;
  padding: 12px 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.key-status {
  display: flex;
  gap: 6px;
  margin-bottom: 8px;
}

.release-card {
  margin: 14px 8px 16px;
  padding: 12px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(53, 162, 235, 0.18), rgba(89, 96, 255, 0.12));
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.12);
}

.release-label {
  color: rgba(255, 255, 255, 0.68);
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.release-version {
  margin-top: 3px;
  color: #ffffff;
  font-size: 20px;
  font-weight: 700;
}

.release-link {
  display: inline-flex;
  margin-top: 8px;
  color: #9fd7ff;
  font-size: 12px;
  font-weight: 600;
  text-decoration: none;
}

.release-link:hover {
  color: #ffffff;
  text-decoration: underline;
}
</style>
