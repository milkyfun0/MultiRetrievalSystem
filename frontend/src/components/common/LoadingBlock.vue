<template>
  <div class="loading-grid" role="status" aria-live="polite" aria-label="内容加载中">
    <div v-for="index in count" :key="index" class="loading-card"></div>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ count?: number }>(), {
  count: 6,
})
</script>
