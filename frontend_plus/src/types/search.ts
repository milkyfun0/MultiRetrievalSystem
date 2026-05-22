export type SearchMode = 'Text2Video' | 'Text2Image' | 'Image2Image'
export type StoreType = 'Folder' | 'DataBase' | 'LongVideo'
export type ViewMode = 'grid' | 'rank_flow'
export type SearchState = 'idle' | 'validating' | 'searching' | 'success' | 'empty' | 'error'
export type SortBy = 'score_desc'

export interface SearchResultItemDTO {
  rank: number
  score: number
  media_type: 'image' | 'video'
  object_key: string
  preview_url?: string
  source_label?: string
  parent_video_name?: string | null
  segment_start_sec?: number | null
  segment_end_sec?: number | null
  frame_timestamp_sec?: number | null
  derive_type?: 'segment' | 'frame' | 'raw' | string | null
}

export interface SearchMetaDTO {
  store_id?: string
  store_status?: 'not_ready' | 'preparing' | 'ready' | 'failed'
  job_id?: string
  model_alias?: string
  latency_ms?: number
  message?: string
}

export interface SearchResponseDTO {
  scene: SearchMode
  store_type: StoreType
  results: SearchResultItemDTO[]
  meta: SearchMetaDTO
}

export interface SearchRequestDTO {
  scene: SearchMode
  store_type: StoreType
  store_id?: string
  topk: number
  need_vectorize?: boolean
  input: {
    text?: string | string[] | null
    image_object_keys?: string[]
  }
  params: {
    model_alias?: string
    auto_prepare?: boolean
    batch_mode?: boolean
    uncertainty_weight?: number
    return_detail_meta?: boolean
  }
}

export interface SearchResultCardVM {
  rank: number
  score: number
  thumbnailUrl: string
  sourceLabel: string
  objectKey: string
  mediaType: 'image' | 'video'
  parentVideoName?: string | null
  segmentStartSec?: number | null
  segmentEndSec?: number | null
  frameTimestampSec?: number | null
  deriveType?: string | null
}

export interface QueryImageUploadResponseDTO {
  object_key: string
  preview_url: string
}

export interface UploadedQueryImageVM {
  name: string
  objectKey: string
  previewUrl: string
}
