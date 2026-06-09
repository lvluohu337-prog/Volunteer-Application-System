<script setup>
defineProps({
  title: {
    type: String,
    default: ""
  },
  description: {
    type: String,
    default: ""
  }
});
</script>

<template>
  <el-card shadow="never" class="panel-card">
    <div v-if="title || description || $slots.extra" class="panel-head">
      <div>
        <h2 v-if="title">{{ title }}</h2>
        <p v-if="description">{{ description }}</p>
      </div>
      <slot name="extra" />
    </div>
    <slot />
  </el-card>
</template>
