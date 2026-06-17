<script setup>
import StatusTag from "../StatusTag.vue";

defineProps({
  meta: {
    type: Object,
    required: true
  },
  resultSource: {
    type: Object,
    required: true
  },
  facts: {
    type: Array,
    default: () => []
  }
});
</script>

<template>
  <el-card shadow="never" class="panel-card result-source-banner">
    <div class="result-source-head">
      <div>
        <h3>{{ meta.title }}</h3>
        <p>
          {{
            resultSource.notice ||
            resultSource.fallbackReason ||
            "正式交付前仍需结合官方位次、院校章程和招生计划复核。"
          }}
        </p>
      </div>
      <StatusTag :label="meta.tagLabel" :variant="meta.tagVariant" />
    </div>

    <div v-if="facts.length" class="result-source-facts">
      <span
        v-for="item in facts"
        :key="item"
        class="result-source-fact"
      >
        {{ item }}
      </span>
    </div>
  </el-card>
</template>

<style scoped>
.result-source-banner {
  gap: 14px;
  margin-bottom: 16px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background:
    radial-gradient(circle at top right, rgba(56, 189, 248, 0.14), transparent 32%),
    linear-gradient(180deg, rgba(248, 250, 252, 0.96), rgba(241, 245, 249, 0.88));
}

.result-source-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.result-source-head h3 {
  margin: 0 0 6px;
  font-size: 16px;
  color: var(--app-text-primary);
}

.result-source-head p {
  margin: 0;
  color: var(--app-text-secondary);
  line-height: 1.7;
}

.result-source-facts {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.result-source-fact {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.05);
  color: var(--app-text-secondary);
  font-size: 13px;
}

@media (max-width: 767px) {
  .result-source-head {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
