<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { fetchStudentDetail, fetchStudentScoreRecords } from "../api/planning.js";
import PageHeader from "../components/PageHeader.vue";
import StatusTag from "../components/StatusTag.vue";

const route = useRoute();
const router = useRouter();

const loading = ref(true);
const student = ref(null);
const scoreRecords = ref([]);

const fourPillars = computed(() => {
  if (!student.value?.derived_profile?.pillars) {
    return "待补充";
  }
  return [
    student.value.derived_profile.pillars.year,
    student.value.derived_profile.pillars.month,
    student.value.derived_profile.pillars.day,
    student.value.derived_profile.pillars.hour
  ]
    .filter(Boolean)
    .join(" / ") || "待补充";
});

const hasBaseInfo = computed(() => {
  const current = student.value ?? {};
  return Boolean(
    current.name &&
      current.province &&
      current.exam_year &&
      current.subject_group &&
      current.admission_batch &&
      (current.final_score ?? current.final_rank ?? current.rank ?? current.total_score)
  );
});

const hasPortraitInfo = computed(() => {
  const current = student.value ?? {};
  return Boolean(
    current.birthday ||
      current.birth_time ||
      current.target_direction ||
      current.interest_preferences ||
      current.development_goal ||
      current.parent_focus ||
      current.derived_profile?.profile?.personalityTraits?.length
  );
});

const canBuildMajorAdvice = computed(() => hasBaseInfo.value);
const canBuildPlan = computed(() => hasBaseInfo.value);
const canChooseReportVersion = computed(() => hasBaseInfo.value);
const canExportReport = computed(() => hasBaseInfo.value);

function buildStepTarget(name) {
  const studentId = String(student.value?.id || route.params.studentId || "");
  if (name === "student-detail") {
    return { name, params: { studentId } };
  }
  if (["analysis", "majors", "plan", "reports", "intake"].includes(name)) {
    return { name, query: { studentId } };
  }
  return { name };
}

function goTo(name) {
  router.push(buildStepTarget(name));
}

const nextAction = computed(() => {
  if (!hasBaseInfo.value) {
    return {
      title: "先完善基础信息",
      detail: "补齐省份、选科、批次、成绩和位次后，后续专业与志愿匹配才会更稳定。",
      buttonLabel: "去完善档案",
      routeName: "intake"
    };
  }
  if (!hasPortraitInfo.value) {
    return {
      title: "补充画像信息",
      detail: "建议补充生日、兴趣、目标和家长关注点，再看画像分析和专业解释会更完整。",
      buttonLabel: "去补画像信息",
      routeName: "intake"
    };
  }
  return {
    title: "进入画像分析",
    detail: "基础信息和画像信息已具备，建议先看画像分析，再继续生成专业推荐和志愿方案。",
    buttonLabel: "查看画像分析",
    routeName: "analysis"
  };
});

const flowSteps = computed(() => {
  const current = student.value ?? {};
  return [
    {
      key: "base",
      step: "01",
      title: "录入个人信息",
      statusLabel: hasBaseInfo.value ? "已完成" : "待补充",
      statusVariant: hasBaseInfo.value ? "success" : "warning",
      summary: hasBaseInfo.value
        ? `${current.province || "待补充"} / ${current.subject_group || "待补充"} / ${current.admission_batch || "待补充"}`
        : "当前还需要补齐省份、选科、批次、成绩和位次。",
      nextHint: hasBaseInfo.value ? "如需修正分数、位次或偏好，可继续编辑档案。" : "先补齐基础档案，后续页面才有稳定结果。",
      buttonLabel: hasBaseInfo.value ? "编辑档案" : "去完善档案",
      routeName: "intake"
    },
    {
      key: "portrait",
      step: "02",
      title: "分析个人画像",
      statusLabel: hasPortraitInfo.value ? "已就绪" : "待补充",
      statusVariant: hasPortraitInfo.value ? "success" : "warning",
      summary: hasPortraitInfo.value
        ? `${current.constellation || "画像已生成"} / ${current.target_direction || "方向待补充"}`
        : "建议补充生日、兴趣、发展目标和家长关注点。",
      nextHint: hasPortraitInfo.value ? "下一步可以先查看画像分析，再进入专业推荐。" : "先补画像字段，再看个性、天赋和适合方向会更完整。",
      buttonLabel: hasPortraitInfo.value ? "查看画像分析" : "去补画像信息",
      routeName: hasPortraitInfo.value ? "analysis" : "intake"
    },
    {
      key: "major",
      step: "03",
      title: "生成专业方向建议",
      statusLabel: canBuildMajorAdvice.value ? "可生成" : "待基础信息",
      statusVariant: canBuildMajorAdvice.value ? "primary" : "warning",
      summary: canBuildMajorAdvice.value
        ? "已具备生成专业方向建议条件，可结合画像解释看适合方向。"
        : "需要先完成基础信息录入。",
      nextHint: canBuildMajorAdvice.value
        ? "下一步：查看适合什么专业，以及为什么适合。"
        : "先回到档案页补齐基础信息。",
      buttonLabel: canBuildMajorAdvice.value ? "去看专业推荐" : "先完善档案",
      routeName: canBuildMajorAdvice.value ? "majors" : "intake"
    },
    {
      key: "plan",
      step: "04",
      title: "匹配院校和专业",
      statusLabel: canBuildPlan.value ? "可生成" : "待补成绩/位次",
      statusVariant: canBuildPlan.value ? "primary" : "warning",
      summary: canBuildPlan.value
        ? "可以开始看哪些城市、哪些学校、哪些专业更匹配。"
        : "需要先补齐正式成绩、位次和批次信息。",
      nextHint: canBuildPlan.value ? "下一步：生成冲稳保志愿方案。" : "先完善成绩与位次数据。",
      buttonLabel: canBuildPlan.value ? "去生成志愿方案" : "先完善档案",
      routeName: canBuildPlan.value ? "plan" : "intake"
    },
    {
      key: "version",
      step: "05",
      title: "选择报告版本",
      statusLabel: canChooseReportVersion.value ? "可选择" : "待方案准备",
      statusVariant: canChooseReportVersion.value ? "primary" : "warning",
      summary: canChooseReportVersion.value
        ? "已可以对比 99 / 399 / 699 / 999 报告版本差异。"
        : "建议先完成志愿方案生成，再进入正式报告页。",
      nextHint: canChooseReportVersion.value ? "下一步：进入报告页选择合适价位版本。" : "先完成前面的基础和志愿方案步骤。",
      buttonLabel: canChooseReportVersion.value ? "去选报告版本" : "先完善前置步骤",
      routeName: canChooseReportVersion.value ? "reports" : "intake"
    },
    {
      key: "export",
      step: "06",
      title: "下载报告",
      statusLabel: canExportReport.value ? "可生成" : "待报告准备",
      statusVariant: canExportReport.value ? "primary" : "warning",
      summary: canExportReport.value
        ? "当前已可以进入报告页生成并下载 PDF / Word。"
        : "前置数据不足，暂不建议直接导出报告。",
      nextHint: canExportReport.value ? "下一步：进入报告页生成并下载正式报告。" : "先把前面的资料和方案补完整。",
      buttonLabel: canExportReport.value ? "去生成并下载报告" : "先完善前置步骤",
      routeName: canExportReport.value ? "reports" : "intake"
    }
  ];
});

const completedFlowCount = computed(() => flowSteps.value.filter((item) => item.statusLabel === "已完成" || item.statusLabel === "已就绪").length);

async function loadPageData() {
  loading.value = true;
  const studentId = Number(route.params.studentId);
  student.value = await fetchStudentDetail(studentId);
  const records = await fetchStudentScoreRecords(studentId);
  scoreRecords.value = records.rows ?? [];
  loading.value = false;
}

watch(
  () => route.params.studentId,
  () => {
    loadPageData();
  }
);

onMounted(() => {
  loadPageData();
});
</script>

<template>
  <section class="page">
    <PageHeader
      :breadcrumb="student ? `学生管理 / ${student.name} / 学生工作台` : '学生管理 / 学生工作台'"
      title="学生工作台"
      description="这里是当前学生的核心业务入口。按“录入信息 -> 看画像 -> 看专业方向 -> 看志愿方案 -> 选报告版本 -> 下载报告”的顺序往下走即可。"
    >
      <template #actions>
        <el-button @click="goTo('intake')">编辑档案</el-button>
        <el-button type="primary" @click="goTo(nextAction.routeName)">{{ nextAction.buttonLabel }}</el-button>
      </template>
    </PageHeader>

    <el-skeleton :loading="loading" animated :rows="12">
      <template #default>
        <template v-if="student">
          <div class="summary-grid">
            <el-card shadow="never" class="panel-card summary-card">
              <h3>正式高考成绩</h3>
              <strong class="summary-value">{{ student.final_score ?? "待补充" }}</strong>
              <p>正式方案优先使用正式高考成绩</p>
            </el-card>
            <el-card shadow="never" class="panel-card summary-card">
              <h3>全省位次</h3>
              <strong class="summary-value">{{ student.final_rank ?? student.rank ?? "待补充" }}</strong>
              <p>正式方案优先使用官方全省位次</p>
            </el-card>
            <el-card shadow="never" class="panel-card summary-card">
              <h3>流程进度</h3>
              <strong class="summary-value">{{ completedFlowCount }}/6</strong>
              <p>已完成基础资料与画像准备，后续按工作台步骤继续推进</p>
            </el-card>
          </div>

          <el-card shadow="never" class="panel-card workflow-card">
            <div class="workflow-head">
              <div>
                <h2>主流程工作台</h2>
                <p class="table-note">不要在多个页面之间来回找入口，直接从这里顺着做下一步。</p>
              </div>
              <StatusTag :label="nextAction.title" variant="primary" />
            </div>

            <div class="next-action-banner">
              <div>
                <strong>{{ nextAction.title }}</strong>
                <p>{{ nextAction.detail }}</p>
              </div>
              <el-button type="primary" @click="goTo(nextAction.routeName)">
                {{ nextAction.buttonLabel }}
              </el-button>
            </div>

            <div class="workflow-grid">
              <article
                v-for="item in flowSteps"
                :key="item.key"
                class="workflow-step"
              >
                <div class="workflow-step-head">
                  <div>
                    <span class="workflow-step-index">步骤 {{ item.step }}</span>
                    <h3>{{ item.title }}</h3>
                  </div>
                  <StatusTag :label="item.statusLabel" :variant="item.statusVariant" />
                </div>

                <p class="workflow-summary">{{ item.summary }}</p>
                <p class="workflow-hint">下一步：{{ item.nextHint }}</p>

                <div class="workflow-actions">
                  <el-button type="primary" plain @click="goTo(item.routeName)">
                    {{ item.buttonLabel }}
                  </el-button>
                </div>
              </article>
            </div>
          </el-card>

          <div class="detail-grid">
            <el-card shadow="never" class="panel-card">
              <div class="section-head">
                <div>
                  <h2>正式决策总览</h2>
                  <p class="table-note">只用于正式志愿判断的硬条件字段。</p>
                </div>
                <StatusTag label="硬条件" variant="primary" />
              </div>
              <div class="kv-grid">
                <div><strong>省份</strong><span>{{ student.province || "待补充" }}</span></div>
                <div><strong>考试类型</strong><span>{{ student.exam_type_label }}</span></div>
                <div><strong>选科组合</strong><span>{{ student.subject_group || "待补充" }}</span></div>
                <div><strong>批次</strong><span>{{ student.admission_batch || "待补充" }}</span></div>
                <div><strong>学校偏好</strong><span>{{ student.school_preference || "待补充" }}</span></div>
                <div><strong>地域要求</strong><span>{{ student.region_preference || "待补充" }}</span></div>
                <div><strong>是否接受调剂</strong><span>{{ student.accept_adjustment || "待补充" }}</span></div>
                <div><strong>是否接受高收费项目</strong><span>{{ student.accept_high_fee_programs || "待补充" }}</span></div>
              </div>
            </el-card>

            <el-card shadow="never" class="panel-card">
              <div class="section-head">
                <div>
                  <h2>画像辅助字段</h2>
                  <p class="table-note">这些字段只用于专业方向推荐、适配理由解释和家长沟通。</p>
                </div>
                <StatusTag label="辅助解释" variant="review" />
              </div>
              <div class="kv-grid">
                <div><strong>阳历生日</strong><span>{{ student.birthday || "待补充" }}</span></div>
                <div><strong>出生时辰</strong><span>{{ student.birth_time || "待补充" }}</span></div>
                <div><strong>星座</strong><span>{{ student.constellation || "待补充" }}</span></div>
                <div><strong>四柱</strong><span>{{ fourPillars }}</span></div>
                <div><strong>专业偏好</strong><span>{{ student.target_direction || "待补充" }}</span></div>
                <div><strong>兴趣标签</strong><span>{{ student.interest_preferences || "待补充" }}</span></div>
                <div><strong>发展目标</strong><span>{{ student.development_goal || "待补充" }}</span></div>
                <div><strong>家长关注点</strong><span>{{ student.parent_focus || "待补充" }}</span></div>
              </div>

              <div class="tag-wrap">
                <el-tag
                  v-for="item in student.derived_profile?.profile?.personalityTraits ?? []"
                  :key="item"
                  class="soft-tag"
                  effect="plain"
                >
                  {{ item }}
                </el-tag>
              </div>
              <p class="table-note detail-note">
                {{ student.derived_profile?.disclaimer || "画像辅助字段只用于解释，不替代真实录取规则。" }}
              </p>
            </el-card>
          </div>

          <el-card shadow="never" class="panel-card">
            <div class="section-head">
              <div>
                <h2>历史成绩归档（估分 / 模拟 / 阶段成绩）</h2>
                <p class="table-note">允许保留展示，但正式推荐默认不把这些成绩作为核心依据。</p>
              </div>
              <StatusTag label="仅展示" variant="warning" />
            </div>
            <el-table :data="scoreRecords" stripe>
              <el-table-column prop="score_source" label="成绩来源" min-width="120" />
              <el-table-column prop="total_score" label="总分" min-width="100" />
              <el-table-column prop="ranking" label="位次" min-width="100" />
              <el-table-column prop="note" label="备注" min-width="220" show-overflow-tooltip />
              <el-table-column prop="updated_at" label="更新时间" min-width="180" />
            </el-table>
            <p v-if="!scoreRecords.length" class="table-note">当前还没有录入历史估分或模拟成绩。</p>
          </el-card>
        </template>
      </template>
    </el-skeleton>
  </section>
</template>

<style scoped>
.detail-grid,
.kv-grid {
  display: grid;
  gap: 16px;
}

.detail-grid {
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  margin-bottom: 16px;
}

.section-head,
.workflow-head,
.workflow-step-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.section-head {
  margin-bottom: 14px;
}

.section-head h2,
.workflow-head h2,
.workflow-step-head h3 {
  margin: 0 0 6px;
}

.kv-grid {
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
}

.kv-grid div {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.tag-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 16px;
}

.detail-note {
  margin-top: 14px;
}

.workflow-card {
  margin-bottom: 16px;
}

.next-action-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 18px 20px;
  border-radius: 16px;
  margin: 18px 0 22px;
  background:
    linear-gradient(135deg, rgba(21, 101, 192, 0.08), rgba(0, 137, 123, 0.08)),
    #ffffff;
  border: 1px solid rgba(21, 101, 192, 0.12);
}

.next-action-banner strong {
  display: block;
  margin-bottom: 8px;
}

.next-action-banner p,
.workflow-summary,
.workflow-hint {
  color: var(--el-text-color-secondary);
}

.workflow-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
}

.workflow-step {
  padding: 18px;
  border-radius: 16px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.95), #ffffff);
}

.workflow-step-index {
  display: inline-block;
  margin-bottom: 8px;
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--el-text-color-secondary);
}

.workflow-summary {
  min-height: 44px;
  margin: 14px 0 10px;
  line-height: 1.7;
}

.workflow-hint {
  min-height: 48px;
  margin: 0 0 14px;
  line-height: 1.7;
}

.workflow-actions {
  display: flex;
  justify-content: flex-start;
}

@media (max-width: 768px) {
  .section-head,
  .workflow-head,
  .workflow-step-head,
  .next-action-banner {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
