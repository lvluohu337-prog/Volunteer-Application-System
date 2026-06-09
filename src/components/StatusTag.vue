<script setup>
import { computed } from "vue";

const props = defineProps({
  label: {
    type: String,
    required: true
  },
  variant: {
    type: String,
    default: "primary"
  }
});

const className = computed(() => `app-tag app-tag-${props.variant}`);
</script>

<template>
  <el-tag :class="className" disable-transitions>
    {{ label }}
  </el-tag>
</template>
