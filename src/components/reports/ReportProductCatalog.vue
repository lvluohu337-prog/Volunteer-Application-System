<script setup>
defineProps({
  activeProductCode: {
    type: String,
    required: true
  },
  reportProducts: {
    type: Array,
    default: () => []
  }
});
</script>

<template>
  <section v-if="reportProducts.length" class="product-catalog">
    <article
      v-for="item in reportProducts"
      :key="item.code"
      class="product-catalog-card"
      :class="{ active: item.code === activeProductCode }"
    >
      <strong>{{ item.label }}</strong>
      <p>{{ item.description }}</p>
      <span>{{ item.targetUser }}</span>
      <footer>
        <em>{{ item.moduleCount }} 个模块 / 约 {{ item.suggestedPages || 0 }} 页</em>
        <em>人工复核 {{ item.manualReviewCount }} 处</em>
        <em>交付渠道 {{ (item.deliveryChannels || []).join(" / ") || "待补充" }}</em>
      </footer>
    </article>
  </section>
</template>

<style scoped>
.product-catalog {
  display: grid;
  gap: 12px;
  margin-bottom: 20px;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.product-catalog-card {
  padding: 16px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(66, 133, 244, 0.1);
}

.product-catalog-card.active {
  background: linear-gradient(180deg, rgba(66, 133, 244, 0.1), rgba(66, 133, 244, 0.04));
  border-color: rgba(66, 133, 244, 0.22);
}

.product-catalog-card strong,
.product-catalog-card span {
  display: block;
}

.product-catalog-card p {
  margin: 8px 0;
  line-height: 1.7;
}

.product-catalog-card footer {
  display: flex;
  flex-direction: column;
  gap: 4px;
  color: var(--app-text-secondary);
  font-size: 12px;
}
</style>
