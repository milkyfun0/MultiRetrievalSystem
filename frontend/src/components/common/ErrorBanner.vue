<template>
  <div v-if="message" class="error-banner" role="alert" aria-live="assertive">
    <span>{{ message }}</span>
    <button type="button" class="ghost-button" @click="$emit('retry')">重试</button>
  </div>
</template>

<script setup lang="ts">
defineProps<{ message: string }>()
defineEmits<{ retry: [] }>()
</script>
