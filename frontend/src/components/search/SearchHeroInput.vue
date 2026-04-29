<template>
  <section class="hero-panel glass-panel" aria-label="检索输入区">
    <template v-if="mode !== 'Image2Image'">
      <textarea
        :value="modelValue"
        class="hero-textarea refined-hero-textarea"
        :placeholder="placeholder"
        :aria-label="mode === 'Text2Video' ? '视频检索输入框' : '图像检索输入框'"
        rows="4"
        @input="$emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)"
      />
      <p class="helper-text" v-if="batchMode">批量模式已开启，可按行输入多条 query。</p>
    </template>

    <template v-else>
      <div class="upload-zone refined-upload-zone">
        <div class="upload-zone__copy">
          <h3>&emsp;上传查询图片</h3>
          <p>
            &emsp;查询图片通过上传到服务器
          </p>
        </div>

        <label class="upload-drop refined-upload-drop">
          <input
            type="file"
            accept="image/*"
            multiple
            class="hidden-input"
            aria-label="选择查询图片"
            @change="handleFileChange"
          />
          <span>{{ uploading ? '上传中...' : '拖拽或点击选择查询图片' }}</span>
        </label>

        <div v-if="uploadedItems.length" class="uploaded-query-list">
          <div v-for="(item, index) in uploadedItems" :key="item.objectKey || `${item.name}-${index}`" class="uploaded-query-item">
            <img :src="item.previewUrl" :alt="item.name || 'query image'" class="preview-thumb" />
            <div class="uploaded-query-meta">
              <strong>&emsp;{{ item.name || 'query image' }}</strong>
              <span class="mono-inline">&emsp;&emsp;{{ item.objectKey }}</span>
            </div>
            <button type="button" class="ghost-button small" @click="$emit('remove-uploaded', index)">移除</button>
          </div>
        </div>

        <div v-if="uploadedItems.length" class="uploaded-query-actions">
          <button type="button" class="ghost-button small" @click="$emit('clear-uploaded')">清空已上传图片</button>
        </div>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SearchMode, UploadedQueryImageVM } from '@/types'

const props = withDefaults(
  defineProps<{
    mode: SearchMode
    modelValue?: string
    uploadedItems?: UploadedQueryImageVM[]
    batchMode?: boolean
    uploading?: boolean
  }>(),
  {
    modelValue: '',
    uploadedItems: () => [],
    batchMode: false,
    uploading: false,
  },
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
  'select-files': [files: FileList | File[]]
  'remove-uploaded': [index: number]
  'clear-uploaded': []
}>()

const placeholders: Record<SearchMode, string> = {
  Text2Video: '输入你想检索的视频内容…\n例如，一个人在室内演讲…\n例如，乐队在小型酒吧表演…',
  Text2Image: '输入你想检索的图像内容…\n例如，肺部下叶阴影…\n例如，梭形细胞病理结构…',
  Image2Image: '',
}

const placeholder = computed(() => placeholders[props.mode])

function handleFileChange(event: Event) {
  const files = (event.target as HTMLInputElement).files
  if (files) {
    emit('select-files', files)
  }
}
</script>
