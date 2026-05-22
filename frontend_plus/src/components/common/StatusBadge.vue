<template>
  <span class="badge" :class="`is-${status}`">{{ label }}</span>
</template>

<script setup lang="ts">
defineProps<{
  status: string
  label: string
}>()
</script>