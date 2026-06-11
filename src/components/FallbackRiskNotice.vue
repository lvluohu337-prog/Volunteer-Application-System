<script setup>
import StatusTag from "./StatusTag.vue";

defineProps({
  title: {
    type: String,
    default: "当前结果未命中真实招生数据"
  },
  description: {
    type: String,
    default: "系统已回退到画像/规则兜底结果，以下内容只能用于方向沟通，不能直接用于正式填报或正式交付。"
  },
  reason: {
    type: String,
    default: ""
  },
  nextSteps: {
    type: Array,
    default: () => []
  }
});
</script>

<template>
  <el-card shadow="never" class="fallback-risk-card">
    <div class="fallback-risk-head">
      <div>
        <h3>{{ title }}</h3>
        <p>{{ description }}</p>
      </div>
      <StatusTag label="高风险提示" variant="warning" />
    </div>

    <div class="fallback-risk-grid">
      <article class="fallback-risk-block">
        <strong>当前原因</strong>
        <p>{{ reason || "当前未命中真实招生候选，请先补齐学生档案并复核报考边界。" }}</p>
      </article>

      <article class="fallback-risk-block">
        <strong>建议下一步</strong>
        <ol class="fallback-risk-steps">
          <li v-for="item in nextSteps" :key="item">{{ item }}</li>
        </ol>
      </article>
    </div>

    <div v-if="$slots.actions" class="fallback-risk-actions">
      <slot name="actions" />
    </div>
  </el-card>
</template>

<style scoped>
.fallback-risk-card {
  gap: 16px;
  margin-bottom: 16px;
  border: 1px solid rgba(245, 108, 108, 0.22);
  background:
    radial-gradient(circle at top right, rgba(251, 191, 36, 0.18), transparent 30%),
    linear-gradient(180deg, rgba(255, 251, 235, 0.96), rgba(254, 242, 242, 0.92));
}

.fallback-risk-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.fallback-risk-head h3 {
  margin: 0 0 6px;
  font-size: 16px;
  color: var(--app-text-primary);
}

.fallback-risk-head p {
  margin: 0;
  color: var(--app-text-secondary);
  line-height: 1.7;
}

.fallback-risk-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
}

.fallback-risk-block {
  padding: 14px 16px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(245, 158, 11, 0.18);
}

.fallback-risk-block strong {
  display: block;
  margin-bottom: 8px;
  color: var(--app-text-primary);
}

.fallback-risk-block p {
  margin: 0;
  color: var(--app-text-secondary);
  line-height: 1.7;
}

.fallback-risk-steps {
  margin: 0;
  padding-left: 18px;
  color: var(--app-text-secondary);
}

.fallback-risk-steps li + li {
  margin-top: 8px;
}

.fallback-risk-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

@media (max-width: 767px) {
  .fallback-risk-head {
    flex-direction: column;
  }
}
</style>
