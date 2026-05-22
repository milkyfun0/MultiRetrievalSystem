export type StoreStatus = 'not_ready' | 'preparing' | 'ready' | 'failed'

export interface StoreItemDTO {
  store_id: string
  store_name: string
  store_description?: string | null
  scene: 'Text2Video' | 'Text2Image' | 'Image2Image'
  store_type: 'Folder' | 'DataBase' | 'LongVideo'
  status: StoreStatus
  model_alias: string
  updated_at: string
}

export interface StoreDetailDTO extends StoreItemDTO {
  resource_path?: string
  current_index_id?: string | null
  created_at?: string
  file_count?: number
  object_count?: number
  active_object_count?: number
  vector_count?: number
  preprocess_mode?: 'segment' | 'frame' | string | null
  interval_sec?: number | null
}

export interface StoreStatusDTO {
  store_id: string
  store_name?: string
  store_description?: string | null
  status: StoreStatus
  current_index_id?: string | null
  model_alias?: string
  file_count?: number
  object_count?: number
  active_object_count?: number
  vector_count?: number
  preprocess_mode?: 'segment' | 'frame' | string | null
  interval_sec?: number | null
}

export interface StoreListResponseDTO {
  items: StoreItemDTO[]
}

export interface DeleteStoreResponseDTO {
  store_id: string
  status: 'deleted'
  message: string
}
