<template>
  <section class="search-hero" aria-label="检索输入区">
    <template v-if="mode !== 'Image2Image'">
      <div class="search-hero__bar">
        <AppIcon name="search" class="search-hero__icon" />
        <textarea
          :value="modelValue"
          class="search-hero__textarea"
          :placeholder="placeholder"
          :aria-label="mode === 'Text2Video' ? '视频检索输入框' : '图像检索输入框'"
          rows="3"
          @input="$emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)"
        />
      </div>
      <div class="search-hero__hint">
        <AppIcon name="sparkles" :size="14" />
        <span v-if="batchMode">批量模式已开启 · 每行一条 query，可输入多个检索语句</span>
        <span v-else>支持自然语言描述，建议 8 - 30 字效果最佳</span>
      </div>
    </template>

    <template v-else>
      <div class="upload-zone">
        <label class="upload-drop">
          <input
            type="file"
            accept="image/*"
            multiple
            aria-label="选择查询图片"
            @change="handleFileChange"
          />
          <div class="upload-drop__icon">
            <AppIcon name="upload" :size="20" />
          </div>
          <div class="text-center">
            <div class="upload-drop__title">
              {{ uploading ? '上传中…' : '点击或拖拽上传查询图片' }}
            </div>
            <div class="upload-drop__hint">支持 PNG / JPG / WEBP · 可多选</div>
          </div>
        </label>

        <div v-if="uploadedItems.length" class="upload-list">
          <div
            v-for="(item, index) in uploadedItems"
            :key="item.objectKey || `${item.name}-${index}`"
            class="upload-item"
          >
            <img :src="item.previewUrl" :alt="item.name || 'query'" class="upload-item__img" />
            <div class="upload-item__meta">
              <div class="upload-item__name">{{ item.name || 'query image' }}</div>
              <div class="upload-item__key">{{ item.objectKey }}</div>
            </div>
            <button
              type="button"
              class="upload-item__remove"
              aria-label="移除该图片"
              @click="$emit('remove-uploaded', index)"
            >
              <AppIcon name="x" :size="14" />
            </button>
          </div>
        </div>

        <div v-if="uploadedItems.length" class="row row--end">
          <button type="button" class="btn btn--sm btn--ghost" @click="$emit('clear-uploaded')">
            <AppIcon name="trash" class="btn__icon" />
            清空已上传图片
          </button>
        </div>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SearchMode, UploadedQueryImageVM } from '@/types'
import AppIcon from '@/components/icons/AppIcon.vue'

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
  Text2Video: '请输入想要检索的视频内容，例如：\n· 一个人在户外讲解咖啡冲煮技巧\n· 城市夜景中行驶的汽车',
  Text2Image: '请输入想要检索的图像内容，例如：\n· 肺部下叶阴影病理切片\n· 梭形细胞结构 100x',
  Image2Image: '',
}

const placeholder = computed(() => placeholders[props.mode])

function handleFileChange(event: Event) {
  const files = (event.target as HTMLInputElement).files
  if (files) emit('select-files', files)
}
</script>