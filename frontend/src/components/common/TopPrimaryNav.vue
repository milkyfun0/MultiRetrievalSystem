<template>
  <header v-if="isPortraitMode" class="top-nav glass-panel portrait-top-nav" aria-label="主导航">
    <div class="brand-group portrait-top-nav__brand">
      <div class="brand-mark">▶</div>
      <div>
        <div class="brand-text">多模态检索系统</div>
        <p class="portrait-top-nav__subtitle">当前为竖版模式，适合较窄窗口与 1080p 密度场景。</p>
      </div>
    </div>

    <nav class="top-nav-links portrait-top-nav__links" aria-label="页面导航">
      <RouterLink class="nav-link" to="/search">检索</RouterLink>
      <RouterLink class="nav-link" to="/prepare">资源准备</RouterLink>
      <RouterLink class="nav-link" to="/stores">资源管理</RouterLink>
    </nav>

    <div class="portrait-top-nav__actions">
      <div class="health-pill" :class="`is-${appStore.serviceStatus}`" role="status" aria-live="polite">
        <span class="health-dot"></span>
        <span>{{ healthText }}</span>
      </div>
      <div class="layout-switch-group layout-switch-group--inline" aria-label="布局模式设置">
        <button type="button" class="layout-switch-chip" :class="{ active: layoutPreference === 'auto' }" @click="setLayoutMode('auto')">自动</button>
        <button type="button" class="layout-switch-chip" :class="{ active: layoutPreference === 'default' }" @click="setLayoutMode('default')">工作台</button>
        <button type="button" class="layout-switch-chip" :class="{ active: layoutPreference === 'portrait' }" @click="setLayoutMode('portrait')">竖版</button>
      </div>
    </div>
  </header>

  <header v-else class="top-nav side-nav glass-panel" aria-label="主导航">
    <div class="side-nav__brand-block">
      <div class="brand-group side-nav__brand">
        <div class="brand-mark">▶</div>
        <div>
          <div class="brand-text">多模态检索系统</div>
          <p class="side-nav__subtitle">统一检索、建库与资源管理工作台</p>
        </div>
      </div>

      <div class="side-nav__current glass-panel-subtle">
        <span class="side-nav__current-label">当前页面</span>
        <strong>{{ currentTitle }}</strong>
      </div>
    </div>

    <nav class="top-nav-links side-nav__links" aria-label="页面导航">
      <RouterLink class="nav-link side-nav__link" to="/search">
        <span class="side-nav__link-title">检索</span>
        <span class="side-nav__link-desc">文本检索图像、视频与以图搜图</span>
      </RouterLink>
      <RouterLink class="nav-link side-nav__link" to="/prepare">
        <span class="side-nav__link-title">资源准备</span>
        <span class="side-nav__link-desc">创建向量化任务并持续跟踪状态</span>
      </RouterLink>
      <RouterLink class="nav-link side-nav__link" to="/stores">
        <span class="side-nav__link-title">资源管理</span>
        <span class="side-nav__link-desc">查看检索库详情并执行删除操作</span>
      </RouterLink>
    </nav>

    <div class="side-nav__footer">
      <div class="health-pill side-nav__health" :class="`is-${appStore.serviceStatus}`" role="status" aria-live="polite">
        <span class="health-dot"></span>
        <span>{{ healthText }}</span>
      </div>

      <div class="layout-mode-card glass-panel-subtle">
        <span class="side-nav__current-label">布局设置</span>
        <strong>{{ layoutModeLabel }}</strong>
        <p class="layout-mode-tip">自动模式会根据窗口宽度和横竖方向切换，更适合 4K / 1440p / 1080p 混合使用。</p>
        <div class="layout-switch-group" aria-label="布局模式设置">
          <button type="button" class="layout-switch-chip" :class="{ active: layoutPreference === 'auto' }" @click="setLayoutMode('auto')">自动适配</button>
          <button type="button" class="layout-switch-chip" :class="{ active: layoutPreference === 'default' }" @click="setLayoutMode('default')">工作台版</button>
          <button type="button" class="layout-switch-chip" :class="{ active: layoutPreference === 'portrait' }" @click="setLayoutMode('portrait')">竖版模式</button>
        </div>
      </div>

      <p class="side-nav__footer-note">
        保留原有业务逻辑与接口调用，仅重构展现结构与视觉层次。
      </p>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useLayoutMode } from '@/composables/useLayoutMode'

const appStore = useAppStore()
const route = useRoute()
const { isPortraitMode, layoutPreference, layoutMode, setLayoutMode } = useLayoutMode()

const healthText = computed(() => {
  switch (appStore.serviceStatus) {
    case 'healthy':
      return '服务正常'
    case 'degraded':
      return '服务降级'
    case 'error':
      return '服务异常'
    default:
      return '状态未知'
  }
})

const currentTitle = computed(() => {
  if (typeof route.meta.title === 'string' && route.meta.title) {
    return route.meta.title
  }
  return '工作台'
})

const layoutModeLabel = computed(() => {
  if (layoutPreference.value === 'auto') {
    return layoutMode.value === 'portrait' ? '自动适配 · 当前为竖版' : '自动适配 · 当前为工作台版'
  }
  return layoutMode.value === 'portrait' ? '当前为竖版模式' : '当前为工作台版'
})

onMounted(() => {
  appStore.fetchHealth()
})
</script>
