<script setup>
const props = defineProps({
  currentPage: {
    type: String,
    required: true
  },
  navigationItems: {
    type: Array,
    required: true
  },
  mobileOpen: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(["navigate"]);
</script>

<template>
  <aside class="sidebar" :class="{ open: props.mobileOpen }">
    <div>
      <div class="brand-block">
        <div class="brand-mark">GAO</div>
        <div class="brand-copy">
          <strong>高考志愿规划系统</strong>
          <span>AI生涯画像与志愿规划后台</span>
        </div>
      </div>

      <nav class="nav-list" aria-label="主导航">
        <button
          v-for="item in props.navigationItems"
          :key="item.key"
          class="nav-item"
          :class="{ active: props.currentPage === item.key }"
          type="button"
          @click="emit('navigate', item.key)"
        >
          <span class="nav-icon">{{ item.short }}</span>
          <span>{{ item.label }}</span>
        </button>
      </nav>
    </div>

    <div class="sidebar-footer">
      <div class="footer-hint">
        <el-tag class="app-tag app-tag-review">演示版</el-tag>
        <p>当前界面遵循“专业、可信、清晰、稳重”的设计规范。</p>
      </div>
    </div>
  </aside>
</template>
