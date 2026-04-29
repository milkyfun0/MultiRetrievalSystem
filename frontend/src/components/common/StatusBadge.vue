<template>
  <span class="status-badge" :class="`is-${status}`">{{ label }}</span>
</template>

<script setup lang="ts">
defineProps<{
  status: 'pending' | 'running' | 'success' | 'failed'
  label: string
}>()
</script>
