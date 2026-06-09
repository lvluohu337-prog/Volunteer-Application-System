<script setup>
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import PageHeader from "../components/PageHeader.vue";
import PanelSection from "../components/PanelSection.vue";
import {
  fetchDemoReport399,
  fetchDemoReport99,
  fetchFoundationSampleStudents
} from "../api/planning.js";
import { COMPLIANCE_DISCLAIMER } from "../constants/compliance.js";

const studentsLoading = ref(false);
const reportLoading = ref(false);
const sampleStudents = ref([]);
const selectedStudentId = ref();
const report = ref(null);

const selectedStudent = computed(() =>
  sampleStudents.value.find((item) => item.id === selectedStudentId.value) ?? null
);

async function loadStudents() {
  studentsLoading.value = true;
  try {
    const data = await fetchFoundationSampleStudents();
    sampleStudents.value = data.rows ?? [];
    if (!selectedStudentId.value && sampleStudents.value.length > 0) {
      selectedStudentId.value = sampleStudents.value[0].id;
    }
  } catch (error) {
    ElMessage.error(error.message || "样例学生加载失败");
  } finally {
    studentsLoading.value = false;
  }
}

async function generateReport(productCode) {
  if (!selectedStudentId.value) {
    ElMessage.warning("请先选择样例学生");
    return;
  }

  reportLoading.value = true;
  try {
    report.value =
      productCode === "99"
        ? await fetchDemoReport99(selectedStudentId.value)
        : await fetchDemoReport399(selectedStudentId.value);
  } catch (error) {
    ElMessage.error(error.message || "报告生成失败");
  } finally {
    reportLoading.value = false;
  }
}

onMounted(async () => {
  await loadStudents();
  if (selectedStudentId.value) {
    await generateReport("99");
  }
});
</script>

<template>
  <section class="page">
    <PageHeader
      breadcrumb="演示报告 / 99 元与 399 元"
      title="报告演示页面"
      description="选择样例学生后可直接生成 99 元或 399 元报告演示版，内容基于已导入的专业大类、城市产业、样例学生和模板字段规则生成。"
    />

    <div class="report-demo-layout">
      <PanelSection
        title="演示控制台"
        description="可切换样例学生，并按产品档位生成对应的规则版演示报告。"
      >
        <div class="demo-control-stack">
          <el-form label-position="top">
            <el-form-item label="选择样例学生">
              <el-select
                v-model="selectedStudentId"
                placeholder="请选择样例学生"
                filterable
                :loading="studentsLoading"
              >
                <el-option
                  v-for="item in sampleStudents"
                  :key="item.id"
                  :label="`${item.name} / ${item.province} / ${item.subject_track}`"
                  :value="item.id"
                />
              </el-select>
            </el-form-item>
          </el-form>

          <div v-if="selectedStudent" class="sample-student-card">
            <strong>{{ selectedStudent.name }}</strong>
            <p>{{ selectedStudent.province }} / {{ selectedStudent.subject_track }}</p>
            <p>预估分：{{ selectedStudent.estimated_score }} / 预估位次：{{ selectedStudent.estimated_rank }}</p>
            <p>推荐专业：{{ selectedStudent.recommended_major_directions }}</p>
            <p>推荐城市：{{ selectedStudent.recommended_cities }}</p>
          </div>

          <div class="page-actions">
            <el-button @click="generateReport('99')">生成 99 元报告</el-button>
            <el-button type="primary" @click="generateReport('399')">生成 399 元报告</el-button>
          </div>
        </div>
      </PanelSection>

      <PanelSection
        title="报告预览"
        description="演示版报告用于验证规则、字段和页面呈现，不替代正式人工交付。"
      >
        <el-skeleton :loading="reportLoading" animated :rows="10">
          <template #default>
            <div v-if="report" class="demo-report-stack">
              <el-card shadow="never" class="panel-card report-summary-card">
                <div class="panel-head">
                  <div>
                    <h2>{{ report.report_title }}</h2>
                    <p>{{ report.report_summary }}</p>
                  </div>
                  <el-tag type="primary">{{ report.product_label }}</el-tag>
                </div>
                <p class="table-note">{{ report.boundary_note }}</p>
              </el-card>

              <el-card shadow="never" class="panel-card">
                <h3 class="section-title">模板模块</h3>
                <div class="template-module-list">
                  <span
                    v-for="item in report.template_modules"
                    :key="`${item.product_name}-${item.module_name}`"
                    class="module-chip"
                  >
                    {{ item.module_name }}
                  </span>
                </div>
              </el-card>

              <el-card
                v-if="report.volunteer_recommendation"
                shadow="never"
                class="panel-card volunteer-plan-card"
              >
                <div class="panel-head">
                  <div>
                    <h3 class="section-title">{{ report.volunteer_recommendation.title }}</h3>
                    <p>{{ report.volunteer_recommendation.first_choice_advice }}</p>
                  </div>
                </div>

                <div class="volunteer-plan-grid">
                  <section
                    v-for="group in [
                      { key: 'rush', title: '冲刺院校' },
                      { key: 'steady', title: '稳妥院校' },
                      { key: 'safe', title: '保底院校' }
                    ]"
                    :key="group.key"
                    class="volunteer-plan-group"
                  >
                    <h4>{{ group.title }}</h4>
                    <div
                      v-for="item in report.volunteer_recommendation[group.key]"
                      :key="`${group.key}-${item.institution_name}-${item.recommended_major}`"
                      class="volunteer-plan-item"
                    >
                      <div class="volunteer-plan-item-head">
                        <strong>{{ item.institution_name }}</strong>
                        <el-tag size="small" type="success">{{ item.match_level }}</el-tag>
                      </div>
                      <p>推荐专业：{{ item.recommended_major }}</p>
                      <p>推荐理由：{{ item.recommended_reason }}</p>
                      <p>风险提示：{{ item.risk_tip }}</p>
                    </div>
                  </section>
                </div>

                <div class="volunteer-plan-summary">
                  <p>{{ report.volunteer_recommendation.final_order_advice }}</p>
                </div>
              </el-card>

              <div class="demo-report-section-list">
                <el-card
                  v-for="section in report.sections"
                  :key="section.title"
                  shadow="never"
                  class="panel-card"
                  :class="{ 'paper-warning': section.warning }"
                >
                  <h3 class="section-title">{{ section.title }}</h3>
                  <p>{{ section.body }}</p>
                  <ul class="line-list">
                    <li v-for="item in section.bullets" :key="item">{{ item }}</li>
                  </ul>
                </el-card>
              </div>

              <el-card shadow="never" class="panel-card disclaimer-card">
                <div>
                  <strong>统一免责声明</strong>
                  <p>{{ report.disclaimer || COMPLIANCE_DISCLAIMER }}</p>
                </div>
              </el-card>
            </div>

            <div v-else class="empty-state">
              <strong>尚未生成报告</strong>
              <span>请选择样例学生后生成 99 元或 399 元演示报告。</span>
            </div>
          </template>
        </el-skeleton>
      </PanelSection>
    </div>
  </section>
</template>

<style scoped>
.volunteer-plan-card,
.volunteer-plan-group,
.volunteer-plan-item {
  border-radius: 20px;
}

.volunteer-plan-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.volunteer-plan-group {
  padding: 16px;
  background: linear-gradient(180deg, rgba(247, 242, 232, 0.9), rgba(255, 255, 255, 0.98));
  border: 1px solid rgba(192, 146, 92, 0.2);
}

.volunteer-plan-group h4 {
  margin: 0 0 12px;
}

.volunteer-plan-item {
  padding: 14px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(210, 182, 146, 0.35);
}

.volunteer-plan-item + .volunteer-plan-item {
  margin-top: 12px;
}

.volunteer-plan-item-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.volunteer-plan-item p,
.volunteer-plan-summary p {
  margin: 8px 0 0;
  line-height: 1.7;
}

.volunteer-plan-summary {
  margin-top: 16px;
  padding: 16px 18px;
  border-radius: 18px;
  background: rgba(249, 247, 240, 0.92);
  border: 1px dashed rgba(176, 132, 79, 0.45);
}
</style>
