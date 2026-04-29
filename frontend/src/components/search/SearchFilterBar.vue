<template>
  <div class="filter-shell glass-panel refined-filter-shell">
    <div class="filter-grid refined-filter-grid">
      <label class="field-shell">
        <span class="field-label">检索库类型</span>
        <select class="field-control compact-field-control" :value="storeType" @change="$emit('update:storeType', ($event.target as HTMLSelectElement).value)">
          <option v-for="type in storeTypes" :key="type" :value="type">{{ storeTypeToChinese(type) }}</option>
        </select>
      </label>

      <label class="field-shell field-shell--wide">
        <span class="field-label">检索库</span>
        <select
          class="field-control compact-field-control"
          :value="selectedStoreId"
          :disabled="storesLoading || !storeOptions.length"
          @change="$emit('update:selectedStoreId', ($event.target as HTMLSelectElement).value)"
        >
          <option value="">{{ storesLoading ? '正在加载检索库...' : storeOptions.length ? '请选择具体检索库' : '当前类型下暂无可选检索库' }}</option>
          <option v-for="item in storeOptions" :key="item.store_id" :value="item.store_id">
            {{ item.store_name }} · {{ storeStatusToChinese(item.status) }}
          </option>
        </select>
      </label>

      <label class="field-shell field-shell--small">
        <span class="field-label">TopK</span>
        <select class="field-control compact-field-control" :value="topK" @change="$emit('update:topK', Number(($event.target as HTMLSelectElement).value))">
          <option v-for="value in topkOptions" :key="value" :value="value">{{ value }}</option>
        </select>
      </label>

      <label class="field-shell field-shell--small">
        <span class="field-label">排序方式</span>
        <select class="field-control compact-field-control" :value="sortBy" @change="$emit('update:sortBy', ($event.target as HTMLSelectElement).value)">
          <option value="score_desc">相似度</option>
        </select>
      </label>

      <div class="filter-actions refined-filter-actions">
        <button type="button" class="secondary-button with-caret medium-button" @click="$emit('toggleAdvanced')">
          高级筛选
        </button>

        <button type="button" class="primary-button search-btn large-search-btn" :disabled="loading" @click="$emit('search')">
          {{ loading ? '搜索中...' : '搜索' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { StoreItemDTO } from '@/types'
import { TOPK_OPTIONS, STORE_TYPES } from '@/utils/constants'
import { storeStatusToChinese, storeTypeToChinese } from '@/utils/display'

defineProps<{
  storeType: string
  selectedStoreId: string
  storeOptions: StoreItemDTO[]
  storesLoading: boolean
  topK: number
  sortBy: string
  loading: boolean
}>()

defineEmits<{
  'update:storeType': [value: string]
  'update:selectedStoreId': [value: string]
  'update:topK': [value: number]
  'update:sortBy': [value: string]
  toggleAdvanced: []
  search: []
}>()

const topkOptions = TOPK_OPTIONS
const storeTypes = STORE_TYPES
</script>
