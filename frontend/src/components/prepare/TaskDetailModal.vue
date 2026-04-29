<script setup lang="ts">
import { computed } from 'vue'
import { phaseToChinese, preprocessModeToChinese, sceneToChinese, storeStatusToChinese, storeTypeToChinese } from '@/utils/display'

type TaskState = 'pending' | 'running' | 'success' | 'failed' | 'terminated'

interface TaskResult {
  store_id?: string
  store_name?: string
  store_description?: string
  scanned_files?: number
  new_files?: number
  new_vectors?: number
  skipped_files?: number
  skipped_vectors?: number
  file_count?: number
  vector_count?: number
  failed_batches?: number
  processed_batches?: number
  total_batches?: number
  final_index_id?: string
  generated_segments?: number
  generated_frames?: number
}

interface VectorizeTaskVM {
  jobId: string
  taskMode?: string
  storeType?: string
  status: TaskState
  progress: number
  message?: string | null
  error?: string | null
  phase?: string | null
  canTerminate?: boolean
  terminatedAt?: string | null
  terminateReason?: string | null
  result?: TaskResult | null
  startedAtLabel?: string
  finishedAtLabel?: string
  timeLabel?: string
}

const props = withDefaults(
  defineProps<{
    visible: boolean
    task: VectorizeTaskVM | null
    loading?: boolean
  }>(),
  {
    visible: false,
    task: null,
    loading: false,
  },
)

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'refresh', taskId: string): void
  (e: 'retry', taskId: string): void
  (e: 'terminate', taskId: string): void
}>()

const stateClass = computed(() => {
  if (!props.task) return 'is-pending'
  return `is-${props.task.status}`
})

const stateText = computed(() => storeStatusToChinese(props.task?.status))
const result = computed<TaskResult>(() => props.task?.result ?? {})

function formatValue(value: unknown, empty = '-') {
  if (value === null || value === undefined || value === '') return empty
  return String(value)
}

function handleRefresh() {
  if (!props.task?.jobId) return
  emit('refresh', props.task.jobId)
}

function handleRetry() {
  if (!props.task?.jobId) return
  emit('retry', props.task.jobId)
}

function handleTerminate() {
  if (!props.task?.jobId) return
  emit('terminate', props.task.jobId)
}
</script>

<template>
  <Teleport to="body">
    <div v-if="visible" class="task-detail-overlay" @click.self="emit('close')">
      <div class="task-detail-modal">
        <div class="modal-header">
          <div>
            <div class="modal-title">任务详情</div>
            <div class="modal-subtitle">查看当前向量化任务的执行状态、阶段与统计结果</div>
          </div>
          <button class="icon-close" type="button" @click="emit('close')">×</button>
        </div>

        <div v-if="task" class="modal-body">
          <div class="top-summary">
            <div class="summary-card">
              <div class="summary-label">任务状态</div>
              <div class="summary-value">
                <span class="state-badge" :class="stateClass">{{ stateText }}</span>
              </div>
            </div>
            <div class="summary-card">
              <div class="summary-label">当前阶段</div>
              <div class="summary-value">{{ phaseToChinese(task.phase) }}</div>
            </div>
            <div class="summary-card">
              <div class="summary-label">当前进度</div>
              <div class="summary-value">{{ task.progress ?? 0 }}%</div>
              <div class="summary-helper">详情刷新会立即同步当前状态</div>
            </div>
            <div class="summary-card">
              <div class="summary-label">任务模式</div>
              <div class="summary-value">{{ sceneToChinese(task.taskMode) }}</div>
            </div>
          </div>

          <div class="section">
            <div class="section-title">基础信息</div>
            <div class="info-grid">
              <div class="info-item">
                <div class="info-label">任务 ID</div>
                <div class="info-value mono">{{ formatValue(task.jobId) }}</div>
              </div>
              <div class="info-item">
                <div class="info-label">状态说明</div>
                <div class="info-value">{{ formatValue(task.message) }}</div>
              </div>
              <div class="info-item">
                <div class="info-label">检索库类型</div>
                <div class="info-value">{{ storeTypeToChinese(task.storeType) }}</div>
              </div>
              <div class="info-item">
                <div class="info-label">可否终止</div>
                <div class="info-value">{{ task.canTerminate ? '可终止' : '不可终止' }}</div>
              </div>
              <div class="info-item">
                <div class="info-label">库 ID</div>
                <div class="info-value mono">{{ formatValue(result.store_id) }}</div>
              </div>
              <div class="info-item">
                <div class="info-label">库名称</div>
                <div class="info-value">{{ formatValue(result.store_name) }}</div>
              </div>
              <div class="info-item info-item-span-2">
                <div class="info-label">备注</div>
                <div class="info-value">{{ formatValue(result.store_description, '暂无备注') }}</div>
              </div>
              <div class="info-item">
                <div class="info-label">开始时间</div>
                <div class="info-value">{{ formatValue(task.startedAtLabel) }}</div>
              </div>
              <div class="info-item">
                <div class="info-label">结束时间</div>
                <div class="info-value">{{ formatValue(task.finishedAtLabel, task.status === 'success' || task.status === 'failed' || task.status === 'terminated' ? '--' : '进行中') }}</div>
              </div>
              <div class="info-item">
                <div class="info-label">终止原因</div>
                <div class="info-value">{{ formatValue(task.terminateReason) }}</div>
              </div>
              <div class="info-item">
                <div class="info-label">起止区间</div>
                <div class="info-value">{{ formatValue(task.timeLabel) }}</div>
              </div>
              <div class="info-item info-item-span-2">
                <div class="info-label">最终索引 ID</div>
                <div class="info-value mono">{{ formatValue(result.final_index_id) }}</div>
              </div>
            </div>
          </div>

          <div class="section">
            <div class="section-title">文件与向量统计</div>
            <div class="stats-grid">
              <div class="stat-tile"><div class="stat-label">扫描文件数</div><div class="stat-value">{{ formatValue(result.scanned_files, '0') }}</div></div>
              <div class="stat-tile"><div class="stat-label">新增文件数</div><div class="stat-value">{{ formatValue(result.new_files, '0') }}</div></div>
              <div class="stat-tile"><div class="stat-label">跳过文件数</div><div class="stat-value">{{ formatValue(result.skipped_files, '0') }}</div></div>
              <div class="stat-tile"><div class="stat-label">当前有效文件数</div><div class="stat-value">{{ formatValue(result.file_count, '0') }}</div></div>
              <div class="stat-tile"><div class="stat-label">新增向量数</div><div class="stat-value">{{ formatValue(result.new_vectors, '0') }}</div></div>
              <div class="stat-tile"><div class="stat-label">跳过向量数</div><div class="stat-value">{{ formatValue(result.skipped_vectors, '0') }}</div></div>
              <div class="stat-tile"><div class="stat-label">当前向量总数</div><div class="stat-value">{{ formatValue(result.vector_count, '0') }}</div></div>
            </div>
          </div>

          <div class="section" v-if="typeof result.generated_segments === 'number' || typeof result.generated_frames === 'number'">
            <div class="section-title">LongVideo 预处理统计</div>
            <div class="stats-grid compact">
              <div class="stat-tile"><div class="stat-label">生成切片数</div><div class="stat-value">{{ formatValue(result.generated_segments, '0') }}</div></div>
              <div class="stat-tile"><div class="stat-label">生成帧数</div><div class="stat-value">{{ formatValue(result.generated_frames, '0') }}</div></div>
              <div class="stat-tile"><div class="stat-label">处理方式</div><div class="stat-value text-value">{{ preprocessModeToChinese(task.taskMode === 'Text2Video' && task.storeType === 'LongVideo' ? 'segment' : task.storeType === 'LongVideo' ? 'frame' : null) }}</div></div>
            </div>
          </div>

          <div class="section">
            <div class="section-title">批次执行情况</div>
            <div class="stats-grid compact">
              <div class="stat-tile"><div class="stat-label">已处理批次</div><div class="stat-value">{{ formatValue(result.processed_batches, '0') }}</div></div>
              <div class="stat-tile"><div class="stat-label">总批次数</div><div class="stat-value">{{ formatValue(result.total_batches, '0') }}</div></div>
              <div class="stat-tile"><div class="stat-label">失败批次数</div><div class="stat-value">{{ formatValue(result.failed_batches, '0') }}</div></div>
            </div>
          </div>

          <div v-if="task.error" class="section">
            <div class="section-title">失败原因</div>
            <div class="error-panel">{{ task.error }}</div>
          </div>
        </div>

        <div v-else class="empty-panel">暂无任务详情</div>

        <div class="modal-footer">
          <button class="btn btn-light" type="button" :disabled="loading" @click="handleRefresh">刷新</button>
          <button
            class="btn btn-danger"
            type="button"
            :disabled="loading || !task || task.status !== 'running' || !task.canTerminate"
            @click="handleTerminate"
          >终止任务</button>
          <button class="btn btn-primary" type="button" :disabled="loading || !task || task.status !== 'failed'" @click="handleRetry">重试任务</button>
          <button class="btn btn-light" type="button" @click="emit('close')">关闭</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.task-detail-overlay { position: fixed; inset: 0; z-index: 2000; display: flex; align-items: center; justify-content: center; background: rgba(15, 23, 42, 0.28); backdrop-filter: blur(4px); }
.task-detail-modal { width: min(920px, calc(100vw - 32px)); max-height: calc(100vh - 40px); overflow: auto; border-radius: 24px; background: #ffffff; box-shadow: 0 24px 80px rgba(15, 23, 42, 0.18); border: 1px solid rgba(148, 163, 184, 0.16); }
.modal-header { display: flex; align-items: flex-start; justify-content: space-between; padding: 22px 24px 14px; border-bottom: 1px solid #eef2f7; }
.modal-title { font-size: 24px; font-weight: 800; color: #1e3a5f; line-height: 1.2; }
.modal-subtitle { margin-top: 6px; font-size: 13px; color: #6b7a90; }
.icon-close { width: 36px; height: 36px; border: none; border-radius: 999px; background: #f5f7fb; color: #6b7a90; font-size: 22px; cursor: pointer; }
.modal-body { padding: 20px 24px 8px; }
.top-summary { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-bottom: 18px; }
.summary-card { padding: 16px 18px; border-radius: 18px; background: linear-gradient(180deg, #fbfdff 0%, #f6f9ff 100%); border: 1px solid #e8eef8; }
.summary-label { font-size: 12px; color: #7b8aa0; margin-bottom: 8px; }
.summary-value { font-size: 22px; font-weight: 800; color: #1f3b64; }
.summary-helper { margin-top: 6px; font-size: 12px; color: #7b8aa0; line-height: 1.5; }
.state-badge { display: inline-flex; align-items: center; justify-content: center; min-width: 76px; height: 34px; padding: 0 12px; border-radius: 999px; font-size: 14px; font-weight: 700; }
.is-pending { background: #fff7e8; color: #b7791f; }
.is-running { background: #e8f1ff; color: #2563eb; }
.is-success { background: #e9f9ef; color: #15803d; }
.is-failed { background: #fdecec; color: #dc2626; }
.is-terminated { background: #f0f2f5; color: #475569; }
.section { margin-bottom: 18px; }
.section-title { margin-bottom: 12px; font-size: 15px; font-weight: 800; color: #1f3b64; }
.info-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px 14px; }
.info-item { padding: 14px 16px; border-radius: 16px; border: 1px solid #ebf0f6; background: #fbfcfe; }
.info-item-span-2 { grid-column: span 2; }
.info-label { font-size: 12px; color: #7b8aa0; margin-bottom: 8px; }
.info-value { font-size: 14px; font-weight: 600; color: #243b53; line-height: 1.6; word-break: break-word; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 13px; }
.stats-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.stats-grid.compact { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.stat-tile { padding: 16px; border-radius: 18px; border: 1px solid #e9eff8; background: #ffffff; box-shadow: inset 0 1px 0 rgba(255,255,255,.7); }
.stat-label { font-size: 12px; color: #7b8aa0; margin-bottom: 10px; }
.stat-value { font-size: 28px; line-height: 1; font-weight: 800; color: #1f3b64; }
.stat-value.text-value { font-size: 20px; line-height: 1.2; }
.error-panel { padding: 14px 16px; border-radius: 16px; background: #fff3f3; border: 1px solid #ffd9d9; color: #b42318; font-size: 14px; line-height: 1.7; word-break: break-word; }
.empty-panel { padding: 48px 24px; text-align: center; color: #7b8aa0; }
.modal-footer { display: flex; justify-content: flex-end; gap: 12px; padding: 14px 24px 22px; border-top: 1px solid #eef2f7; }
.btn { height: 42px; padding: 0 18px; border-radius: 14px; border: none; font-size: 14px; font-weight: 700; cursor: pointer; }
.btn-light { background: #f5f7fb; color: #334155; }
.btn-primary { background: linear-gradient(135deg, #4f8cff 0%, #2563eb 100%); color: #ffffff; box-shadow: 0 10px 24px rgba(37,99,235,.22); }
.btn-danger { background: linear-gradient(135deg, #f87171 0%, #dc2626 100%); color: #ffffff; box-shadow: 0 10px 24px rgba(220,38,38,.18); }
.btn:disabled { opacity: .55; cursor: not-allowed; }
@media (max-width: 900px) { .top-summary,.stats-grid,.stats-grid.compact,.info-grid { grid-template-columns: 1fr 1fr; } .info-item-span-2 { grid-column: span 2; } }
@media (max-width: 640px) { .top-summary,.stats-grid,.stats-grid.compact,.info-grid { grid-template-columns: 1fr; } .info-item-span-2 { grid-column: span 1; } .modal-header,.modal-body,.modal-footer { padding-left: 16px; padding-right: 16px; } .modal-footer { flex-wrap: wrap; } .btn { flex: 1 1 auto; } }
</style>
