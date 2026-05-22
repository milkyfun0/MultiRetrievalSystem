import { http } from './client'
import type { HealthResponseDTO } from '@/types'

export function getHealth() {
  return http.get<HealthResponseDTO>('/api/v1/health')
}
