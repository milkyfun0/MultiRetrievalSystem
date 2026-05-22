<template>
  <div class="result-toolbar">
    <div>
      <div class="result-toolbar__count">
        <AppIcon name="sparkles" :size="16" style="color: var(--color-primary)" />
        共找到 <strong>{{ resultCount }}</strong> 条结果
      </div>
      <div v-if="statusMessage" class="result-toolbar__hint">{{ statusMessage }}</div>
    </div>

    <div class="view-switch" role="tablist">
      <button
        type="button"
        :class="{ 'is-active': viewMode === 'grid' }"
       @click="$emit('update:viewMode', 'grid')"
      >
        <AppIcon name="grid" :size="14" />
        网格视图
      </button>
      <button
        type="button"
        :class="{ 'is-active': viewMode === 'rank_flow' }"
        @click="$emit('update:viewMode', 'rank_flow')"
      >
        <AppIcon name="list" :size="14" />
        Rank 流
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ViewMode } from '@/types'
import AppIcon from '@/components/icons/AppIcon.vue'

defineProps<{
  resultCount: number
  viewMode: ViewMode
  statusMessage?: string
}>()

defineEmits<{ 'update:viewMode': [value: ViewMode] }>()
</script>