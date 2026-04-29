<template>
  <section class="glass-panel task-table-panel refined-task-table-panel">
    <div class="section-title">
      <h2>任务列表</h2>
      <p>展示当前资源准备任务状态，并给出关键统计信息。</p>
    </div>

    <div class="table-wrap refined-table-wrap">
      <table class="task-table refined-task-table">
        <thead>
          <tr>
            <th>task_id</th>
            <th>任务模式</th>
            <th>库类型</th>
            <th>名称</th>
            <th>状态</th>
            <th>阶段</th>
            <th>进度</th>
            <th>新增向量</th>
            <th>跳过向量</th>
            <th>起止时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="11" class="empty-cell">任务状态刷新中...</td>
          </tr>
          <tr v-else-if="!items.length">
            <td colspan="11" class="empty-cell">暂无任务，先提交一个向量化任务吧。</td>
          </tr>
          <tr v-for="task in items" :key="task.jobId" class="task-row" :class="`is-${task.status}`">
            <td class="mono-text">{{ task.jobId }}</td>
            <td>{{ sceneToChinese(task.taskMode) }}</td>
            <td>{{ storeTypeToChinese(task.storeType) }}</td>
            <td>{{ task.storeName || '--' }}</td>
            <td><StatusBadge :status="task.status" :label="storeStatusToChinese(task.status)" /></td>
            <td>{{ phaseToChinese(task.phase) }}</td>
            <td>
              <div class="progress-cell">
                <div class="progress-track refined-progress-track">
                  <div class="progress-bar" :style="{ width: `${task.progress}%` }"></div>
                </div>
                <span class="progress-label">{{ task.progress }}%</span>
              </div>
            </td>
            <td>{{ resultNumber(task.result, 'new_vectors') }}</td>
            <td>{{ resultNumber(task.result, 'skipped_vectors') }}</td>
            <td>{{ task.timeLabel }}</td>
            <td>
              <div class="table-actions">
                <button type="button" class="ghost-button small" @click="$emit('detail', task.jobId)">查看详情</button>
                <button
                  v-if="task.status === 'running' && task.canTerminate"
                  type="button"
                  class="ghost-button small danger-ghost"
                  @click="$emit('terminate', task.jobId)"
                >
                  终止任务
                </button>
                <button
                  v-else-if="task.status === 'failed' || task.status === 'terminated'"
                  type="button"
                  class="ghost-button small"
                  @click="$emit('retry', task.jobId)"
                >重试</button>
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
import type { VectorizeTaskVM } from '@/types'
import { phaseToChinese, sceneToChinese, storeStatusToChinese, storeTypeToChinese } from '@/utils/display'

defineProps<{ items: VectorizeTaskVM[]; loading?: boolean }>()
defineEmits<{ retry: [jobId: string]; detail: [jobId: string]; terminate: [jobId: string] }>()

function resultNumber(result: Record<string, unknown> | null | undefined, key: string) {
  const value = result?.[key]
  return typeof value === 'number' ? value : '--'
}
</script>
