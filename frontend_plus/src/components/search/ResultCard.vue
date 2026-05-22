<template>
  <article class="result-card">
    <div class="result-card__media">
      <div class="result-card__rank">#{{ item.rank }}</div>
      <div class="result-card__score">{{ item.score.toFixed(2) }}</div>

      <template v-if="item.mediaType === 'video'">
        <video
          v-if="item.thumbnailUrl"
          :src="item.thumbnailUrl"
          muted
          autoplay
          loop
          playsinline
          preload="metadata"
        />
        <div v-else class="result-card__media-empty">暂无视频预览</div>
      </template>
      <template v-else>
        <img v-if="item.thumbnailUrl" :src="item.thumbnailUrl" alt="result preview" />
        <div v-else class="result-card__media-empty">暂无图片预览</div>
      </template>
    </div>

    <div class="result-card__body">
      <div class="result-card__pills">
        <span class="pill">
          <AppIcon :name="item.mediaType === 'video' ? 'film' : 'image'" :size="12" />
          {{ mediaTypeLabel }}
        </span>
        <span class="pill pill--soft">{{ sourceLabelText(item.sourceLabel) }}</span>
      </div>

      <p v-if="longVideoMeta" class="text-muted text-sm">
        <AppIcon name="clock" :size="12" style="vertical-align: -2px; margin-right: 4px;" />
        {{ longVideoMeta }}
      </p>

      <p class="result-card__key" :title="item.objectKey">{{ compactKey }}</p>

      <div class="result-card__footer">
        <button type="button" class="btn btn--sm btn--secondary btn--block" @click="$emit('view', index)">
          <AppIcon name="eye" class="btn__icon" />
          查看详情
        </button>
      </div>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SearchResultCardVM } from '@/types'
import { formatLongVideoMeta } from '@/utils/display'
import { truncateMiddle } from '@/utils/normalize'
import AppIcon from '@/components/icons/AppIcon.vue'

const props = defineProps<{
  item: SearchResultCardVM
  index: number
}>()

defineEmits<{ view: [index: number] }>()

const compactKey = computed(() => truncateMiddle(props.item.objectKey || '--', 18, 14))
const mediaTypeLabel = computed(() => (props.item.mediaType === 'video' ? '视频结果' : '图片结果'))

const longVideoMeta = computed(() =>
  formatLongVideoMeta({
    parentVideoName: props.item.parentVideoName,
    segmentStartSec: props.item.segmentStartSec,
    segmentEndSec: props.item.segmentEndSec,
    frameTimestampSec: props.item.frameTimestampSec,
    deriveType: props.item.deriveType,
  }),
)

function sourceLabelText(label?: string | null) {
  if (!label) return '默认数据源'
  if (label === 'Folder') return '文件夹库'
  if (label === 'DataBase') return '数据库'
  if (label === 'LongVideo') return '长视频库'
  return label
}
</script>