import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { getTaskStatus, postVectorize, terminateTask } from '@/api'
import type { PreprocessMode, SearchMode, StoreType, VectorizeTaskVM } from '@/types'
import { createTaskVM } from '@/utils/mapper'

function isAbsolutePath(value: string) {
  if (!value) return false
  return /^[a-zA-Z]:\\/.test(value) || value.startsWith('/')
}

function defaultPreprocessMode(scene: SearchMode): PreprocessMode {
  return scene === 'Text2Video' ? 'segment' : 'frame'
}

function defaultInterval(scene: SearchMode): number {
  return scene === 'Text2Video' ? 5 : 3
}

export const usePrepareStore = defineStore('prepare', () => {
  const submitting = ref(false)
  const taskListLoading = ref(false)
  const taskActionLoading = ref(false)
  const errorMessage = ref('')
  const form = ref({
    scene: 'Text2Video' as SearchMode,
    storeType: 'Folder' as StoreType,
    resourcePathOrId: '',
    storeName: '',
    storeDescription: '',
    modelAlias: 'prod',
    batchSize: 64,
    forceRebuild: false,
    preprocessMode: 'segment' as PreprocessMode,
    intervalSec: 5,
  })

  const tasks = ref<VectorizeTaskVM[]>([])
  const taskDetailVisible = ref(false)
  const currentTaskId = ref<string | null>(null)

  function updateDerivedLongVideoConfig() {
    if (form.value.storeType !== 'LongVideo') return
    form.value.preprocessMode = defaultPreprocessMode(form.value.scene)
    form.value.intervalSec = defaultInterval(form.value.scene)
  }

  function updateFormField(field: string, value: string | number | boolean) {
    ;(form.value as Record<string, string | number | boolean>)[field] = value
    if (field === 'scene' || field === 'storeType') {
      updateDerivedLongVideoConfig()
    }
  }

  function buildPayload(mergeOnNameConflict: boolean | null = null) {
    return {
      scene: form.value.scene,
      store_type: form.value.storeType,
      store_name: form.value.storeName.trim(),
      store_description: form.value.storeDescription.trim(),
      merge_on_name_conflict: mergeOnNameConflict,
      keys: [form.value.resourcePathOrId.trim()],
      params: {
        model_alias: form.value.modelAlias,
        batch_size: form.value.batchSize,
        force_rebuild: form.value.forceRebuild,
        preprocess_mode: form.value.storeType === 'LongVideo' ? form.value.preprocessMode : undefined,
        interval_sec: form.value.storeType === 'LongVideo' ? form.value.intervalSec : undefined,
      },
    }
  }

  async function doSubmit(mergeOnNameConflict: boolean | null = null) {
    const payload = buildPayload(mergeOnNameConflict)
    return postVectorize(payload)
  }

  async function submitTask() {
    submitting.value = true
    errorMessage.value = ''

    if (!form.value.storeName.trim()) {
      errorMessage.value = '请先填写检索库名称。'
      submitting.value = false
      return null
    }

    if (!form.value.resourcePathOrId.trim()) {
      errorMessage.value = form.value.storeType === 'DataBase' ? '请填写资源库标识。' : '请填写资源绝对路径。'
      submitting.value = false
      return null
    }

    if (form.value.storeType !== 'DataBase' && !isAbsolutePath(form.value.resourcePathOrId.trim())) {
      errorMessage.value = '当前建库仍需传入 Windows 本机真实绝对路径。若普通浏览器无法自动获取，请手动补全，例如 F:\\Code\\RetrievalSys\\backend\\test_data\\ImageRetrieval。'
      submitting.value = false
      return null
    }

    try {
      const { data } = await doSubmit(null)
      const task = createTaskVM(
        {
          job_id: data.job_id,
          state: data.status || 'running',
          progress: 0,
          message: data.message || '资源准备任务已启动',
          error: null,
          can_terminate: true,
          result: data.store_id ? { store_id: data.store_id } : null,
        },
        {
          scene: form.value.scene,
          storeType: form.value.storeType,
          storeName: form.value.storeName,
          storeDescription: form.value.storeDescription,
        },
      )
      tasks.value.unshift(task)
      currentTaskId.value = task.jobId
      taskDetailVisible.value = true
      return data.job_id
    } catch (error: any) {
      if (error?.response?.status === 409) {
        const serverMessage = error?.response?.data?.message || '检测到同名检索库，是否将本次资源合并到已有库？'
        const shouldMerge = window.confirm(`${serverMessage}\n\n点击“确定”合库，点击“取消”后请重新命名。`)
        if (shouldMerge) {
          try {
            const { data } = await doSubmit(true)
            const task = createTaskVM(
              {
                job_id: data.job_id,
                state: data.status || 'running',
                progress: 0,
                message: data.message || '已按同名合库方式启动任务',
                error: null,
                can_terminate: true,
                result: data.store_id ? { store_id: data.store_id } : null,
              },
              {
                scene: form.value.scene,
                storeType: form.value.storeType,
                storeName: form.value.storeName,
                storeDescription: form.value.storeDescription,
              },
            )
            tasks.value.unshift(task)
            currentTaskId.value = task.jobId
            taskDetailVisible.value = true
            return data.job_id
          } catch (mergeError: any) {
            errorMessage.value = mergeError?.response?.data?.message || mergeError?.message || '合库重试失败，请稍后重试。'
            return null
          }
        }

        errorMessage.value = '检测到同名库，请修改“检索库名称”后重新提交。'
        return null
      }

      const detail = error?.response?.data?.detail
      if (Array.isArray(detail)) {
        errorMessage.value = detail
          .map((item) => {
            const field = Array.isArray(item?.loc) ? item.loc[item.loc.length - 1] : 'field'
            return `${field}: ${item?.msg || 'invalid'}`
          })
          .join('；')
        return null
      }

      errorMessage.value = error?.response?.data?.message || error?.message || '提交任务失败，请稍后重试。'
      return null
    } finally {
      submitting.value = false
    }
  }

  async function refreshTask(jobId: string, options?: { silent?: boolean }) {
    try {
      const { data } = await getTaskStatus(jobId)
      const index = tasks.value.findIndex((item) => item.jobId === jobId)
      const existing = index >= 0 ? tasks.value[index] : null
      const nextVm = createTaskVM(
        data,
        {
          scene: existing?.taskMode || form.value.scene,
          storeType: existing?.storeType || form.value.storeType,
          storeName: existing?.storeName || form.value.storeName,
          storeDescription: existing?.storeDescription || form.value.storeDescription,
        },
        existing,
      )
      if (index >= 0) {
        tasks.value[index] = { ...existing!, ...nextVm }
      } else {
        tasks.value.unshift(nextVm)
      }
      return nextVm
    } catch (error: any) {
      if (!options?.silent) {
        errorMessage.value = error?.response?.data?.message || error?.message || '刷新任务状态失败。'
      }
      const existing = tasks.value.find((item) => item.jobId === jobId) || null
      return existing
    }
  }

  async function refreshAllTasks(options?: { silent?: boolean }) {
    taskListLoading.value = true
    errorMessage.value = ''
    try {
      await Promise.all(tasks.value.map((task) => refreshTask(task.jobId, options)))
    } finally {
      taskListLoading.value = false
    }
  }

  async function retryTask(jobId: string) {
    const task = tasks.value.find((item) => item.jobId === jobId)
    if (!task) return null
    form.value.scene = task.taskMode
    form.value.storeType = task.storeType
    form.value.storeName = task.storeName || ''
    form.value.storeDescription = task.storeDescription || ''
    updateDerivedLongVideoConfig()
    return submitTask()
  }

  async function terminateRunningTask(jobId: string) {
    taskActionLoading.value = true
    errorMessage.value = ''
    try {
      const { data } = await terminateTask(jobId, { reason: '用户手动终止' })
      const index = tasks.value.findIndex((item) => item.jobId === jobId)
      if (index >= 0) {
        const finishedAt = data.terminated_at || new Date().toISOString()
        tasks.value[index] = {
          ...tasks.value[index],
          status: 'terminated',
          canTerminate: false,
          terminatedAt: data.terminated_at || null,
          terminateReason: '用户手动终止',
          message: data.message || '任务已终止',
          finishedAt,
          finishedAtLabel: new Date(finishedAt).toLocaleTimeString('zh-CN', { hour12: false }),
          timeLabel: `${tasks.value[index].startedAtLabel} - ${new Date(finishedAt).toLocaleTimeString('zh-CN', { hour12: false })}`,
        }
      }
      return true
    } catch (error: any) {
      errorMessage.value = error?.response?.data?.message || error?.message || '终止任务失败。'
      return false
    } finally {
      taskActionLoading.value = false
    }
  }

  function openTaskDetail(jobId: string) {
    currentTaskId.value = jobId
    taskDetailVisible.value = true
  }

  function closeTaskDetail() {
    taskDetailVisible.value = false
  }

  const currentTask = computed(() => tasks.value.find((item) => item.jobId === currentTaskId.value) || null)

  return {
    submitting,
    taskListLoading,
    taskActionLoading,
    errorMessage,
    form,
    tasks,
    taskDetailVisible,
    currentTaskId,
    currentTask,
    updateFormField,
    submitTask,
    refreshTask,
    refreshAllTasks,
    retryTask,
    terminateRunningTask,
    openTaskDetail,
    closeTaskDetail,
  }
})
