<script setup>
const props = defineProps({
  title: {
    type: String,
    required: true
  },
  value: {
    type: String,
    required: true
  },
  note: {
    type: String,
    default: ""
  },
  variant: {
    type: String,
    default: "default"
  }
});
</script>

<template>
  <el-card
    shadow="never"
    class="metric-card"
    :class="{ 'metric-card-risk': props.variant === 'risk' }"
  >
    <span>{{ props.title }}</span>
    <strong>{{ props.value }}</strong>
    <p>{{ props.note }}</p>
  </el-card>
</template>
