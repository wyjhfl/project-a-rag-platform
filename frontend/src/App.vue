<template>
    <AppShell v-model:activeTab="activeTab" :loading="globalLoading" @refresh="refreshAll">
    <AcceptancePage v-if="activeTab === 'acceptance'" data-testid="page-acceptance" :overview="acceptanceOverview" />
    <ArchitecturePage v-if="activeTab === 'architecture'" data-testid="page-architecture" />
    <QualityPage v-if="activeTab === 'quality'" data-testid="page-quality" :overview="acceptanceOverview" />
    <AgenticPage v-if="activeTab === 'agentic'" data-testid="page-agentic" />
    <SystemStatusPage v-if="activeTab === 'status'" data-testid="page-status" ref="statusPage" />
    <DocumentsPage v-if="activeTab === 'documents'" data-testid="page-documents" />
    <JobsPage v-if="activeTab === 'jobs'" data-testid="page-jobs" />
    <AuditPage v-if="activeTab === 'audit'" data-testid="page-audit" />
    <ChatPage v-if="activeTab === 'chat'" data-testid="page-chat" />
    <TicketsPage v-if="activeTab === 'tickets'" data-testid="page-tickets" ref="ticketsPage" />
    <EvaluationsPage v-if="activeTab === 'eval'" data-testid="page-eval" />
  </AppShell>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'

import { loadAcceptanceOverview } from './api/endpoints'
import type { AcceptanceOverviewResponse } from './api/types'
import AppShell from './components/AppShell.vue'
import AcceptancePage from './pages/AcceptancePage.vue'
import AgenticPage from './pages/AgenticPage.vue'
import ArchitecturePage from './pages/ArchitecturePage.vue'
import AuditPage from './pages/AuditPage.vue'
import ChatPage from './pages/ChatPage.vue'
import DocumentsPage from './pages/DocumentsPage.vue'
import EvaluationsPage from './pages/EvaluationsPage.vue'
import JobsPage from './pages/JobsPage.vue'
import QualityPage from './pages/QualityPage.vue'
import SystemStatusPage from './pages/SystemStatusPage.vue'
import TicketsPage from './pages/TicketsPage.vue'

const VALID_TABS = ['acceptance', 'architecture', 'quality', 'agentic', 'status', 'documents', 'jobs', 'audit', 'chat', 'tickets', 'eval']
const TAB_STORAGE_KEY = 'project_a_active_tab'

function isValidTab(value: string): boolean {
  return VALID_TABS.includes(value)
}

function tabFromHash(hash: string = window.location.hash): string | null {
  const route = decodeURIComponent(hash.replace(/^#\/?/, '')).split(/[?#]/)[0].trim()
  return isValidTab(route) ? route : null
}

function tabToHash(tab: string): string {
  return `#/${tab}`
}

function loadTab(): string {
  const hashTab = tabFromHash()
  if (hashTab) return hashTab
  if (window.location.hash) return 'acceptance'
  const stored = localStorage.getItem(TAB_STORAGE_KEY) || ''
  return isValidTab(stored) ? stored : 'acceptance'
}

const activeTab = ref(loadTab())
const globalLoading = ref(false)
const acceptanceOverview = ref<AcceptanceOverviewResponse | null>(null)
const statusPage = ref<InstanceType<typeof SystemStatusPage> | null>(null)
const ticketsPage = ref<InstanceType<typeof TicketsPage> | null>(null)

watch(activeTab, (val) => {
  localStorage.setItem(TAB_STORAGE_KEY, val)
  syncHash(val)
})

function syncHash(tab: string, replace = false) {
  const nextHash = tabToHash(tab)
  if (window.location.hash === nextHash) return
  if (replace) {
    window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}${nextHash}`)
    return
  }
  window.location.hash = nextHash
}

function handleHashChange() {
  const hashTab = tabFromHash()
  if (hashTab) {
    if (hashTab !== activeTab.value) activeTab.value = hashTab
    return
  }
  if (window.location.hash) {
    activeTab.value = 'acceptance'
    syncHash(activeTab.value, true)
  }
}

async function refreshAll() {
  globalLoading.value = true
  try {
    const [acceptanceData] = await Promise.allSettled([
      loadAcceptanceOverview(),
    ])
    if (acceptanceData.status === 'fulfilled') {
      acceptanceOverview.value = acceptanceData.value
    }
    statusPage.value?.refresh()
    ticketsPage.value?.refresh()
  } finally {
    globalLoading.value = false
  }
}

onMounted(() => {
  window.addEventListener('hashchange', handleHashChange)
  syncHash(activeTab.value, true)
  refreshAll()
})

onUnmounted(() => {
  window.removeEventListener('hashchange', handleHashChange)
})
</script>
