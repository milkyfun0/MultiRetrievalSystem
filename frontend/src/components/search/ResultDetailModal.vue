<template>
  <teleport to="body">
    <div v-if="visible && item" class="modal-mask" @click.self="$emit('close')">
      <div
        class="detail-modal glass-panel detail-modal--premium"
        role="dialog"
        aria-modal="true"
        aria-labelledby="result-detail-title"
      >
        <div class="section-title slim detail-modal__header detail-modal__header--premium">
          <div>
            <h3 id="result-detail-title">检索结果详情</h3>
            <p>查看媒体预览、命中信息与来源元数据。</p>
          </div>
          <button type="button" class="icon-close" aria-label="关闭详情弹窗" @click="$emit('close')">×</button>
        </div>

        <div class="detail-modal__hero">
          <div class="detail-preview detail-preview--premium">
            <video
              v-if="item.mediaType === 'video' && item.thumbnailUrl"
              :src="item.thumbnailUrl"
              controls
              autoplay
              playsinline
              preload="metadata"
              class="preview-el"
            />
            <img
              v-else-if="item.mediaType === 'image' && item.thumbnailUrl"
              :src="item.thumbnailUrl"
              alt="detail preview"
              class="preview-el"
            />
            <div v-else class="preview-empty">暂无预览</div>
          </div>

          <div class="detail-side-summary">
            <div class="detail-stat-card">
              <span>Rank</span>
              <strong>#{{ item.rank }}</strong>
            </div>
            <div class="detail-stat-card detail-stat-card--success">
              <span>分数</span>
              <strong>{{ item.score.toFixed(2) }}</strong>
            </div>
            <div class="detail-pill-row">
              <span class="detail-pill">{{ item.mediaType === 'video' ? '视频结果' : '图片结果' }}</span>
              <span class="detail-pill detail-pill--soft">{{ modeText }}</span>
            </div>
          </div>
        </div>

        <div class="detail-content detail-content--premium">
          <p><strong>来源</strong><span>{{ sourceLabelText(item.sourceLabel) }}</span></p>
          <p v-if="item.parentVideoName"><strong>来源长视频</strong><span>{{ item.parentVideoName }}</span></p>
          <p v-if="segmentText"><strong>时间段</strong><span>{{ segmentText }}</span></p>
          <p v-if="frameText"><strong>时间戳</strong><span>{{ frameText }}</span></p>
          <p v-if="deriveText"><strong>派生方式</strong><span>{{ deriveText }}</span></p>

          <div class="object-key-field object-key-field--premium">
            <strong class="object-key-label">Object Key</strong>
            <div class="object-key-box">
              <span class="object-key-text" :title="item.objectKey">
                {{ shortObjectKey }}
              </span>
              <button type="button" class="copy-button inside" @click="handleCopyObjectKey">
                {{ copied ? '已复制' : '复制' }}
              </button>
            </div>
          </div>
        </div>

        <div class="detail-actions detail-actions--premium">
          <button type="button" class="ghost-button" @click="$emit('prev')">上一条</button>
          <button type="button" class="ghost-button" @click="$emit('next')">下一条</button>
          <button type="button" class="primary-button" @click="$emit('close')">关闭</button>
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
  if (
    typeof props.item.segmentStartSec === 'number' &&
    typeof props.item.segmentEndSec === 'number'
  ) {
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

const deriveText = computed(() =>
  preprocessModeToChinese(props.item?.deriveType),
)

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
    window.setTimeout(() => {
      copied.value = false
    }, 1500)
  } catch {
    copied.value = false
    window.alert('复制失败，请手动复制')
  }
}
</script>

<style scoped>
.preview-el {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: contain;
  background: #000;
}

.preview-empty {
  width: 100%;
  min-height: 280px;
  display: grid;
  place-items: center;
  color: #6b7a90;
  background: linear-gradient(180deg, #dfe7f3 0%, #b7c3d4 100%);
  border-radius: 18px;
}

.detail-modal__header {
  margin-bottom: 14px;
}

.detail-modal__hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 220px;
  gap: 16px;
  align-items: stretch;
}

.detail-preview--premium {
  min-height: 360px;
}

.detail-side-summary {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detail-stat-card {
  padding: 16px 18px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(251,253,255,0.98), rgba(244,248,253,0.94));
  border: 1px solid rgba(223, 232, 241, 0.98);
}

.detail-stat-card span {
  display: block;
  color: #7b8ea7;
  font-size: 12px;
  font-weight: 700;
}

.detail-stat-card strong {
  display: block;
  margin-top: 8px;
  color: #173257;
  font-size: 30px;
  line-height: 1;
}

.detail-stat-card--success strong {
  color: #1b7a61;
}

.detail-pill-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.detail-pill {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  background: linear-gradient(180deg, rgba(240,245,255,0.98), rgba(233,241,255,0.94));
  color: #3158d7;
  font-size: 12px;
  font-weight: 800;
}

.detail-pill--soft {
  background: linear-gradient(180deg, rgba(241,250,247,0.98), rgba(233,247,242,0.94));
  color: #2a7d63;
}

.detail-content--premium {
  margin-top: 16px;
}

.detail-content--premium p {
  display: flex;
  flex-direction: column;
}

.object-key-field {
  margin: 8px 0;
}

.object-key-label {
  display: inline-block;
  margin-bottom: 6px;
}

.object-key-box {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  min-height: 42px;
  padding: 0 8px 0 12px;
  border: 1px solid #d8e1ee;
  border-radius: 12px;
  background: #f8fbff;
  box-sizing: border-box;
}

.object-key-text {
  flex: 1;
  min-width: 0;
  line-height: 40px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: #334155;
  cursor: help;
}

.copy-button.inside {
  flex: 0 0 auto;
  height: 28px;
  padding: 0 10px;
  border: 1px solid #d8e1ee;
  border-radius: 8px;
  background: #ffffff;
  color: #1f3b64;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.copy-button.inside:hover {
  background: #eef5ff;
}

@media (max-width: 920px) {
  .detail-modal__hero {
    grid-template-columns: 1fr;
  }
}
</style>
