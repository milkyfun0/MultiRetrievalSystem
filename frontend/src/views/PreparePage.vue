<template>
  <AppLayout>
    <div class="page-stack page-stack--wide">
      <section class="page-banner glass-panel page-banner--prepare">
        <div>
          <div class="page-banner__eyebrow">资源准备</div>
          <h1 class="page-banner__title">资源准备控制台</h1>
          <p class="page-banner__desc">
            创建向量化任务并持续跟踪任务状态
          </p>
        </div>
        <div class="page-banner__meta page-banner__meta--compact">
          <article class="page-banner__meta-card">
            <span>当前任务数</span>
            <strong>{{ prepareStore.tasks.length }}</strong>
          </article>
          <article class="page-banner__meta-card">
            <span>运行中</span>
            <strong>{{ runningCount }}</strong>
          </article>
        </div>
      </section>

      <section class="dashboard-metric-grid dashboard-metric-grid--top">
        <article class="dashboard-metric-card glass-panel">
          <span>全部任务</span>
          <strong>{{ prepareStore.tasks.length }}</strong>
        </article>
        <article class="dashboard-metric-card glass-panel">
          <span>运行中</span>
          <strong>{{ runningCount }}</strong>
        </article>
        <article class="dashboard-metric-card glass-panel">
          <span>成功</span>
          <strong>{{ successCount }}</strong>
        </article>
        <article class="dashboard-metric-card glass-panel">
          <span>失败 / 终止</span>
          <strong>{{ failedCount }}</strong>
        </article>
      </section>

      <div class="console-layout console-layout--top">
        <div class="console-main">
          <VectorizeTaskForm
            :form="prepareStore.form"
            :submitting="prepareStore.submitting"
            @update="handleUpdate"
            @submit="handleSubmit"
          />

          <ErrorBanner :message="prepareStore.errorMessage" @retry="handleSubmit" />
        </div>

        <div class="console-side">
          <section class="glass-panel console-info-card">
            <div class="section-title slim compact-title">
              <div>
                <h3>使用提示</h3>
              </div>
            </div>
            <ul class="tip-list">
              <li>资源路径 / 库标识 由于浏览器权限限制，需要手动输入绝对路径。</li>
              <li>同名库冲突时，确认时候将数据库进行合并。</li>
              <li>需要对于已经向量化的文件重新向量化，勾选强制重建索引。</li>
              <li>当遇到任务长时间卡顿或失败，请重试任务。</li>
              <li>任务提交后会继续轮询到 成功、失败 或 中止 终态。</li>
              <li>当遇到任务长时间卡顿或失败，请在查看详情中刷新状态或重试任务。</li>
            </ul>
          </section>
        </div>
      </div>

      <section class="full-span-panel">
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
      </section>
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
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import ListPagination from '@/components/common/ListPagination.vue'
import TaskDetailModal from '@/components/prepare/TaskDetailModal.vue'
import TaskTable from '@/components/prepare/TaskTable.vue'
import VectorizeTaskForm from '@/components/prepare/VectorizeTaskForm.vue'
import { usePolling } from '@/composables/usePolling'
import AppLayout from '@/layouts/AppLayout.vue'
import { usePrepareStore } from '@/stores/prepare'

const prepareStore = usePrepareStore()
const { active: pollingActive, start, stop } = usePolling()
const POLL_INTERVAL = 2500

const currentTask = computed(() => prepareStore.currentTask)

const runningCount = computed(() => {
  return prepareStore.tasks.filter((task) => task.status === 'running').length
})

const successCount = computed(() => {
  return prepareStore.tasks.filter((task) => task.status === 'success').length
})

const failedCount = computed(() => {
  return prepareStore.tasks.filter(
    (task) => task.status === 'failed' || task.status === 'terminated',
  ).length
})

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

  if (pollingActive.value && !forceRestart) {
    return
  }

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
