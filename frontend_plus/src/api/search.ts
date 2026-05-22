import { http } from './client'
import type { QueryImageUploadResponseDTO, SearchRequestDTO, SearchResponseDTO } from '@/types'

export function postSearch(data: SearchRequestDTO) {
  return http.post<SearchResponseDTO>('/api/v1/search', data)
}

export function uploadQueryImage(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return http.post<QueryImageUploadResponseDTO>('/api/v1/uploads/query-image', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
}
