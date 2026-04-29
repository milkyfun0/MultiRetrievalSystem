<template>
  <div class="mode-tabs">
    <button
      v-for="item in modes"
      :key="item"
      type="button"
      class="mode-tab"
      :class="{ active: item === modelValue }"
      @click="$emit('update:modelValue', item)"
    >
      {{ sceneToChinese(item) }}
    </button>
  </div>
</template>

<script setup lang="ts">
import type { SearchMode } from '@/types'
import { SEARCH_MODES } from '@/utils/constants'
import { sceneToChinese } from '@/utils/display'

defineProps<{ modelValue: SearchMode }>()
defineEmits<{ 'update:modelValue': [value: SearchMode] }>()
const modes = SEARCH_MODES
</script>
