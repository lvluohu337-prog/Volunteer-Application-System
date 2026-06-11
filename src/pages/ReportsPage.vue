<script setup>
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  createReportAdvisorNote,
  downloadReportDelivery,
  exportReportPdf,
  exportReportWord,
  fetchReportData
} from "../api/planning.js";
import FallbackRiskNotice from "../components/FallbackRiskNotice.vue";
import PageHeader from "../components/PageHeader.vue";
import StatusTag from "../components/StatusTag.vue";
import { COMPLIANCE_DISCLAIMER } from "../constants/compliance.js";

const emit = defineEmits(["open-dialog"]);
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

const emptyPortraitRecommendation = {
  preferredDirection: "待补充画像信息",
  recommendedMajorDirections: [],
  majorFitReasons: [],
  parentConcernMatch: { label: "待补充家长诉求", details: "" },
  auxiliaryExplanation: []
};

const bucketDefinitions = [
  {
    key: "rush",
    title: "冲刺推荐",
    shortTitle: "冲",
    tagType: "warning",
    description: "适合少量尝试，重点关注位次临界和计划波动风险。"
  },
  {
    key: "steady",
    title: "稳妥推荐",
    shortTitle: "稳",
    tagType: "primary",
    description: "作为主力志愿区，优先兼顾院校平台、专业方向和风险平衡。"
  },
  {
    key: "safe",
    title: "保底推荐",
    shortTitle: "保",
    tagType: "success",
    description: "用于守住底线，仍需关注调剂接受度与专业接受度。"
  }
];

const loading = ref(true);
const hasStudent = ref(false);
const studentId = ref(null);
const activeProductCode = ref("399");
const activeProductLabel = ref("399 元进阶版报告");
const reportProducts = ref([]);
const outline = ref([]);
const sections = ref([]);
const reportTitle = ref("");
const reportSubtitle = ref("");
const disclaimer = ref(COMPLIANCE_DISCLAIMER);
const boundaryNote = ref("");
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
const reportJson = ref({
  product: { description: "", targetUser: "" },
  delivery: { suggestedTotalPages: 0, manualReviewModules: [] },
  modules: []
});
const recommendationTable = ref([]);
const firstChoice = ref(null);
const alternatives = ref([]);
const notRecommended = ref([]);
const derivedProfile = ref({ ...emptyDerivedProfile });
const portraitRecommendation = ref({ ...emptyPortraitRecommendation });
const policyHighlights = ref([]);
const advisorNotes = ref([]);
const generationRecords = ref([]);
const deliveryRecords = ref([]);
const savingNote = ref(false);
const exporting = ref("");
const downloadingRecordId = ref(null);
const noteForm = ref({
  author_name: "张老师",
  note_title: "",
  note_content: "",
  note_type: "advisor_comment"
});
const ruleSummary = ref({
  scoreLevel: "",
  strategy: { rush_ratio: 0, steady_ratio: 0, safe_ratio: 0 },
  topMajors: [],
  topRisks: [],
  preferredDirection: ""
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

const activeProduct = computed(
  () => reportProducts.value.find((item) => item.code === activeProductCode.value) ?? null
);

const hasStructuredRecommendations = computed(
  () => recommendationTable.value.length > 0 || Boolean(firstChoice.value)
);

const resultSourceMeta = computed(() => {
  const mode = resultSource.value.mode;
  if (mode === "real") {
    return {
      title: "当前报告已命中真实招生数据",
      tagLabel: resultSource.value.label || "真实招生结果",
      tagVariant: "success"
    };
  }
  if (mode === "real_relaxed") {
    return {
      title: "当前报告来自真实招生数据，但已放宽位次硬门槛",
      tagLabel: resultSource.value.label || "真实招生结果（放宽位次）",
      tagVariant: "review"
    };
  }
  if (mode === "fallback") {
    return {
      title: "当前报告未命中真实招生候选，已切回画像/规则兜底",
      tagLabel: resultSource.value.label || "画像/规则兜底结果",
      tagVariant: "warning"
    };
  }
  return {
    title: "当前尚未生成可用正式报告结果",
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
  "先暂停把当前报告作为正式交付版本，不要直接导出给家长或学生。",
  "回到学生详情补齐最新成绩、位次、选科与目标边界，再重新触发推荐链路。",
  "待命中真实招生候选后，再进入志愿方案和报告页完成人工复核与正式导出。"
];

const recommendationBuckets = computed(() => {
  const grouped = { rush: [], steady: [], safe: [] };
  recommendationTable.value.forEach((item) => {
    const bucketKey = item.bucket;
    if (grouped[bucketKey]) {
      grouped[bucketKey].push(item);
    }
  });
  return grouped;
});

const displayOutline = computed(() => {
  const baseItems = [
    "1. 报告版本说明",
    "2. 正式院校专业推荐表",
    "3. 第一志愿与备选方案",
    "4. 不建议报考方向"
  ];

  const sectionItems = sections.value.map((section, index) => `${index + 5}. ${section.title}`);
  return [...baseItems, ...sectionItems];
});

const paperRecommendations = computed(() => recommendationTable.value.slice(0, 11));

const topRiskNotes = computed(() => {
  if (Array.isArray(ruleSummary.value.topRisks) && ruleSummary.value.topRisks.length) {
    return ruleSummary.value.topRisks.slice(0, 3);
  }

  const collected = [];
  recommendationTable.value.forEach((item) => {
    (item.riskNotes ?? []).forEach((note) => {
      if (note && !collected.includes(note)) {
        collected.push(note);
      }
    });
  });
  return collected.slice(0, 3);
});

function parseStudentId() {
  const rawValue = route.query.studentId;
  if (!rawValue) {
    return undefined;
  }
  const numericValue = Number(rawValue);
  return Number.isNaN(numericValue) ? undefined : numericValue;
}

function parseProductCode() {
  const rawValue = route.query.productCode;
  return ["99", "399", "999"].includes(String(rawValue)) ? String(rawValue) : "399";
}

function formatScore(value) {
  if (value === null || value === undefined || value === "") {
    return "待补充";
  }
  return Number(value).toFixed(Number.isInteger(Number(value)) ? 0 : 1);
}

function formatRank(value) {
  if (value === null || value === undefined || value === "") {
    return "待补充";
  }
  return new Intl.NumberFormat("zh-CN").format(Number(value));
}

function formatGap(value, positivePrefix = "+") {
  if (value === null || value === undefined || value === "") {
    return "待补充";
  }
  const numericValue = Number(value);
  if (numericValue > 0) {
    return `${positivePrefix}${numericValue}`;
  }
  return String(numericValue);
}

function formatRankGap(value) {
  if (value === null || value === undefined || value === "") {
    return "待补充";
  }
  const numericValue = Number(value);
  if (numericValue > 0) {
    return `领先 ${formatRank(numericValue)}`;
  }
  if (numericValue < 0) {
    return `落后 ${formatRank(Math.abs(numericValue))}`;
  }
  return "基本持平";
}

function riskTagType(level) {
  return {
    low: "success",
    review: "warning",
    high: "danger"
  }[String(level || "")] || "info";
}

function adjustmentTagType(preference) {
  return {
    accept: "success",
    discuss: "warning",
    reject: "danger"
  }[String(preference || "")] || "info";
}

function formatFileSize(value) {
  const size = Number(value);
  if (!Number.isFinite(size) || size <= 0) {
    return "待补充";
  }
  if (size < 1024) {
    return `${size} B`;
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

async function loadPageData() {
  loading.value = true;
  const data = await fetchReportData(parseStudentId(), parseProductCode());
  hasStudent.value = data.hasStudent ?? false;
  studentId.value = data.studentId ?? null;
  activeProductCode.value = data.activeProductCode ?? parseProductCode();
  activeProductLabel.value = data.activeProductLabel ?? activeProductLabel.value;
  reportProducts.value = data.reportProducts ?? [];
  outline.value = data.outline ?? [];
  sections.value = data.sections ?? [];
  reportTitle.value = data.reportTitle ?? "";
  reportSubtitle.value = data.reportSubtitle ?? "";
  disclaimer.value = data.disclaimer || COMPLIANCE_DISCLAIMER;
  boundaryNote.value = data.boundaryNote || "";
  resultSource.value = data.resultSource ?? resultSource.value;
  reportJson.value = data.reportJson ?? reportJson.value;
  recommendationTable.value = data.recommendationTable ?? [];
  firstChoice.value = data.firstChoice ?? null;
  alternatives.value = data.alternatives ?? [];
  notRecommended.value = data.notRecommended ?? [];
  derivedProfile.value = data.derivedProfile ?? { ...emptyDerivedProfile };
  portraitRecommendation.value = data.portraitRecommendation ?? { ...emptyPortraitRecommendation };
  ruleSummary.value = data.ruleSummary ?? ruleSummary.value;
  policyHighlights.value = data.policyHighlights ?? [];
  advisorNotes.value = data.advisorNotes ?? [];
  generationRecords.value = data.generationRecords ?? [];
  deliveryRecords.value = data.deliveryRecords ?? [];
  loading.value = false;
}

function goToStudentDetail() {
  if (!studentId.value) {
    router.push({ name: "students" });
    return;
  }
  router.push({ name: "student-detail", params: { studentId: String(studentId.value) } });
}

function goToPlan() {
  router.push(
    studentId.value
      ? { name: "plan", query: { studentId: String(studentId.value) } }
      : { name: "plan" }
  );
}

function switchProduct(code) {
  if (code === activeProductCode.value) {
    return;
  }
  router.replace({
    query: {
      ...route.query,
      productCode: code
    }
  });
}

async function submitAdvisorNote() {
  if (!studentId.value || !noteForm.value.note_content.trim()) {
    emit("open-dialog", "请先填写咨询师补充备注内容，再保存到当前报告。");
    return;
  }

  savingNote.value = true;
  try {
    await createReportAdvisorNote(studentId.value, {
      ...noteForm.value,
      product_code: activeProductCode.value
    });
    noteForm.value.note_title = "";
    noteForm.value.note_content = "";
    await loadPageData();
    emit("open-dialog", "咨询师补充备注已保存，并同步进入当前报告留痕。");
  } finally {
    savingNote.value = false;
  }
}

async function runExport(format) {
  if (!studentId.value) {
    return;
  }

  exporting.value = format;
  try {
    const params = {
      reportVersion: activeProductCode.value,
      reviewedBy: noteForm.value.author_name || "咨询师",
      includeSignature: true
    };
    const result =
      format === "pdf"
        ? await exportReportPdf(studentId.value, params)
        : await exportReportWord(studentId.value, params);
    if (result.deliveryRecord?.id) {
      await handleDeliveryDownload(
        {
          id: result.deliveryRecord.id,
          artifact_name: result.artifactName,
          export_format: result.exportFormat,
        },
        { silentSuccess: true }
      );
    }
    await loadPageData();
    emit(
      "open-dialog",
      `${format.toUpperCase()} 正式交付文件已生成并开始下载：${result.artifactName}\n系统已经同步写入导出留痕，可直接用于归档、发送和讲解交付。`
    );
  } finally {
    exporting.value = "";
  }
}

async function handleDeliveryDownload(record, options = {}) {
  if (!studentId.value || !record?.id) {
    emit("open-dialog", "当前导出记录缺少可用下载标识，请先重新导出一次正式文件。");
    return;
  }

  downloadingRecordId.value = record.id;
  try {
    await downloadReportDelivery(studentId.value, record.id, record.artifact_name || "");
    if (!options.silentSuccess) {
      emit(
        "open-dialog",
        `${(record.export_format || "文件").toUpperCase()} 下载已开始：${record.artifact_name || "正式交付文件"}`
      );
    }
  } catch (error) {
    emit(
      "open-dialog",
      `当前下载未成功，可能是文件已失效或已被移动：${record.artifact_name || "正式交付文件"}`
    );
  } finally {
    downloadingRecordId.value = null;
  }
}

watch(
  () => [route.query.studentId, route.query.productCode],
  () => {
    loadPageData();
  },
  { immediate: true }
);
</script>

<template>
  <section class="page">
    <PageHeader
      breadcrumb="报告管理 / 正式报告页"
      title="报告生成"
      description="这里展示正式报告版本差异、冲稳保推荐表、第一志愿建议和可下载交付内容。画像分析只作为解释层，不替代真实录取数据。"
    >
      <template #actions>
        <el-button @click="goToStudentDetail">查看学生详情</el-button>
        <el-button :loading="exporting === 'word'" @click="runExport('word')">导出 Word</el-button>
        <el-button type="primary" :loading="exporting === 'pdf'" @click="runExport('pdf')">导出 PDF</el-button>
      </template>
    </PageHeader>

    <el-skeleton :loading="loading" animated :rows="10">
      <template #default>
        <div v-if="hasStudent" class="report-layout">
          <el-card shadow="never" class="panel-card result-source-banner">
            <div class="result-source-head">
              <div>
                <h3>{{ resultSourceMeta.title }}</h3>
                <p>
                  {{
                    resultSource.notice ||
                    resultSource.fallbackReason ||
                    "正式交付前仍需结合官方位次、院校章程和招生计划复核。"
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
            v-if="resultSource.mode === 'fallback'"
            :reason="resultSource.fallbackReason"
            :next-steps="fallbackNextSteps"
          >
            <template #actions>
              <el-button @click="goToStudentDetail">查看学生详情</el-button>
              <el-button type="primary" @click="goToPlan">返回志愿方案</el-button>
            </template>
          </FallbackRiskNotice>

          <el-card shadow="never" class="panel-card report-outline">
            <div class="product-head">
              <div>
                <h2>报告目录</h2>
                <p class="table-note">{{ activeProductLabel }}</p>
              </div>
              <div class="product-switch">
                <button
                  v-for="item in reportProducts"
                  :key="item.code"
                  class="product-pill"
                  :class="{ active: item.code === activeProductCode }"
                  type="button"
                  @click="switchProduct(item.code)"
                >
                  {{ item.code }} 元
                </button>
              </div>
            </div>
            <p class="table-note">
              {{ ruleSummary.scoreLevel || "待补充分层判断" }}
              / 冲 {{ ruleSummary.strategy?.rush_ratio || 0 }}%
              / 稳 {{ ruleSummary.strategy?.steady_ratio || 0 }}%
              / 保 {{ ruleSummary.strategy?.safe_ratio || 0 }}%
            </p>
            <ul class="outline-list">
              <li
                v-for="(item, index) in displayOutline"
                :key="item"
                :class="{ active: index === 1 }"
              >
                {{ item }}
              </li>
            </ul>
          </el-card>

          <el-card shadow="never" class="panel-card report-preview">
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
                </footer>
              </article>
            </section>

            <div class="report-summary-grid">
              <div class="summary-card">
                <span>优先方向</span>
                <strong>{{ ruleSummary.preferredDirection || portraitRecommendation.preferredDirection || "待补充" }}</strong>
                <p>{{ portraitRecommendation.parentConcernMatch?.label || "待补充家长诉求" }}</p>
              </div>
              <div class="summary-card">
                <span>辅助画像</span>
                <strong>{{ fourPillars }}</strong>
                <p>{{ derivedProfile.constellation || "待补充星座" }}</p>
              </div>
              <div class="summary-card">
                <span>兴趣方向</span>
                <strong>{{ derivedProfile.interestDirections.slice(0, 2).join(" / ") || "待补充" }}</strong>
                <p>{{ derivedProfile.learningStyle || "待补充学习风格" }}</p>
              </div>
              <div class="summary-card">
                <span>城市与发展</span>
                <strong>{{ derivedProfile.regionPreferences.slice(0, 2).join(" / ") || "待补充" }}</strong>
                <p>{{ derivedProfile.developmentGoals.slice(0, 2).join(" / ") || "待补充发展目标" }}</p>
              </div>
            </div>

            <section class="formal-report-block">
              <header class="section-head">
                <div>
                  <strong>正式院校专业推荐表</strong>
                  <span>核心交付以真实院校、专业、专业组代码、最低分和最低位次为主，画像信息仅负责解释，不参与硬录取判断。</span>
                </div>
                <el-tag type="primary">
                  共 {{ recommendationTable.length }} 条推荐
                </el-tag>
              </header>

              <div class="bucket-summary-grid">
                <article
                  v-for="bucket in bucketDefinitions"
                  :key="bucket.key"
                  class="bucket-stat-card"
                >
                  <div class="bucket-stat-head">
                    <el-tag :type="bucket.tagType">{{ bucket.shortTitle }}</el-tag>
                    <strong>{{ bucket.title }}</strong>
                  </div>
                  <p>{{ bucket.description }}</p>
                  <span>{{ recommendationBuckets[bucket.key].length }} 条</span>
                </article>
              </div>

              <article v-if="firstChoice" class="first-choice-card">
                <header class="section-head compact">
                  <div>
                    <strong>第一志愿建议</strong>
                    <span>建议优先作为正式填报时的主力样本，再结合家长沟通和调剂边界做最终确认。</span>
                  </div>
                  <el-tag :type="riskTagType(firstChoice.riskLevel)">
                    {{ firstChoice.riskLabel || "待复核" }}
                  </el-tag>
                </header>

                <div class="first-choice-main">
                  <div>
                    <h3>{{ firstChoice.institutionName }}</h3>
                    <p>
                      {{ firstChoice.majorName }}
                      <template v-if="firstChoice.planGroupCode"> / {{ firstChoice.planGroupCode }}</template>
                    </p>
                    <span>{{ firstChoice.cityText || firstChoice.city || firstChoice.province || "待补充城市" }}</span>
                  </div>
                  <div class="choice-metrics">
                    <div>
                      <small>历史最低分</small>
                      <strong>{{ formatScore(firstChoice.minScore) }}</strong>
                    </div>
                    <div>
                      <small>历史最低位次</small>
                      <strong>{{ formatRank(firstChoice.minRank) }}</strong>
                    </div>
                    <div>
                      <small>位次差</small>
                      <strong>{{ formatRankGap(firstChoice.rankGap) }}</strong>
                    </div>
                    <div>
                      <small>调剂态度</small>
                      <strong>{{ firstChoice.adjustmentAdvice?.label || "待确认" }}</strong>
                    </div>
                  </div>
                </div>

                <div class="choice-grid">
                  <article>
                    <strong>推荐理由</strong>
                    <p>{{ firstChoice.recommendationReason || "待补充推荐理由" }}</p>
                  </article>
                  <article>
                    <strong>风险摘要</strong>
                    <p>{{ firstChoice.riskSummary || "待补充风险说明" }}</p>
                  </article>
                  <article>
                    <strong>城市路径</strong>
                    <p>{{ firstChoice.cityPathNote || "待补充城市-专业-就业路径说明" }}</p>
                  </article>
                  <article>
                    <strong>调剂建议</strong>
                    <p>{{ firstChoice.adjustmentAdvice?.detail || "待确认正式填报时的调剂边界。" }}</p>
                  </article>
                </div>
              </article>

              <div class="bucket-table-stack">
                <section
                  v-for="bucket in bucketDefinitions"
                  :key="bucket.key"
                  class="bucket-table-block"
                >
                  <header class="section-head compact">
                    <div>
                      <strong>{{ bucket.title }}</strong>
                      <span>{{ bucket.description }}</span>
                    </div>
                    <el-tag :type="bucket.tagType">
                      {{ recommendationBuckets[bucket.key].length }} 条
                    </el-tag>
                  </header>

                  <el-table
                    v-if="recommendationBuckets[bucket.key].length"
                    :data="recommendationBuckets[bucket.key]"
                    stripe
                    class="report-table"
                  >
                    <el-table-column label="院校 / 城市" min-width="190">
                      <template #default="{ row }">
                        <div class="cell-stack">
                          <strong>{{ row.institutionName }}</strong>
                          <span>{{ row.cityText || row.city || row.province || "待补充城市" }}</span>
                        </div>
                      </template>
                    </el-table-column>
                    <el-table-column label="专业 / 专业组" min-width="210">
                      <template #default="{ row }">
                        <div class="cell-stack">
                          <strong>{{ row.majorName }}</strong>
                          <span>{{ row.planGroupCode || row.batchCode || "待补充代码" }}</span>
                        </div>
                      </template>
                    </el-table-column>
                    <el-table-column label="最低分 / 位次" min-width="150">
                      <template #default="{ row }">
                        <div class="cell-stack">
                          <strong>{{ formatScore(row.minScore) }}</strong>
                          <span>{{ formatRank(row.minRank) }}</span>
                        </div>
                      </template>
                    </el-table-column>
                    <el-table-column label="位次差 / 分差" min-width="150">
                      <template #default="{ row }">
                        <div class="cell-stack">
                          <strong>{{ formatRankGap(row.rankGap) }}</strong>
                          <span>{{ formatGap(row.scoreGap) }}</span>
                        </div>
                      </template>
                    </el-table-column>
                    <el-table-column label="风险等级" min-width="110">
                      <template #default="{ row }">
                        <el-tag :type="riskTagType(row.riskLevel)">
                          {{ row.riskLabel || "待复核" }}
                        </el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column label="推荐理由与提示" min-width="340">
                      <template #default="{ row }">
                        <div class="reason-stack">
                          <p>{{ row.recommendationReason || "待补充推荐理由" }}</p>
                          <span>{{ row.riskSummary || "待补充风险摘要" }}</span>
                        </div>
                      </template>
                    </el-table-column>
                  </el-table>

                  <div v-else class="table-empty">
                    当前版本暂未生成该梯度的推荐项。
                  </div>
                </section>
              </div>
            </section>

            <section class="formal-report-block">
              <header class="section-head">
                <div>
                  <strong>备选志愿与不建议方向</strong>
                  <span>让正式报告不仅给出“报什么”，也明确“可替换什么”和“暂时不建议报什么”。</span>
                </div>
              </header>

              <div class="decision-grid">
                <article class="decision-card">
                  <header class="decision-head">
                    <strong>备选志愿建议</strong>
                    <el-tag type="primary">{{ alternatives.length }} 条</el-tag>
                  </header>
                  <div v-if="alternatives.length" class="decision-list">
                    <div
                      v-for="item in alternatives"
                      :key="`${item.institutionName}-${item.majorName}-${item.planGroupCode}`"
                      class="decision-item"
                    >
                      <strong>{{ item.institutionName }} - {{ item.majorName }}</strong>
                      <span>{{ item.cityText || item.city || "待补充城市" }} / {{ item.planGroupCode || item.batchCode || "待补充代码" }}</span>
                      <p>{{ item.recommendationReason || item.riskSummary || "待补充说明" }}</p>
                    </div>
                  </div>
                  <p v-else class="table-note">当前暂无备选志愿建议。</p>
                </article>

                <article class="decision-card">
                  <header class="decision-head">
                    <strong>不建议报考方向</strong>
                    <el-tag type="danger">{{ notRecommended.length }} 条</el-tag>
                  </header>
                  <div v-if="notRecommended.length" class="decision-list">
                    <div
                      v-for="item in notRecommended"
                      :key="`${item.institutionName}-${item.majorName}-${item.planGroupCode}`"
                      class="decision-item decision-item-danger"
                    >
                      <strong>{{ item.institutionName }} - {{ item.majorName }}</strong>
                      <span>{{ item.cityText || "待补充城市" }} / {{ item.planGroupCode || "待补充代码" }}</span>
                      <p>{{ item.reason || item.notes?.[0] || "待补充不建议原因" }}</p>
                    </div>
                  </div>
                  <p v-else class="table-note">当前暂无不建议报考项。</p>
                </article>
              </div>
            </section>

            <section class="paper-sheet">
              <header class="paper-header">
                <span>{{ reportTitle }}</span>
                <strong>{{ reportSubtitle }}</strong>
              </header>

              <section class="paper-section">
                <h3>报告交付说明</h3>
                <p>
                  {{ reportJson.product?.description || "当前报告已进入正式版本化结构。" }}
                  目标用户：{{ reportJson.product?.targetUser || "正式交付前复核" }}。
                  预计页数约 {{ reportJson.delivery?.suggestedTotalPages || 0 }} 页。
                </p>
                <p class="table-note">
                  {{
                    reportJson.delivery?.manualReviewModules?.length
                      ? `仍需人工复核模块：${reportJson.delivery.manualReviewModules.join("、")}`
                      : "当前模板模块均已具备系统化输出结构。"
                  }}
                </p>
              </section>

              <section v-if="firstChoice" class="paper-section">
                <h3>第一志愿建议</h3>
                <p>
                  建议优先关注 {{ firstChoice.institutionName }} 的 {{ firstChoice.majorName }}
                  <template v-if="firstChoice.planGroupCode">（{{ firstChoice.planGroupCode }}）</template>，
                  所在城市为 {{ firstChoice.cityText || firstChoice.city || "待补充城市" }}。
                  历史最低分 {{ formatScore(firstChoice.minScore) }}，最低位次 {{ formatRank(firstChoice.minRank) }}，
                  与当前学生位次差为 {{ formatRankGap(firstChoice.rankGap) }}。
                </p>
                <p class="table-note">{{ firstChoice.recommendationReason }}</p>
              </section>

              <section v-if="paperRecommendations.length" class="paper-section">
                <h3>冲稳保推荐表</h3>
                <div class="paper-table-wrapper">
                  <table class="paper-table">
                    <thead>
                      <tr>
                        <th>梯度</th>
                        <th>院校</th>
                        <th>专业</th>
                        <th>专业组/代码</th>
                        <th>城市</th>
                        <th>最低分</th>
                        <th>最低位次</th>
                        <th>位次差</th>
                        <th>风险</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="item in paperRecommendations"
                        :key="`${item.institutionName}-${item.majorName}-${item.planGroupCode}-${item.bucket}`"
                      >
                        <td>{{ item.bucketLabel || item.bucket }}</td>
                        <td>{{ item.institutionName }}</td>
                        <td>{{ item.majorName }}</td>
                        <td>{{ item.planGroupCode || item.batchCode || "-" }}</td>
                        <td>{{ item.cityText || item.city || item.province || "-" }}</td>
                        <td>{{ formatScore(item.minScore) }}</td>
                        <td>{{ formatRank(item.minRank) }}</td>
                        <td>{{ formatRankGap(item.rankGap) }}</td>
                        <td>{{ item.riskLabel || "待复核" }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </section>

              <section class="paper-section">
                <h3>备选志愿与风险提醒</h3>
                <p v-if="alternatives.length">
                  备选志愿建议：
                  {{ alternatives.slice(0, 5).map((item) => `${item.institutionName}-${item.majorName}`).join("；") }}。
                </p>
                <p v-else>当前暂无可展示的备选志愿建议。</p>
                <p v-if="notRecommended.length" class="table-note">
                  当前不建议优先报考：
                  {{ notRecommended.slice(0, 5).map((item) => `${item.institutionName}-${item.majorName}`).join("；") }}。
                </p>
                <p v-if="topRiskNotes.length" class="table-note">
                  风险提醒：{{ topRiskNotes.join("；") }}
                </p>
              </section>

              <section class="paper-section auxiliary-section">
                <h3>辅助画像摘要</h3>
                <div class="auxiliary-grid">
                  <div>
                    <strong>适合专业方向</strong>
                    <p>{{ portraitRecommendation.recommendedMajorDirections.slice(0, 3).join("、") || "待补充画像信息" }}</p>
                    <p class="table-note">{{ portraitRecommendation.parentConcernMatch?.details || "待补充家长诉求说明" }}</p>
                  </div>
                  <div>
                    <strong>星座与出生信息</strong>
                    <p>
                      {{ derivedProfile.birthday || "待补充生日" }}
                      <template v-if="derivedProfile.birthTime"> / {{ derivedProfile.birthTime }}</template>
                      / {{ derivedProfile.constellation || "待补充星座" }}
                    </p>
                  </div>
                  <div>
                    <strong>四柱与时辰</strong>
                    <p>{{ fourPillars }}</p>
                    <p class="table-note">{{ derivedProfile.hourBranchLabel || "未录入出生时辰时，将只保留前三柱辅助分析。" }}</p>
                  </div>
                  <div>
                    <strong>性格与学习</strong>
                    <p>{{ derivedProfile.personalityTraits.join("、") || "待补充" }}</p>
                    <p class="table-note">{{ derivedProfile.learningStyle || "待补充学习风格说明" }}</p>
                  </div>
                  <div>
                    <strong>城市与发展路径</strong>
                    <p>{{ derivedProfile.regionPreferences.join("、") || "待补充城市偏好" }}</p>
                    <p class="table-note">{{ derivedProfile.developmentGoals.join("、") || "待补充发展目标" }}</p>
                  </div>
                </div>
                <p class="table-note auxiliary-note">
                  {{ portraitRecommendation.auxiliaryExplanation?.join(" ") || "画像辅助推荐仅用于解释专业方向与沟通逻辑，不参与录取概率计算。" }}
                </p>
              </section>

              <section
                v-for="section in sections"
                :key="section.title"
                class="paper-section"
                :class="{ 'paper-warning': section.warning }"
              >
                <h3>{{ section.title }}</h3>
                <p>{{ section.body }}</p>
              </section>

              <section v-if="boundaryNote" class="paper-section">
                <h3>接口边界说明</h3>
                <p>{{ boundaryNote }}</p>
              </section>

              <section class="paper-section paper-warning">
                <h3>合规免责说明</h3>
                <p>{{ disclaimer }}</p>
              </section>
            </section>

            <section v-if="reportJson.modules?.length" class="module-block">
              <header class="section-head">
                <div>
                  <strong>正式报告模块映射</strong>
                  <span>{{ reportJson.product?.description || "当前版本已按模板模块映射到正式 reportJson。" }}</span>
                </div>
              </header>
              <div class="module-grid">
                <article
                  v-for="module in reportJson.modules"
                  :key="module.moduleId"
                  class="module-card"
                >
                  <strong>{{ module.moduleName }}</strong>
                  <span>
                    约 {{ module.suggestedPages || 0 }} 页 /
                    {{ module.requiresManualReview ? "需人工复核" : "系统可直接生成" }}
                  </span>
                  <p>{{ module.coreContent || "待补充模块说明" }}</p>
                  <ul>
                    <li v-for="sectionTitle in module.sectionRefs" :key="sectionTitle">
                      {{ sectionTitle }}
                    </li>
                  </ul>
                </article>
              </div>
            </section>

            <section v-if="policyHighlights.length" class="policy-highlight-block">
              <header class="section-head">
                <div>
                  <strong>本省政策依据摘要</strong>
                  <span>用于解释当前志愿判断来自哪些政策规则和招生边界。</span>
                </div>
              </header>
              <div class="policy-highlight-grid">
                <article
                  v-for="item in policyHighlights"
                  :key="`${item.key}-${item.year}`"
                  class="policy-highlight-card"
                >
                  <strong>{{ item.title }}</strong>
                  <span>{{ item.year || "当年" }} / {{ item.source || "省级政策资料" }}</span>
                  <p>{{ item.summary }}</p>
                </article>
              </div>
            </section>

            <section class="traceability-grid">
              <article class="traceability-card">
                <header class="traceability-head">
                  <strong>咨询师补充备注</strong>
                  <span>这些内容会作为正式交付前的人工作业留痕。</span>
                </header>
                <div class="note-form">
                  <el-input v-model="noteForm.author_name" placeholder="咨询师姓名" />
                  <el-input v-model="noteForm.note_title" placeholder="备注标题，例如：与家长沟通重点" />
                  <el-input
                    v-model="noteForm.note_content"
                    type="textarea"
                    :rows="4"
                    placeholder="输入本次需要补充给报告的人工作业说明、特殊提醒或沟通结论。"
                  />
                  <div class="note-actions">
                    <el-button type="primary" :loading="savingNote" @click="submitAdvisorNote">
                      保存咨询师备注
                    </el-button>
                  </div>
                </div>
                <div v-if="advisorNotes.length" class="trace-list">
                  <article
                    v-for="note in advisorNotes"
                    :key="note.id"
                    class="trace-item"
                  >
                    <strong>{{ note.note_title || "未命名备注" }}</strong>
                    <span>{{ note.author_name || "咨询师" }} / {{ note.updated_at }}</span>
                    <p>{{ note.note_content }}</p>
                  </article>
                </div>
                <p v-else class="table-note">当前还没有咨询师补充备注，适合在人工复核后开始积累。</p>
              </article>

              <article class="traceability-card">
                <header class="traceability-head">
                  <strong>报告生成记录</strong>
                  <span>每次打开真实报告都会自动记录一条生成留痕。</span>
                </header>
                <div v-if="generationRecords.length" class="trace-list">
                  <article
                    v-for="record in generationRecords"
                    :key="record.id"
                    class="trace-item"
                  >
                    <strong>{{ record.report_title || reportTitle }}</strong>
                    <span>
                      {{ record.created_at }} / {{ record.generation_mode || "preview" }} / {{ record.generated_by || "system-preview" }}
                    </span>
                    <p>
                      {{ record.summary?.scoreLevel || "待补充分层" }}
                      <template v-if="record.summary?.matchedMajors?.length">
                        / {{ record.summary.matchedMajors.join("、") }}
                      </template>
                    </p>
                  </article>
                </div>
                <p v-else class="table-note">当前还没有生成记录。</p>
              </article>

              <article class="traceability-card">
                <header class="traceability-head">
                  <strong>导出与交付记录</strong>
                  <span>优先提供可直接访问的下载入口，并保留生成时间、操作人与文件留痕信息。</span>
                </header>
                <div v-if="deliveryRecords.length" class="trace-list">
                  <article
                    v-for="record in deliveryRecords"
                    :key="record.id"
                    class="trace-item"
                  >
                    <div class="trace-item-head">
                      <strong>{{ record.export_format?.toUpperCase() }} / {{ record.report_title || reportTitle }}</strong>
                      <el-tag :type="record.artifactExists ? 'success' : 'danger'">
                        {{ record.artifactExists ? "文件可下载" : "文件缺失" }}
                      </el-tag>
                    </div>
                    <span>{{ record.created_at }} / {{ record.generated_by || "system-export" }}</span>
                    <p>{{ record.artifact_name }}</p>
                    <div class="trace-download-row">
                      <el-button
                        type="primary"
                        plain
                        size="small"
                        :disabled="!record.artifactExists"
                        :loading="downloadingRecordId === record.id"
                        @click="handleDeliveryDownload(record)"
                      >
                        下载 {{ record.export_format?.toUpperCase() || "文件" }}
                      </el-button>
                      <span class="table-note">
                        {{ record.artifactSizeBytes ? formatFileSize(record.artifactSizeBytes) : "待补充文件大小" }}
                      </span>
                    </div>
                    <p class="table-note">留痕路径：{{ record.artifactPathLabel || record.artifact_path }}</p>
                  </article>
                </div>
                <p v-else class="table-note">当前还没有导出记录，正式导出后会自动留痕。</p>
              </article>
            </section>
          </el-card>
        </div>

        <el-card v-else shadow="never" class="panel-card">
          <div class="empty-state">
            <strong>暂无可用报告</strong>
            <p>请先录入真实学生档案，再生成正式报告预览。</p>
          </div>
        </el-card>
      </template>
    </el-skeleton>
  </section>
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

.trace-item-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.trace-download-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.product-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.product-switch {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.product-pill {
  border: 1px solid rgba(66, 133, 244, 0.16);
  background: rgba(66, 133, 244, 0.06);
  color: var(--app-text-secondary);
  border-radius: 999px;
  padding: 8px 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.product-pill.active {
  background: linear-gradient(135deg, rgba(66, 133, 244, 0.18), rgba(66, 133, 244, 0.08));
  color: var(--app-text-primary);
  border-color: rgba(66, 133, 244, 0.3);
}

.product-catalog {
  display: grid;
  gap: 12px;
  margin-bottom: 20px;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.product-catalog-card,
.module-card {
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
.product-catalog-card span,
.module-card strong,
.module-card span {
  display: block;
}

.product-catalog-card p,
.module-card p {
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

.report-summary-grid {
  display: grid;
  gap: 14px;
  margin-bottom: 20px;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}

.summary-card {
  padding: 16px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(66, 133, 244, 0.12), rgba(66, 133, 244, 0.04));
  border: 1px solid rgba(66, 133, 244, 0.12);
}

.summary-card span {
  display: block;
  margin-bottom: 6px;
  color: var(--app-text-secondary);
  font-size: 13px;
}

.summary-card strong {
  display: block;
  margin-bottom: 6px;
  color: var(--app-text-primary);
  font-size: 16px;
}

.summary-card p {
  margin: 0;
  color: var(--app-text-secondary);
  line-height: 1.6;
}

.formal-report-block,
.module-block,
.policy-highlight-block {
  margin-bottom: 20px;
  padding: 18px;
  border-radius: 20px;
  border: 1px solid rgba(66, 133, 244, 0.12);
  background: linear-gradient(180deg, rgba(66, 133, 244, 0.08), rgba(66, 133, 244, 0.03));
}

.section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.section-head.compact {
  margin-bottom: 12px;
}

.section-head strong,
.section-head span {
  display: block;
}

.section-head span {
  margin-top: 4px;
  color: var(--app-text-secondary);
  font-size: 13px;
  line-height: 1.6;
}

.bucket-summary-grid,
.module-grid,
.policy-highlight-grid,
.decision-grid,
.auxiliary-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.bucket-stat-card,
.decision-card,
.policy-highlight-card {
  padding: 14px 16px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(66, 133, 244, 0.1);
}

.bucket-stat-head,
.decision-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.bucket-stat-card strong,
.policy-highlight-card strong,
.decision-card strong,
.trace-item strong {
  display: block;
}

.bucket-stat-card p,
.policy-highlight-card p,
.decision-card p {
  margin: 0 0 10px;
  line-height: 1.7;
}

.bucket-stat-card span,
.policy-highlight-card span,
.decision-card span {
  color: var(--app-text-secondary);
  font-size: 12px;
}

.first-choice-card {
  margin: 18px 0;
  padding: 18px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid rgba(66, 133, 244, 0.14);
}

.first-choice-main {
  display: grid;
  gap: 18px;
  grid-template-columns: minmax(0, 1fr) minmax(280px, 360px);
  margin-bottom: 16px;
}

.first-choice-main h3 {
  margin: 0 0 6px;
  font-size: 22px;
}

.first-choice-main p,
.first-choice-main span {
  margin: 0;
  color: var(--app-text-secondary);
}

.choice-metrics,
.choice-grid {
  display: grid;
  gap: 12px;
}

.choice-metrics {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.choice-metrics div,
.choice-grid article {
  padding: 12px 14px;
  border-radius: 14px;
  background: rgba(66, 133, 244, 0.06);
  border: 1px solid rgba(66, 133, 244, 0.1);
}

.choice-metrics small,
.choice-grid strong {
  display: block;
  color: var(--app-text-secondary);
}

.choice-metrics strong {
  display: block;
  margin-top: 6px;
  font-size: 16px;
}

.choice-grid {
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.choice-grid p {
  margin: 8px 0 0;
  line-height: 1.7;
}

.bucket-table-stack {
  display: grid;
  gap: 14px;
}

.bucket-table-block {
  padding: 14px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(66, 133, 244, 0.1);
}

.report-table :deep(.el-table__cell) {
  vertical-align: top;
}

.cell-stack,
.reason-stack {
  display: grid;
  gap: 4px;
}

.cell-stack strong,
.reason-stack p {
  margin: 0;
}

.cell-stack span,
.reason-stack span {
  color: var(--app-text-secondary);
  font-size: 12px;
  line-height: 1.6;
}

.table-empty {
  padding: 18px;
  text-align: center;
  color: var(--app-text-secondary);
  border: 1px dashed rgba(66, 133, 244, 0.2);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.74);
}

.decision-list {
  display: grid;
  gap: 10px;
}

.decision-item {
  padding: 12px 14px;
  border-radius: 14px;
  background: rgba(66, 133, 244, 0.05);
  border: 1px solid rgba(66, 133, 244, 0.08);
}

.decision-item-danger {
  background: rgba(245, 108, 108, 0.06);
  border-color: rgba(245, 108, 108, 0.12);
}

.decision-item p {
  margin: 8px 0 0;
}

.paper-table-wrapper {
  overflow-x: auto;
}

.paper-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.paper-table th,
.paper-table td {
  padding: 10px 8px;
  border: 1px solid #e5edf5;
  text-align: left;
  vertical-align: top;
  line-height: 1.6;
}

.paper-table th {
  background: #f6f9fd;
  color: var(--app-text-secondary);
  font-weight: 600;
}

.auxiliary-section {
  background: rgba(66, 133, 244, 0.04);
}

.auxiliary-grid strong {
  display: block;
  margin-bottom: 6px;
  color: var(--app-text-primary);
}

.auxiliary-grid p {
  margin: 0 0 6px;
}

.auxiliary-note {
  margin-top: 14px;
}

.traceability-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
}

.traceability-card {
  padding: 18px;
  border-radius: 20px;
  border: 1px solid rgba(66, 133, 244, 0.12);
  background: linear-gradient(180deg, rgba(66, 133, 244, 0.06), rgba(66, 133, 244, 0.02));
}

.traceability-head {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 14px;
}

.traceability-head span {
  color: var(--app-text-secondary);
  font-size: 13px;
}

.note-form {
  display: grid;
  gap: 10px;
  margin-bottom: 14px;
}

.note-actions {
  display: flex;
  justify-content: flex-end;
}

.trace-list {
  display: grid;
  gap: 10px;
}

.trace-item {
  padding: 12px 14px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid rgba(66, 133, 244, 0.08);
}

.trace-item span {
  display: block;
  margin: 6px 0 8px;
  color: var(--app-text-secondary);
  font-size: 12px;
}

.trace-item p {
  margin: 0;
  line-height: 1.7;
}

@media (max-width: 1199px) {
  .first-choice-main {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 767px) {
  .result-source-head,
  .section-head,
  .bucket-stat-head,
  .decision-head,
  .product-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .choice-metrics {
    grid-template-columns: 1fr;
  }
}
</style>
