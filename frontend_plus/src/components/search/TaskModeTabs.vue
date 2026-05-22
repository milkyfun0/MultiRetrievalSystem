<template>
  <div class="tabs">
    <button
      v-for="item in modes"
      :key="item.value"
      type="button"
      class="tab"
      :class="{ 'is-active': item.value === modelValue }"
      @click="$emit('update:modelValue', item.value)"
    >
      <AppIcon :name="item.icon" class="tab__icon" />
      {{ item.label }}
    </button>
  </div>
</template>

<script setup lang="ts">
import type { SearchMode } from '@/types'
import AppIcon from '@/components/icons/AppIcon.vue'

defineProps<{ modelValue: SearchMode }>()
defineEmits<{ 'update:modelValue': [value: SearchMode] }>()

const modes: { value: SearchMode; label: string; icon: string }[] = [
  { value: 'Text2Video', label: '文搜视频', icon: 'film' },
  { value: 'Text2Image', label: '文搜图像', icon: 'image' },
  { value: 'Image2Image', label: '以图搜图', icon: 'layers' },
]
</script>