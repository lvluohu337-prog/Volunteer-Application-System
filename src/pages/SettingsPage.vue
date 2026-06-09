<script setup>
import { onMounted, ref } from "vue";
import { fetchSettingsData } from "../api/planning.js";
import PageHeader from "../components/PageHeader.vue";
import PanelSection from "../components/PanelSection.vue";

const loading = ref(true);
const copyRules = ref([]);

onMounted(async () => {
  const data = await fetchSettingsData();
  copyRules.value = data.copyRules;
  loading.value = false;
});
</script>

<template>
  <section class="page">
    <PageHeader
      title="系统设置"
      description="首版作为风格占位页，用于承接后续角色权限、文案模板和导出配置。"
    />

    <el-skeleton :loading="loading" animated :rows="6">
      <template #default>
        <div class="content-grid content-grid-dashboard">
          <PanelSection
            title="文案规范提醒"
            description="避免绝对化与营销化表述，统一风险说明口径。"
          >
            <ul class="notice-list">
              <li v-for="item in copyRules" :key="item">{{ item }}</li>
            </ul>
          </PanelSection>

          <PanelSection
            title="后续可扩展"
            description="该区域可继续接入权限、模板、角色和消息配置。"
          >
            <div class="empty-state">
              <strong>设置模块待完善</strong>
              <p>当前已预留统一组件样式，后续可直接扩展业务配置项。</p>
            </div>
          </PanelSection>
        </div>
      </template>
    </el-skeleton>
  </section>
</template>
