<template>
  <section class="grid-2">
    <el-card>
      <template #header>启动工单</template>
      <el-input v-model="ticketQuestion" type="textarea" :rows="4" />
      <el-input v-model="idempotencyKey" class="section" placeholder="幂等 key" />
      <el-button type="primary" data-testid="ticket-start-button" :loading="createLoading" @click="confirmCreateTicket">启动工单</el-button>
      <div v-if="ticketError" class="section">
        <ApiErrorAlert :error="ticketError" />
      </div>
      <pre v-if="ticketResult" class="mono section">{{ ticketResult }}</pre>
    </el-card>

    <el-card>
      <template #header>人工确认 / 关闭</template>
      <el-select v-model="selectedTicketId" class="section" placeholder="选择工单" style="width: 100%">
        <el-option
          v-for="ticket in tickets"
          :key="ticket.ticket_id"
          :label="`${ticket.ticket_id} / ${ticket.status}`"
          :value="ticket.ticket_id"
        />
      </el-select>
      <div class="toolbar section">
        <el-input v-model="reviewer" placeholder="确认人" style="width: 140px" />
        <el-input v-model="decision" placeholder="decision" style="width: 140px" />
        <el-button :loading="resumeLoading" @click="confirmResume">人工确认</el-button>
      </div>
      <div class="toolbar">
        <el-input v-model="closedBy" placeholder="关闭人" style="width: 140px" />
        <el-button type="danger" :loading="closeLoading" @click="confirmClose">关闭工单</el-button>
      </div>
      <div v-if="opError" class="section">
        <ApiErrorAlert :error="opError" />
      </div>
    </el-card>

    <el-card class="full-span">
      <template #header>工单列表</template>
      <ApiErrorAlert v-if="listError" :error="listError" />
      <el-table :data="tickets" size="small" stripe v-loading="listLoading">
        <el-table-column prop="ticket_id" label="Ticket ID" width="180" />
        <el-table-column prop="status" label="状态" width="130" />
        <el-table-column prop="risk_level" label="风险" width="120" />
        <el-table-column prop="device_model" label="设备" width="140" />
        <el-table-column prop="question" label="问题" />
      </el-table>
      <el-empty v-if="!listLoading && tickets.length === 0 && !listError" description="暂无工单" />
    </el-card>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessageBox } from '../plugins/element-plus'

import { formatApiError } from '../api/client'
import ApiErrorAlert from '../components/ApiErrorAlert.vue'
import { closeTicket, listTickets, resumeTicket, startTicket } from '../api/endpoints'
import type { TicketRecord } from '../api/types'

const ticketQuestion = ref('UPS-30K 电池有异味并冒烟，现场想重启。')
const idempotencyKey = ref(`web-${Date.now()}`)
const ticketResult = ref('')
const ticketError = ref('')
const createLoading = ref(false)

const tickets = ref<TicketRecord[]>([])
const listLoading = ref(false)
const listError = ref('')
const selectedTicketId = ref('')
const reviewer = ref('王工')
const decision = ref('approved')
const closedBy = ref('李工')
const opError = ref('')
const resumeLoading = ref(false)
const closeLoading = ref(false)

async function refreshTickets() {
  listLoading.value = true
  listError.value = ''
  try {
    tickets.value = await listTickets()
  } catch (e) {
    listError.value = formatApiError(e)
  } finally {
    listLoading.value = false
  }
}

async function confirmCreateTicket() {
  try {
    await ElMessageBox.confirm(
      `确认启动工单？问题：「${ticketQuestion.value.slice(0, 60)}」`,
      '确认启动工单',
      { confirmButtonText: '确认', cancelButtonText: '取消', type: 'info' }
    )
  } catch {
    return
  }
  createLoading.value = true
  ticketError.value = ''
  try {
    const result = await startTicket(ticketQuestion.value, idempotencyKey.value)
    ticketResult.value = JSON.stringify(result, null, 2)
    selectedTicketId.value = result.ticket.ticket_id
    await refreshTickets()
  } catch (e) {
    ticketError.value = formatApiError(e)
  } finally {
    createLoading.value = false
  }
}

async function confirmResume() {
  if (!selectedTicketId.value) return
  try {
    await ElMessageBox.confirm(
      `确认对工单 ${selectedTicketId.value} 执行人工确认（${decision.value}）？`,
      '确认人工审核',
      { confirmButtonText: '确认', cancelButtonText: '取消', type: 'info' }
    )
  } catch {
    return
  }
  resumeLoading.value = true
  opError.value = ''
  try {
    ticketResult.value = JSON.stringify(
      await resumeTicket(selectedTicketId.value, reviewer.value, decision.value),
      null, 2
    )
    await refreshTickets()
  } catch (e) {
    opError.value = formatApiError(e)
  } finally {
    resumeLoading.value = false
  }
}

async function confirmClose() {
  if (!selectedTicketId.value) return
  try {
    await ElMessageBox.confirm(
      `确认关闭工单 ${selectedTicketId.value}？关闭后不可随意撤销。`,
      '确认关闭工单',
      { confirmButtonText: '确认关闭', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return
  }
  closeLoading.value = true
  opError.value = ''
  try {
    const result = await closeTicket(selectedTicketId.value, closedBy.value)
    ticketResult.value = JSON.stringify(result, null, 2)
    await refreshTickets()
  } catch (e) {
    opError.value = formatApiError(e)
  } finally {
    closeLoading.value = false
  }
}

onMounted(refreshTickets)

defineExpose({ refresh: refreshTickets })
</script>
