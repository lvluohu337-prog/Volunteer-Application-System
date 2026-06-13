<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { fetchPlanData } from "../api/planning.js";
import FallbackRiskNotice from "../components/FallbackRiskNotice.vue";
import PageHeader from "../components/PageHeader.vue";
import RequestErrorNotice from "../components/RequestErrorNotice.vue";
import StatusTag from "../components/StatusTag.vue";

const route = useRoute();
const router = useRouter();

const emptyPortraitRecommendation = {
  preferredDirection: "待补充画像信息",
  parentConcernMatch: { label: "待补充家长诉求", details: "" },
  majorFitReasons: []
};

const loading = ref(true);
const loadError = ref("");
const hasStudent = ref(false);
const studentId = ref(null);
const columns = ref([]);
const disclaimer = ref("");
const resultSource = ref({
  mode: "empty",
  label: "未生成结果",
  isRealData: false,
  matchedCandidateCount: 0,
  candidateStrategy: null,
  rankSource: null,
  latestAdmissionYear: null,
  fallbackReason: "",
  notice: ""
});
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

const resultSourceMeta = computed(() => {
  const mode = resultSource.value.mode;
  if (mode === "real") {
    return {
      title: "当前结果已命中真实招生数据",
      tagLabel: resultSource.value.label || "真实招生结果",
      tagVariant: "success"
    };
  }
  if (mode === "real_relaxed") {
    return {
      title: "当前结果来自真实招生数据，但已放宽位次硬门槛",
      tagLabel: resultSource.value.label || "真实招生结果（放宽位次）",
      tagVariant: "review"
    };
  }
  if (mode === "fallback") {
    return {
      title: "当前结果未命中真实招生候选，已切回画像/规则兜底",
      tagLabel: resultSource.value.label || "画像/规则兜底结果",
      tagVariant: "warning"
    };
  }
  return {
    title: "当前尚未生成可用志愿方案结果",
    tagLabel: resultSource.value.label || "未生成结果",
    tagVariant: "default"
  };
});

const resultSourceFacts = computed(() => {
  const items = [];
  if (resultSource.value.matchedCandidateCount) {
    items.push(`真实候选 ${resultSource.value.matchedCandidateCount} 条`);
  }
  if (resultSource.value.latestAdmissionYear) {
    items.push(`主要参考年份 ${resultSource.value.latestAdmissionYear}`);
  }
  if (resultSource.value.rankSource) {
    items.push(`位次来源 ${resultSource.value.rankSource}`);
  }
  return items;
});

const fallbackNextSteps = [
  "先回到学生详情，补齐最新成绩、位次、选科和调剂接受边界。",
  "在命中真实候选前，不要直接把当前冲稳保方案用于正式填报或对外承诺。",
  "可先回评估分析页核对风险分层，再等待真实数据命中后生成正式报告。"
];

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
  loadError.value = "";
  try {
    const data = await fetchPlanData(parseStudentId());
    hasStudent.value = data.hasStudent ?? false;
    studentId.value = data.studentId ?? null;
    columns.value = data.columns ?? [];
    disclaimer.value = data.disclaimer ?? "";
    resultSource.value = data.resultSource ?? resultSource.value;
    ruleSummary.value = data.ruleSummary ?? ruleSummary.value;
    portraitRecommendation.value = data.portraitRecommendation ?? { ...emptyPortraitRecommendation };
  } catch (error) {
    loadError.value = error.message || "志愿方案加载失败，请确认后端接口和学生数据状态后重试。";
    hasStudent.value = false;
    studentId.value = null;
    columns.value = [];
  } finally {
    loading.value = false;
  }
}

function goToReport() {
  router.push(
    studentId.value
      ? { name: "reports", query: { studentId: String(studentId.value) } }
      : { name: "reports" }
  );
}

function goToAnalysis() {
  router.push(
    studentId.value
      ? { name: "analysis", query: { studentId: String(studentId.value) } }
      : { name: "analysis" }
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
        <RequestErrorNotice
          v-if="loadError"
          title="志愿方案加载失败"
          :message="loadError"
          hint="在方案接口恢复前，请不要把当前冲稳保结构用于正式填报，也不要直接继续生成正式报告。"
        >
          <template #actions>
            <el-button @click="goToStudentDetail">查看学生详情</el-button>
            <el-button type="primary" @click="loadPageData">重新加载</el-button>
          </template>
        </RequestErrorNotice>

        <template v-else>
        <el-card v-if="hasStudent" shadow="never" class="panel-card result-source-banner">
          <div class="result-source-head">
            <div>
              <h3>{{ resultSourceMeta.title }}</h3>
              <p>
                {{
                  resultSource.notice ||
                  resultSource.fallbackReason ||
                  "正式填报前仍需结合官方位次、院校章程和招生计划复核。"
                }}
              </p>
            </div>
            <StatusTag :label="resultSourceMeta.tagLabel" :variant="resultSourceMeta.tagVariant" />
          </div>

          <div v-if="resultSourceFacts.length" class="result-source-facts">
            <span
              v-for="item in resultSourceFacts"
              :key="item"
              class="result-source-fact"
            >
              {{ item }}
            </span>
          </div>
        </el-card>

        <FallbackRiskNotice
          v-if="hasStudent && resultSource.mode === 'fallback'"
          :reason="resultSource.fallbackReason"
          :next-steps="fallbackNextSteps"
        >
          <template #actions>
            <el-button @click="goToStudentDetail">查看学生详情</el-button>
            <el-button type="primary" @click="goToAnalysis">返回评估分析</el-button>
          </template>
        </FallbackRiskNotice>

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
      </template>
    </el-skeleton>
  </section>
</template>

<style scoped>
.result-source-banner {
  gap: 14px;
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
  .result-source-head,
  .focus-head,
  .column-head {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
