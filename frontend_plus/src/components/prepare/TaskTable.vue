<template>
  <section class="card">
    <div class="card-header">
      <div>
        <div class="card-title">
          <span class="card-title__icon"><AppIcon name="list" :size="16" /></span>
          任务列表
        </div>
        <p class="card-subtitle">展示当前所有向量化任务的状态、阶段与统计</p>
      </div>
    </div>

    <div class="table-wrap">
      <table class="table">
        <thead>
          <tr>
            <th>任务 ID</th>
            <th>模式</th>
            <th>库类型</th>
            <th>名称</th>
            <th>状态</th>
            <th>阶段</th>
            <th>进度</th>
            <th>新增向量</th>
            <th>跳过</th>
            <th>起止时间</th>
            <th style="text-align: right;">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="11" class="table__empty">任务状态刷新中…</td>
          </tr>
          <tr v-else-if="!items.length">
            <td colspan="11" class="table__empty">暂无任务，先提交一个向量化任务吧。</td>
          </tr>
          <tr v-for="task in items" :key="task.jobId">
            <td>
              <span class="font-mono text-xs text-muted">{{ task.jobId }}</span>
            </td>
            <td>{{ sceneToChinese(task.taskMode) }}</td>
            <td>{{ storeTypeToChinese(task.storeType) }}</td>
            <td>
              <div class="table__title">{{ task.storeName || '未命名' }}</div>
              <div class="table__sub">{{ task.storeDescription || '暂无备注' }}</div>
            </td>
            <td>
              <StatusBadge :status="task.status" :label="storeStatusToChinese(task.status)" />
            </td>
            <td>{{ phaseToChinese(task.phase) }}</td>
            <td>
              <div class="progress">
                <div class="progress__track">
                  <div class="progress__bar" :style="{ width: `${task.progress}%` }"></div>
                </div>
                <span class="progress__label">{{ task.progress }}%</span>
              </div>
            </td>
            <td>{{ resultNumber(task.result, 'new_vectors') }}</td>
            <td>{{ resultNumber(task.result, 'skipped_vectors') }}</td>
            <td><span class="text-muted text-sm">{{ task.timeLabel }}</span></td>
            <td>
              <div class="table__actions" style="justify-content: flex-end; display: flex;">
                <button type="button" class="btn btn--sm btn--ghost" @click="$emit('detail', task.jobId)">
                  <AppIcon name="eye" class="btn__icon" />
                  详情
                </button>
                <button
                  v-if="task.status === 'running' && task.canTerminate"
                  type="button"
                  class="btn btn--sm btn--danger"
                  @click="$emit('terminate', task.jobId)"
                >
                  <AppIcon name="stop" class="btn__icon" />
                  终止
                </button>
                <button
                  v-else-if="task.status === 'failed' || task.status === 'terminated'"
                  type="button"
                  class="btn btn--sm btn--secondary"
                  @click="$emit('retry', task.jobId)"
                >
                  <AppIcon name="refresh" class="btn__icon" />
                  重试
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script setup lang="ts">
import StatusBadge from '@/components/common/StatusBadge.vue'
import AppIcon from '@/components/icons/AppIcon.vue'
import type { VectorizeTaskVM } from '@/types'
import { phaseToChinese, sceneToChinese, storeStatusToChinese, storeTypeToChinese } from '@/utils/display'

defineProps<{ items: VectorizeTaskVM[]; loading?: boolean }>()
defineEmits<{ retry: [jobId: string]; detail: [jobId: string]; terminate: [jobId: string] }>()

function resultNumber(result: Record<string, unknown> | null | undefined, key: string) {
  const value = result?.[key]
  return typeof value === 'number' ? value : '--'
}
</script>