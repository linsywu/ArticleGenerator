<template>
  <header class="page-header">
    <div>
      <h1 class="page-title">{{ title }}</h1>
      <p v-if="subtitle" class="page-subtitle">{{ subtitle }}</p>
    </div>
  </header>
</template>

<script setup lang="ts">
defineProps<{
  title: string;
  subtitle?: string;
}>();
</script>

<style scoped>
.page-header {
  margin-bottom: var(--space-xl);
}
.page-title {
  font-family: var(--font-serif);
  font-size: 28px;
  font-weight: 900;
  color: var(--text-on-dark);
  letter-spacing: 1px;
  margin-bottom: 4px;
}
.page-subtitle {
  font-size: 14px;
  color: var(--text-muted);
}
</style>
