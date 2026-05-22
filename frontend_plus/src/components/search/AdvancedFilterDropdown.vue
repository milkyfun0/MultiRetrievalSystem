<template>
  <transition name="fade">
    <div v-if="open" class="card card--inset" style="padding: 20px; margin-top: 12px;">
      <div class="row row--between" style="margin-bottom: 14px;">
        <div class="row gap-sm">
          <div
            style="
              width: 32px; height: 32px; border-radius: 10px;
              background: var(--gradient-brand-soft); color: var(--color-primary);
              display: grid; place-items: center;
            "
          >
            <AppIcon name="settings" :size="16" />
          </div>
          <div>
            <div class="text-strong" style="font-size: 14px;">高级筛选</div>
            <div class="text-muted text-sm">细化检索行为，仅在当前查询生效</div>
          </div>
        </div>
      </div>

      <div class="form-grid">
        <label class="field">
          <span class="field__label">模型版本</span>
          <select
            class="control control--select"
            :value="modelAlias"
            @change="$emit('update:modelAlias', ($event.target as HTMLSelectElement).value)"
          >
            <option v-for="item in modelAliasOptions" :key="item" :value="item">{{ item }}</option>
          </select>
        </label>

        <div class="switch-row">
          <div class="switch-row__main">
            <strong>批量查询</strong>
            <p>开启后可按行输入多条 query 并一次提交</p>
          </div>
          <label class="switch">
            <input
              type="checkbox"
              :checked="batchMode"
              @change="$emit('update:batchMode', ($event.target as HTMLInputElement).checked)"
            />
            <span class="switch__track"></span>
            <span class="switch__thumb"></span>
          </label>
        </div>

        <div class="switch-row">
          <div class="switch-row__main">
            <strong>返回详细元信息</strong>
            <p>结果中附带派生类型、时间段等结构化字段</p>
          </div>
          <label class="switch">
            <input
              type="checkbox"
              :checked="returnDetailMeta"
              @change="$emit('update:returnDetailMeta', ($event.target as HTMLInputElement).checked)"
            />
            <span class="switch__track"></span>
            <span class="switch__thumb"></span>
          </label>
        </div>

        <div class="switch-row">
          <div class="switch-row__main">
            <strong>自动准备检索库</strong>
            <p>未就绪时由后端自动触发向量化</p>
          </div>
          <label class="switch">
            <input
              type="checkbox"
              :checked="autoPrepare"
              @change="$emit('update:autoPrepare', ($event.target as HTMLInputElement).checked)"
            />
            <span class="switch__track"></span>
            <span class="switch__thumb"></span>
          </label>
        </div>
      </div>

      <div v-if="mode === 'Text2Video'" class="card card--flat" style="margin-top: 14px;">
        <div class="row row--between" style="margin-bottom: 8px;">
          <strong class="text-strong text-sm">视频检索 · 不确定性权重</strong>
          <strong class="text-strong" style="color: var(--color-primary)">{{ uncertaintyWeight.toFixed(1) }}</strong>
        </div>
        <input
          class="range"
          type="range"
          min="0"
          max="1"
          step="0.1"
          :style="{ '--val': `${uncertaintyWeight * 100}%` }"
          :value="uncertaintyWeight"
          @input="$emit('update:uncertaintyWeight', Number(($event.target as HTMLInputElement).value))"
        />
        <p class="text-muted text-sm" style="margin-top: 8px;">数值越大，对长尾不确定结果的容忍度越高</p>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import type { SearchMode } from '@/types'
import { MODEL_ALIAS_OPTIONS } from '@/utils/constants'
import AppIcon from '@/components/icons/AppIcon.vue'

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

<style scoped>
.fade-enter-active,
.fade-leave-active { transition: opacity .2s, transform .2s; }
.fade-enter-from,
.fade-leave-to { opacity: 0; transform: translateY(-4px); }
</style>