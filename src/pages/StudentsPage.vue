<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { deleteStudent, fetchStudentsData } from "../api/planning.js";
import PageHeader from "../components/PageHeader.vue";
import StatusTag from "../components/StatusTag.vue";

const router = useRouter();

const loading = ref(true);
const filters = ref({
  keyword: "",
  province: "",
  status: "",
  exam_type: "",
  page: 1,
  pageSize: 20
});
const rows = ref([]);
const total = ref(0);
const filterOptions = ref({
  provinces: [],
  statuses: [],
  exam_types: []
});

async function loadStudents() {
  loading.value = true;
  const data = await fetchStudentsData(filters.value);
  rows.value = data.rows ?? [];
  total.value = data.total ?? 0;
  filterOptions.value = {
    provinces: data.provinces ?? [],
    statuses: data.statuses ?? [],
    exam_types: data.exam_types ?? []
  };
  loading.value = false;
}

function resetFilters() {
  filters.value = {
    keyword: "",
    province: "",
    status: "",
    exam_type: "",
    page: 1,
    pageSize: 20
  };
  loadStudents();
}

async function handleDelete(studentId, studentName) {
  if (!window.confirm(`确认删除学生“${studentName}”吗？`)) {
    return;
  }
  await deleteStudent(studentId);
  await loadStudents();
}

onMounted(() => {
  loadStudents();
});
</script>

<template>
  <section class="page">
    <PageHeader
      breadcrumb="学生管理 / 学生列表"
      title="学生列表"
      description="这里展示正式录入学生档案。录入页保留画像辅助字段，但正式录取判断仍只看真实成绩、位次和招生规则。"
    >
      <template #actions>
        <el-button type="primary" @click="router.push({ name: 'intake' })">录入新学生</el-button>
      </template>
    </PageHeader>

    <el-card shadow="never" class="panel-card filter-card">
      <div class="filter-grid">
        <el-input v-model="filters.keyword" placeholder="搜索姓名 / 学校 / 电话" clearable @keyup.enter="loadStudents" />
        <el-select v-model="filters.province" placeholder="省份" clearable>
          <el-option v-for="item in filterOptions.provinces" :key="item" :label="item" :value="item" />
        </el-select>
        <el-select v-model="filters.status" placeholder="状态" clearable>
          <el-option v-for="item in filterOptions.statuses" :key="item" :label="item" :value="item" />
        </el-select>
        <el-select v-model="filters.exam_type" placeholder="考试类型" clearable>
          <el-option
            v-for="item in filterOptions.exam_types"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
        <div class="filter-actions">
          <el-button @click="loadStudents">筛选</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </div>
      </div>
    </el-card>

    <el-card shadow="never" class="panel-card">
      <div class="table-head">
        <div>
          <h2>学生档案</h2>
          <p class="table-note">共 {{ total }} 位学生</p>
        </div>
      </div>

      <el-table :data="rows" stripe v-loading="loading">
        <el-table-column prop="name" label="姓名" min-width="120" />
        <el-table-column prop="province" label="省份" min-width="100" />
        <el-table-column prop="subject_group" label="选科组合" min-width="120" />
        <el-table-column label="正式高考成绩" min-width="120">
          <template #default="{ row }">{{ row.final_score ?? "待补充" }}</template>
        </el-table-column>
        <el-table-column label="全省位次" min-width="120">
          <template #default="{ row }">{{ row.final_rank ?? row.rank ?? "待补充" }}</template>
        </el-table-column>
        <el-table-column label="画像辅助方向" min-width="180">
          <template #default="{ row }">
            {{ row.target_direction || row.interest_preferences || "待补充画像信息" }}
          </template>
        </el-table-column>
        <el-table-column label="状态" min-width="110">
          <template #default="{ row }">
            <StatusTag :label="row.status_label" :variant="row.status_variant" />
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="340" fixed="right">
          <template #default="{ row }">
            <div class="action-row">
              <el-button link type="primary" @click="router.push({ name: 'student-detail', params: { studentId: String(row.id) } })">详情</el-button>
              <el-button link type="primary" @click="router.push({ name: 'intake', query: { studentId: String(row.id) } })">编辑</el-button>
              <el-button link type="primary" @click="router.push({ name: 'majors', query: { studentId: String(row.id) } })">专业推荐</el-button>
              <el-button link type="primary" @click="router.push({ name: 'plan', query: { studentId: String(row.id) } })">志愿方案</el-button>
              <el-button link type="danger" @click="handleDelete(row.id, row.name)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </section>
</template>

<style scoped>
.filter-card {
  margin-bottom: 16px;
}

.filter-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: 1.4fr repeat(3, minmax(120px, 1fr)) auto;
}

.filter-actions,
.action-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}

.table-head h2 {
  margin: 0 0 6px;
}

@media (max-width: 960px) {
  .filter-grid {
    grid-template-columns: 1fr;
  }
}
</style>
