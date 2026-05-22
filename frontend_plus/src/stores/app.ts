import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getHealth } from '@/api'
import type { ServiceStatus } from '@/types'

export const useAppStore = defineStore('app', () => {
  const serviceStatus = ref<ServiceStatus>('unknown')

  async function fetchHealth() {
    try {
      const { data } = await getHealth()
      serviceStatus.value = data.status === 'healthy' ? 'healthy' : 'degraded'
    } catch {
      serviceStatus.value = 'error'
    }
  }

  return {
    serviceStatus,
    fetchHealth,
  }
})
