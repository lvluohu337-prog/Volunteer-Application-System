import { apiRequest, downloadRequest } from "./client.js";
import {
  API_ENDPOINTS,
  createPath,
  mapDashboardQuery,
  mapFoundationQuery,
  mapMajorQuery,
  mapReportAdvisorNotePayload,
  mapPlanQuery,
  mapReportExportBody,
  mapScoreRecordPayload,
  mapStudentIntakePayload,
  mapStudentListQuery
} from "./contracts.js";
import {
  DEFAULT_REPORT_PRODUCT_CODE,
  getReportProductLabel,
  normalizeReportProductCode
} from "../constants/reportProducts.js";
import { INTAKE_DISCLAIMER } from "../constants/compliance.js";

const intakeTemplateFallback = {
  provinces: ["河南", "河北", "山东", "江苏", "安徽"],
  exam_types: [
    { value: "gaokao", label: "高考" },
    { value: "zhongkao", label: "中考" }
  ],
  genders: ["男", "女"],
  status_options: [
    { value: "draft", label: "草稿" },
    { value: "review_pending", label: "待复核" },
    { value: "reviewed", label: "已复核" }
  ],
  score_types: [
    { value: "manual", label: "手工录入" },
    { value: "mock", label: "模拟成绩" },
    { value: "official", label: "正式成绩" }
  ],
  admission_batches: ["本科提前批", "本科批", "专科批", "综合评价", "待定"],
  interest_options: ["计算机", "医学", "师范", "财经", "法学", "电子信息", "机械自动化", "设计传媒"],
  school_preference_options: ["院校层次优先", "城市平台优先", "省内院校优先", "985 / 211 优先", "公办本科优先"],
  region_preference_options: ["本省优先", "外省优先", "北方", "南方", "一线城市", "省会城市", "离家近"],
  family_preference_options: ["稳定就业", "考公考编", "赚钱发展", "名校优先", "离家近", "读研深造"],
  development_goal_options: ["就业优先", "考研深造", "考公考编", "技术研发", "医学发展", "综合待定"],
  acceptance_options: [
    { value: "accept", label: "接受" },
    { value: "reject", label: "不接受" },
    { value: "discuss", label: "可单独沟通" }
  ],
  score_source_options: ["一模", "二模", "三模", "平时估分", "正式成绩"],
  subject_groups: {
    gaokao: ["物理类", "历史类", "物化生", "物化地", "史政地"],
    zhongkao: ["中考统招", "指标生", "特长方向"]
  },
  defaults: {
    name: "",
    gender: "",
    birthday: "",
    birth_time: "",
    constellation: "",
    bazi_year_pillar: "",
    bazi_month_pillar: "",
    bazi_day_pillar: "",
    bazi_hour_pillar: "",
    exam_type: "gaokao",
    province: "",
    city: "",
    district: "",
    school: "",
    phone: "",
    parent_phone: "",
    exam_year: 2026,
    admission_batch: "",
    subject_group: "",
    target_direction: "",
    interest_preferences: "",
    school_preference: "",
    region_preference: "",
    family_preferences: "",
    parent_focus: "",
    development_goal: "",
    accept_adjustment: "discuss",
    accept_high_fee_programs: "reject",
    communication_notes: "",
    status: "draft",
    remark: "",
    mock_score: null,
    estimated_score: null,
    final_score: null,
    estimated_rank: null,
    final_rank: null,
    score_type: "manual",
    chinese: null,
    math: null,
    english: null,
    physics: null,
    chemistry: null,
    biology: null,
    politics: null,
    history: null,
    geography: null,
    pe: null,
    experiment: null,
    info_tech: null,
    rank: null
  },
  birth_time_options: [
    { value: "23:30", label: "子时 23:00-00:59" },
    { value: "01:30", label: "丑时 01:00-02:59" },
    { value: "03:30", label: "寅时 03:00-04:59" },
    { value: "05:30", label: "卯时 05:00-06:59" },
    { value: "07:30", label: "辰时 07:00-08:59" },
    { value: "09:30", label: "巳时 09:00-10:59" },
    { value: "11:30", label: "午时 11:00-12:59" },
    { value: "13:30", label: "未时 13:00-14:59" },
    { value: "15:30", label: "申时 15:00-16:59" },
    { value: "17:30", label: "酉时 17:00-18:59" },
    { value: "19:30", label: "戌时 19:00-20:59" },
    { value: "21:30", label: "亥时 21:00-22:59" }
  ],
  birthday_notice: "请输入学生阳历生日与出生时辰，系统会自动辅助推算星座、八字四柱和兴趣倾向。",
  disclaimer: INTAKE_DISCLAIMER
};

const derivedProfileFallback = {
  birthdayType: "公历",
  birthTime: "09:30",
  constellation: "双子座",
  pillars: {
    year: "甲辰",
    month: "己巳",
    day: "壬午",
    hour: "乙巳"
  },
  hourBranchLabel: "巳时(09:00-10:59)",
  wuxing: {
    counts: { 木: 1, 火: 2, 土: 1, 金: 0, 水: 2 },
    dominant: "火",
    secondary: "水"
  },
  profile: {
    personalityTraits: ["行动力强", "表达欲强", "学习快", "信息处理快"],
    learningStyle: ["更适合目标清晰、反馈频繁的训练"],
    interestDirections: ["电子信息", "传媒", "计算机", "数据方向"],
    regionPreferences: ["南方", "节奏较快城市", "创新资源密集区域"],
    developmentGoals: ["技术研发", "快速成长", "跨领域创新"],
    explanations: [
      "系统按阳历生日自动推算星座与前六字。",
      "兴趣和区域建议仅作辅助参考。"
    ]
  },
  autofill: {
    constellation: "双子座",
    bazi_year_pillar: "甲辰",
    bazi_month_pillar: "己巳",
    bazi_day_pillar: "壬午",
    bazi_hour_pillar: "乙巳",
    interest_preferences: "电子信息、传媒、计算机、数据方向",
    region_preference: "南方、节奏较快城市、创新资源密集区域",
    development_goal: "技术研发、快速成长、跨领域创新"
  },
  disclaimer: "前六字、星座和五行倾向仅作为辅助分析，不替代真实招生数据和正式填报规则。"
};

const emptyStudentDrivenState = Object.freeze({
  hasStudent: false,
  studentId: null
});

const emptyResultSource = Object.freeze({
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

async function resolveStudentId(studentId) {
  if (studentId !== undefined && studentId !== null && studentId !== "") {
    return Number(studentId);
  }

  const data = await fetchStudentsData({ page: 1, pageSize: 1 });
  return data.rows?.[0]?.id ?? null;
}

export async function fetchDashboardData(params = {}) {
  return apiRequest(API_ENDPOINTS.dashboard.path, {
    method: API_ENDPOINTS.dashboard.method,
    query: mapDashboardQuery(params)
  });
}

export async function fetchStudentsData(filters = {}) {
  return apiRequest(API_ENDPOINTS.students.list.path, {
    method: API_ENDPOINTS.students.list.method,
    query: mapStudentListQuery(filters)
  });
}

export async function fetchStudentDetail(studentId) {
  return apiRequest(createPath(API_ENDPOINTS.students.detail.path, { studentId }), {
    method: API_ENDPOINTS.students.detail.method
  });
}

export async function deleteStudent(studentId) {
  return apiRequest(createPath(API_ENDPOINTS.students.delete.path, { studentId }), {
    method: API_ENDPOINTS.students.delete.method
  });
}

export async function fetchStudentScoreRecords(studentId) {
  return apiRequest(createPath(API_ENDPOINTS.students.scores.list.path, { studentId }), {
    method: API_ENDPOINTS.students.scores.list.method
  });
}

export async function createStudentScoreRecord(studentId, form) {
  return apiRequest(createPath(API_ENDPOINTS.students.scores.create.path, { studentId }), {
    method: API_ENDPOINTS.students.scores.create.method,
    body: mapScoreRecordPayload(form)
  });
}

export async function updateStudentScoreRecord(scoreId, form) {
  return apiRequest(createPath(API_ENDPOINTS.scores.update.path, { scoreId }), {
    method: API_ENDPOINTS.scores.update.method,
    body: mapScoreRecordPayload(form)
  });
}

export async function deleteStudentScoreRecord(scoreId) {
  return apiRequest(createPath(API_ENDPOINTS.scores.delete.path, { scoreId }), {
    method: API_ENDPOINTS.scores.delete.method
  });
}

export async function fetchIntakeData() {
  return apiRequest(API_ENDPOINTS.intake.template.path, {
    method: API_ENDPOINTS.intake.template.method,
    mockData: intakeTemplateFallback
  });
}

export async function fetchIntakeDerivedProfile(birthday, birthTime) {
  return apiRequest(API_ENDPOINTS.intake.deriveProfile.path, {
    method: API_ENDPOINTS.intake.deriveProfile.method,
    query: { birthday, birth_time: birthTime },
    mockData: derivedProfileFallback
  });
}

export async function submitStudentIntake(form, studentId) {
  const method = studentId ? API_ENDPOINTS.students.update.method : API_ENDPOINTS.students.create.method;
  const path = studentId
    ? createPath(API_ENDPOINTS.students.update.path, { studentId })
    : API_ENDPOINTS.students.create.path;

  return apiRequest(path, {
    method,
    body: mapStudentIntakePayload(form)
  });
}

export async function fetchAnalysisData(studentId) {
  const resolvedStudentId = await resolveStudentId(studentId);
  if (!resolvedStudentId) {
    return {
      ...emptyStudentDrivenState,
      summary: { name: "暂无学生档案", meta: "请先录入学生信息后再查看分析结果", tags: [] },
      metrics: [],
      buckets: [],
      subjectBars: [],
      resultSource: {
        ...emptyResultSource,
        fallbackReason: "请先创建真实学生档案，并补充分数与位次信息。"
      },
      warnings: ["请先创建真实学生档案，并补充分数与位次信息。"]
    };
  }

  return apiRequest(createPath(API_ENDPOINTS.analysis.detail.path, { studentId: resolvedStudentId }), {
    method: API_ENDPOINTS.analysis.detail.method
  });
}

export async function fetchMajorsData(studentId, params = {}) {
  const resolvedStudentId = await resolveStudentId(studentId);
  if (!resolvedStudentId) {
    return {
      ...emptyStudentDrivenState,
      rows: [],
      disclaimer: "请先录入真实学生档案，再进行专业推荐。"
    };
  }

  return apiRequest(createPath(API_ENDPOINTS.majors.detail.path, { studentId: resolvedStudentId }), {
    method: API_ENDPOINTS.majors.detail.method,
    query: mapMajorQuery(params)
  });
}

export async function fetchPlanData(studentId, params = {}) {
  const resolvedStudentId = await resolveStudentId(studentId);
  if (!resolvedStudentId) {
    return {
      ...emptyStudentDrivenState,
      columns: [],
      resultSource: {
        ...emptyResultSource,
        fallbackReason: "请先录入真实学生档案，再查看志愿方案建议。"
      },
      disclaimer: "请先录入真实学生档案，再查看志愿方案建议。"
    };
  }

  return apiRequest(createPath(API_ENDPOINTS.plans.detail.path, { studentId: resolvedStudentId }), {
    method: API_ENDPOINTS.plans.detail.method,
    query: mapPlanQuery(params)
  });
}

export async function fetchReportData(studentId, productCode = DEFAULT_REPORT_PRODUCT_CODE) {
  const normalizedProductCode = normalizeReportProductCode(productCode);
  const resolvedStudentId = await resolveStudentId(studentId);
  if (!resolvedStudentId) {
    return {
      ...emptyStudentDrivenState,
      activeProductCode: normalizedProductCode,
      activeProductLabel: getReportProductLabel(normalizedProductCode),
      reportProducts: [],
      outline: [],
      sections: [],
      reportTitle: "暂无可用报告",
      reportSubtitle: "请先录入真实学生档案",
      resultSource: {
        ...emptyResultSource,
        fallbackReason: "请先录入真实学生档案，再生成报告预览。"
      },
      disclaimer: "请先录入真实学生档案，再生成报告预览。"
    };
  }

  return apiRequest(createPath(API_ENDPOINTS.reports.detail.path, { studentId: resolvedStudentId }), {
    method: API_ENDPOINTS.reports.detail.method,
    query: { product_code: normalizedProductCode }
  });
}

export async function createReportAdvisorNote(studentId, form = {}) {
  return apiRequest(createPath(API_ENDPOINTS.reports.advisorNotes.create.path, { studentId }), {
    method: API_ENDPOINTS.reports.advisorNotes.create.method,
    body: mapReportAdvisorNotePayload(form)
  });
}

export async function exportReportPdf(studentId, params = {}) {
  return apiRequest(createPath(API_ENDPOINTS.reports.exportPdf.path, { studentId }), {
    method: API_ENDPOINTS.reports.exportPdf.method,
    body: mapReportExportBody(params)
  });
}

export async function exportReportWord(studentId, params = {}) {
  return apiRequest(createPath(API_ENDPOINTS.reports.exportWord.path, { studentId }), {
    method: API_ENDPOINTS.reports.exportWord.method,
    body: mapReportExportBody(params)
  });
}

export async function downloadReportDelivery(studentId, recordId, artifactName = "") {
  return downloadRequest(
    createPath(API_ENDPOINTS.reports.deliveryDownload.path, { studentId, recordId }),
    {
      method: API_ENDPOINTS.reports.deliveryDownload.method,
      filename: artifactName || undefined
    }
  );
}

export async function fetchFoundationMajors(params = {}) {
  return apiRequest(API_ENDPOINTS.foundation.majors.path, {
    method: API_ENDPOINTS.foundation.majors.method,
    query: mapFoundationQuery(params)
  });
}

export async function fetchFoundationCities(params = {}) {
  return apiRequest(API_ENDPOINTS.foundation.cities.path, {
    method: API_ENDPOINTS.foundation.cities.method,
    query: mapFoundationQuery(params)
  });
}

export async function fetchFoundationSampleStudents(params = {}) {
  return apiRequest(API_ENDPOINTS.foundation.sampleStudents.path, {
    method: API_ENDPOINTS.foundation.sampleStudents.method,
    query: mapFoundationQuery(params)
  });
}

export async function fetchFoundationReportTemplateFields(params = {}) {
  return apiRequest(API_ENDPOINTS.foundation.reportTemplateFields.path, {
    method: API_ENDPOINTS.foundation.reportTemplateFields.method,
    query: mapFoundationQuery(params)
  });
}

