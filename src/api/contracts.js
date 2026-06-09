export const API_RESPONSE_ENVELOPE = {
  code: "number",
  message: "string",
  data: "any"
};

export const API_ENDPOINTS = {
  navigation: {
    method: "GET",
    path: "/navigation",
    summary: "获取导航配置"
  },
  dashboard: {
    method: "GET",
    path: "/dashboard",
    summary: "获取工作台数据"
  },
  students: {
    list: {
      method: "GET",
      path: "/students",
      summary: "获取学生列表"
    },
    detail: {
      method: "GET",
      path: "/students/:studentId",
      summary: "获取学生详情"
    },
    create: {
      method: "POST",
      path: "/students",
      summary: "新增学生"
    },
    update: {
      method: "PUT",
      path: "/students/:studentId",
      summary: "更新学生"
    },
    delete: {
      method: "DELETE",
      path: "/students/:studentId",
      summary: "删除学生"
    },
    scores: {
      list: {
        method: "GET",
        path: "/students/:studentId/scores",
        summary: "获取学生估分记录"
      },
      create: {
        method: "POST",
        path: "/students/:studentId/scores",
        summary: "新增学生估分记录"
      }
    }
  },
  scores: {
    update: {
      method: "PUT",
      path: "/scores/:scoreId",
      summary: "更新估分记录"
    },
    delete: {
      method: "DELETE",
      path: "/scores/:scoreId",
      summary: "删除估分记录"
    }
  },
  intake: {
    template: {
      method: "GET",
      path: "/intake/template",
      summary: "获取录入模板"
    },
    deriveProfile: {
      method: "GET",
      path: "/intake/derive-profile",
      summary: "自动推算星座与前六字"
    }
  },
  analysis: {
    detail: {
      method: "GET",
      path: "/analysis/student/:studentId",
      summary: "获取分析结果"
    }
  },
  majors: {
    detail: {
      method: "GET",
      path: "/majors/student/:studentId",
      summary: "获取专业推荐"
    }
  },
  plans: {
    detail: {
      method: "GET",
      path: "/plans/student/:studentId",
      summary: "获取志愿方案"
    }
  },
  reports: {
    detail: {
      method: "GET",
      path: "/reports/student/:studentId",
      summary: "获取报告预览"
    },
    advisorNotes: {
      create: {
        method: "POST",
        path: "/reports/student/:studentId/advisor-notes",
        summary: "新增咨询师报告备注"
      }
    },
    exportPdf: {
      method: "POST",
      path: "/reports/student/:studentId/export/pdf",
      summary: "导出 PDF 报告"
    },
    exportWord: {
      method: "POST",
      path: "/reports/student/:studentId/export/word",
      summary: "导出 Word 报告"
    }
  },
  foundation: {
    majors: {
      method: "GET",
      path: "/foundation/majors",
      summary: "获取专业大类库"
    },
    cities: {
      method: "GET",
      path: "/foundation/cities",
      summary: "获取城市产业库"
    },
    sampleStudents: {
      method: "GET",
      path: "/foundation/sample-students",
      summary: "获取样例学生数据"
    },
    reportTemplateFields: {
      method: "GET",
      path: "/foundation/report-template-fields",
      summary: "获取报告模板字段"
    }
  },
  demoReports: {
    report99: {
      method: "GET",
      path: "/demo-reports/99",
      summary: "获取 99 元报告演示"
    },
    report399: {
      method: "GET",
      path: "/demo-reports/399",
      summary: "获取 399 元报告演示"
    }
  },
  settings: {
    detail: {
      method: "GET",
      path: "/settings",
      summary: "获取系统设置"
    }
  }
};

function replacePathParams(path, params = {}) {
  return Object.entries(params).reduce((result, [key, value]) => {
    return result.replace(`:${key}`, encodeURIComponent(String(value)));
  }, path);
}

function emptyToUndefined(value) {
  if (value === "" || value === null || value === undefined) {
    return undefined;
  }

  return value;
}

function normalizeSubjectScores(subjectScores = {}) {
  return Object.fromEntries(
    Object.entries(subjectScores).filter(([, value]) => value !== "" && value !== null && value !== undefined)
  );
}

export function createPath(template, params) {
  return replacePathParams(template, params);
}

export function mapStudentListQuery(filters = {}) {
  return {
    keyword: emptyToUndefined(filters.keyword),
    exam_type: emptyToUndefined(filters.exam_type),
    province: emptyToUndefined(filters.province),
    status: emptyToUndefined(filters.status),
    page: filters.page ?? 1,
    page_size: filters.pageSize ?? 10
  };
}

export function mapDashboardQuery(params = {}) {
  return {
    counselorId: emptyToUndefined(params.counselorId),
    date: emptyToUndefined(params.date)
  };
}

export function mapMajorQuery(params = {}) {
  return {
    scoreRangeType: emptyToUndefined(params.scoreRangeType),
    riskPreference: emptyToUndefined(params.riskPreference),
    majorCategory: emptyToUndefined(params.majorCategory),
    keyword: emptyToUndefined(params.keyword)
  };
}

export function mapPlanQuery(params = {}) {
  return {
    strategyVersion: emptyToUndefined(params.strategyVersion),
    volunteerBatch: emptyToUndefined(params.volunteerBatch),
    includeAdjustment: params.includeAdjustment ?? true
  };
}

export function mapReportExportBody(params = {}) {
  return {
    reportVersion: emptyToUndefined(params.reportVersion),
    reviewedBy: emptyToUndefined(params.reviewedBy),
    includeSignature: params.includeSignature ?? false
  };
}

export function mapReportAdvisorNotePayload(form = {}) {
  return {
    product_code: emptyToUndefined(form.product_code),
    note_type: emptyToUndefined(form.note_type) ?? "advisor_comment",
    note_title: emptyToUndefined(form.note_title),
    note_content: emptyToUndefined(form.note_content),
    author_name: emptyToUndefined(form.author_name)
  };
}

export function mapFoundationQuery(params = {}) {
  return {
    keyword: emptyToUndefined(params.keyword),
    region: emptyToUndefined(params.region),
    product: emptyToUndefined(params.product),
    suggested_product: emptyToUndefined(params.suggested_product)
  };
}

export function mapStudentIntakePayload(form = {}) {
  return {
    name: emptyToUndefined(form.name),
    gender: emptyToUndefined(form.gender),
    birthday: emptyToUndefined(form.birthday),
    birth_time: emptyToUndefined(form.birth_time),
    constellation: emptyToUndefined(form.constellation),
    bazi_year_pillar: emptyToUndefined(form.bazi_year_pillar),
    bazi_month_pillar: emptyToUndefined(form.bazi_month_pillar),
    bazi_day_pillar: emptyToUndefined(form.bazi_day_pillar),
    bazi_hour_pillar: emptyToUndefined(form.bazi_hour_pillar),
    exam_type: emptyToUndefined(form.exam_type),
    province: emptyToUndefined(form.province),
    city: emptyToUndefined(form.city),
    district: emptyToUndefined(form.district),
    school: emptyToUndefined(form.school),
    phone: emptyToUndefined(form.phone),
    parent_phone: emptyToUndefined(form.parent_phone),
    exam_year: form.exam_year ?? undefined,
    admission_batch: emptyToUndefined(form.admission_batch),
    subject_group: emptyToUndefined(form.subject_group),
    target_direction: emptyToUndefined(form.target_direction),
    interest_preferences: emptyToUndefined(form.interest_preferences),
    school_preference: emptyToUndefined(form.school_preference),
    region_preference: emptyToUndefined(form.region_preference),
    family_preferences: emptyToUndefined(form.family_preferences),
    parent_focus: emptyToUndefined(form.parent_focus),
    development_goal: emptyToUndefined(form.development_goal),
    accept_adjustment: emptyToUndefined(form.accept_adjustment),
    accept_high_fee_programs: emptyToUndefined(form.accept_high_fee_programs),
    communication_notes: emptyToUndefined(form.communication_notes),
    status: emptyToUndefined(form.status) ?? "draft",
    remark: emptyToUndefined(form.remark),
    mock_score: form.mock_score ?? undefined,
    estimated_score: form.estimated_score ?? undefined,
    final_score: form.final_score ?? undefined,
    estimated_rank: form.estimated_rank ?? undefined,
    final_rank: form.final_rank ?? undefined,
    chinese: form.chinese ?? undefined,
    math: form.math ?? undefined,
    english: form.english ?? undefined,
    physics: form.physics ?? undefined,
    chemistry: form.chemistry ?? undefined,
    biology: form.biology ?? undefined,
    politics: form.politics ?? undefined,
    history: form.history ?? undefined,
    geography: form.geography ?? undefined,
    pe: form.pe ?? undefined,
    experiment: form.experiment ?? undefined,
    info_tech: form.info_tech ?? undefined,
    rank: form.rank ?? undefined,
    score_type: emptyToUndefined(form.score_type)
  };
}

export function mapScoreRecordPayload(form = {}) {
  return {
    exam_type: emptyToUndefined(form.exam_type),
    total_score: form.total_score ?? undefined,
    subject_scores: normalizeSubjectScores(form.subject_scores),
    ranking: form.ranking ?? undefined,
    score_source: emptyToUndefined(form.score_source),
    note: emptyToUndefined(form.note)
  };
}
