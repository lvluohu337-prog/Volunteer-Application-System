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
    method: API_ENDPOINTS.intake.template.method
  });
}

export async function fetchIntakeDerivedProfile(birthday, birthTime) {
  return apiRequest(API_ENDPOINTS.intake.deriveProfile.path, {
    method: API_ENDPOINTS.intake.deriveProfile.method,
    query: { birthday, birth_time: birthTime }
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

