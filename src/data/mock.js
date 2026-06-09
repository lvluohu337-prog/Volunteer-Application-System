export const navigationItems = [
  { key: "dashboard", label: "工作台", short: "DB" },
  { key: "students", label: "学生管理", short: "ST" },
  { key: "intake", label: "学生录入", short: "FM" },
  { key: "analysis", label: "估分分析", short: "AN" },
  { key: "majors", label: "专业推荐", short: "MJ" },
  { key: "plan", label: "志愿方案", short: "PL" },
  { key: "reports", label: "报告管理", short: "RP" },
  { key: "base-data", label: "基础数据", short: "DT" },
  { key: "demo-reports", label: "演示报告", short: "DM" },
  { key: "settings", label: "系统设置", short: "SE" }
];

export const dashboardMetrics = [
  { title: "今日新增学生", value: "12", note: "较昨日增加 3 人，晚间录入量较高。", variant: "default" },
  { title: "待人工复核", value: "08", note: "其中 3 份报告已生成，建议今晚完成复核。", variant: "default" },
  { title: "已交付报告", value: "26", note: "本周累计交付 26 份，交付率稳定。", variant: "default" },
  { title: "高风险学生", value: "05", note: "集中在冲一冲方案，建议结合正式位次再核对。", variant: "risk" }
];

export const quickActions = [
  { title: "学生管理", description: "查看档案、更新状态、安排复核", target: "students" },
  { title: "录入新学生", description: "使用步骤表单收集基础信息与兴趣画像", target: "intake" },
  { title: "生成估分分析", description: "快速对比成绩、位次和冲稳保分层", target: "analysis" },
  { title: "进入报告预览", description: "检查目录结构和风险声明可见性", target: "reports" }
];

export const recentStudents = [
  { name: "张一诺", detail: "河南 / 物理+化学+生物 / 估分 602", tag: "review", tagLabel: "待复核" },
  { name: "刘知远", detail: "河北 / 历史+政治+地理 / 估分 554", tag: "warning", tagLabel: "中风险" },
  { name: "许安然", detail: "山东 / 物理+化学 / 报告已生成", tag: "success", tagLabel: "已生成报告" },
  { name: "周嘉禾", detail: "江苏 / 物理+生物+地理 / 冲稳保待调整", tag: "danger", tagLabel: "高风险" },
  { name: "陈思予", detail: "安徽 / 历史+政治+生物 / 基础信息已录入", tag: "primary", tagLabel: "基础信息完成" }
];

export const studentRows = [
  {
    id: 1,
    name: "张一诺",
    province: "河南",
    year: "2026",
    subjects: "物理+化学+生物",
    score: 602,
    status: "待复核",
    statusVariant: "review",
    updatedAt: "2026-05-07 19:22"
  },
  {
    id: 2,
    name: "刘知远",
    province: "河北",
    year: "2026",
    subjects: "历史+政治+地理",
    score: 554,
    status: "中风险",
    statusVariant: "warning",
    updatedAt: "2026-05-07 18:47"
  },
  {
    id: 3,
    name: "许安然",
    province: "山东",
    year: "2026",
    subjects: "物理+化学",
    score: 618,
    status: "已生成报告",
    statusVariant: "success",
    updatedAt: "2026-05-07 16:11"
  },
  {
    id: 4,
    name: "周嘉禾",
    province: "江苏",
    year: "2026",
    subjects: "物理+生物+地理",
    score: 581,
    status: "高风险",
    statusVariant: "danger",
    updatedAt: "2026-05-07 15:08"
  }
];

export const studentSummary = {
  name: "张一诺",
  meta: "河南 / 2026 届 / 物理+化学+生物 / 当前状态：待人工复核",
  tags: [
    { label: "待复核", variant: "review" },
    { label: "理工倾向", variant: "primary" }
  ]
};

export const scoreMetrics = [
  { title: "预估总分", value: "602", note: "结合近 3 次模考成绩和学科稳定性进行估算。" },
  { title: "参考位次", value: "18,240", note: "需以正式成绩公布后的官方位次为准。" },
  { title: "适配专业数", value: "27", note: "当前偏向工学、信息类与应用技术方向。" }
];

export const scoreBars = [
  { label: "语文", value: 118, percent: 78 },
  { label: "数学", value: 126, percent: 84 },
  { label: "英语", value: 132, percent: 88 },
  { label: "物理", value: 89, percent: 74 },
  { label: "化学", value: 71, percent: 68 },
  { label: "生物", value: 66, percent: 64 }
];

export const volunteerBuckets = [
  {
    key: "rush",
    title: "冲一冲",
    note: "适合少量尝试，建议控制在总方案中的 20%-30%。",
    tagLabel: "风险较高",
    tagVariant: "warning",
    items: ["华中科技大学 - 自动化类", "电子科技大学 - 智能制造工程", "西安电子科技大学 - 电子信息类"]
  },
  {
    key: "steady",
    title: "稳一稳",
    note: "和当前定位更贴近，建议作为主力区间重点打磨。",
    tagLabel: "匹配较好",
    tagVariant: "primary",
    items: ["武汉理工大学 - 计算机类", "南京邮电大学 - 通信工程", "合肥工业大学 - 自动化"]
  },
  {
    key: "safe",
    title: "保一保",
    note: "用于保障底线，注意避免因专业不匹配带来后续落差。",
    tagLabel: "相对安全",
    tagVariant: "success",
    items: ["长沙理工大学 - 电气工程", "河南大学 - 软件工程", "南昌航空大学 - 机械设计制造"]
  }
];

export const analysisWarnings = [
  "当前方案存在一定风险，建议结合正式位次进一步复核。",
  "英语优势明显，但化学、生物稳定性仍建议用近三次成绩交叉验证。",
  "冲一冲院校占比不宜过高，避免整体方案波动过大。"
];

export const majors = [
  {
    title: "计算机科学与技术",
    type: "工学 / 信息类",
    score: 92,
    reason: "数学与英语表现较强，适合进入应用型强、就业面广的技术方向。",
    meta: ["学习难度：较高", "就业稳定性：高", "建议考研：可选"],
    tagLabel: "低风险",
    tagVariant: "success",
    footer: "建议优先关注课程强度与城市资源匹配。"
  },
  {
    title: "自动化",
    type: "工学 / 智能制造方向",
    score: 88,
    reason: "适合逻辑分析能力较强、能接受一定硬件与系统课程强度的学生。",
    meta: ["学习难度：较高", "就业稳定性：较高", "建议考研：建议考虑"],
    tagLabel: "稳妥推荐",
    tagVariant: "primary",
    footer: "后续建议结合院校实验资源与方向细分。"
  },
  {
    title: "电子信息工程",
    type: "工学 / 电子通信方向",
    score: 84,
    reason: "和当前选科优势方向匹配度较好，但院校层次波动会明显影响培养体验。",
    meta: ["学习难度：中高", "就业稳定性：高", "建议考研：视院校而定"],
    tagLabel: "中风险",
    tagVariant: "warning",
    footer: "建议优先选择学科平台扎实的院校。"
  },
  {
    title: "数据科学与大数据技术",
    type: "工学 / 数据应用方向",
    score: 81,
    reason: "适合对信息处理、分析与技术应用有兴趣的学生，但课程基础要求较强。",
    meta: ["学习难度：中高", "就业稳定性：较高", "建议考研：可提升空间"],
    tagLabel: "待复核",
    tagVariant: "review",
    footer: "建议结合学生实际兴趣与编程接受度进一步判断。"
  }
];

export const planColumns = [
  {
    title: "冲一冲",
    note: "可尝试，但建议结合正式位次进一步复核。",
    tagLabel: "风险较高",
    tagVariant: "warning",
    cards: [
      {
        school: "华中科技大学",
        detail: "武汉 / 公办 / 985",
        metrics: ["最低分 607", "位次 15,900"],
        major: "推荐专业：自动化类",
        reason: "适合作为冲刺目标，但需控制整体比例。"
      },
      {
        school: "西安电子科技大学",
        detail: "西安 / 公办 / 211",
        metrics: ["最低分 604", "位次 17,200"],
        major: "推荐专业：电子信息类",
        reason: "专业方向高度匹配，录取波动需重点关注。"
      }
    ]
  },
  {
    title: "稳一稳",
    note: "与当前定位较匹配，建议作为方案主体。",
    tagLabel: "建议主力区",
    tagVariant: "primary",
    cards: [
      {
        school: "武汉理工大学",
        detail: "武汉 / 公办 / 211",
        metrics: ["最低分 597", "位次 19,480"],
        major: "推荐专业：计算机类",
        reason: "学校平台稳定，城市资源与专业方向均较匹配。"
      },
      {
        school: "南京邮电大学",
        detail: "南京 / 公办 / 双一流建设学科",
        metrics: ["最低分 593", "位次 20,630"],
        major: "推荐专业：通信工程",
        reason: "行业辨识度较高，适合当前学生方向。"
      }
    ]
  },
  {
    title: "保一保",
    note: "防止滑档，但仍需兼顾专业接受度。",
    tagLabel: "相对安全",
    tagVariant: "success",
    cards: [
      {
        school: "长沙理工大学",
        detail: "长沙 / 公办 / 省重点",
        metrics: ["最低分 584", "位次 23,100"],
        major: "推荐专业：电气工程",
        reason: "稳定性较好，适合作为保障层院校。"
      },
      {
        school: "河南大学",
        detail: "开封 / 公办 / 双一流",
        metrics: ["最低分 579", "位次 24,900"],
        major: "推荐专业：软件工程",
        reason: "区域稳定，家庭沟通成本较低。"
      }
    ]
  }
];

export const reportOutline = [
  "1. 学生基础信息",
  "2. 成绩与位次分析",
  "3. 专业推荐说明",
  "4. 志愿方案建议",
  "5. 风险提示与声明"
];

export const reportSections = [
  {
    title: "学生基础信息",
    body: "学生为河南省 2026 届考生，选科组合为物理、化学、生物，当前预估总分为 602 分。"
  },
  {
    title: "分析结论摘要",
    body: "当前成绩结构适合理工类专业方向，稳妥区院校建议重点布局在计算机、自动化、电子信息等相关专业。"
  },
  {
    title: "志愿方案建议",
    body: "整体方案建议采用“冲 2 / 稳 4 / 保 2”的结构，并在正式位次公布后进行二次复核。"
  },
  {
    title: "风险提示与声明",
    body: "本报告仅作为志愿规划辅助建议，不构成录取承诺。当前方案存在一定风险，建议结合正式位次、招生计划和院校最新要求进一步复核。",
    warning: true
  }
];
