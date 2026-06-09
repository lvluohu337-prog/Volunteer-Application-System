<script setup>
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import PageHeader from "../components/PageHeader.vue";
import PanelSection from "../components/PanelSection.vue";
import {
  fetchFoundationCities,
  fetchFoundationMajors,
  fetchFoundationReportTemplateFields,
  fetchFoundationSampleStudents
} from "../api/planning.js";
import { COMPLIANCE_DISCLAIMER } from "../constants/compliance.js";

const loading = ref(false);
const activeTab = ref("majors");
const majorRows = ref([]);
const cityRows = ref([]);
const sampleStudentRows = ref([]);
const templateRows = ref([]);

const summaryItems = computed(() => [
  { title: "专业大类", value: majorRows.value.length, note: "来自 Excel《专业大类库》" },
  { title: "城市产业", value: cityRows.value.length, note: "来自 Excel《城市产业库》" },
  { title: "样例学生", value: sampleStudentRows.value.length, note: "来自 Excel《样例学生数据》" },
  { title: "模板字段", value: templateRows.value.length, note: "来自 Excel《报告模板字段》" }
]);

async function loadPageData() {
  loading.value = true;
  try {
    const [majorsData, citiesData, studentsData, templatesData] = await Promise.all([
      fetchFoundationMajors(),
      fetchFoundationCities(),
      fetchFoundationSampleStudents(),
      fetchFoundationReportTemplateFields()
    ]);
    majorRows.value = majorsData.rows ?? [];
    cityRows.value = citiesData.rows ?? [];
    sampleStudentRows.value = studentsData.rows ?? [];
    templateRows.value = templatesData.rows ?? [];
  } catch (error) {
    ElMessage.error(error.message || "基础数据加载失败");
  } finally {
    loading.value = false;
  }
}

onMounted(loadPageData);
</script>

<template>
  <section class="page">
    <PageHeader
      breadcrumb="基础数据 / Excel 导入结果"
      title="基础数据查看"
      description="集中查看本次 Excel 数据包导入后的 4 类基础数据，便于核对字段、内容和后续报告演示引用情况。"
    >
      <template #actions>
        <el-button type="primary" @click="loadPageData">刷新数据</el-button>
      </template>
    </PageHeader>

    <div class="summary-grid">
      <el-card
        v-for="item in summaryItems"
        :key="item.title"
        shadow="never"
        class="panel-card summary-card"
      >
        <h3>{{ item.title }}</h3>
        <strong class="summary-value">{{ item.value }}</strong>
        <p>{{ item.note }}</p>
      </el-card>
    </div>

    <PanelSection
      title="数据明细"
      description="以下页面仅用于查看导入结果与演示数据，不代表正式录取结论。"
    >
      <el-tabs v-model="activeTab" class="dataset-tabs">
        <el-tab-pane label="专业大类库" name="majors">
          <el-table :data="majorRows" stripe v-loading="loading">
            <el-table-column prop="category_name" label="专业大类" min-width="140" />
            <el-table-column prop="representative_majors" label="代表专业" min-width="220" show-overflow-tooltip />
            <el-table-column prop="suitable_traits" label="适合学生特质" min-width="200" show-overflow-tooltip />
            <el-table-column prop="subject_requirement_reference" label="选科要求参考" min-width="180" show-overflow-tooltip />
            <el-table-column prop="matching_cities_industries" label="适配城市/产业" min-width="220" show-overflow-tooltip />
            <el-table-column prop="risk_notes" label="主要风险" min-width="180" show-overflow-tooltip />
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="城市产业库" name="cities">
          <el-table :data="cityRows" stripe v-loading="loading">
            <el-table-column prop="city_name" label="城市/城市群" min-width="140" />
            <el-table-column prop="region" label="区域" min-width="120" />
            <el-table-column prop="pace" label="节奏" min-width="100" />
            <el-table-column prop="leading_industries" label="主导产业" min-width="220" show-overflow-tooltip />
            <el-table-column prop="suitable_major_directions" label="适合专业方向" min-width="200" show-overflow-tooltip />
            <el-table-column prop="risk_tips" label="风险提示" min-width="180" show-overflow-tooltip />
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="样例学生数据" name="students">
          <el-table :data="sampleStudentRows" stripe v-loading="loading">
            <el-table-column prop="sample_code" label="编号" min-width="80" />
            <el-table-column prop="name" label="姓名" min-width="120" />
            <el-table-column prop="province" label="省份" min-width="100" />
            <el-table-column prop="subject_track" label="选科/科类" min-width="180" />
            <el-table-column prop="estimated_score" label="预估分" min-width="100" />
            <el-table-column prop="estimated_rank" label="预估位次" min-width="120" />
            <el-table-column prop="recommended_major_directions" label="推荐专业方向" min-width="220" show-overflow-tooltip />
            <el-table-column prop="recommended_cities" label="推荐城市" min-width="180" show-overflow-tooltip />
            <el-table-column prop="suggested_product" label="建议产品" min-width="100" />
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="报告模板字段" name="templates">
          <el-table :data="templateRows" stripe v-loading="loading">
            <el-table-column prop="product_name" label="产品" min-width="150" />
            <el-table-column prop="module_name" label="模块" min-width="180" />
            <el-table-column prop="suggested_pages" label="页数建议" min-width="100" />
            <el-table-column prop="core_content" label="核心内容" min-width="260" show-overflow-tooltip />
            <el-table-column label="必须人工复核" min-width="120">
              <template #default="{ row }">
                {{ row.requires_manual_review ? "是" : "否" }}
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </PanelSection>

    <el-card shadow="never" class="panel-card disclaimer-card">
      <div>
        <strong>合规边界说明</strong>
        <p>{{ COMPLIANCE_DISCLAIMER }}</p>
      </div>
    </el-card>
  </section>
</template>
