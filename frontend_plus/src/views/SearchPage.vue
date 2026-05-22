<template>
  <AppLayout>
    <div class="page-stack">
      <!-- Hero -->
      <section class="hero-banner">
        <div class="hero-banner__content">
          <span class="hero-banner__eyebrow">
            <AppIcon name="sparkles" :size="12" />
            Multimodal · Retrieval Workspace
          </span>
          <h1 class="hero-banner__title">智能多模态检索工作台</h1>
          <p class="hero-banner__desc">
            统一支持 文搜视频、文搜图像、以图搜图 三大场景，秒级返回 Top-K 相似结果。
            通过精选检索库 + 高级筛选，让创作者与运营高效定位海量素材。
          </p>
        </div>

        <div class="hero-banner__meta">
          <article class="hero-stat">
            <span class="hero-stat__label">当前模式</span>
            <span class="hero-stat__value">{{ sceneToChinese(searchStore.mode) }}</span>
            <span class="hero-stat__hint">可在下方切换</span>
          </article>
          <article class="hero-stat">
            <span class="hero-stat__label">可用检索库</span>
            <span class="hero-stat__value">{{ searchStore.filteredStores.length }}</span>
            <span class="hero-stat__hint">{{ readyStoreCount }} 个已就绪</span>
          </article>
        </div>
      </section>

      <!-- 主体两栏：检索工作区 / 侧栏 -->
      <div class="split split--main-side">
        <div class="col gap-lg">
          <!-- 检索工作区 -->
          <section class="card">
            <div class="card-header">
              <div>
                <div class="card-title">
                  <span class="card-title__icon"><AppIcon name="search" :size="16" /></span>
                  检索工作区
                </div>
                <p class="card-subtitle">选择模式 → 输入查询 → 调整参数 → 一键检索</p>
              </div>
            </div>

            <TaskModeTabs
              :model-value="searchStore.mode"
              @update:model-value="searchStore.setMode"
            />

            <div style="height: 14px"></div>

            <SearchHeroInput
              :mode="searchStore.mode"
              :model-value="searchStore.queryText"
              :uploaded-items="searchStore.uploadedQueryImages"
              :batch-mode="searchStore.batchMode"
              :uploading="searchStore.queryImagesUploading"
              @update:model-value="searchStore.queryText = $event"
              @select-files="searchStore.uploadQueryFiles"
              @remove-uploaded="searchStore.removeUploadedQueryImage"
              @clear-uploaded="searchStore.clearUploadedQueryImages"
            />

            <div style="height: 14px"></div>

            <SearchFilterBar
              :store-type="searchStore.storeType"
              :selected-store-id="searchStore.selectedStoreId"
              :store-options="searchStore.filteredStores"
              :stores-loading="searchStore.storesLoading"
              :top-k="searchStore.topK"
              :sort-by="searchStore.sortBy"
              :loading="searchStore.searchState === 'searching' || searchStore.searchState === 'validating'"
              @update:store-type="searchStore.storeType = $event as any"
              @update:selected-store-id="searchStore.selectedStoreId = $event"
              @update:top-k="searchStore.topK = $event"
              @update:sort-by="searchStore.sortBy = $event as any"
              @toggle-advanced="searchStore.advancedOpen = !searchStore.advancedOpen"
              @search="searchStore.runSearch"
            />

            <AdvancedFilterDropdown
              :open="searchStore.advancedOpen"
              :mode="searchStore.mode"
              :model-alias="searchStore.modelAlias"
              :batch-mode="searchStore.batchMode"
              :return-detail-meta="searchStore.returnDetailMeta"
              :auto-prepare="searchStore.autoPrepare"
              :uncertainty-weight="searchStore.uncertaintyWeight"
              @update:model-alias="searchStore.modelAlias = $event"
              @update:batch-mode="searchStore.batchMode = $event"
              @update:return-detail-meta="searchStore.returnDetailMeta = $event"
              @update:auto-prepare="searchStore.autoPrepare = $event"
              @update:uncertainty-weight="searchStore.uncertaintyWeight = $event"
            />
          </section>

          <ErrorBanner :message="searchStore.errorMessage || searchStore.storesError" @retry="handleRetry" />

          <template v-if="searchStore.searchState !== 'idle'">
            <ResultToolbar
              :result-count="searchStore.resultCount"
              :view-mode="searchStore.viewMode"
              :status-message="searchStore.statusMessage"
              @update:view-mode="searchStore.toggleView"
            />
          </template>

          <LoadingBlock
            v-if="searchStore.searchState === 'searching' || searchStore.searchState === 'validating'"
            :count="8"
          />

          <template v-else-if="searchStore.searchState === 'success'">
            <ResultGrid
              v-if="searchStore.viewMode === 'grid'"
              :items="visibleResults"
              :index-offset="pageStartIndex"
              @view="searchStore.openDetail"
            />
            <ResultRankFlow
              v-else
              :items="visibleResults"
              :index-offset="pageStartIndex"
              @view="searchStore.openDetail"
            />

            <section v-if="paginationVisible" class="pagination" aria-label="结果分页">
              <div class="pagination__info">
                <strong>第 {{ currentPage }} / {{ totalPages }} 页</strong>
                ，显示 {{ pageStartIndex + 1 }} - {{ pageEndIndex }} 条，共 {{ searchStore.resultCount }} 条
              </div>
              <div class="pagination__controls">
                <button
                  type="button"
                  class="btn btn--sm btn--secondary"
                  :disabled="currentPage === 1"
                  @click="goToPage(currentPage - 1)"
                >
                  <AppIcon name="arrow_left" class="btn__icon" /> 上一页
                </button>
                <button
                  v-for="page in pageButtons"
                  :key="page"
                  type="button"
                  class="page-chip"
                  :class="{ 'is-active': page === currentPage }"
                  @click="goToPage(page)"
                >
                  {{ page }}
                </button>
                <button
                  type="button"
                  class="btn btn--sm btn--secondary"
                  :disabled="currentPage === totalPages"
                  @click="goToPage(currentPage + 1)"
                >
                  下一页 <AppIcon name="arrow_right" class="btn__icon" />
                </button>
              </div>
            </section>
          </template>

          <EmptyState
            v-else-if="searchStore.searchState === 'empty'"
            icon="inbox"
            title="暂无匹配结果"
            :description="searchStore.statusMessage || '请调整查询关键词、TopK 或更换检索库后再试一次。'"
          />

          <EmptyState
            v-else-if="searchStore.searchState === 'idle'"
            icon="zap"
            title="开始你的第一次检索"
            description="在上方输入文本或上传图片，选择检索库后点击「开始检索」即可获得 Top-K 相似结果。"
          />
        </div>

        <!-- 侧栏 -->
        <aside class="col gap-lg">
          <section class="focus-card">
            <div class="card-header" style="margin-bottom: 0">
              <div>
                <div class="card-title">
                  <span class="card-title__icon"><AppIcon name="cube" :size="16" /></span>
                  当前检索库
                </div>
                <p class="card-subtitle">展示当前选中的库状态与规模</p>
              </div>
              <button type="button" class="btn btn--ghost btn--sm" @click="searchStore.fetchStores">
                <AppIcon name="refresh" class="btn__icon" />
                刷新
              </button>
            </div>

            <template v-if="searchStore.selectedStore">
              <div class="focus-card__head">
                <div class="focus-card__name">
                  {{ searchStore.selectedStore.store_name }}
                  <span class="badge" :class="`is-${searchStore.selectedStore.status}`">
                    {{ searchStore.selectedStoreStatusText }}
                  </span>
                </div>
                <div class="focus-card__id">{{ searchStore.selectedStore.store_id }}</div>
              </div>

              <div class="focus-card__pills">
                <span class="pill">{{ storeTypeToChinese(searchStore.selectedStore.store_type) }}</span>
                <span class="pill pill--soft">{{ searchStore.selectedStore.model_alias }}</span>
                <span class="pill pill--accent">{{ sceneToChinese(searchStore.selectedStore.scene) }}</span>
              </div>

              <div class="focus-card__desc">{{ searchStore.selectedStoreDescription }}</div>

              <div class="focus-card__grid">
                <div class="focus-card__cell">
                  <span class="focus-card__cell-label">最近更新</span>
                  <span class="focus-card__cell-value">{{ searchStore.selectedStoreUpdatedLabel }}</span>
                </div>
                <div class="focus-card__cell">
                  <span class="focus-card__cell-label">文件数</span>
                  <span class="focus-card__cell-value">{{ searchStore.selectedStoreFileCount }}</span>
                </div>
                <div class="focus-card__cell">
                  <span class="focus-card__cell-label">向量数</span>
                  <span class="focus-card__cell-value">{{ searchStore.selectedStoreVectorCount }}</span>
                </div>
                <div class="focus-card__cell">
                  <span class="focus-card__cell-label">检索状态</span>
                  <span class="focus-card__cell-value">{{ searchStore.selectedStoreStatusText }}</span>
                </div>
                <div v-if="searchStore.selectedStorePreprocessMode !== '--'" class="focus-card__cell">
                  <span class="focus-card__cell-label">LongVideo 预处理</span>
                  <span class="focus-card__cell-value">{{ searchStore.selectedStorePreprocessMode }}</span>
                </div>
                <div v-if="searchStore.selectedStoreIntervalSec !== '--'" class="focus-card__cell">
                  <span class="focus-card__cell-label">处理间隔</span>
                  <span class="focus-card__cell-value">{{ searchStore.selectedStoreIntervalSec }}</span>
                </div>
              </div>
            </template>

            <EmptyState
              v-else
              icon="inbox"
              title="当前没有可选检索库"
              :description="searchStore.storesError || '请先在「资源准备」创建该模式 + 库类型的检索库。'"
            />
          </section>

          <section class="tips-card">
            <div class="tips-card__title">
              <AppIcon name="info" :size="16" />
              使用提示
            </div>
            <ul class="tips-list">
              <li>先选择模式与库类型，再挑选具体检索库。</li>
              <li>图搜图请先上传查询图片再开始检索。</li>
              <li>若检索库未就绪，可在高级筛选开启「自动准备」。</li>
              <li>支持网格 / Rank 流双视图，自由切换。</li>
            </ul>
          </section>
        </aside>
      </div>
    </div>

    <ResultDetailModal
      :visible="searchStore.detailModalVisible"
      :item="searchStore.currentDetail"
      :mode="searchStore.mode"
      @close="searchStore.closeDetail"
      @next="searchStore.nextDetail"
      @prev="searchStore.prevDetail"
    />
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import AppLayout from '@/layouts/AppLayout.vue'
import AppIcon from '@/components/icons/AppIcon.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import LoadingBlock from '@/components/common/LoadingBlock.vue'
import AdvancedFilterDropdown from '@/components/search/AdvancedFilterDropdown.vue'
import ResultDetailModal from '@/components/search/ResultDetailModal.vue'
import ResultGrid from '@/components/search/ResultGrid.vue'
import ResultRankFlow from '@/components/search/ResultRankFlow.vue'
import ResultToolbar from '@/components/search/ResultToolbar.vue'
import SearchFilterBar from '@/components/search/SearchFilterBar.vue'
import SearchHeroInput from '@/components/search/SearchHeroInput.vue'
import TaskModeTabs from '@/components/search/TaskModeTabs.vue'
import { useSearchStore } from '@/stores/search'
import { sceneToChinese, storeTypeToChinese } from '@/utils/display'

const searchStore = useSearchStore()

const viewportWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1920)
const currentPage = ref(1)

const readyStoreCount = computed(
  () => searchStore.filteredStores.filter((item) => item.status === 'ready').length,
)

const pageSize = computed(() => {
  const width = viewportWidth.value
  if (searchStore.viewMode === 'rank_flow') {
    if (width >= 2200) return 10
    if (width >= 1800) return 8
    if (width >= 1440) return 6
    if (width >= 1080) return 5
    return 4
  }
  if (width >= 2400) return 16
  if (width >= 1900) return 12
  if (width >= 1536) return 9
  if (width >= 1200) return 6
  if (width >= 900) return 4
  return 3
})

const totalPages = computed(() => Math.max(1, Math.ceil(searchStore.resultCount / pageSize.value)))
const pageStartIndex = computed(() => (currentPage.value - 1) * pageSize.value)
const pageEndIndex = computed(() =>
  Math.min(pageStartIndex.value + pageSize.value, searchStore.resultCount),
)
const visibleResults = computed(() => searchStore.results.slice(pageStartIndex.value, pageEndIndex.value))
const paginationVisible = computed(() => searchStore.resultCount > pageSize.value)

const pageButtons = computed(() => {
  const total = totalPages.value
  if (total <= 7) return Array.from({ length: total }, (_, index) => index + 1)
  const start = Math.max(1, currentPage.value - 2)
  const end = Math.min(total, currentPage.value + 2)
  const pages = new Set([1, total])
  for (let page = start; page <= end; page += 1) pages.add(page)
  return Array.from(pages).sort((a, b) => a - b)
})

function updateViewport() {
  viewportWidth.value = window.innerWidth
}

function goToPage(page: number) {
  currentPage.value = Math.min(Math.max(page, 1), totalPages.value)
  if (typeof window !== 'undefined') {
    window.requestAnimationFrame(() => {
      const toolbar = document.querySelector('.result-toolbar')
      toolbar?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    })
  }
}

watch(
  [() => searchStore.resultCount, () => searchStore.viewMode, pageSize],
  () => {
    currentPage.value = Math.min(currentPage.value, totalPages.value)
    if (searchStore.searchState !== 'success' || currentPage.value < 1) {
      currentPage.value = 1
      return
    }
    if (pageStartIndex.value >= searchStore.resultCount) currentPage.value = 1
  },
  { immediate: true },
)

watch(() => searchStore.results, () => {
  currentPage.value = 1
})

function handleRetry() {
  if (searchStore.storesError) {
    searchStore.fetchStores()
    return
  }
  searchStore.runSearch()
}

onMounted(() => {
  searchStore.fetchStores()
  if (typeof window !== 'undefined') {
    window.addEventListener('resize', updateViewport, { passive: true })
  }
})

onBeforeUnmount(() => {
  if (typeof window !== 'undefined') {
    window.removeEventListener('resize', updateViewport)
  }
})
</script>