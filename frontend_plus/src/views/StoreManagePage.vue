<template>
  <AppLayout>
    <div class="page-stack">
      <!-- Hero -->
      <section class="hero-banner">
        <div class="hero-banner__content">
          <span class="hero-banner__eyebrow">
            <AppIcon name="layers" :size="12" />
            Knowledge · Store Manager
          </span>
          <h1 class="hero-banner__title">资源管理面板</h1>
          <p class="hero-banner__desc">
            查看全部检索库的状态、规模与索引明细，支持快速筛选与安全删除。
            管理一站式触手可得，让海量知识库始终保持整洁与可控。
          </p>
        </div>
        <div class="hero-banner__meta">
          <article class="hero-stat">
            <span class="hero-stat__label">检索库数量</span>
            <span class="hero-stat__value">{{ filteredStores.length }}</span>
            <span class="hero-stat__hint">已应用当前筛选</span>
          </article>
          <article class="hero-stat">
            <span class="hero-stat__label">已就绪</span>
            <span class="hero-stat__value">{{ readyCount }}</span>
            <span class="hero-stat__hint">可直接用于检索</span>
          </article>
        </div>
      </section>

      <!-- Stats -->
      <section class="metric-grid">
        <article class="metric-card">
          <div class="metric-card__icon"><AppIcon name="cube" :size="20" /></div>
          <div class="metric-card__label">全部检索库</div>
          <div class="metric-card__value">{{ filteredStores.length }}</div>
        </article>
        <article class="metric-card">
          <div class="metric-card__icon is-success"><AppIcon name="check_circle" :size="20" /></div>
          <div class="metric-card__label">已就绪</div>
          <div class="metric-card__value">{{ readyCount }}</div>
        </article>
        <article class="metric-card">
          <div class="metric-card__icon is-info"><AppIcon name="film" :size="20" /></div>
          <div class="metric-card__label">长视频库</div>
          <div class="metric-card__value">{{ longVideoCount }}</div>
        </article>
        <article class="metric-card">
          <div class="metric-card__icon is-warning"><AppIcon name="database" :size="20" /></div>
          <div class="metric-card__label">向量总数</div>
          <div class="metric-card__value">{{ totalVectors }}</div>
        </article>
      </section>

      <div class="split split--main-side">
        <div class="col gap-lg">
          <section class="card">
            <div class="card-header">
              <div>
                <div class="card-title">
                  <span class="card-title__icon"><AppIcon name="list" :size="16" /></span>
                  检索库列表
                </div>
                <p class="card-subtitle">按任务模式与库类型筛选现有检索库</p>
              </div>
              <button type="button" class="btn btn--secondary btn--sm" @click="loadStores">
                <AppIcon name="refresh" class="btn__icon" />
                刷新
              </button>
            </div>

            <div class="form-grid" style="margin-bottom: 14px;">
              <label class="field">
                <span class="field__label">任务模式</span>
                <select v-model="sceneFilter" class="control control--select">
                  <option value="">全部模式</option>
                  <option v-for="scene in SEARCH_MODES" :key="scene" :value="scene">
                    {{ sceneToChinese(scene) }}
                  </option>
                </select>
              </label>
              <label class="field">
                <span class="field__label">库类型</span>
                <select v-model="storeTypeFilter" class="control control--select">
                  <option value="">全部类型</option>
                  <option v-for="type in STORE_TYPES" :key="type" :value="type">
                    {{ storeTypeToChinese(type) }}
                  </option>
                </select>
              </label>
            </div>

            <div v-if="bannerMessage" class="error-banner" style="background: var(--color-success-soft); border-color: rgba(16,185,129,.2); color: #065f46;">
              <div class="error-banner__icon" style="background: rgba(16,185,129,.15); color: var(--color-success);">
                <AppIcon name="check_circle" :size="18" />
              </div>
              <div class="error-banner__msg">{{ bannerMessage }}</div>
            </div>
            <ErrorBanner :message="errorMessage" @retry="loadStores" />

            <div class="table-wrap" style="margin-top: 12px;">
              <table class="table">
                <thead>
                  <tr>
                    <th>库名称</th>
                    <th>模式</th>
                    <th>库类型</th>
                    <th>状态</th>
                    <th>文件数</th>
                    <th>向量数</th>
                    <th>更新时间</th>
                    <th style="text-align: right;">操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-if="loading">
                    <td colspan="8" class="table__empty">检索库加载中…</td>
                  </tr>
                  <tr v-else-if="!filteredStores.length">
                    <td colspan="8" class="table__empty">
                      暂无检索库，请先前往「资源准备」创建检索库。
                    </td>
                  </tr>
                  <tr v-for="store in visibleStores" :key="store.store_id">
                    <td>
                      <div class="table__title">{{ store.store_name }}</div>
                      <div class="table__sub">{{ store.store_description || '暂无备注' }}</div>
                    </td>
                    <td>{{ sceneToChinese(store.scene) }}</td>
                    <td>{{ storeTypeToChinese(store.store_type) }}</td>
                    <td>
                      <StatusBadge :status="store.status" :label="storeStatusToChinese(store.status)" />
                    </td>
                    <td>{{ numberLabel(store.file_count) }}</td>
                    <td>{{ numberLabel(store.vector_count) }}</td>
                    <td><span class="text-muted text-sm">{{ formatDateTime(store.updated_at) }}</span></td>
                    <td>
                      <div class="table__actions" style="justify-content: flex-end; display: flex;">
                        <button type="button" class="btn btn--sm btn--ghost" @click="openDetail(store)">
                          <AppIcon name="eye" class="btn__icon" />
                          详情
                        </button>
                        <button type="button" class="btn btn--sm btn--danger" @click="confirmDelete(store)">
                          <AppIcon name="trash" class="btn__icon" />
                          删除
                        </button>
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

        <aside class="col gap-lg">
          <section class="focus-card">
            <div class="card-header" style="margin-bottom: 0;">
              <div>
                <div class="card-title">
                  <span class="card-title__icon"><AppIcon name="filter" :size="16" /></span>
                  筛选摘要
                </div>
                <p class="card-subtitle">当前列表的过滤口径与统计</p>
              </div>
            </div>
            <div class="focus-card__grid">
              <div class="focus-card__cell">
                <span class="focus-card__cell-label">任务模式</span>
                <span class="focus-card__cell-value">{{ sceneFilter ? sceneToChinese(sceneFilter) : '全部' }}</span>
              </div>
              <div class="focus-card__cell">
                <span class="focus-card__cell-label">库类型</span>
                <span class="focus-card__cell-value">{{ storeTypeFilter ? storeTypeToChinese(storeTypeFilter) : '全部' }}</span>
              </div>
              <div class="focus-card__cell">
                <span class="focus-card__cell-label">列表数量</span>
                <span class="focus-card__cell-value">{{ filteredStores.length }}</span>
              </div>
              <div class="focus-card__cell">
                <span class="focus-card__cell-label">向量总数</span>
                <span class="focus-card__cell-value">{{ totalVectors }}</span>
              </div>
            </div>
          </section>

          <section class="tips-card">
            <div class="tips-card__title">
              <AppIcon name="info" :size="16" />
              使用提示
            </div>
            <ul class="tips-list">
              <li>详情弹窗展示完整的库元数据与索引明细。</li>
              <li>删除成功后会自动刷新列表并保留操作提示。</li>
              <li>若当前正打开详情，删除该库会自动关闭弹窗。</li>
              <li>删除会同步清理索引文件，操作不可恢复，请谨慎。</li>
            </ul>
          </section>
        </aside>
      </div>
    </div>

    <!-- Detail Modal -->
    <teleport to="body">
      <div v-if="detailVisible && currentStore" class="modal-mask" @click.self="detailVisible = false">
        <div class="modal modal--lg" role="dialog" aria-modal="true">
          <div class="modal__header">
            <div>
              <div class="modal__title">检索库详情</div>
              <div class="modal__subtitle">查看库的状态、规模与索引信息</div>
            </div>
            <button class="modal__close" type="button" aria-label="关闭" @click="detailVisible = false">
              <AppIcon name="x" :size="18" />
            </button>
          </div>

          <div class="modal__body">
            <!-- Topbar -->
            <div class="focus-card" style="margin-bottom: 16px;">
              <div class="focus-card__head">
                <div class="focus-card__name">
                  {{ currentStore.store_name }}
                  <StatusBadge :status="currentStore.status" :label="storeStatusToChinese(currentStore.status)" />
                </div>
                <div class="focus-card__id">ID · {{ currentStore.store_id || '--' }}</div>
              </div>
              <div class="focus-card__pills">
                <span class="pill">{{ sceneToChinese(currentStore.scene) }}</span>
                <span class="pill pill--soft">{{ storeTypeToChinese(currentStore.store_type) }}</span>
                <span v-if="currentStore.model_alias" class="pill pill--accent">{{ currentStore.model_alias }}</span>
              </div>
              <div class="focus-card__desc">{{ currentStore.store_description || '暂无备注' }}</div>
            </div>

            <!-- Stats -->
            <div class="metric-grid">
              <article class="metric-card">
                <div class="metric-card__icon"><AppIcon name="pulse" :size="20" /></div>
                <div class="metric-card__label">当前状态</div>
                <div class="metric-card__value" style="font-size: 20px;">{{ storeStatusToChinese(currentStore.status) }}</div>
              </article>
              <article class="metric-card">
                <div class="metric-card__icon is-info"><AppIcon name="folder" :size="20" /></div>
                <div class="metric-card__label">文件数</div>
                <div class="metric-card__value">{{ numberLabel(currentStore.file_count) }}</div>
              </article>
              <article class="metric-card">
                <div class="metric-card__icon is-success"><AppIcon name="database" :size="20" /></div>
                <div class="metric-card__label">向量数</div>
                <div class="metric-card__value">{{ numberLabel(currentStore.vector_count) }}</div>
              </article>
              <article class="metric-card">
                <div class="metric-card__icon is-warning"><AppIcon name="clock" :size="20" /></div>
                <div class="metric-card__label">最近更新</div>
                <div class="metric-card__value" style="font-size: 16px;">{{ formatDateTime(currentStore.updated_at) }}</div>
              </article>
            </div>

            <!-- Identity -->
            <div class="section-title" style="margin-top: 20px; margin-bottom: 10px;">
              <h2><AppIcon name="info" :size="14" /> 基础标识</h2>
            </div>
            <div class="form-grid">
              <div class="card card--inset" style="padding: 14px 16px;">
                <div class="text-muted text-xs" style="letter-spacing: 1px; text-transform: uppercase;">检索库 ID</div>
                <div class="font-mono" style="margin-top: 6px; word-break: break-all;">{{ currentStore.store_id || '--' }}</div>
              </div>
              <div class="card card--inset" style="padding: 14px 16px;">
                <div class="text-muted text-xs" style="letter-spacing: 1px; text-transform: uppercase;">模型别名</div>
                <div style="margin-top: 6px;">{{ currentStore.model_alias || '--' }}</div>
              </div>
              <div class="card card--inset" style="padding: 14px 16px;">
                <div class="text-muted text-xs" style="letter-spacing: 1px; text-transform: uppercase;">任务模式</div>
                <div style="margin-top: 6px;">{{ sceneToChinese(currentStore.scene) }}</div>
              </div>
              <div class="card card--inset" style="padding: 14px 16px;">
                <div class="text-muted text-xs" style="letter-spacing: 1px; text-transform: uppercase;">库类型</div>
                <div style="margin-top: 6px;">{{ storeTypeToChinese(currentStore.store_type) }}</div>
              </div>
            </div>

            <!-- Source & Index -->
            <div class="section-title" style="margin-top: 20px; margin-bottom: 10px;">
              <h2><AppIcon name="folder" :size="14" /> 来源与索引</h2>
            </div>
            <div class="form-grid">
              <div class="card card--inset field--full" style="padding: 14px 16px;">
                <div class="text-muted text-xs" style="letter-spacing: 1px; text-transform: uppercase;">资源路径 / 标识</div>
                <div class="font-mono" style="margin-top: 6px; word-break: break-all;">{{ currentStore.resource_path || '--' }}</div>
              </div>
              <div class="card card--inset field--full" style="padding: 14px 16px;">
                <div class="text-muted text-xs" style="letter-spacing: 1px; text-transform: uppercase;">当前索引 ID</div>
                <div class="font-mono" style="margin-top: 6px; word-break: break-all;">{{ currentStore.current_index_id || '--' }}</div>
              </div>
            </div>

            <!-- LongVideo -->
            <div
              v-if="currentStore.preprocess_mode || typeof currentStore.interval_sec === 'number'"
              class="section-title"
              style="margin-top: 20px; margin-bottom: 10px;"
            >
              <h2><AppIcon name="film" :size="14" /> 预处理补充</h2>
            </div>
            <div
              v-if="currentStore.preprocess_mode || typeof currentStore.interval_sec === 'number'"
              class="form-grid"
            >
              <div v-if="currentStore.preprocess_mode" class="card card--inset" style="padding: 14px 16px;">
                <div class="text-muted text-xs" style="letter-spacing: 1px; text-transform: uppercase;">LongVideo 预处理</div>
                <div style="margin-top: 6px;">{{ preprocessModeToChinese(currentStore.preprocess_mode) }}</div>
              </div>
              <div v-if="typeof currentStore.interval_sec === 'number'" class="card card--inset" style="padding: 14px 16px;">
                <div class="text-muted text-xs" style="letter-spacing: 1px; text-transform: uppercase;">处理间隔</div>
                <div style="margin-top: 6px;">{{ currentStore.interval_sec }} 秒</div>
              </div>
            </div>
          </div>

          <div class="modal__footer">
            <button type="button" class="btn btn--ghost" @click="detailVisible = false">关闭</button>
          </div>
        </div>
      </div>
    </teleport>
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import AppLayout from '@/layouts/AppLayout.vue'
import AppIcon from '@/components/icons/AppIcon.vue'
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

const filteredStores = computed(() =>
  stores.value.filter((item) => {
    const sceneOk = !sceneFilter.value || item.scene === sceneFilter.value
    const typeOk = !storeTypeFilter.value || item.store_type === storeTypeFilter.value
    return sceneOk && typeOk
  }),
)

const readyCount = computed(
  () => filteredStores.value.filter((item) => item.status === 'ready').length,
)
const longVideoCount = computed(
  () => filteredStores.value.filter((item) => item.store_type === 'LongVideo').length,
)
const totalVectors = computed(() =>
  filteredStores.value.reduce(
    (sum, item) => sum + (typeof item.vector_count === 'number' ? item.vector_count : 0),
    0,
  ),
)

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
    `确定删除检索库「${store.store_name}」吗？\n\n删除后会同步清理索引文件与映射关系，且该操作不可恢复。`,
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