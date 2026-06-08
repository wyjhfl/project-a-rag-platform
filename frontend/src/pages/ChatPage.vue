<template>
  <section class="grid-2">
    <el-card>
      <template #header>单轮问答</template>
      <el-input v-model="question" type="textarea" :rows="4" placeholder="输入设备相关问题" />
      <el-button class="section" type="primary" :loading="chatLoading" @click="handleChat">提问</el-button>
      <div v-if="chatError" class="section">
        <ApiErrorAlert :error="chatError" />
      </div>
      <template v-if="chatResult">
        <div class="section">
          <strong>回答：</strong>
          <p>{{ chatResult.answer }}</p>
        </div>
        <el-alert v-if="chatResult.safety_warning" type="warning" :closable="false" show-icon class="section">
          <template #title>安全警告已触发</template>
        </el-alert>
        <el-alert v-if="chatResult.insufficient" type="info" :closable="false" show-icon class="section">
          <template #title>信息不足，无法给出确定回答</template>
        </el-alert>
        <el-collapse v-if="chatResult.citations.length > 0" class="section">
          <el-collapse-item :title="`引用 (${chatResult.citations.length})`">
            <div v-for="(c, i) in chatResult.citations" :key="i" class="citation">
              <el-tag size="small" type="info">{{ c.source }} #{{ c.chunk_index }}</el-tag>
              <p class="muted">{{ truncate(c.content, 300) }}</p>
            </div>
          </el-collapse-item>
        </el-collapse>
      </template>
    </el-card>

    <el-card>
      <template #header>多轮会话</template>
      <el-input v-model="sessionId" placeholder="Session ID" style="width: 100%" class="section" />
      <el-input v-model="sessionQuestion" type="textarea" :rows="4" placeholder="输入设备相关问题（多轮上下文）" />
      <el-button class="section" type="primary" :loading="sessionLoading" @click="handleSessionChat">提问</el-button>
      <div v-if="sessionError" class="section">
        <ApiErrorAlert :error="sessionError" />
      </div>
      <template v-if="sessionResult">
        <div class="section">
          <p class="muted">解析后问题：{{ sessionResult.resolved_question }}</p>
        </div>
        <div class="section">
          <strong>回答：</strong>
          <p>{{ sessionResult.answer }}</p>
        </div>
        <el-collapse v-if="sessionResult.citations.length > 0" class="section">
          <el-collapse-item :title="`引用 (${sessionResult.citations.length})`">
            <div v-for="(c, i) in sessionResult.citations" :key="i" class="citation">
              <el-tag size="small" type="info">{{ c.source }} #{{ c.chunk_index }}</el-tag>
              <p class="muted">{{ truncate(c.content, 300) }}</p>
            </div>
          </el-collapse-item>
        </el-collapse>
      </template>
    </el-card>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'

import { formatApiError } from '../api/client'
import ApiErrorAlert from '../components/ApiErrorAlert.vue'
import { chat, sessionChat } from '../api/endpoints'
import type { ChatResponse, SessionChatResponse } from '../api/types'

const question = ref('VFD-4500 过流保护如何复位？')
const chatLoading = ref(false)
const chatResult = ref<ChatResponse | null>(null)
const chatError = ref('')

const sessionId = ref(`web-session-${Date.now()}`)
const sessionQuestion = ref('上次提到的设备还有其他报警吗？')
const sessionLoading = ref(false)
const sessionResult = ref<SessionChatResponse | null>(null)
const sessionError = ref('')

function truncate(s: string, max: number): string {
  return s.length > max ? s.slice(0, max) + '...' : s
}

async function handleChat() {
  chatLoading.value = true
  chatError.value = ''
  chatResult.value = null
  try {
    chatResult.value = await chat(question.value)
  } catch (e) {
    chatError.value = formatApiError(e)
  } finally {
    chatLoading.value = false
  }
}

async function handleSessionChat() {
  sessionLoading.value = true
  sessionError.value = ''
  sessionResult.value = null
  try {
    sessionResult.value = await sessionChat(sessionId.value, sessionQuestion.value)
  } catch (e) {
    sessionError.value = formatApiError(e)
  } finally {
    sessionLoading.value = false
  }
}
</script>

<style scoped>
.citation {
  margin-bottom: 8px;
  padding: 8px;
  border-radius: 6px;
  background: #f8fafc;
}
</style>
