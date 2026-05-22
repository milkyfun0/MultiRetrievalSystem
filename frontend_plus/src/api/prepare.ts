import { http } from './client'
import type {
  TaskStatusResponseDTO,
  TerminateTaskRequestDTO,
  TerminateTaskResponseDTO,
  VectorizeRequestDTO,
  VectorizeResponseDTO,
} from '@/types'

export function postVectorize(data: VectorizeRequestDTO) {
  return http.post<VectorizeResponseDTO>('/api/v1/vectorize', data)
}

export function getTaskStatus(taskId: string) {
  return http.get<TaskStatusResponseDTO>(`/api/v1/tasks/${taskId}`)
}

export function terminateTask(taskId: string, data: TerminateTaskRequestDTO) {
  return http.post<TerminateTaskResponseDTO>(`/api/v1/tasks/${taskId}/terminate`, data)
}
