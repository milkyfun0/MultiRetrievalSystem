<template>
  <AppLayout>
    <div class="page-stack page-stack--wide">
      <section class="page-banner page-banner--stores glass-panel">
        <div>
          <div class="page-banner__eyebrow">资源管理</div>
          <h1 class="page-banner__title">资源管理面板</h1>
          <p class="page-banner__desc">
            查看检索库详情并执行删除操作
          </p>
        </div>
        <div class="page-banner__meta">
          <article class="page-banner__meta-card">
            <span>当前库数量</span>
            <strong>{{ filteredStores.length }}</strong>
          </article>
          <article class="page-banner__meta-card">
            <span>可用状态</span>
            <strong>{{ readyCount }}</strong>
          </article>
        </div>
      </section>

      <section class="dashboard-metric-grid dashboard-metric-grid--top">
        <article class="dashboard-metric-card glass-panel">
          <span>全部检索库</span>
          <strong>{{ filteredStores.length }}</strong>
        </article>
        <article class="dashboard-metric-card glass-panel">
          <span>可用状态</span>
          <strong>{{ readyCount }}</strong>
        </article>
        <article class="dashboard-metric-card glass-panel">
          <span>长视频库</span>
          <strong>{{ longVideoCount }}</strong>
        </article>
        <article class="dashboard-metric-card glass-panel">
          <span>资源总向量</span>
          <strong>{{ totalVectors }}</strong>
        </article>
      </section>

      <div class="workspace-grid manage-workspace-grid">
        <div class="workspace-main">
          <section class="glass-panel resource-manage-panel">
            <div class="section-title slim compact-title">
              <div>
                <h3>检索库列表</h3>
                <p>按任务模式和库类型筛选现有检索库。</p>
              </div>
              <button type="button" class="ghost-button small" @click="loadStores">刷新列表</button>
            </div>

            <div class="resource-filter-grid">
              <label class="field-block">
                <span>任务模式</span>
                <select v-model="sceneFilter" class="field-control">
                  <option value="">全部</option>
                  <option v-for="scene in SEARCH_MODES" :key="scene" :value="scene">
                    {{ sceneToChinese(scene) }}
                  </option>
                </select>
              </label>

              <label class="field-block">
                <span>检索库类型</span>
                <select v-model="storeTypeFilter" class="field-control">
                  <option value="">全部</option>
                  <option v-for="type in STORE_TYPES" :key="type" :value="type">
                    {{ storeTypeToChinese(type) }}
                  </option>
                </select>
              </label>
            </div>

            <div v-if="bannerMessage" class="tip-banner resource-banner" role="status" aria-live="polite">{{ bannerMessage }}</div>
            <ErrorBanner :message="errorMessage" @retry="loadStores" />

            <div class="resource-table-meta">
              <div>
                <strong>当前结果 {{ filteredStores.length }}</strong>
                <p>按模式与库类型筛选后的管理列表，支持详情查看与删除操作。</p>
              </div>
              <span class="result-meta-pill result-meta-pill--source">总向量 {{ totalVectors }}</span>
            </div>

            <div class="table-wrap refined-table-wrap">
              <table class="task-table refined-task-table store-manage-table">
                <thead>
                  <tr>
                    <th>库名称</th>
                    <th>任务模式</th>
                    <th>库类型</th>
                    <th>状态</th>
                    <th>文件数</th>
                    <th>向量数</th>
                    <th>更新时间</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-if="loading">
                    <td colspan="8" class="empty-cell">检索库加载中...</td>
                  </tr>
                  <tr v-else-if="!filteredStores.length">
                    <td colspan="8" class="empty-cell">暂无检索库，请先前往资源准备创建检索库。</td>
                  </tr>
                  <tr v-for="store in visibleStores" :key="store.store_id">
                    <td>
                      <div class="store-list-name">{{ store.store_name }}</div>
                      <div class="store-list-desc">{{ store.store_description || '暂无备注' }}</div>
                    </td>
                    <td>{{ sceneToChinese(store.scene) }}</td>
                    <td>{{ storeTypeToChinese(store.store_type) }}</td>
                    <td>
                      <StatusBadge :status="store.status" :label="storeStatusToChinese(store.status)" />
                    </td>
                    <td>{{ numberLabel(store.file_count) }}</td>
                    <td>{{ numberLabel(store.vector_count) }}</td>
                    <td>{{ formatDateTime(store.updated_at) }}</td>
                    <td>
                      <div class="table-actions">
                        <button type="button" class="ghost-button small" @click="openDetail(store)">查看详情</button>
                        <button type="button" class="ghost-button small danger-ghost" @click="confirmDelete(store)">删除</button>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <ListPagination
              v-if="storePaginationVisible"
              aria-label="检索库列表分页"
              :current-page="storeCurrentPage"
              :total-pages="storeTotalPages"
              :total="filteredStores.length"
              :start="storePageStart"
              :end="storePageEnd"
              :page-size="storePageSize"
              :page-size-options="storePageSizeOptions"
              @update:page="goToStorePage"
              @update:page-size="updateStorePageSize"
            />
          </section>
        </div>

        <aside class="workspace-side page-sidebar">
          <section class="glass-panel console-info-card sidebar-context-card">
            <div class="section-title slim compact-title">
              <div>
                <h3>当前筛选摘要</h3>
                <p>帮助快速确认列表展示范围，而不改变实际过滤逻辑。</p>
              </div>
            </div>
            <div class="sidebar-context-grid sidebar-context-grid--store">
              <div>
                <span class="metric-label">任务模式</span>
                <strong>{{ sceneFilter ? sceneToChinese(sceneFilter) : '全部' }}</strong>
              </div>
              <div>
                <span class="metric-label">库类型</span>
                <strong>{{ storeTypeFilter ? storeTypeToChinese(storeTypeFilter) : '全部' }}</strong>
              </div>
              <div>
                <span class="metric-label">当前列表数量</span>
                <strong>{{ filteredStores.length }}</strong>
              </div>
              <div>
                <span class="metric-label">总向量数</span>
                <strong>{{ totalVectors }}</strong>
              </div>
            </div>
          </section>

          <section class="glass-panel console-info-card">
            <div class="section-title slim compact-title">
              <div>
                <h3>使用提示</h3>
              </div>
            </div>
            <ul class="tip-list tip-list--divided">
              <li>详情弹窗展示的是的原始库明细字段。</li>
              <li>删除成功后会刷新列表，并保留 提示。</li>
              <li>如当前详情正在打开，删除当前库后会自动关闭详情弹窗。</li>
            </ul>
          </section>
        </aside>
      </div>
    </div>

    <teleport to="body">
      <div v-if="detailVisible && currentStore" class="modal-mask" @click.self="detailVisible = false">
        <div class="task-detail-modal glass-panel refined-task-detail-modal store-detail-modal" role="dialog" aria-modal="true" aria-labelledby="store-detail-title">
          <div class="section-title slim detail-modal__header detail-modal__header--premium">
            <div>
              <h3 id="store-detail-title">检索库详情</h3>
              <p>查看当前检索库的状态、规模与索引信息。</p>
            </div>
            <button type="button" class="icon-close" aria-label="关闭检索库详情" @click="detailVisible = false">×</button>
          </div>

          <div class="store-detail-topbar store-detail-topbar--premium">
            <div class="store-detail-main">
              <strong>{{ currentStore.store_name }}</strong>
              <span>{{ currentStore.store_description || '暂无备注' }}</span>
              <p class="store-detail-main__meta">{{ currentStore.store_id || '--' }}</p>
            </div>
            <div class="detail-pill-row">
              <span class="detail-pill">{{ sceneToChinese(currentStore.scene) }}</span>
              <span class="detail-pill detail-pill--soft">{{ storeTypeToChinese(currentStore.store_type) }}</span>
              <span v-if="currentStore.model_alias" class="detail-pill detail-pill--brand">{{ currentStore.model_alias }}</span>
              <span class="detail-pill detail-pill--state">{{ storeStatusToChinese(currentStore.status) }}</span>
            </div>
          </div>

          <div class="store-detail-hero-grid store-detail-hero-grid--dense">
            <div class="store-detail-stat-card">
              <span>当前状态</span>
              <strong>{{ storeStatusToChinese(currentStore.status) }}</strong>
            </div>
            <div class="store-detail-stat-card">
              <span>当前文件数</span>
              <strong>{{ numberLabel(currentStore.file_count) }}</strong>
            </div>
            <div class="store-detail-stat-card store-detail-stat-card--teal">
              <span>当前向量数</span>
              <strong>{{ numberLabel(currentStore.vector_count) }}</strong>
            </div>
            <div class="store-detail-stat-card">
              <span>最近更新时间</span>
              <strong>{{ formatDateTime(currentStore.updated_at) }}</strong>
            </div>
          </div>

          <div class="store-detail-section-grid store-detail-section-grid--dense">
            <section class="store-detail-section-card">
              <div class="store-detail-section-head">
                <h4>基础标识</h4>
                <p>统一查看库的身份、模式和模型版本。</p>
              </div>
              <div class="store-detail-body-grid">
                <div><strong>检索库 ID</strong><span>{{ currentStore.store_id || '--' }}</span></div>
                <div><strong>模型别名</strong><span>{{ currentStore.model_alias || '--' }}</span></div>
                <div><strong>任务模式</strong><span>{{ sceneToChinese(currentStore.scene) }}</span></div>
                <div><strong>库类型</strong><span>{{ storeTypeToChinese(currentStore.store_type) }}</span></div>
              </div>
            </section>

            <section class="store-detail-section-card">
              <div class="store-detail-section-head">
                <h4>来源与索引</h4>
                <p>聚合查看资源路径、索引标识与向量化载体。</p>
              </div>
              <div class="store-detail-body-grid">
                <div class="store-detail-wide-field"><strong>资源路径 / 标识</strong><span>{{ currentStore.resource_path || '--' }}</span></div>
                <div class="store-detail-wide-field"><strong>当前索引 ID</strong><span>{{ currentStore.current_index_id || '--' }}</span></div>
              </div>
            </section>

            <section class="store-detail-section-card">
              <div class="store-detail-section-head">
                <h4>预处理补充</h4>
                <p>仅在长视频相关库中展示额外配置与时间信息。</p>
              </div>
              <div class="store-detail-body-grid store-detail-body-grid--compact">
                <div v-if="currentStore.preprocess_mode"><strong>LongVideo 预处理</strong><span>{{ preprocessModeToChinese(currentStore.preprocess_mode) }}</span></div>
                <div v-if="typeof currentStore.interval_sec === 'number'"><strong>处理间隔</strong><span>{{ currentStore.interval_sec }} 秒</span></div>
                <div><strong>最近更新时间</strong><span>{{ formatDateTime(currentStore.updated_at) }}</span></div>
              </div>
            </section>
          </div>

          <div class="detail-actions">
            <button type="button" class="ghost-button" @click="detailVisible = false">关闭</button>
          </div>
        </div>
      </div>
    </teleport>
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import AppLayout from '@/layouts/AppLayout.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import ListPagination from '@/components/common/ListPagination.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { deleteStore, getStoreDetail, getStores } from '@/api/stores'
import type { SearchMode, StoreDetailDTO, StoreType } from '@/types'
import { SEARCH_MODES, STORE_TYPES } from '@/utils/constants'
import {
  preprocessModeToChinese,
  sceneToChinese,
  storeStatusToChinese,
  storeTypeToChinese,
} from '@/utils/display'

const loading = ref(false)
const errorMessage = ref('')
const bannerMessage = ref('')
const stores = ref<StoreDetailDTO[]>([])
const detailVisible = ref(false)
const currentStore = ref<StoreDetailDTO | null>(null)
const sceneFilter = ref<SearchMode | ''>('')
const storeTypeFilter = ref<StoreType | ''>('')
const storeCurrentPage = ref(1)
const storePageSize = ref(10)
const storePageSizeOptions = [5, 10, 20, 50]

const filteredStores = computed(() => {
  return stores.value.filter((item) => {
    const sceneOk = !sceneFilter.value || item.scene === sceneFilter.value
    const typeOk = !storeTypeFilter.value || item.store_type === storeTypeFilter.value
    return sceneOk && typeOk
  })
})

const readyCount = computed(() => {
  return filteredStores.value.filter((item) => item.status === 'ready').length
})

const longVideoCount = computed(() => {
  return filteredStores.value.filter((item) => item.store_type === 'LongVideo').length
})

const totalVectors = computed(() => {
  return filteredStores.value.reduce((sum, item) => {
    return sum + (typeof item.vector_count === 'number' ? item.vector_count : 0)
  }, 0)
})

const storeTotalPages = computed(() => Math.max(1, Math.ceil(filteredStores.value.length / storePageSize.value)))
const storePageStart = computed(() => (storeCurrentPage.value - 1) * storePageSize.value)
const storePageEnd = computed(() => Math.min(storePageStart.value + storePageSize.value, filteredStores.value.length))
const visibleStores = computed(() => filteredStores.value.slice(storePageStart.value, storePageEnd.value))
const storePaginationVisible = computed(() => filteredStores.value.length > storePageSize.value)

function goToStorePage(page: number) {
  storeCurrentPage.value = Math.min(Math.max(page, 1), storeTotalPages.value)
}

function updateStorePageSize(size: number) {
  storePageSize.value = size
  storeCurrentPage.value = 1
}

function formatDateTime(value?: string) {
  if (!value) return '--'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false })
}

function numberLabel(value?: number) {
  return typeof value === 'number' ? value : '--'
}

async function loadStores() {
  loading.value = true
  errorMessage.value = ''
  try {
    const { data } = await getStores()
    const details = await Promise.all(
      (data.items || []).map(async (item) => {
        try {
          const detailResp = await getStoreDetail(item.store_id)
          return { ...item, ...detailResp.data }
        } catch {
          return item as StoreDetailDTO
        }
      }),
    )
    stores.value = details
  } catch (error: any) {
    errorMessage.value = error?.response?.data?.message || error?.message || '检索库加载失败。'
    stores.value = []
  } finally {
    loading.value = false
  }
}

function openDetail(store: StoreDetailDTO) {
  currentStore.value = store
  detailVisible.value = true
}

async function confirmDelete(store: StoreDetailDTO) {
  const ok = window.confirm(
    `确定删除检索库“${store.store_name}”吗？\n\n删除后会同步清理索引文件与映射关系，且该操作不可恢复。`,
  )
  if (!ok) return

  try {
    const { data } = await deleteStore(store.store_id)
    bannerMessage.value = data.message || '检索库已删除。'
    if (currentStore.value?.store_id === store.store_id) {
      detailVisible.value = false
      currentStore.value = null
    }
    await loadStores()
  } catch (error: any) {
    errorMessage.value = error?.response?.data?.message || error?.message || '删除检索库失败。'
  }
}

watch([filteredStores, storePageSize], () => {
  storeCurrentPage.value = Math.min(storeCurrentPage.value, storeTotalPages.value)
  if (storePageStart.value >= filteredStores.value.length) storeCurrentPage.value = 1
}, { immediate: true })

watch([sceneFilter, storeTypeFilter], () => {
  storeCurrentPage.value = 1
})

onMounted(() => {
  loadStores()
})
</script>
