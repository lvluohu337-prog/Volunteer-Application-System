<script setup>
import { onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  fetchIntakeData,
  fetchIntakeDerivedProfile,
  fetchStudentDetail,
  submitStudentIntake
} from "../api/planning.js";
import PageHeader from "../components/PageHeader.vue";
import StatusTag from "../components/StatusTag.vue";

const emit = defineEmits(["open-dialog"]);
const route = useRoute();
const router = useRouter();

const loading = ref(true);
const saving = ref(false);
const deriving = ref(false);
const template = ref({
  provinces: [],
  province_support: {
    formalSupportedProvinces: [],
    formalSupportedLabel: "",
    pendingProvinces: [],
    options: [],
    notice: "",
    lastVerifiedDate: ""
  },
  exam_types: [],
  genders: [],
  status_options: [],
  admission_batches: [],
  school_preference_options: [],
  region_preference_options: [],
  family_preference_options: [],
  development_goal_options: [],
  acceptance_options: [],
  subject_groups: { gaokao: [], zhongkao: [] },
  birth_time_options: [],
  defaults: {}
});
const form = ref({});
const derivedProfile = ref(null);
const lastDeriveKey = ref("");

function parseStudentId() {
  const rawValue = route.query.studentId;
  if (!rawValue) {
    return undefined;
  }
  const numericValue = Number(rawValue);
  return Number.isNaN(numericValue) ? undefined : numericValue;
}

async function refreshDerivedProfile() {
  if (!form.value.birthday) {
    derivedProfile.value = null;
    lastDeriveKey.value = "";
    return;
  }

  const deriveKey = `${form.value.birthday || ""}-${form.value.birth_time || ""}`;
  if (lastDeriveKey.value === deriveKey) {
    return;
  }

  deriving.value = true;
  try {
    const result = await fetchIntakeDerivedProfile(form.value.birthday, form.value.birth_time || undefined);
    derivedProfile.value = result;
    lastDeriveKey.value = deriveKey;
    const autofill = result.autofill ?? {};
    form.value.constellation = autofill.constellation ?? form.value.constellation;
    form.value.bazi_year_pillar = autofill.bazi_year_pillar ?? form.value.bazi_year_pillar;
    form.value.bazi_month_pillar = autofill.bazi_month_pillar ?? form.value.bazi_month_pillar;
    form.value.bazi_day_pillar = autofill.bazi_day_pillar ?? form.value.bazi_day_pillar;
    form.value.bazi_hour_pillar = autofill.bazi_hour_pillar ?? form.value.bazi_hour_pillar;
    if (!form.value.interest_preferences) {
      form.value.interest_preferences = autofill.interest_preferences ?? "";
    }
    if (!form.value.region_preference) {
      form.value.region_preference = autofill.region_preference ?? "";
    }
    if (!form.value.development_goal) {
      form.value.development_goal = autofill.development_goal ?? "";
    }
  } finally {
    deriving.value = false;
  }
}

async function loadPageData() {
  loading.value = true;
  const templateData = await fetchIntakeData();
  template.value = templateData;
  form.value = { ...(templateData.defaults ?? {}) };

  const studentId = parseStudentId();
  if (studentId) {
    const detail = await fetchStudentDetail(studentId);
    form.value = { ...form.value, ...detail };
  }

  if (form.value.birthday) {
    await refreshDerivedProfile();
  }
  loading.value = false;
}

async function handleSubmit() {
  saving.value = true;
  try {
    form.value.rank = form.value.final_rank ?? form.value.rank ?? null;
    const result = await submitStudentIntake(form.value, parseStudentId());
    emit("open-dialog", "学生档案已保存，正式成绩与画像辅助字段都已同步更新。");
    router.push({ name: "student-detail", params: { studentId: String(result.id) } });
  } finally {
    saving.value = false;
  }
}

watch(
  () => [form.value?.birthday, form.value?.birth_time],
  () => {
    refreshDerivedProfile();
  }
);

watch(
  () => form.value?.exam_type,
  () => {
    if (!form.value?.subject_group) {
      const options = template.value.subject_groups?.[form.value.exam_type] ?? [];
      form.value.subject_group = options[0] ?? "";
    }
  }
);

onMounted(() => {
  loadPageData();
});
</script>

<template>
  <section class="page">
    <PageHeader
      :breadcrumb="parseStudentId() ? '学生管理 / 编辑学生录入' : '学生管理 / 学生录入'"
      title="学生录入"
      description="正式录入主流程只服务正式志愿决策；估分和模拟成绩后续将移到独立页面，不再作为正式方案核心依据。"
    >
      <template #actions>
        <StatusTag :label="parseStudentId() ? '编辑模式' : '新建档案'" variant="primary" />
      </template>
    </PageHeader>

    <el-skeleton :loading="loading" animated :rows="12">
      <template #default>
        <el-card shadow="never" class="panel-card notice-card">
          <strong>字段边界说明</strong>
          <p>正式推荐与正式报告默认只使用正式高考成绩、全省位次、选科组合、批次和招生规则。前六段、八字、星座、性格、兴趣与发展目标只用于专业方向解释和家长沟通。</p>
          <el-alert
            type="warning"
            :closable="false"
            class="province-support-alert"
            :title="template.province_support?.notice || '当前正式支持省份待补充。'"
            :description="`本次核验时间：${template.province_support?.lastVerifiedDate || '待补充'}。待核验省份：${template.province_support?.pendingProvinces?.join(' / ') || '暂无'}`"
          />
        </el-card>

        <el-form :model="form" label-position="top" class="intake-form">
          <div class="form-grid">
            <el-card shadow="never" class="panel-card form-card">
              <h2>正式基础档案</h2>
              <div class="field-grid">
                <el-form-item label="学生姓名">
                  <el-input v-model="form.name" placeholder="请输入学生姓名" />
                </el-form-item>
                <el-form-item label="性别">
                  <el-select v-model="form.gender" placeholder="请选择">
                    <el-option v-for="item in template.genders" :key="item" :label="item" :value="item" />
                  </el-select>
                </el-form-item>
                <el-form-item label="省份">
                  <el-select v-model="form.province" placeholder="请选择">
                    <el-option
                      v-for="item in template.province_support?.options?.length ? template.province_support.options : template.provinces.map((province) => ({ value: province, label: province, disabled: false }))"
                      :key="item.value || item"
                      :label="item.label || item"
                      :value="item.value || item"
                      :disabled="item.disabled"
                    />
                  </el-select>
                  <p class="table-note">当前只有正式支持省份可新建正式学生档案；其它省份先保留为待核验范围。</p>
                </el-form-item>
                <el-form-item label="考试类型">
                  <el-select v-model="form.exam_type" placeholder="请选择">
                    <el-option
                      v-for="item in template.exam_types"
                      :key="item.value"
                      :label="item.label"
                      :value="item.value"
                    />
                  </el-select>
                </el-form-item>
                <el-form-item label="选科组合">
                  <el-select v-model="form.subject_group" placeholder="请选择">
                    <el-option
                      v-for="item in template.subject_groups?.[form.exam_type] ?? []"
                      :key="item"
                      :label="item"
                      :value="item"
                    />
                  </el-select>
                </el-form-item>
                <el-form-item label="批次">
                  <el-select v-model="form.admission_batch" placeholder="请选择">
                    <el-option v-for="item in template.admission_batches" :key="item" :label="item" :value="item" />
                  </el-select>
                </el-form-item>
                <el-form-item label="毕业年份">
                  <el-input-number v-model="form.exam_year" :min="2024" :max="2035" controls-position="right" />
                </el-form-item>
                <el-form-item label="状态">
                  <el-select v-model="form.status" placeholder="请选择">
                    <el-option
                      v-for="item in template.status_options"
                      :key="item.value"
                      :label="item.label"
                      :value="item.value"
                    />
                  </el-select>
                </el-form-item>
              </div>
            </el-card>

            <el-card shadow="never" class="panel-card form-card">
              <h2>正式高考成绩</h2>
              <p class="table-note">这里只录入正式高考成绩和正式位次。估分、模考、阶段成绩请放到后续独立页面。</p>
              <div class="field-grid">
                <el-form-item label="正式高考成绩">
                  <el-input-number v-model="form.final_score" :min="0" :max="900" :precision="1" controls-position="right" />
                </el-form-item>
                <el-form-item label="全省位次">
                  <el-input-number v-model="form.final_rank" :min="0" controls-position="right" />
                </el-form-item>
                <el-form-item label="学校偏好">
                  <el-select v-model="form.school_preference" placeholder="请选择或自行补充" allow-create filterable default-first-option>
                    <el-option
                      v-for="item in template.school_preference_options"
                      :key="item"
                      :label="item"
                      :value="item"
                    />
                  </el-select>
                </el-form-item>
                <el-form-item label="是否接受调剂">
                  <el-select v-model="form.accept_adjustment" placeholder="请选择">
                    <el-option
                      v-for="item in template.acceptance_options"
                      :key="item.value"
                      :label="item.label"
                      :value="item.value"
                    />
                  </el-select>
                </el-form-item>
                <el-form-item label="是否接受民办 / 中外合作 / 高收费">
                  <el-select v-model="form.accept_high_fee_programs" placeholder="请选择">
                    <el-option
                      v-for="item in template.acceptance_options"
                      :key="item.value"
                      :label="item.label"
                      :value="item.value"
                    />
                  </el-select>
                </el-form-item>
                <el-form-item label="备注">
                  <el-input v-model="form.remark" type="textarea" :rows="3" placeholder="填写正式录入补充说明" />
                </el-form-item>
              </div>
            </el-card>

            <el-card shadow="never" class="panel-card form-card">
              <div class="section-head">
                <div>
                  <h2>画像辅助信息</h2>
                  <p class="table-note">这些字段只用于专业方向推荐、适配理由解释、城市建议和家长沟通。</p>
                </div>
                <StatusTag :label="deriving ? '推导中' : '辅助字段'" :variant="deriving ? 'warning' : 'review'" />
              </div>

              <div class="field-grid">
                <el-form-item label="阳历出生日期">
                  <el-date-picker
                    v-model="form.birthday"
                    type="date"
                    value-format="YYYY-MM-DD"
                    format="YYYY-MM-DD"
                    placeholder="请选择"
                  />
                </el-form-item>
                <el-form-item label="出生时辰">
                  <el-select v-model="form.birth_time" placeholder="可选">
                    <el-option
                      v-for="item in template.birth_time_options"
                      :key="item.value"
                      :label="item.label"
                      :value="item.value"
                    />
                  </el-select>
                </el-form-item>
                <el-form-item label="专业偏好">
                  <el-input v-model="form.target_direction" placeholder="例如：计算机、师范、医学" />
                </el-form-item>
                <el-form-item label="兴趣标签">
                  <el-input v-model="form.interest_preferences" placeholder="例如：计算机、数据、管理" />
                </el-form-item>
                <el-form-item label="地域要求">
                  <el-select v-model="form.region_preference" placeholder="请选择或自行补充" allow-create filterable default-first-option>
                    <el-option
                      v-for="item in template.region_preference_options"
                      :key="item"
                      :label="item"
                      :value="item"
                    />
                  </el-select>
                </el-form-item>
                <el-form-item label="发展目标">
                  <el-select v-model="form.development_goal" placeholder="请选择或自行补充" allow-create filterable default-first-option>
                    <el-option
                      v-for="item in template.development_goal_options"
                      :key="item"
                      :label="item"
                      :value="item"
                    />
                  </el-select>
                </el-form-item>
                <el-form-item label="家长关注点">
                  <el-input v-model="form.parent_focus" placeholder="例如：离家近、稳定就业、考研" />
                </el-form-item>
                <el-form-item label="家庭偏好 / 就业诉求">
                  <el-select v-model="form.family_preferences" placeholder="请选择或自行补充" allow-create filterable default-first-option>
                    <el-option
                      v-for="item in template.family_preference_options"
                      :key="item"
                      :label="item"
                      :value="item"
                    />
                  </el-select>
                </el-form-item>
                <el-form-item label="沟通记录">
                  <el-input v-model="form.communication_notes" type="textarea" :rows="3" placeholder="记录老师访谈、性格观察或家长沟通重点" />
                </el-form-item>
              </div>

              <div v-if="derivedProfile" class="derived-preview">
                <div>
                  <strong>自动推导</strong>
                  <p>{{ derivedProfile.constellation || "待补充星座" }}</p>
                </div>
                <div>
                  <strong>四柱</strong>
                  <p>
                    {{
                      [
                        derivedProfile.pillars?.year,
                        derivedProfile.pillars?.month,
                        derivedProfile.pillars?.day,
                        derivedProfile.pillars?.hour
                      ].filter(Boolean).join(" / ") || "待补充"
                    }}
                  </p>
                </div>
                <div>
                  <strong>辅助解释</strong>
                  <p>{{ derivedProfile.profile?.explanations?.[0] || derivedProfile.disclaimer || "待补充画像解释" }}</p>
                </div>
              </div>
            </el-card>
          </div>

          <div class="submit-row">
            <el-button @click="router.push({ name: 'students' })">返回学生列表</el-button>
            <el-button type="primary" :loading="saving" @click="handleSubmit">保存学生档案</el-button>
          </div>
        </el-form>
      </template>
    </el-skeleton>
  </section>
</template>

<style scoped>
.notice-card,
.form-card {
  margin-bottom: 16px;
}

.form-grid,
.field-grid,
.derived-preview {
  display: grid;
  gap: 16px;
}

.form-grid {
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
}

.field-grid {
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.section-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 12px;
}

.section-head h2,
.form-card h2 {
  margin: 0 0 8px;
}

.derived-preview {
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  margin-top: 8px;
  padding-top: 12px;
  border-top: 1px solid var(--el-border-color-light);
}

.derived-preview p {
  margin: 6px 0 0;
  color: var(--el-text-color-secondary);
}

.submit-row {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 16px;
}

@media (max-width: 768px) {
  .section-head,
  .submit-row {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
