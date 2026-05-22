<template>
  <div class="skeleton-grid" role="status" aria-live="polite" aria-label="加载中">
    <div v-for="index in count" :key="index" class="skeleton-card"></div>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ count?: number }>(), {
  count: 6,
})
</script>