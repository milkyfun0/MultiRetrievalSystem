<template>
  <aside class="sidebar" aria-label="主导航">
    <div class="sidebar-brand">
      <div class="sidebar-brand__logo">
        <AppIcon name="logo" :size="22" />
      </div>
      <div>
        <div class="sidebar-brand__title">Atlas 多模态检索</div>
        <div class="sidebar-brand__sub">Multimodal · Retrieval</div>
      </div>
    </div>

    <div class="sidebar-section-label">工作台</div>
    <nav class="sidebar-nav">
      <RouterLink
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="sidebar-link"
      >
        <AppIcon :name="item.icon" class="sidebar-link__icon" />
        <span>{{ item.label }}</span>
      </RouterLink>
    </nav>

    <div class="sidebar-footer">
      <div class="sidebar-health" :class="`is-${appStore.serviceStatus}`" role="status" aria-live="polite">
        <span class="sidebar-health__dot"></span>
        <span>{{ healthText }}</span>
      </div>
      <p class="sidebar-footer__note">
        企业级多模态检索体验<br />
        支持 T2V · T2I · I2I 全栈检索
      </p>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useAppStore } from '@/stores/app'
import AppIcon from '@/components/icons/AppIcon.vue'

const appStore = useAppStore()

const navItems = [
  { path: '/search', label: '智能检索', icon: 'search' },
  { path: '/prepare', label: '资源准备', icon: 'cpu' },
  { path: '/stores', label: '资源管理', icon: 'layers' },
]

const healthText = computed(() => {
  switch (appStore.serviceStatus) {
    case 'healthy':
      return '服务正常'
    case 'degraded':
      return '服务降级'
    case 'error':
      return '服务异常'
    default:
      return '检测中…'
  }
})

onMounted(() => {
  appStore.fetchHealth()
})
</script>