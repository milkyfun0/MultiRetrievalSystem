<template>
  <section class="card">
    <div class="card-header">
      <div>
        <div class="card-title">
          <span class="card-title__icon"><AppIcon name="plus" :size="16" /></span>
          新建向量化任务
        </div>
        <p class="card-subtitle">支持自定义检索库名称与备注；同名冲突时可选择合库或重命名。</p>
      </div>
    </div>

    <!-- Step 1 -->
    <div class="step-head">
      <span class="step-head__num">01</span>
      <div>
        <div class="step-head__title">基础配置</div>
        <div class="step-head__sub">任务场景、库类型与业务标识</div>
      </div>
    </div>

    <div class="form-grid">
      <label class="field">
        <span class="field__label">任务模式</span>
        <select
          class="control control--select"
          :value="form.scene"
          @change="updateField('scene', ($event.target as HTMLSelectElement).value)"
        >
          <option value="Text2Video">文搜视频</option>
          <option value="Text2Image">文搜图像</option>
          <option value="Image2Image">以图搜图</option>
        </select>
      </label>

      <label class="field">
        <span class="field__label">检索库类型</span>
        <select
          class="control control--select"
          :value="form.storeType"
          @change="updateField('storeType', ($event.target as HTMLSelectElement).value)"
        >
          <option value="Folder">文件夹</option>
          <option value="DataBase">数据库</option>
          <option value="LongVideo">长视频</option>
        </select>
      </label>

      <label class="field">
        <span class="field__label">检索库名称</span>
        <input
          class="control"
          :value="form.storeName"
          placeholder="例如：胸片病理图库、演讲视频库"
          @input="updateField('storeName', ($event.target as HTMLInputElement).value)"
        />
      </label>

      <label class="field">
        <span class="field__label">备注</span>
        <input
          class="control"
          :value="form.storeDescription"
          placeholder="该检索库的用途、来源或版本"
          @input="updateField('storeDescription', ($event.target as HTMLInputElement).value)"
        />
      </label>
    </div>

    <!-- Step 2 -->
    <div class="step-head">
      <span class="step-head__num">02</span>
      <div>
        <div class="step-head__title">资源与索引配置</div>
        <div class="step-head__sub">资源来源、模型与索引策略，减少后续返工</div>
      </div>
    </div>

    <div class="form-grid">
      <div class="field field--full">
        <span class="field__label row row--between">
          资源路径 / 库标识
          <span class="text-muted text-sm" style="text-transform: none; letter-spacing: 0">支持桌面桥接或手动补全</span>
        </span>
        <div class="control-row">
          <input
            class="control"
            :placeholder="resourcePlaceholder"
            :value="form.resourcePathOrId"
            @input="updateField('resourcePathOrId', ($event.target as HTMLInputElement).value)"
          />
          <button
            v-if="showPickerButton"
            type="button"
            class="btn btn--secondary"
            @click="handlePickResource"
          >
            <AppIcon name="folder" class="btn__icon" />
            {{ pickerButtonText }}
          </button>
        </div>

        <input
          ref="folderInputRef"
          type="file"
          class="hidden-input"
          webkitdirectory
          directory
          multiple
          @change="handleLegacyFolderChange"
        />

        <input
          ref="videoFileInputRef"
          type="file"
          class="hidden-input"
          accept="video/*,.mp4,.avi,.mov,.mkv,.flv,.webm,.mpeg,.mpg,.m4v"
          @change="handleVideoFileChange"
        />

        <p class="field__hint">{{ resourceHelperText }}</p>
        <p v-if="selectedResourceSummary" class="field__hint field__hint--success">
          <AppIcon name="check_circle" :size="14" style="vertical-align: -2px;" />
          {{ selectedResourceSummary }}
        </p>
      </div>

      <label class="field">
        <span class="field__label">模型版本</span>
        <select
          class="control control--select"
          :value="form.modelAlias"
          @change="updateField('modelAlias', ($event.target as HTMLSelectElement).value)"
        >
          <option value="prod">prod</option>
        </select>
      </label>

      <label class="field">
        <span class="field__label">批量大小</span>
        <input
          class="control"
          type="number"
          min="1"
          :value="form.batchSize"
          @input="updateField('batchSize', Number(($event.target as HTMLInputElement).value))"
        />
      </label>

      <div v-if="showLongVideoControls" class="field field--full">
        <span class="field__label row row--between">
          {{ intervalLabel }}
          <strong style="color: var(--color-primary); font-size: 14px; letter-spacing: 0;">{{ form.intervalSec }} 秒</strong>
        </span>
        <input
          class="range"
          type="range"
          :min="0"
          :max="longVideoIntervalOptions.length - 1"
          :step="1"
          :style="{ '--val': `${(selectedIntervalIndex / (longVideoIntervalOptions.length - 1)) * 100}%` }"
          :value="selectedIntervalIndex"
          @input="handleIntervalChange(($event.target as HTMLInputElement).value)"
        />
        <div class="row row--between text-muted text-sm" style="margin-top: 6px;">
          <span v-for="value in longVideoIntervalOptions" :key="value">{{ value }}s</span>
        </div>
        <p class="field__hint">
          当前将按 {{ preprocessModeText }}方式预处理长视频，再复用建库链路。
        </p>
      </div>

      <div class="switch-row field--full">
        <div class="switch-row__main">
          <strong>强制重建索引</strong>
          <p>底层资源已变更但库名保持不变时启用，会清理并重建索引。</p>
        </div>
        <label class="switch">
          <input
            type="checkbox"
            :checked="form.forceRebuild"
            @change="updateField('forceRebuild', ($event.target as HTMLInputElement).checked)"
          />
          <span class="switch__track"></span>
          <span class="switch__thumb"></span>
        </label>
      </div>
    </div>

    <div class="row row--end" style="margin-top: 22px;">
      <button
        type="button"
        class="btn btn--primary btn--lg"
        :disabled="submitting"
        @click="$emit('submit')"
      >
        <AppIcon name="bolt" class="btn__icon" />
        {{ submitting ? '提交中…' : '提交向量化任务' }}
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { preprocessModeToChinese } from '@/utils/display'
import AppIcon from '@/components/icons/AppIcon.vue'

const props = withDefaults(
  defineProps<{
    form?: {
      scene: string
      storeType: string
      resourcePathOrId: string
      storeName: string
      storeDescription: string
      modelAlias: string
      batchSize: number
      forceRebuild: boolean
      preprocessMode: 'segment' | 'frame'
      intervalSec: number
    }
    submitting?: boolean
  }>(),
  {
    form: () => ({
      scene: 'Text2Video',
      storeType: 'Folder',
      resourcePathOrId: '',
      storeName: '',
      storeDescription: '',
      modelAlias: 'prod',
      batchSize: 64,
      forceRebuild: false,
      preprocessMode: 'segment' as const,
      intervalSec: 5,
    }),
    submitting: false,
  },
)

const emit = defineEmits<{
  update: [field: string, value: string | number | boolean]
  submit: []
}>()

const folderInputRef = ref<HTMLInputElement | null>(null)
const videoFileInputRef = ref<HTMLInputElement | null>(null)
const selectedResourceSummary = ref('')

const longVideoSegmentIntervals = [1, 3, 5, 10, 30]
const longVideoFrameIntervals = [1, 3, 5, 10, 30]

const showLongVideoControls = computed(() => props.form.storeType === 'LongVideo')
const showPickerButton = computed(() => props.form.storeType !== 'DataBase')
const isLongVideo = computed(() => props.form.storeType === 'LongVideo')

const pickerButtonText = computed(() => (isLongVideo.value ? '选择文件' : '选择文件夹'))
const preprocessModeText = computed(() => preprocessModeToChinese(props.form.preprocessMode))
const intervalLabel = computed(() =>
  props.form.preprocessMode === 'segment' ? '切片间隔（秒）' : '抽帧间隔（秒）',
)

const longVideoIntervalOptions = computed(() =>
  props.form.preprocessMode === 'segment' ? longVideoSegmentIntervals : longVideoFrameIntervals,
)

const selectedIntervalIndex = computed(() => {
  const foundIndex = longVideoIntervalOptions.value.findIndex((v) => v === props.form.intervalSec)
  return foundIndex >= 0 ? foundIndex : 0
})

const resourcePlaceholder = computed(() => {
  if (props.form.storeType === 'DataBase') return '请输入数据库资源标识或库 ID'
  if (props.form.storeType === 'LongVideo') return '请输入单个长视频文件的绝对路径，例如 F:\\videos\\meeting.mp4'
  return '请输入资源绝对路径，例如 F:\\Code\\RetrievalSys\\backend\\test_data\\ImageRetrieval'
})

const resourceHelperText = computed(() => {
  if (props.form.storeType === 'DataBase') return '数据库类型填写资源标识或库 ID。'
  if (props.form.storeType === 'LongVideo')
    return 'LongVideo 只接受单个长视频文件路径。文搜视频会切片，文搜图/以图搜图会抽帧。'
  return '优先通过本地桌面桥接获取绝对路径。若浏览器无法直接返回真实路径，请手动补全。'
})

function updateField(field: string, value: string | number | boolean) {
  emit('update', field, value)
}

function handleIntervalChange(indexValue: string) {
  const nextIndex = Number(indexValue)
  const nextValue = longVideoIntervalOptions.value[nextIndex] ?? longVideoIntervalOptions.value[0]
  updateField('intervalSec', nextValue)
}

async function handlePickResource() {
  try {
    const nativePath = await tryNativePicker()
    if (nativePath) {
      selectedResourceSummary.value = isLongVideo.value
        ? `已选择本机文件：${nativePath}`
        : `已选择本机目录：${nativePath}`
      updateField('resourcePathOrId', nativePath)
      return
    }
    if (isLongVideo.value) {
      videoFileInputRef.value?.click()
      return
    }
    const picker = (window as any).showDirectoryPicker
    if (typeof picker === 'function') {
      const handle = await picker({ mode: 'read' })
      if (handle?.name) {
        selectedResourceSummary.value = `已选择文件夹：${handle.name}。当前浏览器未暴露真实绝对路径，请手动补全。`
      }
      return
    }
    folderInputRef.value?.click()
  } catch (error: any) {
    if (error?.name !== 'AbortError') {
      if (isLongVideo.value) videoFileInputRef.value?.click()
      else folderInputRef.value?.click()
    }
  }
}

async function tryNativePicker() {
  const bridge = (window as any).__MMR_NATIVE__
  if (isLongVideo.value) {
    if (bridge?.pickVideoFilePath) return bridge.pickVideoFilePath()
    if (bridge?.pickFilePath) return bridge.pickFilePath({ filters: ['mp4', 'avi', 'mov', 'mkv', 'flv', 'webm', 'mpeg', 'mpg', 'm4v'] })
    return ''
  }
  if (bridge?.pickFolderPath) return bridge.pickFolderPath()
  if (bridge?.pickDirectoryPath) return bridge.pickDirectoryPath()
  return ''
}

function handleLegacyFolderChange(event: Event) {
  const files = Array.from((event.target as HTMLInputElement).files || [])
  if (!files.length) return
  const first = files[0] as File & { path?: string }
  const rootFolder = first.webkitRelativePath?.split('/')?.[0] || first.name
  let absoluteRoot = ''
  if (typeof first.path === 'string' && first.path) {
    const relative = (first.webkitRelativePath || '').replace(/\//g, '\\')
    if (relative && first.path.toLowerCase().endsWith(relative.toLowerCase())) {
      absoluteRoot = first.path.slice(0, first.path.length - relative.length).replace(/[\\/]$/, '')
    } else {
      absoluteRoot = first.path
    }
  }
  if (absoluteRoot) {
    selectedResourceSummary.value = `已识别本机目录：${absoluteRoot}`
    updateField('resourcePathOrId', absoluteRoot)
  } else {
    selectedResourceSummary.value = `已选择文件夹：${rootFolder}，共 ${files.length} 个文件，请手动补全完整路径。`
  }
}

function handleVideoFileChange(event: Event) {
  const files = Array.from((event.target as HTMLInputElement).files || [])
  if (!files.length) return
  const first = files[0] as File & { path?: string }
  if (typeof first.path === 'string' && first.path) {
    selectedResourceSummary.value = `已识别本机视频文件：${first.path}`
    updateField('resourcePathOrId', first.path)
    return
  }
  selectedResourceSummary.value = `已选择文件：${first.name}，请手动补全完整路径。`
}
</script>