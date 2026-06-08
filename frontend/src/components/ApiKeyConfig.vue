<template>
  <el-dialog :model-value="visible" title="API Key 配置" width="460px" @update:model-value="$emit('update:visible', $event)">
    <div class="key-form">
      <el-alert
        type="info"
        :closable="false"
        show-icon
        class="section"
      >
        <template #title>
          API Key 保存到浏览器 localStorage，不会发送到第三方。
          如后端 AUTH_ENABLED=false，可不填 Key 直接使用。
          前端选择的「角色」仅作 UI 能力提示，实际权限由后端根据 X-API-Key 判定。
        </template>
      </el-alert>

      <el-form label-position="top">
        <el-form-item label="API Key">
          <el-input
            v-model="inputKey"
            type="password"
            show-password
            data-testid="api-key-input"
            placeholder="输入后端分配的 API Key"
          />
        </el-form-item>

        <el-form-item label="角色">
          <el-radio-group v-model="inputRole" data-testid="api-key-role-group">
            <el-radio value="viewer">viewer（只读）</el-radio>
            <el-radio value="operator">operator（操作）</el-radio>
            <el-radio value="admin">admin（管理）</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>

      <div class="role-hints">
        <div class="role-hint"><strong>viewer</strong>：查看状态、Jobs、问答</div>
        <div class="role-hint"><strong>operator</strong>：上传、入库、工单操作</div>
        <div class="role-hint"><strong>admin</strong>：审计日志、评测运行</div>
      </div>
    </div>

    <template #footer>
      <el-button @click="$emit('update:visible', false)">取消</el-button>
      <el-button type="danger" data-testid="api-key-clear-button" @click="handleClear" :disabled="!auth.hasKey">清除密钥</el-button>
      <el-button type="primary" data-testid="api-key-save-button" @click="handleSave">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

import { useAuthStore } from '../stores/auth'

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{ 'update:visible': [value: boolean] }>()

const auth = useAuthStore()
const inputKey = ref('')
const inputRole = ref('viewer')

watch(
  () => props.visible,
  (val) => {
    if (val) {
      inputKey.value = auth.apiKey
      inputRole.value = auth.role
    }
  }
)

function handleSave() {
  auth.setKey(inputKey.value, inputRole.value)
  emit('update:visible', false)
}

function handleClear() {
  inputKey.value = ''
  inputRole.value = 'viewer'
  auth.clearKey()
  emit('update:visible', false)
}
</script>

<style scoped>
.key-form {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.role-hints {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  border-radius: 10px;
  background: #f8fafc;
  border: 1px solid #e4ebf1;
}

.role-hint {
  font-size: 13px;
  color: #536273;
}
</style>
