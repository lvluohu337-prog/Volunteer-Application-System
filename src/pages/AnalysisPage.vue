<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { fetchAnalysisData } from "../api/planning.js";
import FallbackRiskNotice from "../components/FallbackRiskNotice.vue";
import PageHeader from "../components/PageHeader.vue";
import PanelSection from "../components/PanelSection.vue";
import StatusTag from "../components/StatusTag.vue";

const route = useRoute();
const router = useRouter();

const emptyDerivedProfile = {
  constellation: "",
  birthday: "",
  birthTime: "",
  pillars: { year: "", month: "", day: "", hour: "" },
  hourBranchLabel: "",
  wuxing: { dominant: "", secondary: "", counts: {} },
  personalityTraits: [],
  learningStyle: "",
  decisionStyle: "",
  stressStyle: "",
  socialStyle: "",
  interestDirections: [],
  regionPreferences: [],
  developmentGoals: [],
  explanations: [],
  disclaimer: ""
};

const loading = ref(true);
const hasStudent = ref(false);
const studentId = ref(null);
const summary = ref({ name: "", meta: "", tags: [] });
const metrics = ref([]);
const buckets = ref([]);
const subjectBars = ref([]);
const warnings = ref([]);
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
const derivedProfile = ref({ ...emptyDerivedProfile });
const policyHighlights = ref([]);
const ruleSummary = ref({
  scoreLevel: "",
  scoreComment: "",
  riskLevel: "",
  riskItems: [],
  studentSubjects: [],
  strategy: { rush_ratio: 0, steady_ratio: 0, safe_ratio: 0 },
  topMajors: []
});

const routeStudentId = computed(() => {
  const rawValue = route.query.studentId;
  if (!rawValue) {
    return undefined;
  }
  const numericValue = Number(rawValue);
  return Number.isNaN(numericValue) ? undefined : numericValue;
});

const fourPillars = computed(() =>
  [
    derivedProfile.value.pillars?.year,
    derivedProfile.value.pillars?.month,
    derivedProfile.value.pillars?.day,
    derivedProfile.value.pillars?.hour
  ]
    .filter(Boolean)
    .join(" / ") || "待补充"
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
    title: "当前尚未生成可用分析结果",
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
  "先回到学生详情，补齐最新总分、位次和选科组合。",
  "复核目标省份、院校层次和专业范围，必要时适当放宽筛选边界。",
  "在命中真实候选前，本页内容只能用于方向讨论，不能直接作为正式填报依据。"
];

async function loadPageData() {
  loading.value = true;
  const data = await fetchAnalysisData(routeStudentId.value);
  hasStudent.value = data.hasStudent ?? false;
  studentId.value = data.studentId ?? null;
  summary.value = data.summary ?? { name: "", meta: "", tags: [] };
  metrics.value = data.metrics ?? [];
  buckets.value = data.buckets ?? [];
  subjectBars.value = data.subjectBars ?? [];
  warnings.value = data.warnings ?? [];
  resultSource.value = data.resultSource ?? resultSource.value;
  ruleSummary.value = data.ruleSummary ?? ruleSummary.value;
  derivedProfile.value = data.derivedProfile ?? { ...emptyDerivedProfile };
  policyHighlights.value = data.policyHighlights ?? [];
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
  if (!summary.value.name) {
    loadPageData();
  }
});
</script>

<template>
  <section class="page">
    <PageHeader
      :breadcrumb="hasStudent ? `学生管理 / ${summary.name} / 评估分析` : '学生管理 / 评估分析'"
      title="评估分析"
      description="基于真实学生档案、当前成绩和四柱辅助画像生成分析结果，正式决策仍需结合官方位次与招生规则复核。"
    >
      <template #actions>
        <el-button @click="goToStudentDetail">查看学生详情</el-button>
        <el-button type="primary" @click="goToPlan">进入志愿方案</el-button>
      </template>
    </PageHeader>

    <el-skeleton :loading="loading" animated :rows="8">
      <template #default>
        <el-card shadow="never" class="panel-card student-hero">
          <div class="student-hero-main">
            <h2>{{ summary.name }}</h2>
            <p>{{ summary.meta }}</p>
          </div>
          <div class="student-hero-tags">
            <StatusTag
              v-for="tag in summary.tags"
              :key="tag.label"
              :label="tag.label"
              :variant="tag.variant"
            />
          </div>
        </el-card>

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
            <el-button type="primary" @click="goToPlan">进入志愿方案</el-button>
          </template>
        </FallbackRiskNotice>

        <div v-if="hasStudent" class="content-grid content-grid-analysis">
          <el-card
            v-for="item in metrics"
            :key="item.title"
            shadow="never"
            class="panel-card emphasis-card"
          >
            <span>{{ item.title }}</span>
            <strong>{{ item.value }}</strong>
            <p>{{ item.note }}</p>
          </el-card>
        </div>

        <div v-if="hasStudent" class="tri-column">
          <el-card
            v-for="bucket in buckets"
            :key="bucket.key"
            shadow="never"
            class="panel-card risk-column"
            :class="{
              'risk-column-high': bucket.key === 'rush',
              'risk-column-safe': bucket.key === 'safe'
            }"
          >
            <div class="column-head">
              <h2>{{ bucket.title }}</h2>
              <StatusTag :label="bucket.tagLabel" :variant="bucket.tagVariant" />
            </div>
            <p>{{ bucket.note }}</p>
            <ul class="line-list">
              <li v-for="item in bucket.items" :key="item">{{ item }}</li>
            </ul>
          </el-card>
        </div>

        <div class="content-grid content-grid-analysis">
          <PanelSection
            title="规则判断"
            description="当前结果来自第一阶段规则引擎，已综合分数层级、位次完整度、选科匹配和冲稳保比例。"
          >
            <div v-if="hasStudent" class="list-stack">
              <div class="student-row">
                <div>
                  <strong>分数层级</strong>
                  <span>{{ ruleSummary.scoreLevel }}</span>
                </div>
                <StatusTag label="已计算" variant="success" />
              </div>
              <div class="student-row">
                <div>
                  <strong>当前选科</strong>
                  <span>{{ ruleSummary.studentSubjects.join(" / ") || "待补充" }}</span>
                </div>
                <StatusTag label="已识别" variant="primary" />
              </div>
              <div class="student-row">
                <div>
                  <strong>冲稳保比例</strong>
                  <span>
                    冲 {{ ruleSummary.strategy.rush_ratio }}% / 稳 {{ ruleSummary.strategy.steady_ratio }}% / 保 {{ ruleSummary.strategy.safe_ratio }}%
                  </span>
                </div>
                <StatusTag label="规则建议" variant="review" />
              </div>
              <div class="student-row">
                <div>
                  <strong>优先专业</strong>
                  <span>{{ ruleSummary.topMajors.map((item) => item.name).join(" / ") || "待补充" }}</span>
                </div>
                <StatusTag label="已匹配" variant="success" />
              </div>
              <p class="table-note">{{ ruleSummary.scoreComment }}</p>
            </div>
          </PanelSection>

          <PanelSection
            title="四柱辅助画像"
            description="生日与出生时辰会自动推算八字四柱、五行倾向和辅助兴趣解释，但不能替代真实录取数据。"
          >
            <div v-if="hasStudent" class="derived-profile">
              <div class="derived-metrics">
                <div class="derived-metric">
                  <span>星座</span>
                  <strong>{{ derivedProfile.constellation || "待补充" }}</strong>
                </div>
                <div class="derived-metric">
                  <span>四柱</span>
                  <strong>{{ fourPillars }}</strong>
                </div>
                <div class="derived-metric">
                  <span>五行主导</span>
                  <strong>
                    {{ derivedProfile.wuxing?.dominant || "待识别" }}
                    <template v-if="derivedProfile.wuxing?.secondary">
                      / {{ derivedProfile.wuxing.secondary }}
                    </template>
                  </strong>
                </div>
                <div class="derived-metric">
                  <span>出生时辰</span>
                  <strong>{{ derivedProfile.birthTime || "待补充" }}</strong>
                </div>
              </div>

              <p class="table-note">
                {{ derivedProfile.hourBranchLabel || "未录入出生时辰时，将只用年柱、月柱、日柱做辅助分析。" }}
              </p>

              <div class="derived-groups">
                <div class="derived-group">
                  <h3>性格与学习</h3>
                  <div class="tag-wrap">
                    <el-tag
                      v-for="item in derivedProfile.personalityTraits"
                      :key="item"
                      class="soft-tag"
                    >
                      {{ item }}
                    </el-tag>
                  </div>
                  <ul class="notice-list compact-list">
                    <li>学习方式：{{ derivedProfile.learningStyle || "待补充" }}</li>
                    <li>决策风格：{{ derivedProfile.decisionStyle || "待补充" }}</li>
                    <li>抗压特点：{{ derivedProfile.stressStyle || "待补充" }}</li>
                    <li>社交适应：{{ derivedProfile.socialStyle || "待补充" }}</li>
                  </ul>
                </div>

                <div class="derived-group">
                  <h3>辅助倾向</h3>
                  <ul class="notice-list compact-list">
                    <li>兴趣方向：{{ derivedProfile.interestDirections.join("、") || "待补充" }}</li>
                    <li>区域偏好：{{ derivedProfile.regionPreferences.join("、") || "待补充" }}</li>
                    <li>成长路径：{{ derivedProfile.developmentGoals.join("、") || "待补充" }}</li>
                  </ul>
                </div>
              </div>

              <ul class="notice-list compact-list">
                <li
                  v-for="item in derivedProfile.explanations"
                  :key="item"
                >
                  {{ item }}
                </li>
              </ul>
            </div>
          </PanelSection>

          <PanelSection
            title="学科对比"
            description="使用当前学生档案中的成绩快照做结构化展示。"
          >
            <div v-if="hasStudent" class="chart-bars">
              <div
                v-for="item in subjectBars"
                :key="item.label"
                class="bar-item"
              >
                <span>{{ item.label }}</span>
                <div>
                  <i :style="{ width: `${item.percent}%` }" />
                </div>
                <strong>{{ item.value }}</strong>
              </div>
            </div>
            <div v-else class="empty-state">
              <strong>暂无可分析学生</strong>
              <p>请先录入真实学生档案，并补充分数与位次信息。</p>
            </div>
          </PanelSection>

          <PanelSection
            title="本省政策依据"
            description="这些摘要来自已导入的河南政策文件，用于解释当前风险提示和志愿判断的来源。"
          >
            <div v-if="policyHighlights.length" class="policy-list">
              <article
                v-for="item in policyHighlights"
                :key="`${item.key}-${item.year}`"
                class="policy-item"
              >
                <div class="policy-head">
                  <strong>{{ item.title }}</strong>
                  <StatusTag :label="`${item.year || '当年'}政策`" variant="primary" />
                </div>
                <p>{{ item.summary }}</p>
                <span class="table-note">{{ item.source || "河南政策资料" }}</span>
              </article>
            </div>
            <div v-else class="empty-state">
              <strong>暂未命中政策摘要</strong>
              <p>当前结果仍可继续使用风险标签，但正式交付前建议补充政策原文复核。</p>
            </div>
          </PanelSection>

          <PanelSection
            title="风险提示"
            description="所有结论均需结合当年官方数据与人工复核共同判断。"
          >
            <ul class="notice-list">
              <li v-for="item in warnings" :key="item">{{ item }}</li>
            </ul>
          </PanelSection>
        </div>
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

.derived-profile {
  display: grid;
  gap: 16px;
}

.policy-list {
  display: grid;
  gap: 12px;
}

.policy-item {
  padding: 14px 16px;
  border-radius: 16px;
  border: 1px solid rgba(66, 133, 244, 0.12);
  background: linear-gradient(180deg, rgba(66, 133, 244, 0.08), rgba(66, 133, 244, 0.03));
}

.policy-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.policy-item p {
  margin: 0 0 8px;
  line-height: 1.7;
}

.derived-metrics {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
}

.derived-metric {
  padding: 14px 16px;
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(66, 133, 244, 0.1), rgba(66, 133, 244, 0.04));
  border: 1px solid rgba(66, 133, 244, 0.12);
}

.derived-metric span {
  display: block;
  margin-bottom: 6px;
  color: var(--app-text-secondary);
  font-size: 13px;
}

.derived-metric strong {
  color: var(--app-text-primary);
  font-size: 15px;
  line-height: 1.5;
}

.derived-groups {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
}

.derived-group h3 {
  margin: 0 0 10px;
  font-size: 15px;
  color: var(--app-text-primary);
}

.tag-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.soft-tag {
  border-radius: 999px;
}

.compact-list {
  gap: 8px;
}

@media (max-width: 720px) {
  .result-source-head {
    flex-direction: column;
  }
}
</style>
