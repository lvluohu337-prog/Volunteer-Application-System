<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { fetchMajorsData } from "../api/planning.js";
import PageHeader from "../components/PageHeader.vue";
import StatusTag from "../components/StatusTag.vue";

const route = useRoute();
const router = useRouter();

const emptyDerivedProfile = {
  constellation: "",
  personalityTraits: [],
  interestDirections: [],
  developmentGoals: [],
  explanations: []
};

const emptyPortraitRecommendation = {
  preferredDirection: "待补充画像信息",
  recommendedMajorDirections: [],
  avoidMajorDirections: [],
  majorFitReasons: [],
  personalityMatchTags: [],
  parentConcernMatch: { label: "待补充家长诉求", details: "" },
  subjectMatchSummary: "",
  auxiliaryExplanation: [],
  disclaimer: ""
};

const loading = ref(true);
const hasStudent = ref(false);
const studentId = ref(null);
const rows = ref([]);
const disclaimer = ref("");
const derivedProfile = ref({ ...emptyDerivedProfile });
const portraitRecommendation = ref({ ...emptyPortraitRecommendation });
const ruleSummary = ref({
  preferredDirection: "待补充画像信息",
  preferredDirectionReason: "",
  topMajors: []
});

const displayedRows = computed(() => rows.value.slice(0, 8));
const primaryReason = computed(() => portraitRecommendation.value.majorFitReasons?.[0] ?? null);
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
  const data = await fetchMajorsData(parseStudentId());
  hasStudent.value = data.hasStudent ?? false;
  studentId.value = data.studentId ?? null;
  rows.value = data.rows ?? [];
  disclaimer.value = data.disclaimer ?? "";
  ruleSummary.value = data.ruleSummary ?? ruleSummary.value;
  derivedProfile.value = data.derivedProfile ?? { ...emptyDerivedProfile };
  portraitRecommendation.value = data.portraitRecommendation ?? { ...emptyPortraitRecommendation };
  loading.value = false;
}

function goToPlan() {
  router.push(
    studentId.value
      ? { name: "plan", query: { studentId: String(studentId.value) } }
      : { name: "plan" }
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
  if (rows.value.length === 0) {
    loadPageData();
  }
});
</script>

<template>
  <section class="page">
    <PageHeader
      breadcrumb="学生管理 / 专业推荐"
      title="专业推荐"
      description="专业方向推荐会同时展示硬条件校验与画像辅助解释。录取概率和冲稳保仍只看真实成绩、位次、选科和招生规则。"
    >
      <template #actions>
        <el-button @click="goToStudentDetail">查看学生详情</el-button>
        <el-button type="primary" @click="goToPlan">生成志愿方案</el-button>
      </template>
    </PageHeader>

    <el-skeleton :loading="loading" animated :rows="10">
      <template #default>
        <div v-if="hasStudent" class="summary-grid">
          <el-card shadow="never" class="panel-card summary-card">
            <h3>优先推荐方向</h3>
            <strong class="summary-value">{{ preferredDirection }}</strong>
            <p>{{ primaryReason?.subjectMatch || portraitRecommendation.subjectMatchSummary || "待补充选科匹配说明" }}</p>
          </el-card>

          <el-card shadow="never" class="panel-card summary-card">
            <h3>家长诉求匹配</h3>
            <strong class="summary-value">{{ portraitRecommendation.parentConcernMatch?.label || "待补充" }}</strong>
            <p>{{ portraitRecommendation.parentConcernMatch?.details || "待补充家长关注点说明" }}</p>
          </el-card>

          <el-card shadow="never" class="panel-card summary-card">
            <h3>辅助画像标签</h3>
            <strong class="summary-value">
              {{ derivedProfile.constellation || "待补充星座" }}
            </strong>
            <p>{{ portraitRecommendation.personalityMatchTags?.slice(0, 3).join(" / ") || "待补充性格标签" }}</p>
          </el-card>
        </div>

        <div v-if="hasStudent" class="portrait-grid">
          <el-card shadow="never" class="panel-card portrait-card">
            <div class="card-head">
              <div>
                <h2>优先推荐方向</h2>
                <p>以下方向来自画像辅助推荐，不直接参与录取概率计算。</p>
              </div>
              <StatusTag label="辅助推荐" variant="review" />
            </div>

            <div class="tag-wrap">
              <el-tag
                v-for="direction in portraitRecommendation.recommendedMajorDirections"
                :key="direction"
                class="soft-tag"
                effect="plain"
              >
                {{ direction }}
              </el-tag>
            </div>
          </el-card>

          <el-card shadow="never" class="panel-card portrait-card">
            <div class="card-head">
              <div>
                <h2>谨慎选择方向</h2>
                <p>这些方向通常和当前选科组合或家长诉求存在偏差，需要单独沟通。</p>
              </div>
              <StatusTag label="需复核" variant="warning" />
            </div>
            <div class="tag-wrap">
              <el-tag
                v-for="direction in portraitRecommendation.avoidMajorDirections"
                :key="direction"
                class="soft-tag"
                type="warning"
                effect="plain"
              >
                {{ direction }}
              </el-tag>
              <span v-if="!portraitRecommendation.avoidMajorDirections?.length" class="table-note">
                当前未识别出明显需要回避的方向，仍建议逐校核对具体专业组。
              </span>
            </div>
          </el-card>
        </div>

        <div v-if="hasStudent" class="reason-grid">
          <el-card
            v-for="item in portraitRecommendation.majorFitReasons"
            :key="item.direction"
            shadow="never"
            class="panel-card reason-card"
          >
            <div class="card-head">
              <div>
                <h2>{{ item.direction }}</h2>
                <p>{{ item.subjectMatch }}</p>
              </div>
              <span class="score-pill">{{ Math.round(item.score || 0) }}</span>
            </div>

            <ul class="notice-list compact-list">
              <li v-for="reason in item.reasons" :key="reason">{{ reason }}</li>
            </ul>

            <div class="reason-footer">
              <div>
                <strong>硬条件交叉验证</strong>
                <p>{{ item.hardEvidence?.join("；") || "正式录取仍需结合真实分数、位次和选科要求。" }}</p>
              </div>
              <div>
                <strong>画像辅助解释</strong>
                <p>{{ item.auxiliaryEvidence?.join("；") || "待补充画像辅助解释。" }}</p>
              </div>
            </div>
          </el-card>
        </div>

        <el-card v-if="hasStudent" shadow="never" class="panel-card portrait-card">
          <div class="card-head">
            <div>
              <h2>与画像和家长诉求的匹配</h2>
              <p>正式建议只把这部分作为解释层，不作为录取判断层。</p>
            </div>
            <StatusTag label="边界清晰" variant="success" />
          </div>

          <div class="portrait-columns">
            <div>
              <strong>性格 / 星座 / 前六段辅助解释</strong>
              <p>{{ portraitRecommendation.auxiliaryExplanation?.join(" ") || "待补充辅助解释。" }}</p>
            </div>
            <div>
              <strong>与选科组合的匹配情况</strong>
              <p>{{ portraitRecommendation.subjectMatchSummary || "待补充选科匹配说明。" }}</p>
            </div>
            <div>
              <strong>与家长诉求的匹配情况</strong>
              <p>{{ portraitRecommendation.parentConcernMatch?.details || "待补充家长诉求说明。" }}</p>
            </div>
          </div>
        </el-card>

        <el-card v-if="hasStudent && displayedRows.length" shadow="never" class="panel-card">
          <div class="card-head">
            <div>
              <h2>真实招生样本专业</h2>
              <p>这部分来自当前已命中的真实专业候选，用于和画像方向做交叉验证。</p>
            </div>
            <StatusTag label="真实数据" variant="primary" />
          </div>

          <div class="major-grid">
            <el-card
              v-for="major in displayedRows"
              :key="major.title"
              shadow="never"
              class="major-card"
            >
              <div class="major-head">
                <div>
                  <h2>{{ major.title }}</h2>
                  <p>{{ major.type }}</p>
                </div>
                <span class="score-pill">{{ major.score }}</span>
              </div>

              <p class="major-reason">{{ major.reason }}</p>

              <div class="major-meta">
                <span v-for="meta in major.meta" :key="meta">{{ meta }}</span>
              </div>

              <div class="major-footer">
                <StatusTag :label="major.tagLabel" :variant="major.tagVariant" />
                <span>{{ major.footer }}</span>
              </div>
            </el-card>
          </div>
        </el-card>

        <el-card v-else-if="!hasStudent" shadow="never" class="panel-card">
          <div class="empty-state">
            <strong>暂无可推荐学生</strong>
            <p>请先录入真实学生档案，再查看专业推荐结果。</p>
          </div>
        </el-card>

        <el-card shadow="never" class="panel-card disclaimer-card">
          <strong>合规说明</strong>
          <p>{{ portraitRecommendation.disclaimer || disclaimer }}</p>
        </el-card>
      </template>
    </el-skeleton>
  </section>
</template>

<style scoped>
.portrait-grid,
.reason-grid,
.portrait-columns,
.major-grid {
  display: grid;
  gap: 16px;
}

.portrait-grid,
.portrait-columns {
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
}

.reason-grid {
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  margin-top: 16px;
}

.major-grid {
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
}

.portrait-card,
.reason-card {
  margin-bottom: 16px;
}

.card-head,
.major-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.card-head h2,
.major-head h2 {
  margin: 0;
}

.card-head p,
.major-head p,
.reason-footer p {
  margin: 6px 0 0;
  color: var(--el-text-color-secondary);
}

.tag-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
}

.score-pill {
  display: inline-flex;
  min-width: 52px;
  justify-content: center;
  padding: 8px 12px;
  border-radius: 999px;
  background: linear-gradient(135deg, #cbe6ff, #f6fbff);
  color: #114a88;
  font-weight: 700;
}

.reason-footer {
  display: grid;
  gap: 12px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--el-border-color-light);
}

.major-card {
  border: 1px solid rgba(17, 74, 136, 0.12);
}

.major-reason {
  margin: 14px 0;
}

.major-meta {
  display: flex;
  flex-direction: column;
  gap: 8px;
  color: var(--el-text-color-secondary);
  margin-bottom: 16px;
}

.major-footer {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  color: var(--el-text-color-secondary);
}

@media (max-width: 768px) {
  .card-head,
  .major-head,
  .major-footer {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
