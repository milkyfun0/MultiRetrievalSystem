<template>
  <section class="list-pagination glass-panel" :aria-label="ariaLabel || '列表分页'">
    <div class="list-pagination__summary">
      <div>
        <strong>第 {{ currentPage }} / {{ totalPages }} 页</strong>
        <p>当前显示 {{ start + 1 }} - {{ end }} 条，共 {{ total }} 条。</p>
      </div>
      <label class="list-pagination__size-picker">
        <span>每页</span>
        <select class="field-control compact-field-control pagination-select" :value="pageSize" @change="$emit('update:pageSize', Number(($event.target as HTMLSelectElement).value))">
          <option v-for="option in pageSizeOptions" :key="option" :value="option">{{ option }} 条</option>
        </select>
      </label>
    </div>

    <div class="list-pagination__controls">
      <button type="button" class="ghost-button small" :disabled="currentPage === 1" @click="$emit('update:page', currentPage - 1)">上一页</button>
      <div class="list-pagination__pages">
        <button
          v-for="(page, index) in pageButtons"
          :key="`page-${index}-${page}`"
          type="button"
          class="page-chip"
          :class="{ active: page === currentPage, ellipsis: page === '...' }"
          :disabled="page === '...'"
          @click="handlePageClick(page)"
        >
          {{ page }}
        </button>
      </div>
      <button type="button" class="ghost-button small" :disabled="currentPage === totalPages" @click="$emit('update:page', currentPage + 1)">下一页</button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  currentPage: number
  totalPages: number
  total: number
  start: number
  end: number
  pageSize: number
  pageSizeOptions?: number[]
  ariaLabel?: string
}>(), {
  pageSizeOptions: () => [5, 10, 20, 50],
  ariaLabel: '列表分页',
})

const emit = defineEmits<{
  'update:page': [page: number]
  'update:pageSize': [pageSize: number]
}>()

const pageButtons = computed<(number | string)[]>(() => {
  const total = props.totalPages
  const current = props.currentPage
  if (total <= 7) return Array.from({ length: total }, (_, index) => index + 1)

  const pages: (number | string)[] = [1]
  const start = Math.max(2, current - 1)
  const end = Math.min(total - 1, current + 1)

  if (start > 2) pages.push('...')
  for (let page = start; page <= end; page += 1) pages.push(page)
  if (end < total - 1) pages.push('...')
  pages.push(total)
  return pages
})

function handlePageClick(page: number | string) {
  if (typeof page === 'number') emit('update:page', page)
}

</script>
