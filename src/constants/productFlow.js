export const FIRST_ENTRY_PRODUCT_FLOW = [
  {
    key: "entry_profile",
    step: "01",
    title: "入口引导 / 画像分析",
    description: "先建立正式学生档案，补齐生日、兴趣、家庭诉求和目标方向，让后续专业解释有上下文。",
    routeName: "intake",
    primaryAction: "开始建档",
    evidence: "学生档案、画像字段、选科与批次边界"
  },
  {
    key: "score_conversion",
    step: "02",
    title: "分数换算",
    description: "用正式高考分数、全省位次和一分一段/历史录取数据完成层级判断，形成可解释的冲稳保基础。",
    routeName: "analysis",
    primaryAction: "查看换算",
    evidence: "分数层级、位次来源、真实候选命中情况"
  },
  {
    key: "formal_report",
    step: "03",
    title: "正式推荐报告",
    description: "在正式报告页选择 99 / 399 / 999 产品版本，复核推荐表、备注和导出记录后交付。",
    routeName: "reports",
    primaryAction: "生成报告",
    evidence: "报告版本、正式推荐表、导出与交付留痕"
  }
];

export function buildProductFlowTarget(routeName, studentId) {
  if (!studentId) {
    return { name: routeName };
  }
  if (routeName === "student-detail") {
    return { name: routeName, params: { studentId: String(studentId) } };
  }
  return { name: routeName, query: { studentId: String(studentId) } };
}
