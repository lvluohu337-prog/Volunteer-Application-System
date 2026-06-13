<script setup>
import StatusTag from "./StatusTag.vue";

defineProps({
  title: {
    type: String,
    default: "当前页面数据加载失败"
  },
  message: {
    type: String,
    default: "请检查后端服务、网络连接或学生数据状态后重试。"
  },
  hint: {
    type: String,
    default: "在错误恢复前，请不要把当前页面视为正式可交付结果。"
  }
});
</script>

<template>
  <el-card shadow="never" class="request-error-card">
    <div class="request-error-head">
      <div>
        <h3>{{ title }}</h3>
        <p>{{ message }}</p>
      </div>
      <StatusTag label="接口失败" variant="danger" />
    </div>

    <div class="request-error-body">
      <strong>当前建议</strong>
      <p>{{ hint }}</p>
    </div>

    <div v-if="$slots.actions" class="request-error-actions">
      <slot name="actions" />
    </div>
  </el-card>
</template>

<style scoped>
.request-error-card {
  margin-bottom: 16px;
  border: 1px solid rgba(190, 24, 93, 0.16);
  background:
    linear-gradient(135deg, rgba(255, 241, 242, 0.94), rgba(255, 247, 237, 0.92)),
    #fff;
}

.request-error-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.request-error-head h3 {
  margin: 0 0 8px;
}

.request-error-head p,
.request-error-body p {
  margin: 0;
  color: var(--el-text-color-secondary);
  line-height: 1.7;
}

.request-error-body {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid rgba(190, 24, 93, 0.12);
}

.request-error-body strong {
  display: block;
  margin-bottom: 8px;
}

.request-error-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 16px;
}

@media (max-width: 768px) {
  .request-error-head {
    flex-direction: column;
  }

  .request-error-actions {
    flex-direction: column;
  }
}
</style>
