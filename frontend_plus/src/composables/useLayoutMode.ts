import { computed, ref } from 'vue'

export type LayoutMode = 'default' | 'portrait'
export type LayoutPreference = 'auto' | LayoutMode

const LEGACY_STORAGE_KEY = 'frontend-layout-mode'
const STORAGE_KEY = 'frontend-layout-preference'
const layoutPreferenceRef = ref<LayoutPreference>('auto')
const effectiveLayoutModeRef = ref<LayoutMode>('default')
let initialized = false
let listenersBound = false
let portraitMediaQuery: MediaQueryList | null = null

function resolveAutoMode(): LayoutMode {
  if (typeof window === 'undefined') return 'default'
  const width = window.innerWidth
  const isPortraitViewport = window.matchMedia('(orientation: portrait)').matches
  return isPortraitViewport || width <= 1366 ? 'portrait' : 'default'
}

function syncEffectiveMode() {
  effectiveLayoutModeRef.value =
    layoutPreferenceRef.value === 'auto' ? resolveAutoMode() : layoutPreferenceRef.value

  if (typeof document !== 'undefined') {
    document.documentElement.dataset.layoutPreference = layoutPreferenceRef.value
    document.documentElement.dataset.layoutMode = effectiveLayoutModeRef.value
    document.body.dataset.layoutPreference = layoutPreferenceRef.value
    document.body.dataset.layoutMode = effectiveLayoutModeRef.value
  }
}

function bindListeners() {
  if (listenersBound || typeof window === 'undefined') return
  listenersBound = true
  const onViewportChange = () => syncEffectiveMode()
  window.addEventListener('resize', onViewportChange, { passive: true })
  portraitMediaQuery = window.matchMedia('(orientation: portrait)')
  if (typeof portraitMediaQuery.addEventListener === 'function') {
    portraitMediaQuery.addEventListener('change', onViewportChange)
  } else if (typeof portraitMediaQuery.addListener === 'function') {
    portraitMediaQuery.addListener(onViewportChange)
  }
}

function setLayoutPreference(preference: LayoutPreference) {
  layoutPreferenceRef.value = preference
  syncEffectiveMode()
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(STORAGE_KEY, preference)
  }
}

function initLayoutMode() {
  if (initialized) return
  initialized = true

  if (typeof window === 'undefined') {
    syncEffectiveMode()
    return
  }

  const savedPreference = window.localStorage.getItem(STORAGE_KEY)
  const legacyPreference = window.localStorage.getItem(LEGACY_STORAGE_KEY)
  if (savedPreference === 'auto' || savedPreference === 'default' || savedPreference === 'portrait') {
    layoutPreferenceRef.value = savedPreference
  } else if (legacyPreference === 'portrait') {
    layoutPreferenceRef.value = 'portrait'
  } else {
    layoutPreferenceRef.value = 'auto'
  }

  syncEffectiveMode()
  bindListeners()
}

export function useLayoutMode() {
  initLayoutMode()

  return {
    layoutMode: computed(() => effectiveLayoutModeRef.value),
    layoutPreference: computed(() => layoutPreferenceRef.value),
    isPortraitMode: computed(() => effectiveLayoutModeRef.value === 'portrait'),
    isAutoLayoutMode: computed(() => layoutPreferenceRef.value === 'auto'),
    setLayoutMode: setLayoutPreference,
    setLayoutPreference,
    toggleLayoutMode: () =>
      setLayoutPreference(effectiveLayoutModeRef.value === 'portrait' ? 'default' : 'portrait'),
  }
}
