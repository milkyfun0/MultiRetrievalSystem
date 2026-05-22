import type {
  SearchMode,
  SearchResultCardVM,
  SearchResultItemDTO,
  StoreType,
  TaskStatus,
  TaskStatusResponseDTO,
  VectorizeTaskVM,
} from '@/types'

function resolvePreviewUrl(item: SearchResultItemDTO) {
  if (item.preview_url && String(item.preview_url).trim()) {
    return item.preview_url
  }

  if (item.object_key && String(item.object_key).trim()) {
    return `/api/v1/media/preview?object_key=${encodeURIComponent(item.object_key)}`
  }

  return ''
}


function formatClockTime(value?: string | null) {
  if (!value) return '--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '--'
  return date.toLocaleTimeString('zh-CN', { hour12: false })
}

function isTerminalState(state: TaskStatus) {
  return state === 'success' || state === 'failed' || state === 'terminated'
}

function resolveFinishedAt(task: TaskStatusResponseDTO, previous?: VectorizeTaskVM | null) {
  if (task.state === 'terminated' && task.terminated_at) return task.terminated_at
  if (previous?.finishedAt) return previous.finishedAt
  if (isTerminalState(task.state)) return new Date().toISOString()
  return null
}

function formatTaskTimeRange(startedAt?: string | null, finishedAt?: string | null, state?: TaskStatus) {
  const startLabel = formatClockTime(startedAt)
  if (!startedAt) return '--'
  if (finishedAt) return `${startLabel} - ${formatClockTime(finishedAt)}`
  if (state === 'pending') return `${startLabel} - 等待中`
  return `${startLabel} - 进行中`
}

export function mapSearchResultToCard(item: SearchResultItemDTO): SearchResultCardVM {
  return {
    rank: item.rank,
    score: item.score,
    thumbnailUrl: resolvePreviewUrl(item),
    sourceLabel: item.source_label || '默认数据源',
    objectKey: item.object_key,
    mediaType: item.media_type,
    parentVideoName: item.parent_video_name ?? null,
    segmentStartSec: item.segment_start_sec ?? null,
    segmentEndSec: item.segment_end_sec ?? null,
    frameTimestampSec: item.frame_timestamp_sec ?? null,
    deriveType: item.derive_type ?? null,
  }
}

export function createTaskVM(
  task: TaskStatusResponseDTO,
  defaults?: { scene?: SearchMode; storeType?: StoreType; storeName?: string; storeDescription?: string },
  previous?: VectorizeTaskVM | null,
): VectorizeTaskVM {
  const startedAt = previous?.startedAt || new Date().toISOString()
  const finishedAt = resolveFinishedAt(task, previous)

  return {
    jobId: task.job_id,
    taskMode: defaults?.scene || previous?.taskMode || 'Text2Video',
    storeType: defaults?.storeType || previous?.storeType || 'Folder',
    storeName: defaults?.storeName || previous?.storeName,
    storeDescription: defaults?.storeDescription || previous?.storeDescription,
    status: task.state,
    progress: task.progress,
    message: task.message,
    error: task.error,
    phase: task.phase ?? null,
    canTerminate: Boolean(task.can_terminate),
    terminatedAt: task.terminated_at ?? previous?.terminatedAt ?? null,
    terminateReason: task.terminate_reason ?? previous?.terminateReason ?? null,
    result: task.result || previous?.result || null,
    startedAt,
    finishedAt,
    startedAtLabel: formatClockTime(startedAt),
    finishedAtLabel: formatClockTime(finishedAt),
    timeLabel: formatTaskTimeRange(startedAt, finishedAt, task.state),
  }
}
