<script setup lang="ts">
import { computed } from 'vue'
import { phaseToChinese, preprocessModeToChinese, sceneToChinese, storeStatusToChinese, storeTypeToChinese } from '@/utils/display'
import AppIcon from '@/components/icons/AppIcon.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'

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
  { visible: false, task: null, loading: false },
)

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'refresh', taskId: string): void
  (e: 'retry', taskId: string): void
  (e: 'terminate', taskId: string): void
}>()

const result = computed<TaskResult>(() => props.task?.result ?? {})
const statusLabel = computed(() => storeStatusToChinese(props.task?.status))

function formatValue(value: unknown, empty = '--') {
  if (value === null || value === undefined || value === '') return empty
  return String(value)
}

function handleRefresh() {
  if (props.task?.jobId) emit('refresh', props.task.jobId)
}
function handleRetry() {
  if (props.task?.jobId) emit('retry', props.task.jobId)
}
function handleTerminate() {
  if (props.task?.jobId) emit('terminate', props.task.jobId)
}
</script>

<template>
  <Teleport to="body">
    <div v-if="visible" class="modal-mask" @click.self="emit('close')">
      <div class="modal modal--lg" role="dialog" aria-modal="true">
        <div class="modal__header">
          <div>
            <div class="modal__title">任务详情</div>
            <div class="modal__subtitle">查看向量化任务的执行状态、阶段与统计结果</div>
          </div>
          <button class="modal__close" type="button" aria-label="关闭" @click="emit('close')">
            <AppIcon name="x" :size="18" />
          </button>
        </div>

        <div v-if="task" class="modal__body">
          <!-- 顶部摘要 -->
          <div class="metric-grid" style="grid-template-columns: repeat(4, 1fr);">
            <article class="metric-card">
              <div class="metric-card__icon"><AppIcon name="pulse" :size="20" /></div>
              <div class="metric-card__label">任务状态</div>
              <div class="metric-card__value">
                <StatusBadge :status="task.status" :label="statusLabel" />
              </div>
            </article>
            <article class="metric-card">
              <div class="metric-card__icon is-info"><AppIcon name="layout" :size="20" /></div>
              <div class="metric-card__label">当前阶段</div>
              <div class="metric-card__value" style="font-size: 20px;">{{ phaseToChinese(task.phase) }}</div>
            </article>
            <article class="metric-card">
              <div class="metric-card__icon is-warning"><AppIcon name="bolt" :size="20" /></div>
              <div class="metric-card__label">进度</div>
              <div class="metric-card__value">{{ task.progress ?? 0 }}%</div>
              <div class="metric-card__delta">实时刷新可同步最新状态</div>
            </article>
            <article class="metric-card">
              <div class="metric-card__icon is-success"><AppIcon name="cube" :size="20" /></div>
              <div class="metric-card__label">任务模式</div>
              <div class="metric-card__value" style="font-size: 20px;">{{ sceneToChinese(task.taskMode) }}</div>
            </article>
          </div>

          <!-- 基础信息 -->
          <div class="section-title" style="margin-top: 20px; margin-bottom: 10px;">
            <h2><AppIcon name="info" :size="14" /> 基础信息</h2>
          </div>
          <div class="form-grid">
            <div class="card card--inset" style="padding: 14px 16px;">
              <div class="text-muted text-xs" style="letter-spacing: 1px; text-transform: uppercase;">任务 ID</div>
              <div class="font-mono" style="margin-top: 6px;">{{ formatValue(task.jobId) }}</div>
            </div>
            <div class="card card--inset" style="padding: 14px 16px;">
              <div class="text-muted text-xs" style="letter-spacing: 1px; text-transform: uppercase;">状态说明</div>
              <div style="margin-top: 6px;">{{ formatValue(task.message) }}</div>
            </div>
            <div class="card card--inset" style="padding: 14px 16px;">
              <div class="text-muted text-xs" style="letter-spacing: 1px; text-transform: uppercase;">库类型</div>
              <div style="margin-top: 6px;">{{ storeTypeToChinese(task.storeType) }}</div>
            </div>
            <div class="card card--inset" style="padding: 14px 16px;">
              <div class="text-muted text-xs" style="letter-spacing: 1px; text-transform: uppercase;">是否可终止</div>
              <div style="margin-top: 6px;">{{ task.canTerminate ? '可终止' : '不可终止' }}</div>
            </div>
            <div class="card card--inset" style="padding: 14px 16px;">
              <div class="text-muted text-xs" style="letter-spacing: 1px; text-transform: uppercase;">库 ID</div>
              <div class="font-mono" style="margin-top: 6px;">{{ formatValue(result.store_id) }}</div>
            </div>
            <div class="card card--inset" style="padding: 14px 16px;">
              <div class="text-muted text-xs" style="letter-spacing: 1px; text-transform: uppercase;">库名称</div>
              <div style="margin-top: 6px;">{{ formatValue(result.store_name) }}</div>
            </div>
            <div class="card card--inset field--full" style="padding: 14px 16px;">
              <div class="text-muted text-xs" style="letter-spacing: 1px; text-transform: uppercase;">备注</div>
              <div style="margin-top: 6px;">{{ formatValue(result.store_description, '暂无备注') }}</div>
            </div>
            <div class="card card--inset" style="padding: 14px 16px;">
         <div class="text-muted text-xs" style="letter-spacing: 1px; text-transform: uppercase;">开始时间</div>
              <div style="margin-top: 6px;">{{ formatValue(task.startedAtLabel) }}</div>
            </div>
            <div class="card card--inset" style="padding: 14px 16px;">
              <div class="text-muted text-xs" style="letter-spacing: 1px; text-transform: uppercase;">结束时间</div>
              <div style="margin-top: 6px;">
                {{ formatValue(task.finishedAtLabel, task.status === 'success' || task.status === 'failed' || task.status === 'terminated' ? '--' : '进行中') }}
              </div>
            </div>
            <div class="card card--inset" style="padding: 14px 16px;">
              <div class="text-muted text-xs" style="letter-spacing: 1px; text-transform: uppercase;">终止原因</div>
              <div style="margin-top: 6px;">{{ formatValue(task.terminateReason) }}</div>
            </div>
            <div class="card card--inset" style="padding: 14px 16px;">
              <div class="text-muted text-xs" style="letter-spacing: 1px; text-transform: uppercase;">起止区间</div>
              <div style="margin-top: 6px;">{{ formatValue(task.timeLabel) }}</div>
            </div>
            <div class="card card--inset field--full" style="padding: 14px 16px;">
              <div class="text-muted text-xs" style="letter-spacing: 1px; text-transform: uppercase;">最终索引 ID</div>
              <div class="font-mono" style="margin-top: 6px;">{{ formatValue(result.final_index_id) }}</div>
            </div>
          </div>

          <!-- 文件向量统计 -->
          <div class="section-title" style="margin-top: 20px; margin-bottom: 10px;">
            <h2><AppIcon name="database" :size="14" /> 文件与向量统计</h2>
          </div>
          <div class="metric-grid">
            <article class="metric-card">
              <div class="metric-card__label">扫描文件</div>
              <div class="metric-card__value">{{ formatValue(result.scanned_files, '0') }}</div>
            </article>
            <article class="metric-card">
              <div class="metric-card__label">新增文件</div>
              <div class="metric-card__value">{{ formatValue(result.new_files, '0') }}</div>
            </article>
            <article class="metric-card">
              <div class="metric-card__label">跳过文件</div>
              <div class="metric-card__value">{{ formatValue(result.skipped_files, '0') }}</div>
            </article>
            <article class="metric-card">
              <div class="metric-card__label">有效文件</div>
              <div class="metric-card__value">{{ formatValue(result.file_count, '0') }}</div>
            </article>
            <article class="metric-card">
              <div class="metric-card__icon is-success"><AppIcon name="trending" :size="20" /></div>
              <div class="metric-card__label">新增向量</div>
              <div class="metric-card__value">{{ formatValue(result.new_vectors, '0') }}</div>
            </article>
            <article class="metric-card">
              <div class="metric-card__label">跳过向量</div>
              <div class="metric-card__value">{{ formatValue(result.skipped_vectors, '0') }}</div>
            </article>
            <article class="metric-card">
              <div class="metric-card__icon is-info"><AppIcon name="cube" :size="20" /></div>
              <div class="metric-card__label">向量总数</div>
              <div class="metric-card__value">{{ formatValue(result.vector_count, '0') }}</div>
            </article>
          </div>

          <div
            v-if="typeof result.generated_segments === 'number' || typeof result.generated_frames === 'number'"
            class="section-title"
            style="margin-top: 20px; margin-bottom: 10px;"
          >
            <h2><AppIcon name="film" :size="14" /> LongVideo 预处理</h2>
          </div>
          <div
            v-if="typeof result.generated_segments === 'number' || typeof result.generated_frames === 'number'"
            class="metric-grid"
            style="grid-template-columns: repeat(3, 1fr);"
          >
            <article class="metric-card">
              <div class="metric-card__label">生成切片</div>
              <div class="metric-card__value">{{ formatValue(result.generated_segments, '0') }}</div>
            </article>
            <article class="metric-card">
              <div class="metric-card__label">生成帧数</div>
              <div class="metric-card__value">{{ formatValue(result.generated_frames, '0') }}</div>
            </article>
            <article class="metric-card">
              <div class="metric-card__label">处理方式</div>
              <div class="metric-card__value" style="font-size: 20px;">
                {{ preprocessModeToChinese(task.taskMode === 'Text2Video' && task.storeType === 'LongVideo' ? 'segment' : task.storeType === 'LongVideo' ? 'frame' : null) }}
              </div>
            </article>
          </div>

          <div class="section-title" style="margin-top: 20px; margin-bottom: 10px;">
            <h2><AppIcon name="layers" :size="14" /> 批次执行</h2>
          </div>
          <div class="metric-grid" style="grid-template-columns: repeat(3, 1fr);">
            <article class="metric-card">
              <div class="metric-card__label">已处理批次</div>
              <div class="metric-card__value">{{ formatValue(result.processed_batches, '0') }}</div>
            </article>
            <article class="metric-card">
              <div class="metric-card__label">总批次</div>
              <div class="metric-card__value">{{ formatValue(result.total_batches, '0') }}</div>
            </article>
            <article class="metric-card">
              <div class="metric-card__icon is-warning"><AppIcon name="alert" :size="20" /></div>
              <div class="metric-card__label">失败批次</div>
              <div class="metric-card__value">{{ formatValue(result.failed_batches, '0') }}</div>
            </article>
          </div>

          <div v-if="task.error" class="error-banner" style="margin-top: 20px;">
            <div class="error-banner__icon"><AppIcon name="alert" :size="18" /></div>
            <div class="error-banner__msg">{{ task.error }}</div>
          </div>
        </div>

        <div v-else class="modal__body text-center text-muted" style="padding: 60px 24px;">
          暂无任务详情
        </div>

        <div class="modal__footer">
          <button class="btn btn--secondary" type="button" :disabled="loading" @click="handleRefresh">
            <AppIcon name="refresh" class="btn__icon" />
            刷新
          </button>
          <button
            class="btn btn--danger"
            type="button"
            :disabled="loading || !task || task.status !== 'running' || !task.canTerminate"
            @click="handleTerminate"
          >
            <AppIcon name="stop" class="btn__icon" />
            终止任务
          </button>
          <button
            class="btn btn--primary"
            type="button"
            :disabled="loading || !task || task.status !== 'failed'"
            @click="handleRetry"
          >
            <AppIcon name="refresh" class="btn__icon" />
            重试任务
          </button>
          <button class="btn btn--ghost" type="button" @click="emit('close')">关闭</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>