<template>
  <div class="empty-state" role="status" aria-live="polite">
    <div class="empty-state__icon">
      <AppIcon :name="icon" :size="26" />
    </div>
    <h3>{{ title }}</h3>
    <p>{{ description }}</p>
    <slot name="actions" />
  </div>
</template>

<script setup lang="ts">
import AppIcon from '@/components/icons/AppIcon.vue'

withDefaults(defineProps<{
  title: string
  description: string
  icon?: string
}>(), {
  icon: 'inbox',
})
</script>