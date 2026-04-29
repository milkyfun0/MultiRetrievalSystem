import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { getStoreDetail, getStores, postSearch, uploadQueryImage } from '@/api'
import type {
  SearchMode,
  SearchRequestDTO,
  SearchResponseDTO,
  SearchResultCardVM,
  SearchState,
  StoreDetailDTO,
  StoreItemDTO,
  StoreType,
  UploadedQueryImageVM,
  ViewMode,
} from '@/types'
import { mapSearchResultToCard } from '@/utils/mapper'
import { preprocessModeToChinese } from '@/utils/display'
import { splitLinesToItems } from '@/utils/normalize'

function pickDefaultStore(stores: StoreItemDTO[]) {
  return stores.find((item) => item.status === 'ready') || stores[0] || null
}

export const useSearchStore = defineStore('search', () => {
  const mode = ref<SearchMode>('Text2Video')
  const storeType = ref<StoreType>('Folder')
  const selectedStoreId = ref('')
  const topK = ref(10)
  const sortBy = ref<'score_desc'>('score_desc')
  const advancedOpen = ref(false)
  const viewMode = ref<ViewMode>('grid')
  const searchState = ref<SearchState>('idle')

  const queryText = ref('')
  const uploadedQueryImages = ref<UploadedQueryImageVM[]>([])
  const queryImagesUploading = ref(false)
  const batchMode = ref(false)
  const modelAlias = ref('prod')
  const returnDetailMeta = ref(false)
  const uncertaintyWeight = ref(0.6)
  const autoPrepare = ref(true)

  const storesLoading = ref(false)
  const storesError = ref('')
  const allStores = ref<StoreItemDTO[]>([])
  const selectedStoreDetail = ref<StoreDetailDTO | null>(null)

  const resultCount = ref(0)
  const results = ref<SearchResultCardVM[]>([])
  const rawResponse = ref<SearchResponseDTO | null>(null)
  const errorMessage = ref('')
  const statusMessage = ref('')

  const detailModalVisible = ref(false)
  const detailCurrentIndex = ref(0)

  const imageObjectKeys = computed(() => uploadedQueryImages.value.map((item) => item.objectKey))

  const filteredStores = computed(() =>
    allStores.value.filter((item) => item.scene === mode.value && item.store_type === storeType.value),
  )

  const selectedStore = computed(
    () => filteredStores.value.find((item) => item.store_id === selectedStoreId.value) || null,
  )

  const selectedStoreStatusText = computed(() => {
    switch (selectedStore.value?.status) {
      case 'ready':
        return '已就绪'
      case 'preparing':
        return '准备中'
      case 'failed':
        return '失败'
      case 'not_ready':
        return '未准备'
      default:
        return '未选择'
    }
  })

  const selectedStoreUpdatedLabel = computed(() => {
    if (!selectedStore.value?.updated_at) return '--'
    const date = new Date(selectedStore.value.updated_at)
    if (Number.isNaN(date.getTime())) return selectedStore.value.updated_at
    return date.toLocaleString('zh-CN', { hour12: false })
  })

  const selectedStoreDescription = computed(() => {
    return selectedStoreDetail.value?.store_description || selectedStore.value?.store_description || '暂无备注'
  })

  const selectedStoreFileCount = computed(() => {
    const value = selectedStoreDetail.value?.file_count
    return typeof value === 'number' ? value : '--'
  })

  const selectedStoreVectorCount = computed(() => {
    const value = selectedStoreDetail.value?.vector_count
    return typeof value === 'number' ? value : '--'
  })

  const selectedStorePreprocessMode = computed(() => {
    const value = selectedStoreDetail.value?.preprocess_mode
    return value ? preprocessModeToChinese(value) : '--'
  })

  const selectedStoreIntervalSec = computed(() => {
    const value = selectedStoreDetail.value?.interval_sec
    return typeof value === 'number' ? `${value} 秒` : '--'
  })

  function syncSelectedStore() {
    const current = filteredStores.value.find((item) => item.store_id === selectedStoreId.value)
    if (current) return
    selectedStoreId.value = pickDefaultStore(filteredStores.value)?.store_id || ''
  }

  async function fetchStores() {
    storesLoading.value = true
    storesError.value = ''
    try {
      const { data } = await getStores()
      allStores.value = data.items || []
      syncSelectedStore()
    } catch (error: any) {
      storesError.value = error?.response?.data?.message || error?.message || '检索库列表加载失败。'
      allStores.value = []
      selectedStoreId.value = ''
    } finally {
      storesLoading.value = false
    }
  }

  async function fetchSelectedStoreDetail() {
    selectedStoreDetail.value = null
    if (!selectedStoreId.value) return
    try {
      const { data } = await getStoreDetail(selectedStoreId.value)
      selectedStoreDetail.value = data
    } catch {
      selectedStoreDetail.value = null
    }
  }

  function setMode(nextMode: SearchMode) {
    mode.value = nextMode
    results.value = []
    resultCount.value = 0
    rawResponse.value = null
    searchState.value = 'idle'
    errorMessage.value = ''
    statusMessage.value = ''
    if (nextMode !== 'Image2Image') {
      uploadedQueryImages.value = []
    }
    syncSelectedStore()
  }

  function toggleView(nextMode: ViewMode) {
    viewMode.value = nextMode
  }

  function buildRequest(): SearchRequestDTO {
    const isTextMode = mode.value !== 'Image2Image'
    const batchText = batchMode.value ? splitLinesToItems(queryText.value) : queryText.value.trim()

    return {
      scene: mode.value,
      store_type: storeType.value,
      store_id: selectedStoreId.value || undefined,
      topk: topK.value,
      need_vectorize: false,
      input: {
        text: isTextMode ? (batchMode.value ? batchText : batchText || null) : null,
        image_object_keys: !isTextMode ? imageObjectKeys.value : [],
      },
      params: {
        model_alias: modelAlias.value,
        auto_prepare: autoPrepare.value,
        batch_mode: batchMode.value,
        return_detail_meta: returnDetailMeta.value,
        uncertainty_weight: mode.value === 'Text2Video' ? uncertaintyWeight.value : undefined,
      },
    }
  }

  async function runSearch() {
    errorMessage.value = ''
    statusMessage.value = ''
    searchState.value = 'validating'

    if (!selectedStoreId.value) {
      searchState.value = 'error'
      errorMessage.value = storesLoading.value ? '检索库列表加载中，请稍后再试。' : '请先选择一个具体检索库。'
      return
    }

    const request = buildRequest()
    const hasTextInput = Array.isArray(request.input.text)
      ? request.input.text.length > 0
      : Boolean(request.input.text)
    const hasImageKeys = (request.input.image_object_keys?.length || 0) > 0

    if (!hasTextInput && !hasImageKeys) {
      searchState.value = 'error'
      errorMessage.value = mode.value === 'Image2Image' ? '请先上传至少一张查询图片。' : '请先输入检索内容。'
      return
    }

    searchState.value = 'searching'

    try {
      const { data } = await postSearch(request)
      rawResponse.value = data
      results.value = data.results.map(mapSearchResultToCard)
      resultCount.value = results.value.length
      statusMessage.value = data.meta?.message || ''
      if (data.meta?.store_status === 'preparing') {
        searchState.value = 'empty'
        statusMessage.value = data.meta.message || '检索库正在准备中，请稍后重试。'
        return
      }
      searchState.value = results.value.length ? 'success' : 'empty'
    } catch (error: any) {
      searchState.value = 'error'
      errorMessage.value = error?.response?.data?.message || error?.message || '检索失败，请稍后重试。'
    }
  }

  async function uploadQueryFiles(files: FileList | File[]) {
    const list = Array.from(files || [])
    if (!list.length) return
    queryImagesUploading.value = true
    errorMessage.value = ''
    try {
      const uploaded: UploadedQueryImageVM[] = []
      for (const file of list) {
        const { data } = await uploadQueryImage(file)
        uploaded.push({
          name: file.name,
          objectKey: data.object_key,
          previewUrl: data.preview_url,
        })
      }
      uploadedQueryImages.value = uploaded
      statusMessage.value = `已上传 ${uploaded.length} 张查询图片，可直接发起检索。`
    } catch (error: any) {
      errorMessage.value = error?.response?.data?.message || error?.message || '查询图片上传失败。'
    } finally {
      queryImagesUploading.value = false
    }
  }

  function removeUploadedQueryImage(index: number) {
    uploadedQueryImages.value = uploadedQueryImages.value.filter((_, currentIndex) => currentIndex !== index)
  }

  function clearUploadedQueryImages() {
    uploadedQueryImages.value = []
  }

  function openDetail(index: number) {
    detailCurrentIndex.value = index
    detailModalVisible.value = true
  }

  function closeDetail() {
    detailModalVisible.value = false
  }

  function nextDetail() {
    if (!results.value.length) return
    detailCurrentIndex.value = (detailCurrentIndex.value + 1) % results.value.length
  }

  function prevDetail() {
    if (!results.value.length) return
    detailCurrentIndex.value = (detailCurrentIndex.value - 1 + results.value.length) % results.value.length
  }

  const currentDetail = computed(() => results.value[detailCurrentIndex.value] || null)

  watch([mode, storeType], () => {
    syncSelectedStore()
  }, { immediate: true })

  watch(selectedStoreId, () => {
    fetchSelectedStoreDetail()
  }, { immediate: true })

  return {
    mode,
    storeType,
    selectedStoreId,
    selectedStore,
    selectedStoreDetail,
    selectedStoreDescription,
    selectedStoreStatusText,
    selectedStoreUpdatedLabel,
    selectedStoreFileCount,
    selectedStoreVectorCount,
    selectedStorePreprocessMode,
    selectedStoreIntervalSec,
    storesLoading,
    storesError,
    allStores,
    filteredStores,
    topK,
    sortBy,
    advancedOpen,
    viewMode,
    searchState,
    queryText,
    uploadedQueryImages,
    imageObjectKeys,
    queryImagesUploading,
    batchMode,
    modelAlias,
    returnDetailMeta,
    uncertaintyWeight,
    autoPrepare,
    resultCount,
    results,
    errorMessage,
    statusMessage,
    detailModalVisible,
    currentDetail,
    detailCurrentIndex,
    fetchStores,
    fetchSelectedStoreDetail,
    setMode,
    toggleView,
    runSearch,
    uploadQueryFiles,
    removeUploadedQueryImage,
    clearUploadedQueryImages,
    openDetail,
    closeDetail,
    nextDetail,
    prevDetail,
  }
})
