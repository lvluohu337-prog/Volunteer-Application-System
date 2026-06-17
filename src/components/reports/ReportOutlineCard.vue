<script setup>
defineProps({
  activeProductCode: {
    type: String,
    required: true
  },
  activeProductLabel: {
    type: String,
    required: true
  },
  reportProducts: {
    type: Array,
    default: () => []
  },
  ruleSummary: {
    type: Object,
    required: true
  },
  plannedProductNotice: {
    type: String,
    default: ""
  },
  outlineItems: {
    type: Array,
    default: () => []
  }
});

const emit = defineEmits(["switch-product"]);
</script>

<template>
  <el-card shadow="never" class="panel-card report-outline">
    <div class="product-head">
      <div>
        <h2>报告目录</h2>
        <p class="table-note">{{ activeProductLabel }}</p>
      </div>
      <div class="product-switch">
        <button
          v-for="item in reportProducts"
          :key="item.code"
          class="product-pill"
          :class="{ active: item.code === activeProductCode }"
          type="button"
          @click="emit('switch-product', item.code)"
        >
          {{ item.code }} 元
        </button>
      </div>
    </div>
    <p class="table-note">
      {{ ruleSummary.scoreLevel || "待补充分层判断" }}
      / 冲 {{ ruleSummary.strategy?.rush_ratio || 0 }}%
      / 稳 {{ ruleSummary.strategy?.steady_ratio || 0 }}%
      / 保 {{ ruleSummary.strategy?.safe_ratio || 0 }}%
    </p>
    <el-alert
      v-if="plannedProductNotice"
      type="info"
      :closable="false"
      class="planned-product-alert"
      :title="`当前正式支持 99 / 399 / 999。${plannedProductNotice}`"
    />
    <ul class="outline-list">
      <li
        v-for="(item, index) in outlineItems"
        :key="item"
        :class="{ active: index === 1 }"
      >
        {{ item }}
      </li>
    </ul>
  </el-card>
</template>

<style scoped>
.product-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.product-switch {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.product-pill {
  border: 1px solid rgba(66, 133, 244, 0.16);
  background: rgba(66, 133, 244, 0.06);
  color: var(--app-text-secondary);
  border-radius: 999px;
  padding: 8px 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.product-pill.active {
  background: linear-gradient(135deg, rgba(66, 133, 244, 0.18), rgba(66, 133, 244, 0.08));
  color: var(--app-text-primary);
  border-color: rgba(66, 133, 244, 0.3);
}

.planned-product-alert {
  margin-top: 12px;
}

@media (max-width: 767px) {
  .product-head {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
