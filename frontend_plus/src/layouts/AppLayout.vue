<template>
  <div class="app-shell">
    <Sidebar />
    <div class="app-workspace">
      <header class="workspace-topbar">
        <div class="crumbs">
          <AppIcon name="layout" :size="16" />
          <span>Atlas 工作台</span>
          <span class="crumbs__divider">/</span>
          <span class="crumbs__current">{{ currentTitle }}</span>
        </div>
        <div class="row gap-sm">
          <button type="button" class="btn btn--ghost btn--sm" @click="refreshHealth">
            <AppIcon name="refresh" class="btn__icon" />
            刷新状态
          </button>
        </div>
      </header>
      <main class="page-shell">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import Sidebar from '@/components/common/Sidebar.vue'
import AppIcon from '@/components/icons/AppIcon.vue'
import { useAppStore } from '@/stores/app'

const route = useRoute()
const appStore = useAppStore()

const currentTitle = computed(() => {
  return typeof route.meta.title === 'string' ? route.meta.title : '工作台'
})

function refreshHealth() {
  appStore.fetchHealth()
}
</script>