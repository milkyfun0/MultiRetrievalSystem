<template>
  <div
    class="app-shell overhaul-shell"
    :class="[`layout-mode--${layoutMode}`, `layout-pref--${layoutPreference}`]"
  >
    <TopPrimaryNav class="app-side-nav" />
    <div class="app-workspace">
      <main class="page-shell">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import TopPrimaryNav from '@/components/common/TopPrimaryNav.vue'
import { useLayoutMode } from '@/composables/useLayoutMode'

const { layoutMode, layoutPreference } = useLayoutMode()
</script>
