import type { SearchMode, StoreType } from './search'

export type PrepareState = 'idle' | 'submitting' | 'success' | 'error'
export type TaskStatus = 'pending' | 'running' | 'success' | 'failed' | 'terminated'
export type PreprocessMode = 'segment' | 'frame'
export type TaskPhase = 'validating' | 'preprocessing' | 'vectorizing' | 'saving' | string

export interface VectorizeRequestDTO {
  scene: SearchMode
  store_type: StoreType
  store_name: string
  store_description: string
  merge_on_name_conflict: boolean | null
  keys: string[]
  params: {
    model_alias?: string
    batch_size?: number
    force_rebuild?: boolean
    preprocess_mode?: PreprocessMode
    interval_sec?: number
  }
}

export interface VectorizeResponseDTO {
  job_id: string
  status?: TaskStatus
  store_id?: string
  message?: string
}

export interface TaskResultDTO {
  store_id?: string
  store_name?: string
  store_description?: string
  scanned_files?: number
  file_count?: number
  new_files?: number
  new_vectors?: number
  skipped_files?: number
  skipped_vectors?: number
  processed_batches?: number
  total_batches?: number
  failed_batches?: number
  vector_count?: number
  final_index_id?: string
  generated_segments?: number
  generated_frames?: number
}

export interface TaskStatusResponseDTO {
  job_id: string
  state: TaskStatus
  progress: number
  message?: string | null
  error?: string | null
  phase?: TaskPhase | null
  can_terminate?: boolean | null
  terminated_at?: string | null
  terminate_reason?: string | null
  result?: TaskResultDTO | null
}

export interface TerminateTaskRequestDTO {
  reason?: string
}

export interface TerminateTaskResponseDTO {
  job_id: string
  state: 'terminated'
  message?: string
  terminated_at?: string
}

export interface VectorizeTaskVM {
  jobId: string
  taskMode: SearchMode
  storeType: StoreType
  storeName?: string
  storeDescription?: string
  status: TaskStatus
  progress: number
  message?: string | null
  error?: string | null
  phase?: TaskPhase | null
  canTerminate?: boolean
  terminatedAt?: string | null
  terminateReason?: string | null
  result?: TaskResultDTO | null
  startedAt?: string | null
  finishedAt?: string | null
  startedAtLabel: string
  finishedAtLabel: string
  timeLabel: string
}
