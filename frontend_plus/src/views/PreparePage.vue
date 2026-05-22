<template>
  <AppLayout>
    <div class="page-stack">
      <!-- Hero -->
      <section class="hero-banner">
        <div class="hero-banner__content">
          <span class="hero-banner__eyebrow">
            <AppIcon name="cpu" :size="12" />
            Vectorization · Console
          </span>
          <h1 class="hero-banner__title">资源准备控制台</h1>
          <p class="hero-banner__desc">
            一键提交向量化任务，实时跟踪从校验、预处理到写入索引的全链路状态。
            支持文件夹、数据库、长视频三类资源，覆盖增量与重建场景。
          </p>
        </div>
        <div class="hero-banner__meta">
          <article class="hero-stat">
            <span class="hero-stat__label">当前任务总数</span>
            <span class="hero-stat__value">{{ prepareStore.tasks.length }}</span>
            <span class="hero-stat__hint">含历史与运行中</span>
          </article>
          <article class="hero-stat">
            <span class="hero-stat__label">运行中</span>
            <span class="hero-stat__value">{{ runningCount }}</span>
            <span class="hero-stat__hint">实时轮询状态</span>
          </article>
        </div>
      </section>

      <!-- Stats -->
      <section class="metric-grid">
        <article class="metric-card">
          <div class="metric-card__icon"><AppIcon name="inbox" :size="20" /></div>
          <div class="metric-card__label">全部任务</div>
          <div class="metric-card__value">{{ prepareStore.tasks.length }}</div>
        </article>
        <article class="metric-card">
          <div class="metric-card__icon is-info"><AppIcon name="pulse" :size="20" /></div>
          <div class="metric-card__label">运行中</div>
          <div class="metric-card__value">{{ runningCount }}</div>
        </article>
        <article class="metric-card">
          <div class="metric-card__icon is-success"><AppIcon name="check_circle" :size="20" /></div>
          <div class="metric-card__label">成功</div>
          <div class="metric-card__value">{{ successCount }}</div>
        </article>
        <article class="metric-card">
          <div class="metric-card__icon is-warning"><AppIcon name="alert" :size="20" /></div>
          <div class="metric-card__label">失败 / 终止</div>
          <div class="metric-card__value">{{ failedCount }}</div>
        </article>
      </section>

      <!-- Main + Side -->
      <div class="split split--main-side">
        <div class="col gap-lg">
          <VectorizeTaskForm
            :form="prepareStore.form"
            :submitting="prepareStore.submitting"
            @update="handleUpdate"
            @submit="handleSubmit"
          />
          <ErrorBanner :message="prepareStore.errorMessage" @retry="handleSubmit" />
        </div>

        <aside class="col gap-lg">
          <section class="tips-card">
            <div class="tips-card__title">
              <AppIcon name="info" :size="16" />
              使用提示
            </div>
            <ul class="tips-list">
              <li>资源路径需要手动输入绝对路径（浏览器权限限制）。</li>
              <li>同名库冲突时，可选择将数据并入已有库或重新命名。</li>
              <li>底层资源已变更但库名不变时，请勾选「强制重建索引」。</li>
              <li>任务提交后会持续轮询到成功 / 失败 / 中止 终态。</li>
              <li>长时间卡顿或失败，可在详情中刷新状态或重试。</li>
            </ul>
          </section>

          <section class="card card--gradient">
            <div class="card-header" style="margin-bottom: 12px;">
              <div>
                <div class="card-title">
                  <span class="card-title__icon"><AppIcon name="shield" :size="16" /></span>
                  系统约定
                </div>
                <p class="card-subtitle">合理使用以获得稳定的检索体验</p>
              </div>
            </div>
            <ul class="tips-list">
              <li>建议在准备阶段一次性提供干净、规范的数据。</li>
              <li>大批量任务请配合 batch_size 控制资源占用。</li>
              <li>长视频任务的间隔越短，索引粒度越精细但耗时越长。</li>
            </ul>
          </section>
        </aside>
      </div>

      <!-- Task table full width -->
      <TaskTable
        :items="visibleTasks"
        :loading="prepareStore.taskListLoading"
        @retry="handleRetry"
        @detail="openDetail"
        @terminate="handleTerminate"
      />

      <ListPagination
        v-if="taskPaginationVisible"
        aria-label="任务列表分页"
        :current-page="taskCurrentPage"
        :total-pages="taskTotalPages"
        :total="prepareStore.tasks.length"
        :start="taskPageStart"
        :end="taskPageEnd"
        :page-size="taskPageSize"
        :page-size-options="taskPageSizeOptions"
        @update:page="goToTaskPage"
        @update:page-size="updateTaskPageSize"
      />
    </div>

    <TaskDetailModal
      :visible="prepareStore.taskDetailVisible"
      :task="currentTask"
      :loading="prepareStore.taskActionLoading"
      @close="prepareStore.closeTaskDetail"
      @retry="handleRetry"
      @refresh="handleRefresh"
      @terminate="handleTerminate"
    />
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import AppLayout from '@/layouts/AppLayout.vue'
import AppIcon from '@/components/icons/AppIcon.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import ListPagination from '@/components/common/ListPagination.vue'
import TaskDetailModal from '@/components/prepare/TaskDetailModal.vue'
import TaskTable from '@/components/prepare/TaskTable.vue'
import VectorizeTaskForm from '@/components/prepare/VectorizeTaskForm.vue'
import { usePolling } from '@/composables/usePolling'
import { usePrepareStore } from '@/stores/prepare'

const prepareStore = usePrepareStore()
const { active: pollingActive, start, stop } = usePolling()
const POLL_INTERVAL = 2500

const currentTask = computed(() => prepareStore.currentTask)

const runningCount = computed(
  () => prepareStore.tasks.filter((task) => task.status === 'running').length,
)
const successCount = computed(
  () => prepareStore.tasks.filter((task) => task.status === 'success').length,
)
const failedCount = computed(
  () => prepareStore.tasks.filter((task) => task.status === 'failed' || task.status === 'terminated').length,
)

const taskCurrentPage = ref(1)
const taskPageSize = ref(10)
const taskPageSizeOptions = [5, 10, 20, 50]

const taskTotalPages = computed(() => Math.max(1, Math.ceil(prepareStore.tasks.length / taskPageSize.value)))
const taskPageStart = computed(() => (taskCurrentPage.value - 1) * taskPageSize.value)
const taskPageEnd = computed(() => Math.min(taskPageStart.value + taskPageSize.value, prepareStore.tasks.length))
const visibleTasks = computed(() => prepareStore.tasks.slice(taskPageStart.value, taskPageEnd.value))
const taskPaginationVisible = computed(() => prepareStore.tasks.length > taskPageSize.value)

const activeTaskIds = computed(() =>
  prepareStore.tasks
    .filter((task) => shouldContinuePolling(task.status))
    .map((task) => task.jobId),
)

async function pollActiveTasks() {
  const ids = [...activeTaskIds.value]
  if (!ids.length) return false
  await Promise.all(ids.map((jobId) => prepareStore.refreshTask(jobId, { silent: true })))
  return prepareStore.tasks.some((task) => shouldContinuePolling(task.status))
}

function ensureActiveTaskPolling(forceRestart = false) {
  if (!activeTaskIds.value.length) {
    stop()
    return
  }
  if (pollingActive.value && !forceRestart) return
  void start(pollActiveTasks, POLL_INTERVAL)
}

function goToTaskPage(page: number) {
  taskCurrentPage.value = Math.min(Math.max(page, 1), taskTotalPages.value)
}

function updateTaskPageSize(size: number) {
  taskPageSize.value = size
  taskCurrentPage.value = 1
}

watch(() => prepareStore.tasks.length, () => {
  taskCurrentPage.value = Math.min(taskCurrentPage.value, taskTotalPages.value)
  if (taskPageStart.value >= prepareStore.tasks.length) taskCurrentPage.value = 1
}, { immediate: true })

watch(activeTaskIds, (ids) => {
  if (!ids.length) {
    stop()
    return
  }
  ensureActiveTaskPolling()
}, { immediate: true })

function shouldContinuePolling(status?: string | null) {
  return status === 'pending' || status === 'running'
}

function handleUpdate(field: string, value: string | number | boolean) {
  prepareStore.updateFormField(field, value)
}

async function handleSubmit() {
  const jobId = await prepareStore.submitTask()
  if (jobId) {
    await prepareStore.refreshTask(jobId, { silent: true })
    ensureActiveTaskPolling(true)
  }
}

function openDetail(jobId: string) {
  prepareStore.openTaskDetail(jobId)
  void prepareStore.refreshTask(jobId, { silent: true })
}

async function handleRefresh(jobId: string) {
  await prepareStore.refreshTask(jobId)
}

async function handleRetry(jobId: string) {
  const newJobId = await prepareStore.retryTask(jobId)
  if (newJobId) {
    await prepareStore.refreshTask(newJobId, { silent: true })
    ensureActiveTaskPolling(true)
  }
}

async function handleTerminate(jobId: string) {
  const ok = window.confirm('确定终止该任务？终止后不可恢复。')
  if (!ok) return
  const terminated = await prepareStore.terminateRunningTask(jobId)
  if (terminated) {
    await prepareStore.refreshTask(jobId, { silent: true })
    ensureActiveTaskPolling(true)
  }
}

function handleVisibilityChange() {
  if (document.visibilityState !== 'visible') return
  if (!activeTaskIds.value.length) return
  void pollActiveTasks()
  ensureActiveTaskPolling(true)
}

onMounted(() => {
  document.addEventListener('visibilitychange', handleVisibilityChange)
  ensureActiveTaskPolling()
})

onBeforeUnmount(() => {
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
</script>