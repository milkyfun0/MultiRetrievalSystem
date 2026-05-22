<template>
  <teleport to="body">
    <div v-if="visible && item" class="modal-mask" @click.self="$emit('close')">
      <div class="modal modal--lg" role="dialog" aria-modal="true" aria-labelledby="result-detail-title">
        <div class="modal__header">
          <div>
            <div class="modal__title" id="result-detail-title">检索结果详情</div>
            <div class="modal__subtitle">查看媒体预览、命中信息与来源元数据</div>
          </div>
          <button class="modal__close" type="button" aria-label="关闭" @click="$emit('close')">
            <AppIcon name="x" :size="18" />
          </button>
        </div>

        <div class="modal__body">
          <div class="detail-hero">
            <div class="detail-preview">
              <video
                v-if="item.mediaType === 'video' && item.thumbnailUrl"
                :src="item.thumbnailUrl"
                controls
                autoplay
                playsinline
                preload="metadata"
              />
              <img
                v-else-if="item.mediaType === 'image' && item.thumbnailUrl"
                :src="item.thumbnailUrl"
                alt="detail preview"
              />
              <div v-else class="detail-preview__empty">
                <AppIcon name="image" :size="32" />
                <p>暂无预览资源</p>
              </div>
            </div>

            <div class="detail-side">
              <div class="detail-stat">
                <span>Rank</span>
                <strong>#{{ item.rank }}</strong>
              </div>
              <div class="detail-stat detail-stat--success">
                <span>相似度</span>
                <strong>{{ item.score.toFixed(2) }}</strong>
              </div>
              <div class="row gap-sm" style="flex-wrap: wrap;">
                <span class="pill">
                  <AppIcon :name="item.mediaType === 'video' ? 'film' : 'image'" :size="12" />
                  {{ item.mediaType === 'video' ? '视频结果' : '图片结果' }}
                </span>
                <span class="pill pill--accent">{{ modeText }}</span>
              </div>
            </div>
          </div>

          <div class="detail-meta">
            <div class="detail-meta__row">
              <span>来源</span>
              <strong>{{ sourceLabelText(item.sourceLabel) }}</strong>
            </div>
            <div v-if="item.parentVideoName" class="detail-meta__row">
              <span>来源长视频</span>
              <strong>{{ item.parentVideoName }}</strong>
            </div>
            <div v-if="segmentText" class="detail-meta__row">
              <span>时间段</span>
              <strong>{{ segmentText }}</strong>
            </div>
            <div v-if="frameText" class="detail-meta__row">
              <span>时间戳</span>
              <strong>{{ frameText }}</strong>
            </div>
            <div v-if="deriveText && deriveText !== '--'" class="detail-meta__row">
              <span>派生方式</span>
              <strong>{{ deriveText }}</strong>
            </div>

            <div class="detail-meta__row">
              <span>Object Key</span>
              <div class="object-key">
                <span :title="item.objectKey">{{ shortObjectKey }}</span>
                <button type="button" class="btn btn--sm btn--ghost" @click="handleCopyObjectKey">
                  <AppIcon name="copy" class="btn__icon" />
                  {{ copied ? '已复制' : '复制' }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="modal__footer">
          <button type="button" class="btn btn--secondary" @click="$emit('prev')">
            <AppIcon name="arrow_left" class="btn__icon" />
            上一条
          </button>
          <button type="button" class="btn btn--secondary" @click="$emit('next')">
            下一条
            <AppIcon name="arrow_right" class="btn__icon" />
          </button>
          <button type="button" class="btn btn--primary" @click="$emit('close')">关闭</button>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { SearchMode, SearchResultCardVM } from '@/types'
import { preprocessModeToChinese, sceneToChinese } from '@/utils/display'
import { truncateMiddle } from '@/utils/normalize'
import AppIcon from '@/components/icons/AppIcon.vue'

const props = defineProps<{
  visible: boolean
  item: SearchResultCardVM | null
  mode: SearchMode
}>()

defineEmits<{ close: []; next: []; prev: [] }>()

const copied = ref(false)

const shortObjectKey = computed(() =>
  props.item ? truncateMiddle(props.item.objectKey, 28, 18) : '',
)
const modeText = computed(() => sceneToChinese(props.mode))

const segmentText = computed(() => {
  if (!props.item) return ''
  if (typeof props.item.segmentStartSec === 'number' && typeof props.item.segmentEndSec === 'number') {
    return `${props.item.segmentStartSec}s - ${props.item.segmentEndSec}s`
  }
  return ''
})

const frameText = computed(() => {
  if (!props.item) return ''
  if (typeof props.item.frameTimestampSec === 'number') {
    return `${props.item.frameTimestampSec}s`
  }
  return ''
})

const deriveText = computed(() => preprocessModeToChinese(props.item?.deriveType))

function sourceLabelText(label?: string | null) {
  if (!label) return '默认数据源'
  if (label === 'Folder') return '文件夹库'
  if (label === 'DataBase') return '数据库'
  if (label === 'LongVideo') return '长视频库'
  return label
}

async function handleCopyObjectKey() {
  if (!props.item?.objectKey) return
  try {
    await navigator.clipboard.writeText(props.item.objectKey)
    copied.value = true
    window.setTimeout(() => (copied.value = false), 1500)
  } catch {
    window.alert('复制失败，请手动复制')
  }
}
</script>

<style scoped>
.detail-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 240px;
  gap: 16px;
  align-items: stretch;
}
.detail-preview {
  border-radius: var(--radius-xl);
  background: #0b0f1a;
  overflow: hidden;
  min-height: 360px;
  display: grid;
  place-items: center;
}
.detail-preview video,
.detail-preview img {
  width: 100%;
  height: 100%;
  max-height: 460px;
  object-fit: contain;
  background: #000;
}
.detail-preview__empty {
  color: #94a3b8;
  text-align: center;
}
.detail-preview__empty p {
  margin-top: 8px;
  font-size: 13px;
}
.detail-side {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.detail-stat {
  padding: 18px 20px;
  border-radius: var(--radius-lg);
  background: var(--gradient-card);
  border: 1px solid var(--color-border);
}
.detail-stat span {
  display: block;
  font-size: 11px;
  font-weight: 700;
  color: var(--color-text-muted);
  letter-spacing: 1px;
  text-transform: uppercase;
}
.detail-stat strong {
  display: block;
  margin-top: 8px;
  font-size: 30px;
  font-weight: 800;
  color: var(--color-text-strong);
}
.detail-stat--success strong {
  color: var(--color-success);
}
.detail-meta {
  margin-top: 18px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.detail-meta__row {
  display: grid;
  grid-template-columns: 140px 1fr;
  gap: 14px;
  padding: 12px 14px;
  border-radius: var(--radius-md);
  background: var(--color-surface-2);
  border: 1px solid var(--color-divider);
}
.detail-meta__row span {
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.6px;
  text-transform: uppercase;
}
.detail-meta__row strong {
  color: var(--color-text-strong);
  font-size: 13px;
  word-break: break-all;
}
.object-key {
  display: flex;
  align-items: center;
  gap: 10px;
  font-family: var(--font-mono);
  color: var(--color-text-strong);
  font-size: 13px;
  word-break: break-all;
}
@media (max-width: 920px) {
  .detail-hero { grid-template-columns: 1fr; }
  .detail-meta__row { grid-template-columns: 1fr; }
}
</style>