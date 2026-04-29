<template>
  <div class="rank-flow refined-rank-flow">
    <article
      v-for="(item, index) in items"
      :key="`${item.objectKey}-${index}`"
      class="rank-row glass-panel refined-rank-row"
    >
      <div class="rank-chip">#{{ item.rank }}</div>

      <div class="rank-media">
        <video
          v-if="item.mediaType === 'video'"
          :src="item.thumbnailUrl"
          muted
          playsinline
          preload="metadata"
        />
        <img v-else :src="item.thumbnailUrl" alt="preview" />
      </div>

      <div class="rank-body refined-rank-body">
        <div class="rank-body__top">
          <div class="rank-body__title-wrap">
            <h4>{{ primaryTitle(item) }}</h4>
            <p class="muted-row rank-subtitle-line">{{ secondaryLabel(item) }}</p>
            <p v-if="getLongVideoMeta(item)" class="muted-row rank-meta-line">{{ getLongVideoMeta(item) }}</p>
          </div>
          <div class="rank-body__pills">
            <span class="result-meta-pill result-meta-pill--type">{{ item.mediaType === 'video' ? '视频结果' : '图片结果' }}</span>
            <span class="result-meta-pill result-meta-pill--source">分数 {{ item.score.toFixed(2) }}</span>
          </div>
        </div>

        <el-tooltip
          :content="item.objectKey"
          placement="top"
          effect="dark"
          :show-after="200"
        >
          <p class="muted-row object-key-ellipsis rank-object-key-box">
            {{ compactKey(item.objectKey) }}
          </p>
        </el-tooltip>
      </div>

      <button type="button" class="ghost-button rank-detail-button" @click="$emit('view', indexOffset + index)">
        查看详情
      </button>
    </article>
  </div>
</template>

<script setup lang="ts">
import type { SearchResultCardVM } from '@/types'
import { formatLongVideoMeta } from '@/utils/display'
import { truncateMiddle } from '@/utils/normalize'

withDefaults(
  defineProps<{ items: SearchResultCardVM[]; indexOffset?: number }>(),
  { indexOffset: 0 },
)
defineEmits<{ view: [index: number] }>()

const compactKey = (value: string) => `Object Key · ${truncateMiddle(value || '--', 22, 16)}`

const getLongVideoMeta = (item: SearchResultCardVM) =>
  formatLongVideoMeta({
    parentVideoName: item.parentVideoName,
    segmentStartSec: item.segmentStartSec,
    segmentEndSec: item.segmentEndSec,
    frameTimestampSec: item.frameTimestampSec,
    deriveType: item.deriveType,
  })

const sourceLabelText = (label?: string | null) => {
  if (!label) return '默认数据源'
  if (label === 'Folder') return '文件夹库'
  if (label === 'DataBase') return '数据库'
  if (label === 'LongVideo') return '长视频库'
  return label
}

const basename = (value?: string | null) => {
  if (!value) return ''
  const normalized = value.split('?')[0].split('#')[0]
  const parts = normalized.split('/')
  return parts[parts.length - 1] || normalized
}

const stripDuplicateMediaSuffix = (value: string) => {
  return value.replace(/(\.(mp4|mov|avi|mkv|webm))\1$/i, '$1')
}

const primaryTitle = (item: SearchResultCardVM) => {
  const parent = item.parentVideoName?.trim()
  if (parent) return stripDuplicateMediaSuffix(parent)

  const objectName = basename(item.objectKey)
  if (objectName) return stripDuplicateMediaSuffix(objectName)

  return item.mediaType === 'video' ? '视频检索结果' : '图片检索结果'
}

const secondaryLabel = (item: SearchResultCardVM) => {
  return `${sourceLabelText(item.sourceLabel)} · Rank #${item.rank}`
}
</script>

<style scoped>
.rank-body {
  min-width: 0;
}

.rank-body__top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.rank-body__title-wrap {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.rank-body__top h4 {
  margin: 0;
}

.rank-body__pills {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 8px;
}

.rank-subtitle-line {
  color: #7386a0;
  font-size: 13px;
  line-height: 1.45;
}

.rank-meta-line {
  margin-top: 0;
}

.muted-row {
  min-width: 0;
}

.object-key-ellipsis {
  max-width: 100%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  cursor: help;
}
</style>
