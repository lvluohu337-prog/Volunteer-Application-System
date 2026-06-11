<script setup>
import { computed, onMounted, ref } from "vue";
import MetricCard from "../components/MetricCard.vue";
import PageHeader from "../components/PageHeader.vue";
import PanelSection from "../components/PanelSection.vue";
import StatusTag from "../components/StatusTag.vue";
import { fetchDashboardData } from "../api/planning.js";

const emit = defineEmits(["navigate", "open-dialog"]);

const loading = ref(true);
const metrics = ref([]);
const students = ref([]);

const coreActions = computed(() => [
  {
    title: "新增学生",
    description: "从正式录入开始建立学生档案，补齐分数、位次、选科和基础偏好。",
    target: "intake"
  },
  {
    title: "继续处理学生",
    description: "进入学生列表或学生工作台，继续做画像、专业和志愿方案。",
    target: "students"
  },
  {
    title: "生成正式报告",
    description: "进入报告中心，选择当前正式支持的 99 / 399 / 999 版本并查看交付内容。",
    target: "reports"
  }
]);

onMounted(async () => {
  const data = await fetchDashboardData();
  metrics.value = data.metrics ?? [];
  students.value = data.recentStudents ?? [];
  loading.value = false;
});
</script>

<template>
  <section class="page">
    <PageHeader
      title="工作台"
      description="把系统入口收束成一条主流程：录入学生信息、完善画像与专业方向、生成志愿方案、选择报告版本并交付下载。"
    >
      <template #actions>
        <el-button @click="emit('navigate', 'students')">学生列表</el-button>
        <el-button type="primary" @click="emit('navigate', 'intake')">新增学生</el-button>
      </template>
    </PageHeader>

    <el-skeleton :loading="loading" animated :rows="6">
      <template #template>
        <el-card shadow="never" class="panel-card">
          <el-skeleton-item variant="h1" style="width: 30%;" />
          <el-skeleton-item variant="text" style="margin-top: 12px;" />
          <el-skeleton-item variant="text" style="width: 80%;" />
        </el-card>
      </template>

      <template #default>
        <div class="metrics-grid">
          <MetricCard
            v-for="metric in metrics"
            :key="metric.title"
            :title="metric.title"
            :value="metric.value"
            :note="metric.note"
            :variant="metric.variant"
          />
        </div>

        <el-card shadow="never" class="panel-card workflow-card">
          <div class="workflow-copy">
            <strong>推荐使用顺序</strong>
            <p>新增学生 -> 学生工作台 -> 画像分析与专业方向 -> 志愿方案 -> 报告版本 -> 导出交付</p>
          </div>
          <el-alert
            type="info"
            :closable="false"
            title="分析页、专业页和志愿方案页不再作为首页入口暴露，改由学生工作台按步骤引导进入。"
          />
        </el-card>

        <div class="content-grid content-grid-dashboard">
          <PanelSection
            title="核心快捷入口"
            description="这里只保留高频主流程入口，避免把使用者分散到演示页、测试页和非当前必需页面。"
          >
            <div class="quick-actions">
              <button
                v-for="item in coreActions"
                :key="item.title"
                type="button"
                class="quick-action-card"
                @click="emit('navigate', item.target)"
              >
                <strong>{{ item.title }}</strong>
                <span>{{ item.description }}</span>
              </button>
            </div>
          </PanelSection>

          <PanelSection
            title="最近学生"
            description="优先继续处理最近录入或等待复核的学生；需要进入单个学生流程时，请从学生列表进入学生工作台。"
          >
            <template #extra>
              <el-button text type="primary" @click="emit('navigate', 'students')">进入学生列表</el-button>
            </template>

            <div class="list-stack">
              <div
                v-for="student in students"
                :key="`${student.name}-${student.detail}`"
                class="student-row"
              >
                <div>
                  <strong>{{ student.name }}</strong>
                  <span>{{ student.detail }}</span>
                </div>
                <StatusTag :label="student.tagLabel" :variant="student.tag" />
              </div>
            </div>
          </PanelSection>
        </div>
      </template>
    </el-skeleton>
  </section>
</template>

<style scoped>
.workflow-card {
  margin-bottom: 16px;
}

.workflow-copy {
  margin-bottom: 12px;
}

.workflow-copy strong {
  display: block;
  margin-bottom: 6px;
  font-size: 15px;
}

.workflow-copy p {
  margin: 0;
  color: var(--app-text-secondary);
}
</style>
