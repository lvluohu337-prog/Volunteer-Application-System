<script setup>
import { computed } from "vue";
import { FIRST_ENTRY_PRODUCT_FLOW, buildProductFlowTarget } from "../constants/productFlow.js";
import StatusTag from "./StatusTag.vue";

const props = defineProps({
  studentId: {
    type: [String, Number],
    default: ""
  },
  currentStep: {
    type: String,
    default: ""
  },
  compact: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(["navigate"]);

const steps = computed(() =>
  FIRST_ENTRY_PRODUCT_FLOW.map((item) => ({
    ...item,
    isActive: item.key === props.currentStep
  }))
);

function handleNavigate(item) {
  emit("navigate", buildProductFlowTarget(item.routeName, props.studentId));
}
</script>

<template>
  <section class="product-flow-guide" :class="{ 'product-flow-guide-compact': compact }">
    <div class="product-flow-head">
      <div>
        <span>首次进入产品流</span>
        <h2>画像分析 -> 分数换算 -> 正式推荐报告</h2>
      </div>
      <StatusTag label="同事架构对齐" variant="primary" />
    </div>

    <div class="product-flow-steps">
      <article
        v-for="item in steps"
        :key="item.key"
        class="product-flow-step"
        :class="{ 'product-flow-step-active': item.isActive }"
      >
        <div class="step-index">{{ item.step }}</div>
        <div class="step-copy">
          <h3>{{ item.title }}</h3>
          <p>{{ item.description }}</p>
          <span>{{ item.evidence }}</span>
        </div>
        <el-button type="primary" plain @click="handleNavigate(item)">
          {{ item.primaryAction }}
        </el-button>
      </article>
    </div>
  </section>
</template>

<style scoped>
.product-flow-guide {
  padding: 20px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 8px;
  background:
    linear-gradient(135deg, rgba(14, 116, 144, 0.08), rgba(22, 163, 74, 0.08)),
    #ffffff;
}

.product-flow-guide-compact {
  padding: 16px;
}

.product-flow-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 16px;
}

.product-flow-head span {
  display: block;
  margin-bottom: 4px;
  font-size: 12px;
  color: var(--app-text-secondary);
}

.product-flow-head h2 {
  margin: 0;
  font-size: 18px;
}

.product-flow-steps {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.product-flow-step {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 12px;
  align-items: start;
  min-width: 0;
  padding: 14px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.82);
}

.product-flow-step :deep(.el-button) {
  grid-column: 2;
  width: fit-content;
}

.product-flow-step-active {
  border-color: rgba(14, 116, 144, 0.34);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
}

.step-index {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  color: #ffffff;
  background: #0f766e;
  font-weight: 700;
}

.step-copy {
  min-width: 0;
}

.step-copy h3 {
  margin: 0 0 6px;
  font-size: 15px;
}

.step-copy p,
.step-copy span {
  display: block;
  margin: 0;
  color: var(--app-text-secondary);
  line-height: 1.6;
}

.step-copy span {
  margin-top: 8px;
  font-size: 12px;
}

@media (max-width: 920px) {
  .product-flow-steps {
    grid-template-columns: 1fr;
  }

  .product-flow-head {
    flex-direction: column;
  }
}
</style>
