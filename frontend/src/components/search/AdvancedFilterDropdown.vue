<template>
  <transition name="fade-slide">
    <div v-if="open" class="advanced-dropdown glass-panel">
      <div class="advanced-grid">
        <label class="field-block">
          <span>模型版本</span>
          <select class="field-control" :value="modelAlias" @change="$emit('update:modelAlias', ($event.target as HTMLSelectElement).value)">
            <option v-for="item in modelAliasOptions" :key="item" :value="item">{{ item }}</option>
          </select>
        </label>

        <label class="switch-row">
          <span>批量输入开关</span>
          <input type="checkbox" :checked="batchMode" @change="$emit('update:batchMode', ($event.target as HTMLInputElement).checked)" />
        </label>

        <label class="switch-row">
          <span>返回详细元信息</span>
          <input type="checkbox" :checked="returnDetailMeta" @change="$emit('update:returnDetailMeta', ($event.target as HTMLInputElement).checked)" />
        </label>

        <label class="switch-row">
          <span>自动准备检索库</span>
          <input type="checkbox" :checked="autoPrepare" @change="$emit('update:autoPrepare', ($event.target as HTMLInputElement).checked)" />
        </label>
      </div>

      <div v-if="mode === 'Text2Video'" class="slider-block">
        <div class="slider-header">
          <span>Text2Video 特有: 不确定性权重</span>
          <strong>{{ uncertaintyWeight.toFixed(1) }}</strong>
        </div>
        <input
          type="range"
          min="0"
          max="1"
          step="0.1"
          :value="uncertaintyWeight"
          @input="$emit('update:uncertaintyWeight', Number(($event.target as HTMLInputElement).value))"
        />
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import type { SearchMode } from '@/types'
import { MODEL_ALIAS_OPTIONS } from '@/utils/constants'

defineProps<{
  open: boolean
  mode: SearchMode
  modelAlias: string
  batchMode: boolean
  returnDetailMeta: boolean
  autoPrepare: boolean
  uncertaintyWeight: number
}>()

defineEmits<{
  'update:modelAlias': [value: string]
  'update:batchMode': [value: boolean]
  'update:returnDetailMeta': [value: boolean]
  'update:autoPrepare': [value: boolean]
  'update:uncertaintyWeight': [value: number]
}>()

const modelAliasOptions = MODEL_ALIAS_OPTIONS
</script>
