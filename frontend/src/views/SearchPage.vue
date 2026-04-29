<template>
  <AppLayout>
    <div class="page-stack page-stack--wide">
      <section class="page-banner page-banner--search glass-panel">
        <div>
          <div class="page-banner__eyebrow">多模态统一检索入口</div>
          <h1 class="page-banner__title">多模态检索工作台</h1>
          <p class="page-banner__desc">
            支持用户文本检索图像、视频与以图搜图
          </p>
        </div>
        <div class="page-banner__meta">
          <article class="page-banner__meta-card">
            <span>当前模式</span>
            <strong>{{ sceneToChinese(searchStore.mode) }}</strong>
          </article>
          <article class="page-banner__meta-card">
            <span>可用库数量</span>
            <strong>{{ searchStore.filteredStores.length }}</strong>
          </article>
        </div>
      </section>

      <div class="workspace-grid search-workspace-grid">
        <div class="workspace-main search-main-stack">
          <section class="search-command-card glass-panel">
            <div class="section-title slim compact-title">
              <div>
                <h3>检索工作区</h3>
                <p>先选择模式并输入查询，再筛选具体检索库与参数。</p>
              </div>
            </div>

            <TaskModeTabs :model-value="searchStore.mode" @update:model-value="searchStore.setMode" />

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

          <LoadingBlock v-if="searchStore.searchState === 'searching' || searchStore.searchState === 'validating'" :count="6" />

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

            <section v-if="paginationVisible" class="result-pagination glass-panel" aria-label="检索结果分页">
              <div class="result-pagination__summary">
                <div>
                  <strong>第 {{ currentPage }} / {{ totalPages }} 页</strong>
                  <p>当前显示 {{ pageStartIndex + 1 }} - {{ pageEndIndex }} 条，共 {{ searchStore.resultCount }} 条结果。</p>
                </div>
                <div class="result-pagination__meta">
                  <span class="result-meta-pill result-meta-pill--type">每页 {{ pageSize }} 条</span>
                  <span class="result-meta-pill result-meta-pill--source">已显示 {{ pageEndIndex }}/{{ searchStore.resultCount }}</span>
                </div>
              </div>

              <div class="result-pagination__progress" aria-hidden="true">
                <div class="result-pagination__progress-bar" :style="{ width: `${paginationProgress}%` }"></div>
              </div>

              <div class="result-pagination__controls">
                <button type="button" class="ghost-button small" :disabled="currentPage === 1" @click="goToPage(currentPage - 1)">上一页</button>
                <div class="result-pagination__pages">
                  <button
                    v-for="page in pageButtons"
                    :key="page"
                    type="button"
                    class="page-chip"
                    :class="{ active: page === currentPage }"
                    @click="goToPage(page)"
                  >
                    {{ page }}
                  </button>
                </div>
                <button type="button" class="ghost-button small" :disabled="currentPage === totalPages" @click="goToPage(currentPage + 1)">下一页</button>
              </div>
            </section>
          </template>

          <EmptyState
            v-else-if="searchStore.searchState === 'empty'"
            title="暂无结果"
            :description="searchStore.statusMessage || '当前没有匹配结果，或检索库尚未准备完成。'"
          />
        </div>

        <aside class="workspace-side page-sidebar">
          <div class="store-focus-card glass-panel refined-store-card">
            <div class="section-title slim compact-title">
              <div>
                <h3>当前检索库</h3>
                <p>集中展示可用于检索的关键信息。</p>
              </div>
              <button type="button" class="ghost-button small" @click="searchStore.fetchStores">刷新列表</button>
            </div>

            <div v-if="searchStore.selectedStore" class="store-focus-body">
              <div class="store-main">
                <div>
                  <div class="store-name-row">
                    <strong class="store-name">{{ searchStore.selectedStore.store_name }}</strong>
                    <span class="status-badge" :class="`is-${searchStore.selectedStore.status}`">{{ searchStore.selectedStoreStatusText }}</span>
                  </div>
                  <p class="store-meta-line">{{ searchStore.selectedStore.store_id }}</p>
                </div>
                <div class="store-tags">
                  <span class="pill-tag">{{ storeTypeToChinese(searchStore.selectedStore.store_type) }}</span>
                  <span class="pill-tag">{{ searchStore.selectedStore.model_alias }}</span>
                  <span class="pill-tag">{{ sceneToChinese(searchStore.selectedStore.scene) }}</span>
                </div>
              </div>

              <div class="store-note-card">
                <span class="metric-label">备注</span>
                <p>{{ searchStore.selectedStoreDescription }}</p>
              </div>

              <div class="store-detail-grid refined-store-detail-grid">
                <div>
                  <span class="metric-label">最近更新时间</span>
                  <strong>{{ searchStore.selectedStoreUpdatedLabel }}</strong>
                </div>
                <div>
                  <span class="metric-label">检索状态</span>
                  <strong>{{ searchStore.selectedStoreStatusText }}</strong>
                </div>
                <div>
                  <span class="metric-label">当前文件数</span>
                  <strong>{{ searchStore.selectedStoreFileCount }}</strong>
                </div>
                <div>
                  <span class="metric-label">当前向量数</span>
                  <strong>{{ searchStore.selectedStoreVectorCount }}</strong>
                </div>
                <div v-if="searchStore.selectedStorePreprocessMode !== '--'">
                  <span class="metric-label">LongVideo 预处理</span>
                  <strong>{{ searchStore.selectedStorePreprocessMode }}</strong>
                </div>
                <div v-if="searchStore.selectedStoreIntervalSec !== '--'">
                  <span class="metric-label">处理间隔</span>
                  <strong>{{ searchStore.selectedStoreIntervalSec }}</strong>
                </div>
              </div>
            </div>

            <EmptyState
              v-else
              title="当前没有可选检索库"
              :description="searchStore.storesError || '请先在资源准备页创建并准备对应 scene 和 store_type 的检索库。'"
            />
          </div>

<!--          <div class="tip-card glass-panel refined-tip-card sidebar-context-card">-->
<!--            <div class="section-title slim compact-title">-->
<!--              <div>-->
<!--                <h3>检索上下文</h3>-->
<!--                <p>把当前模式、结果视图和检索策略集中到侧栏，减少主区信息干扰。</p>-->
<!--              </div>-->
<!--            </div>-->
<!--            <div class="sidebar-context-grid sidebar-context-grid&#45;&#45;search">-->
<!--              <div>-->
<!--                <span class="metric-label">当前模式</span>-->
<!--                <strong>{{ sceneToChinese(searchStore.mode) }}</strong>-->
<!--              </div>-->
<!--              <div>-->
<!--                <span class="metric-label">库类型</span>-->
<!--                <strong>{{ storeTypeToChinese(searchStore.storeType) }}</strong>-->
<!--              </div>-->
<!--              <div>-->
<!--                <span class="metric-label">结果视图</span>-->
<!--                <strong>{{ searchStore.viewMode === 'grid' ? '网格卡片' : 'Rank 流' }}</strong>-->
<!--              </div>-->
<!--              <div>-->
<!--                <span class="metric-label">TopK</span>-->
<!--                <strong>{{ searchStore.topK }}</strong>-->
<!--              </div>-->
<!--              <div>-->
<!--                <span class="metric-label">排序方式</span>-->
<!--                <strong>{{ sortByText(searchStore.sortBy) }}</strong>-->
<!--              </div>-->
<!--              <div>-->
<!--                <span class="metric-label">自动准备</span>-->
<!--                <strong>{{ searchStore.autoPrepare ? '已开启' : '未开启' }}</strong>-->
<!--              </div>-->
<!--            </div>-->
<!--          </div>-->

          <div class="glass-panel console-info-card">
            <div class="section-title slim compact-title">
              <div>
                <h3>使用提示</h3>
              </div>
            </div>
            <ul class="tip-list tip-list--divided">
              <li>先选文件夹或长视频，再选具体检索库。</li>
              <li>具体检索库来自后台建立。</li>
              <li>图搜图查询采用先上传图片。</li>
              <li>若当前库未就绪，可在资源准备中完成建库，或开启自动准备。</li>
            </ul>
          </div>

          <div class="tip-banner refined-tip-banner tip-banner--search">
            当前检索库若未完成向量化，建议先前往资源准备建立索引。
          </div>
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

const totalPages = computed(() => {
  return Math.max(1, Math.ceil(searchStore.resultCount / pageSize.value))
})

const pageStartIndex = computed(() => {
  return (currentPage.value - 1) * pageSize.value
})

const pageEndIndex = computed(() => {
  return Math.min(pageStartIndex.value + pageSize.value, searchStore.resultCount)
})

const visibleResults = computed(() => {
  return searchStore.results.slice(pageStartIndex.value, pageEndIndex.value)
})

const paginationVisible = computed(() => searchStore.resultCount > pageSize.value)

const paginationProgress = computed(() => {
  if (!searchStore.resultCount) return 0
  return Math.round((pageEndIndex.value / searchStore.resultCount) * 100)
})

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
    if (pageStartIndex.value >= searchStore.resultCount) {
      currentPage.value = 1
    }
  },
  { immediate: true },
)

watch(
  () => searchStore.results,
  () => {
    currentPage.value = 1
  },
)

function sortByText(value: string) {
  if (value === 'score_desc') return '相似度优先'
  return value
}

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
