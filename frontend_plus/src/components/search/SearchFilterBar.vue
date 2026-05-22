<template>
  <div class="card card--inset" style="padding: 18px;">
    <div class="form-grid form-grid--3" style="gap: 14px;">
      <label class="field">
        <span class="field__label">检索库类型</span>
        <select
          class="control control--select"
          :value="storeType"
          @change="$emit('update:storeType', ($event.target as HTMLSelectElement).value)"
        >
          <option v-for="type in storeTypes" :key="type" :value="type">{{ storeTypeToChinese(type) }}</option>
        </select>
      </label>

      <label class="field" style="grid-column: span 2;">
        <span class="field__label">检索库</span>
        <select
          class="control control--select"
          :value="selectedStoreId"
          :disabled="storesLoading || !storeOptions.length"
          @change="$emit('update:selectedStoreId', ($event.target as HTMLSelectElement).value)"
        >
          <option value="">
            {{ storesLoading ? '正在加载检索库…' : storeOptions.length ? '请选择具体检索库' : '当前类型下暂无可选检索库' }}
          </option>
          <option v-for="item in storeOptions" :key="item.store_id" :value="item.store_id">
            {{ item.store_name }} · {{ storeStatusToChinese(item.status) }}
          </option>
        </select>
      </label>

      <label class="field">
        <span class="field__label">TopK 数量</span>
        <select
          class="control control--select"
          :value="topK"
          @change="$emit('update:topK', Number(($event.target as HTMLSelectElement).value))"
        >
          <option v-for="value in topkOptions" :key="value" :value="value">{{ value }}</option>
        </select>
      </label>

      <label class="field">
        <span class="field__label">排序策略</span>
        <select
          class="control control--select"
          :value="sortBy"
          @change="$emit('update:sortBy', ($event.target as HTMLSelectElement).value)"
        >
          <option value="score_desc">按相似度（高→低）</option>
        </select>
      </label>

      <div class="field" style="justify-content: flex-end;">
        <span class="field__label" style="opacity:0">操作</span>
        <div class="row gap-sm">
          <button type="button" class="btn btn--secondary" @click="$emit('toggleAdvanced')">
            <AppIcon name="filter" class="btn__icon" />
            高级筛选
          </button>
          <button
            type="button"
            class="btn btn--primary"
            style="flex:1"
            :disabled="loading"
            @click="$emit('search')"
          >
            <AppIcon name="search" class="btn__icon" />
            {{ loading ? '检索中…' : '开始检索' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { StoreItemDTO } from '@/types'
import { TOPK_OPTIONS, STORE_TYPES } from '@/utils/constants'
import { storeStatusToChinese, storeTypeToChinese } from '@/utils/display'
import AppIcon from '@/components/icons/AppIcon.vue'

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