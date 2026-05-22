<template>
  <section class="pagination" :aria-label="ariaLabel || '列表分页'">
    <div class="pagination__info">
      <strong>第 {{ currentPage }} / {{ totalPages }} 页</strong>
      ，显示 {{ start + 1 }} - {{ end }} 条，共 {{ total }} 条
      <label class="row gap-sm" style="display:inline-flex; margin-left:14px;">
        <span class="text-muted text-sm">每页</span>
        <select
          class="control control--select"
          style="width: 100px; height: 32px; padding: 0 28px 0 10px;"
          :value="pageSize"
          @change="$emit('update:pageSize', Number(($event.target as HTMLSelectElement).value))"
        >
          <option v-for="option in pageSizeOptions" :key="option" :value="option">{{ option }} 条</option>
        </select>
      </label>
    </div>

    <div class="pagination__controls">
      <button
        type="button"
        class="btn btn--sm btn--secondary"
        :disabled="currentPage === 1"
        @click="$emit('update:page', currentPage - 1)"
      >
        <AppIcon name="arrow_left" class="btn__icon" />
        上一页
      </button>
      <button
        v-for="(page, index) in pageButtons"
        :key="`page-${index}-${page}`"
        type="button"
        class="page-chip"
        :class="{ 'is-active': page === currentPage, 'is-ellipsis': page === '...' }"
        :disabled="page === '...'"
        @click="handlePageClick(page)"
      >
        {{ page }}
      </button>
      <button
        type="button"
        class="btn btn--sm btn--secondary"
        :disabled="currentPage === totalPages"
        @click="$emit('update:page', currentPage + 1)"
      >
        下一页
        <AppIcon name="arrow_right" class="btn__icon" />
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/components/icons/AppIcon.vue'

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