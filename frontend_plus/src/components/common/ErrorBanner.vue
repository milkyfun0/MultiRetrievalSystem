<template>
  <div v-if="message" class="error-banner" role="alert" aria-live="assertive">
    <div class="error-banner__icon">
      <AppIcon name="alert" :size="18" />
    </div>
    <div class="error-banner__msg">{{ message }}</div>
    <button type="button" class="btn btn--sm btn--secondary" @click="$emit('retry')">
      <AppIcon name="refresh" class="btn__icon" />
      重试
    </button>
  </div>
</template>

<script setup lang="ts">
import AppIcon from '@/components/icons/AppIcon.vue'

defineProps<{ message: string }>()
defineEmits<{ retry: [] }>()
</script>