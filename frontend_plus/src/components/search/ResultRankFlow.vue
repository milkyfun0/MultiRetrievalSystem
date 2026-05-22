<template>
  <div class="rank-flow">
    <article
      v-for="(item, index) in items"
      :key="`${item.objectKey}-${index}`"
      class="rank-row"
    >
      <div class="rank-row__rank">
        <span class="rank-row__rank-num">{{ item.rank }}</span>
        <span class="rank-row__rank-label">Rank</span>
      </div>

      <div class="rank-row__media">
        <video
          v-if="item.mediaType === 'video'"
          :src="item.thumbnailUrl"
          muted
          playsinline
          preload="metadata"
        />
        <img v-else :src="item.thumbnailUrl" alt="preview" />
      </div>

      <div class="rank-row__body">
        <div class="rank-row__title">{{ primaryTitle(item) }}</div>
        <div class="rank-row__sub">
          {{ sourceLabelText(item.sourceLabel) }} · 分数 {{ item.score.toFixed(2) }}
          <span v-if="getLongVideoMeta(item)" class="text-muted"> · {{ getLongVideoMeta(item) }}</span>
        </div>
        <div class="rank-row__pills">
          <span class="pill">
            <AppIcon :name="item.mediaType === 'video' ? 'film' : 'image'" :size="12" />
            {{ item.mediaType === 'video' ? '视频结果' : '图片结果' }}
          </span>
          <span class="pill pill--accent">Top {{ item.rank }}</span>
        </div>
        <div class="rank-row__key" :title="item.objectKey">{{ compactKey(item.objectKey) }}</div>
      </div>

      <button type="button" class="btn btn--secondary" @click="$emit('view', indexOffset + index)">
        <AppIcon name="eye" class="btn__icon" />
        详情
      </button>
    </article>
  </div>
</template>

<script setup lang="ts">
import type { SearchResultCardVM } from '@/types'
import { formatLongVideoMeta } from '@/utils/display'
import { truncateMiddle } from '@/utils/normalize'
import AppIcon from '@/components/icons/AppIcon.vue'

withDefaults(
  defineProps<{ items: SearchResultCardVM[]; indexOffset?: number }>(),
  { indexOffset: 0 },
)
defineEmits<{ view: [index: number] }>()

const compactKey = (value: string) => truncateMiddle(value || '--', 22, 16)

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

const stripDuplicateMediaSuffix = (value: string) =>
  value.replace(/(\.(mp4|mov|avi|mkv|webm))\1$/i, '$1')

const primaryTitle = (item: SearchResultCardVM) => {
  const parent = item.parentVideoName?.trim()
  if (parent) return stripDuplicateMediaSuffix(parent)
  const objectName = basename(item.objectKey)
  if (objectName) return stripDuplicateMediaSuffix(objectName)
  return item.mediaType === 'video' ? '视频检索结果' : '图片检索结果'
}
</script>