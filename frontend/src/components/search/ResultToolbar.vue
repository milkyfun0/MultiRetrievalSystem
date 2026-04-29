<template>
  <div class="result-toolbar refined-result-toolbar">
    <div>
      <strong class="toolbar-count">结果数: {{ resultCount }}</strong>
      <p v-if="statusMessage" class="helper-text compact">{{ statusMessage }}</p>
    </div>

    <div class="toolbar-actions refined-toolbar-actions">
      <button type="button" class="view-toggle" :class="{ active: viewMode === 'grid' }" @click="$emit('update:viewMode', 'grid')">网格</button>
      <button type="button" class="view-toggle" :class="{ active: viewMode === 'rank_flow' }" @click="$emit('update:viewMode', 'rank_flow')">Rank流</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ViewMode } from '@/types'

defineProps<{
  resultCount: number
  viewMode: ViewMode
  statusMessage?: string
}>()

defineEmits<{ 'update:viewMode': [value: ViewMode] }>()
</script>
