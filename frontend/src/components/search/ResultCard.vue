<template>
  <article class="result-card glass-panel refined-result-card">
    <div class="rank-corner">#{{ item.rank }}</div>

    <div class="media-frame refined-media-frame">
      <template v-if="item.mediaType === 'video'">
        <video
          v-if="item.thumbnailUrl"
          class="media-el"
          :src="item.thumbnailUrl"
          muted
          autoplay
          loop
          playsinline
          preload="metadata"
        />
        <div v-else class="media-placeholder">暂无视频预览</div>
      </template>

      <template v-else>
        <img v-if="item.thumbnailUrl" class="media-el" :src="item.thumbnailUrl" alt="result preview" />
        <div v-else class="media-placeholder">暂无图片预览</div>
      </template>

      <div class="media-overlay"></div>
    </div>

    <div class="card-meta refined-card-meta">
      <div class="result-pill-row refined-result-pill-row">
        <span class="result-meta-pill result-meta-pill--type">{{ mediaTypeLabel }}</span>
        <span class="result-meta-pill result-meta-pill--source">{{ sourceLabelText(item.sourceLabel) }}</span>
      </div>

      <div class="result-meta-head">
        <p class="score-caption">分数 <strong>{{ item.score.toFixed(2) }}</strong></p>
        <p class="source-line">Top {{ item.rank }} 检索结果</p>
      </div>

      <p v-if="longVideoMeta" class="longvideo-line">{{ longVideoMeta }}</p>
      <p class="object-key-line" :title="item.objectKey">{{ compactKey }}</p>
    </div>

    <button type="button" class="ghost-button full-width card-detail-button" @click="$emit('view', index)">查看详情</button>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SearchResultCardVM } from '@/types'
import { formatLongVideoMeta } from '@/utils/display'
import { truncateMiddle } from '@/utils/normalize'

const props = defineProps<{
  item: SearchResultCardVM
  index: number
}>()

defineEmits<{ view: [index: number] }>()

const compactKey = computed(() => `Object Key · ${truncateMiddle(props.item.objectKey || '--', 18, 14)}`)
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

<style scoped>
.media-el {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  background: #edf2f8;
}

.media-placeholder {
  width: 100%;
  height: 100%;
  display: grid;
  place-items: center;
  color: #6b7a90;
  font-size: 14px;
  background: linear-gradient(180deg, #dfe7f3 0%, #b7c3d4 100%);
}

.object-key-line {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.longvideo-line {
  margin-top: 2px;
  color: #5b6f8f;
  font-size: 13px;
}
</style>
