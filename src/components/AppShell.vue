<script setup>
import { ref } from "vue";
import AppSidebar from "./AppSidebar.vue";
import AppTopbar from "./AppTopbar.vue";

const props = defineProps({
  currentPage: {
    type: String,
    required: true
  },
  navigationItems: {
    type: Array,
    required: true
  }
});

const emit = defineEmits(["navigate"]);
const mobileSidebarOpen = ref(false);

function handleNavigate(page) {
  emit("navigate", page);
  mobileSidebarOpen.value = false;
}
</script>

<template>
  <div class="app-shell">
    <div
      v-if="mobileSidebarOpen"
      class="app-overlay"
      @click="mobileSidebarOpen = false"
    />

    <AppSidebar
      :current-page="props.currentPage"
      :navigation-items="props.navigationItems"
      :mobile-open="mobileSidebarOpen"
      @navigate="handleNavigate"
    />

    <div class="main-shell">
      <AppTopbar @toggle-menu="mobileSidebarOpen = !mobileSidebarOpen" />

      <main class="page-container">
        <div class="screen-tip">
          当前原型优先适配桌面端，窄屏下内容将自动收起为紧凑布局。
        </div>
        <slot />
      </main>
    </div>
  </div>
</template>
