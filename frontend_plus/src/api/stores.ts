import { http } from './client'
import type { DeleteStoreResponseDTO, StoreDetailDTO, StoreListResponseDTO, StoreStatusDTO } from '@/types'

export function getStores() {
  return http.get<StoreListResponseDTO>('/api/v1/stores')
}

export function getStoreDetail(storeId: string) {
  return http.get<StoreDetailDTO>(`/api/v1/stores/${storeId}`)
}

export function getStoreStatus(storeId: string) {
  return http.get<StoreStatusDTO>(`/api/v1/stores/${storeId}/status`)
}

export function deleteStore(storeId: string) {
  return http.delete<DeleteStoreResponseDTO>(`/api/v1/stores/${storeId}`)
}
