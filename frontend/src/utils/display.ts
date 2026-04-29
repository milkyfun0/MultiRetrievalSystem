import type { SearchMode, StoreType } from '@/types'

export function sceneToChinese(scene?: SearchMode | string | null) {
  switch (scene) {
    case 'Text2Video':
      return '视频检索'
    case 'Text2Image':
      return '图像检索'
    case 'Image2Image':
      return '以图搜图'
    default:
      return scene || '--'
  }
}

export function storeTypeToChinese(storeType?: StoreType | string | null) {
  switch (storeType) {
    case 'Folder':
      return '文件夹'
    case 'DataBase':
      return '数据库'
    case 'LongVideo':
      return '长视频'
    default:
      return storeType || '--'
  }
}

export function storeStatusToChinese(status?: string | null) {
  switch (status) {
    case 'ready':
      return '已就绪'
    case 'preparing':
      return '准备中'
    case 'failed':
      return '失败'
    case 'not_ready':
      return '未准备'
    case 'deleted':
      return '已删除'
    case 'pending':
      return '等待中'
    case 'running':
      return '执行中'
    case 'success':
      return '成功'
    case 'terminated':
      return '已终止'
    default:
      return status || '--'
  }
}

export function phaseToChinese(phase?: string | null) {
  switch (phase) {
    case 'validating':
      return '参数校验'
    case 'preprocessing':
      return '长视频预处理'
    case 'vectorizing':
      return '向量化中'
    case 'saving':
      return '写入索引'
    default:
      return phase || '--'
  }
}

export function preprocessModeToChinese(mode?: string | null) {
  switch (mode) {
    case 'segment':
      return '均匀切片'
    case 'frame':
      return '均匀抽帧'
    default:
      return mode || '--'
  }
}

export function formatLongVideoMeta(item: {
  parentVideoName?: string | null
  segmentStartSec?: number | null
  segmentEndSec?: number | null
  frameTimestampSec?: number | null
  deriveType?: string | null
}) {
  if (item.deriveType === 'segment') {
    if (typeof item.segmentStartSec === 'number' && typeof item.segmentEndSec === 'number') {
      return `时间段 ${item.segmentStartSec}s - ${item.segmentEndSec}s`
    }
    return '长视频切片结果'
  }

  if (item.deriveType === 'frame') {
    if (typeof item.frameTimestampSec === 'number') {
      return `时间戳 ${item.frameTimestampSec}s`
    }
    return '长视频抽帧结果'
  }

  return ''
}
