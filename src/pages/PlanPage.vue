<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { fetchPlanData } from "../api/planning.js";
import PageHeader from "../components/PageHeader.vue";
import StatusTag from "../components/StatusTag.vue";

const route = useRoute();
const router = useRouter();

const emptyPortraitRecommendation = {
  preferredDirection: "待补充画像信息",
  parentConcernMatch: { label: "待补充家长诉求", details: "" },
  majorFitReasons: []
};

const loading = ref(true);
const hasStudent = ref(false);
const studentId = ref(null);
const columns = ref([]);
const disclaimer = ref("");
const portraitRecommendation = ref({ ...emptyPortraitRecommendation });
const ruleSummary = ref({
  strategy: { rush_ratio: 0, steady_ratio: 0, safe_ratio: 0 },
  preferredDirection: "待补充画像信息",
  preferredDirectionReason: "",
  topMajors: []
});

const preferredDirection = computed(
  () => ruleSummary.value.preferredDirection || portraitRecommendation.value.preferredDirection || "待补充画像信息"
);

function parseStudentId() {
  const rawValue = route.query.studentId;
  if (!rawValue) {
    return undefined;
  }
  const numericValue = Number(rawValue);
  return Number.isNaN(numericValue) ? undefined : numericValue;
}

async function loadPageData() {
  loading.value = true;
  const data = await fetchPlanData(parseStudentId());
  hasStudent.value = data.hasStudent ?? false;
  studentId.value = data.studentId ?? null;
  columns.value = data.columns ?? [];
  disclaimer.value = data.disclaimer ?? "";
  ruleSummary.value = data.ruleSummary ?? ruleSummary.value;
  portraitRecommendation.value = data.portraitRecommendation ?? { ...emptyPortraitRecommendation };
  loading.value = false;
}

function goToReport() {
  router.push(
    studentId.value
      ? { name: "reports", query: { studentId: String(studentId.value) } }
      : { name: "reports" }
  );
}

function goToStudentDetail() {
  if (!studentId.value) {
    router.push({ name: "students" });
    return;
  }
  router.push({ name: "student-detail", params: { studentId: String(studentId.value) } });
}

watch(
  () => route.query.studentId,
  () => {
    loadPageData();
  },
  { immediate: true }
);

onMounted(() => {
  if (columns.value.length === 0) {
    loadPageData();
  }
});
</script>

<template>
  <section class="page">
    <PageHeader
      breadcrumb="学生管理 / 志愿方案"
      title="志愿方案"
      description="冲稳保比例继续来自真实成绩、位次与招生规则；右上角优先方向改为读取画像辅助推荐结果。"
    >
      <template #actions>
        <el-button @click="goToStudentDetail">查看学生详情</el-button>
        <el-button type="primary" @click="goToReport">生成规划报告</el-button>
      </template>
    </PageHeader>

    <el-skeleton :loading="loading" animated :rows="8">
      <template #default>
        <div v-if="hasStudent" class="summary-grid">
          <el-card shadow="never" class="panel-card summary-card">
            <h3>冲稳保比例</h3>
            <strong class="summary-value">
              {{ ruleSummary.strategy.rush_ratio }}/{{ ruleSummary.strategy.steady_ratio }}/{{ ruleSummary.strategy.safe_ratio }}
            </strong>
            <p>对应冲刺 / 稳妥 / 保底建议占比</p>
          </el-card>

          <el-card shadow="never" class="panel-card summary-card">
            <h3>优先方向</h3>
            <strong class="summary-value">
              {{ preferredDirection }}
            </strong>
            <p>{{ ruleSummary.preferredDirectionReason || portraitRecommendation.parentConcernMatch?.details || "待补充画像辅助说明" }}</p>
          </el-card>

          <el-card shadow="never" class="panel-card summary-card">
            <h3>家长诉求匹配</h3>
            <strong class="summary-value">
              {{ portraitRecommendation.parentConcernMatch?.label || "待补充" }}
            </strong>
            <p>{{ portraitRecommendation.parentConcernMatch?.details || "待补充家长诉求说明" }}</p>
          </el-card>
        </div>

        <el-card v-if="hasStudent" shadow="never" class="panel-card focus-card">
          <div class="focus-head">
            <div>
              <h2>方案优先方向说明</h2>
              <p>这里展示的是画像辅助推荐的首选方向，不替代冲稳保概率判断。</p>
            </div>
            <StatusTag
              :label="ruleSummary.preferredDirectionStatus === 'needs_profile' ? '待补画像' : '画像辅助'"
              :variant="ruleSummary.preferredDirectionStatus === 'needs_profile' ? 'warning' : 'review'"
            />
          </div>
          <p class="focus-copy">{{ ruleSummary.preferredDirectionReason || "待补充画像辅助说明。" }}</p>
        </el-card>

        <div v-if="hasStudent" class="plan-grid">
          <el-card
            v-for="column in columns"
            :key="column.title"
            shadow="never"
            class="panel-card plan-column"
          >
            <div class="column-head">
              <h2>{{ column.title }}</h2>
              <StatusTag :label="column.tagLabel" :variant="column.tagVariant" />
            </div>
            <p class="column-note">{{ column.note }}</p>

            <el-card
              v-for="card in column.cards"
              :key="card.school"
              shadow="never"
              class="school-card"
            >
              <h3>{{ card.school }}</h3>
              <p>{{ card.detail }}</p>
              <div class="school-metrics">
                <span v-for="item in card.metrics" :key="item">{{ item }}</span>
              </div>
              <p class="school-major">{{ card.major }}</p>
              <p class="school-reason">{{ card.reason }}</p>
            </el-card>
          </el-card>
        </div>

        <el-card v-else shadow="never" class="panel-card">
          <div class="empty-state">
            <strong>暂无可用方案</strong>
            <p>请先录入真实学生档案，再查看志愿方案建议。</p>
          </div>
        </el-card>

        <el-card shadow="never" class="panel-card disclaimer-card">
          <strong>合规说明</strong>
          <p>{{ disclaimer }}</p>
        </el-card>
      </template>
    </el-skeleton>
  </section>
</template>

<style scoped>
.focus-card {
  margin-bottom: 16px;
}

.focus-head,
.column-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.focus-head h2,
.column-head h2 {
  margin: 0;
}

.focus-head p,
.column-note,
.school-reason {
  color: var(--el-text-color-secondary);
}

.focus-copy {
  margin-top: 14px;
  line-height: 1.75;
}

.plan-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
}

.school-card {
  margin-top: 16px;
}

.school-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin: 14px 0;
  color: var(--el-text-color-secondary);
}

.school-major {
  font-weight: 600;
}

@media (max-width: 768px) {
  .focus-head,
  .column-head {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
