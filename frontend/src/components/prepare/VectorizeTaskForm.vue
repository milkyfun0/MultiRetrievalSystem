<template>
  <section class="glass-panel prepare-form-panel refined-prepare-form-panel">
    <div class="section-title">
      <h2>新建向量化任务</h2>
      <p>建库时支持自定义检索库名称与备注。名称冲突时，前端会根据后端返回结果询问是否合库。</p>
    </div>

    <div class="prepare-group-head">
      <span class="prepare-group-index">01</span>
      <div>
        <strong>基础配置</strong>
        <p>先确定任务场景、库类型与库的业务标识。</p>
      </div>
    </div>

    <div class="prepare-form-grid refined-prepare-form-grid">
      <label class="field-block">
        <span>任务模式</span>
        <select
          class="field-control"
          :value="form.scene"
          @change="updateField('scene', ($event.target as HTMLSelectElement).value)"
        >
          <option value="Text2Video">视频检索</option>
          <option value="Text2Image">图像检索</option>
          <option value="Image2Image">以图搜图</option>
        </select>
      </label>

      <label class="field-block">
        <span>检索库类型</span>
        <select
          class="field-control"
          :value="form.storeType"
          @change="updateField('storeType', ($event.target as HTMLSelectElement).value)"
        >
          <option value="Folder">文件夹</option>
          <option value="DataBase">数据库</option>
          <option value="LongVideo">长视频</option>
        </select>
      </label>

      <label class="field-block">
        <span>检索库名称</span>
        <input
          class="field-control"
          :value="form.storeName"
          @input="updateField('storeName', ($event.target as HTMLInputElement).value)"
          placeholder="例如：胸片病理图库、演讲视频库"
        />
      </label>

      <label class="field-block">
        <span>备注</span>
        <input
          class="field-control"
          :value="form.storeDescription"
          @input="updateField('storeDescription', ($event.target as HTMLInputElement).value)"
          placeholder="用于说明这个检索库的用途、来源或版本"
        />
      </label>
    </div>

    <div class="prepare-group-head prepare-group-head--soft">
      <span class="prepare-group-index">02</span>
      <div>
        <strong>资源与索引配置</strong>
        <p>再配置资源来源、模型、批量与索引策略，减少后续返工。</p>
      </div>
    </div>

    <div class="prepare-form-grid refined-prepare-form-grid prepare-form-grid--dense">
      <div class="field-block span-2">
        <div class="field-title-row">
          <span>资源路径 / 库标识</span>
          <span class="field-caption">支持桌面桥接或手动补全</span>
        </div>
        <div class="resource-picker-row">
          <input
            class="field-control"
            :placeholder="resourcePlaceholder"
            :value="form.resourcePathOrId"
            @input="updateField('resourcePathOrId', ($event.target as HTMLInputElement).value)"
          />
          <button
            v-if="showPickerButton"
            type="button"
            class="secondary-button"
            @click="handlePickResource"
          >
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

        <p class="helper-text compact">{{ resourceHelperText }}</p>
        <p v-if="selectedResourceSummary" class="folder-selected-summary">
          {{ selectedResourceSummary }}
        </p>
      </div>

      <label class="field-block">
        <span>模型版本</span>
        <select
          class="field-control"
          :value="form.modelAlias"
          @change="updateField('modelAlias', ($event.target as HTMLSelectElement).value)"
        >
          <option value="prod">prod</option>
        </select>
      </label>

      <label class="field-block">
        <span>批量大小</span>
        <input
          class="field-control"
          type="number"
          min="1"
          :value="form.batchSize"
          @input="updateField('batchSize', Number(($event.target as HTMLInputElement).value))"
        />
      </label>

      <div
        v-if="showLongVideoControls"
        class="field-block span-2 longvideo-config-block"
      >
        <div class="longvideo-config-header">
          <span>{{ intervalLabel }}</span>
          <strong>{{ form.intervalSec }} 秒</strong>
        </div>

        <input
          class="range-control"
          type="range"
          :min="0"
          :max="longVideoIntervalOptions.length - 1"
          :step="1"
          :value="selectedIntervalIndex"
          @input="handleIntervalChange(($event.target as HTMLInputElement).value)"
        />

        <div class="range-ticks">
          <span v-for="value in longVideoIntervalOptions" :key="value">{{ value }}</span>
        </div>

        <p class="helper-text compact">
          当前将按 {{ preprocessModeText }}方式对长视频进行预处理，再复用原有建库链路。
        </p>
      </div>

      <label class="switch-row span-2 refined-switch-row">
        <div>
          <span>强制重建索引</span>
          <p>适合底层资源内容已变化但库名称仍保持不变的场景。</p>
        </div>
        <input
          type="checkbox"
          :checked="form.forceRebuild"
          @change="updateField('forceRebuild', ($event.target as HTMLInputElement).checked)"
        />
      </label>
    </div>

    <div class="form-footer refined-form-footer">
      <button
        type="button"
        class="primary-button refined-submit-button"
        :disabled="submitting"
        @click="$emit('submit')"
      >
        {{ submitting ? '提交中...' : '提交向量化任务' }}
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import {computed, ref} from 'vue'
import {preprocessModeToChinese} from '@/utils/display'

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

const pickerButtonText = computed(() =>
    isLongVideo.value ? '选择文件' : '选择文件夹',
)

const preprocessModeText = computed(() =>
    preprocessModeToChinese(props.form.preprocessMode),
)

const intervalLabel = computed(() =>
    props.form.preprocessMode === 'segment' ? '切片间隔（秒）' : '抽帧间隔（秒）',
)

const longVideoIntervalOptions = computed(() =>
    props.form.preprocessMode === 'segment'
        ? longVideoSegmentIntervals
        : longVideoFrameIntervals,
)

const selectedIntervalIndex = computed(() => {
  const foundIndex = longVideoIntervalOptions.value.findIndex(
      (value) => value === props.form.intervalSec,
  )
  return foundIndex >= 0 ? foundIndex : 0
})

const resourcePlaceholder = computed(() => {
  if (props.form.storeType === 'DataBase') {
    return '请输入数据库资源标识或库 ID'
  }
  if (props.form.storeType === 'LongVideo') {
    return '请输入单个长视频文件的 Windows 绝对路径，例如 F:\\videos\\meeting.mp4'
  }
  return '请输入 Windows 本机真实绝对路径，例如 F:\\Code\\RetrievalSys\\backend\\test_data\\ImageRetrieval'
})

const resourceHelperText = computed(() => {
  if (props.form.storeType === 'DataBase') {
    return '数据库类型通常填写数据库资源标识或库 ID。'
  }
  if (props.form.storeType === 'LongVideo') {
    return 'LongVideo 只接受单个长视频文件路径。Text2Video 会切片，Text2Image / Image2Image 会抽帧。'
  }
  return '优先尝试通过本地桌面桥接能力获取绝对路径。若当前运行在普通浏览器中，系统文件夹选择器通常无法直接返回真实绝对路径，此时请在输入框中手动补全。'
})

function updateField(field: string, value: string | number | boolean) {
  emit('update', field, value)
}

function handleIntervalChange(indexValue: string) {
  const nextIndex = Number(indexValue)
  const nextValue =
      longVideoIntervalOptions.value[nextIndex] ?? longVideoIntervalOptions.value[0]
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
      const handle = await picker({mode: 'read'})
      if (handle?.name) {
        selectedResourceSummary.value = `已选择文件夹：${handle.name}。当前浏览器未暴露真实绝对路径，请在输入框中补充完整路径。`
      }
      return
    }

    folderInputRef.value?.click()
  } catch (error: any) {
    if (error?.name !== 'AbortError') {
      if (isLongVideo.value) {
        videoFileInputRef.value?.click()
      } else {
        folderInputRef.value?.click()
      }
    }
  }
}

async function tryNativePicker() {
  const bridge = window.__MMR_NATIVE__
  if (isLongVideo.value) {
    if (bridge?.pickVideoFilePath) return bridge.pickVideoFilePath()
    if (bridge?.pickFilePath) return bridge.pickFilePath({filters: ['mp4', 'avi', 'mov', 'mkv', 'flv', 'webm', 'mpeg', 'mpg', 'm4v']})
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
      absoluteRoot = first.path
          .slice(0, first.path.length - relative.length)
          .replace(/[\\/]$/, '')
    } else {
      absoluteRoot = first.path
    }
  }

  if (absoluteRoot) {
    selectedResourceSummary.value = `已识别本机目录：${absoluteRoot}`
    updateField('resourcePathOrId', absoluteRoot)
  } else {
    selectedResourceSummary.value = `已选择文件夹：${rootFolder}，共识别 ${files.length} 个文件。当前浏览器未提供真实绝对路径，请手动补全。`
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

  selectedResourceSummary.value = `已选择文件：${first.name}。当前浏览器未提供真实绝对路径，请在输入框中手动补全完整视频路径。`
}
</script>

<style scoped>
.prepare-group-head {
  display: flex;
  align-items: center;
  gap: 14px;
  margin: 18px 0 14px;
  padding: 12px 14px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(247, 250, 255, 0.96), rgba(241, 246, 254, 0.88));
  border: 1px solid rgba(225, 233, 243, 0.96);
}

.prepare-group-head--soft {
  margin-top: 22px;
}

.prepare-group-index {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  background: linear-gradient(180deg, rgba(79, 120, 255, 0.16), rgba(79, 120, 255, 0.08));
  color: #3158d7;
  font-size: 12px;
  font-weight: 800;
}

.prepare-group-head strong {
  display: block;
  color: #173257;
  font-size: 14px;
}

.prepare-group-head p {
  margin: 4px 0 0;
  color: #73849b;
  font-size: 12px;
}

.prepare-form-grid--dense {
  margin-top: 2px;
}

.field-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 6px;
}

.field-caption {
  color: #8092a8;
  font-size: 12px;
}

.longvideo-config-block {
  padding: 14px 16px;
  border-radius: 18px;
  background: linear-gradient(180deg, #f8fbff 0%, #f3f8ff 100%);
  border: 1px solid #e6eef8;
}

.longvideo-config-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  color: #1f3b64;
  font-weight: 700;
}

.range-control {
  width: 100%;
}

.range-ticks {
  display: flex;
  justify-content: space-between;
  margin-top: 6px;
  color: #7b8aa0;
  font-size: 12px;
}

.switch-row {
  align-items: center;
}

.switch-row p {
  margin: 4px 0 0;
  color: #7c8ea4;
  font-size: 12px;
}

.hidden-input {
  display: none;
}
</style>
