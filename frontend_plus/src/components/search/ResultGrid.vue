<template>
  <div class="result-grid">
    <ResultCard
      v-for="(item, index) in items"
      :key="`${item.objectKey}-${indexOffset + index}`"
      :item="item"
      :index="indexOffset + index"
      @view="$emit('view', $event)"
    />
  </div>
</template>

<script setup lang="ts">
import ResultCard from './ResultCard.vue'
import type { SearchResultCardVM } from '@/types'

withDefaults(
  defineProps<{
    items: SearchResultCardVM[]
    indexOffset?: number
  }>(),
  {
    indexOffset: 0,
  },
)

defineEmits<{ view: [index: number] }>()
</script>