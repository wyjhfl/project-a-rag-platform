import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

const STORAGE_KEY_API_KEY = 'project_a_api_key'
const STORAGE_KEY_ROLE = 'project_a_role'

const ROLE_HIERARCHY: Record<string, number> = { viewer: 0, operator: 1, admin: 2 }

export const useAuthStore = defineStore('auth', () => {
  const apiKey = ref(localStorage.getItem(STORAGE_KEY_API_KEY) || '')
  const role = ref(localStorage.getItem(STORAGE_KEY_ROLE) || 'viewer')

  const hasKey = computed(() => apiKey.value.length > 0)
  const canOperate = computed(() => ROLE_HIERARCHY[role.value] >= ROLE_HIERARCHY.operator)
  const canAdmin = computed(() => ROLE_HIERARCHY[role.value] >= ROLE_HIERARCHY.admin)

  function setKey(key: string, newRole: string) {
    apiKey.value = key
    role.value = newRole
    localStorage.setItem(STORAGE_KEY_API_KEY, key)
    localStorage.setItem(STORAGE_KEY_ROLE, newRole)
  }

  function clearKey() {
    apiKey.value = ''
    role.value = 'viewer'
    localStorage.removeItem(STORAGE_KEY_API_KEY)
    localStorage.removeItem(STORAGE_KEY_ROLE)
  }

  return { apiKey, role, hasKey, canOperate, canAdmin, setKey, clearKey }
})
