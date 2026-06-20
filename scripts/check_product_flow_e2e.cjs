const fs = require("fs");
const http = require("http");
const path = require("path");
const { chromium } = require("playwright");

const DIST_DIR = path.resolve(__dirname, "..", "dist");
const STUDENT_ID = 101;

const CONTENT_TYPES = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".jpeg": "image/jpeg",
  ".jpg": "image/jpeg",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".woff2": "font/woff2"
};

const UNSAFE_BROWSER_PORTS = new Set([
  1, 7, 9, 11, 13, 15, 17, 19, 20, 21, 22, 23, 25, 37, 42, 43, 53, 69, 77, 79, 87,
  95, 101, 102, 103, 104, 109, 110, 111, 113, 115, 117, 119, 123, 135, 137, 139,
  143, 161, 179, 389, 427, 465, 512, 513, 514, 515, 526, 530, 531, 532, 540, 548,
  554, 556, 563, 587, 601, 636, 989, 990, 993, 995, 1719, 1720, 1723, 2049, 3659,
  4045, 5060, 5061, 6000, 6566, 6665, 6666, 6667, 6668, 6669, 6697, 10080
]);

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function ok(data) {
  return JSON.stringify({ code: 0, message: "ok", data });
}

const intakeTemplate = {
  provinces: ["河南"],
  province_support: {
    formalSupportedProvinces: ["河南"],
    formalSupportedLabel: "河南",
    pendingProvinces: ["江西"],
    options: [{ value: "河南", label: "河南", disabled: false }],
    notice: "当前正式支持河南真实招生数据。",
    lastVerifiedDate: "2026-06-18"
  },
  exam_types: [{ value: "gaokao", label: "高考" }],
  genders: ["女", "男"],
  status_options: [{ value: "active", label: "正式跟进" }],
  admission_batches: ["本科批"],
  school_preference_options: ["专业优先"],
  region_preference_options: ["省内优先"],
  family_preference_options: ["就业稳定"],
  development_goal_options: ["计算机方向"],
  acceptance_options: [{ value: "yes", label: "接受" }],
  subject_groups: { gaokao: ["物理/化学/生物"], zhongkao: [] },
  birth_time_options: [{ value: "zi", label: "子时" }],
  defaults: {
    name: "测试学生",
    gender: "女",
    province: "河南",
    exam_type: "gaokao",
    subject_group: "物理/化学/生物",
    admission_batch: "本科批",
    exam_year: 2026,
    final_score: 612,
    final_rank: 18500,
    birthday: "2008-06-06",
    birth_time: "zi",
    status: "active"
  }
};

const derivedProfile = {
  constellation: "双子座",
  birthday: "2008-06-06",
  birthTime: "子时",
  pillars: { year: "戊子", month: "戊午", day: "丁酉", hour: "庚子" },
  hourBranchLabel: "子时",
  wuxing: { dominant: "火", secondary: "金", counts: { fire: 2, metal: 2 } },
  profile: { explanations: ["适合信息技术、数据分析和沟通协作型方向。"] },
  autofill: {
    constellation: "双子座",
    bazi_year_pillar: "戊子",
    bazi_month_pillar: "戊午",
    bazi_day_pillar: "丁酉",
    bazi_hour_pillar: "庚子",
    interest_preferences: "计算机、数据",
    region_preference: "省内优先",
    development_goal: "计算机方向"
  },
  disclaimer: "画像只用于解释专业方向。"
};

const dashboardData = {
  metrics: [
    { title: "学生档案", value: "1", note: "E2E fixture", variant: "primary" },
    { title: "正式报告", value: "1", note: "已生成", variant: "success" }
  ],
  recentStudents: [
    { name: "测试学生", detail: "河南 / 本科批 / 612分", tagLabel: "正式跟进", tag: "success" }
  ]
};

const studentDetail = {
  id: STUDENT_ID,
  name: "测试学生",
  gender: "女",
  province: "河南",
  exam_type: "gaokao",
  subject_group: "物理/化学/生物",
  admission_batch: "本科批",
  final_score: 612,
  final_rank: 18500,
  birthday: "2008-06-06",
  birth_time: "zi",
  interest_preferences: "计算机、数据",
  target_direction: "计算机",
  status: "active"
};

const analysisData = {
  hasStudent: true,
  studentId: STUDENT_ID,
  summary: {
    name: "测试学生",
    meta: "河南 / 本科批 / 612分 / 18500位",
    tags: [{ label: "正式数据", variant: "success" }]
  },
  metrics: [{ title: "分数层级", value: "稳妥", note: "真实位次换算", variant: "success" }],
  buckets: [
    { key: "rush", title: "冲刺", tagLabel: "少量尝试", tagVariant: "warning", note: "控制数量", items: ["A大学"] },
    { key: "steady", title: "稳妥", tagLabel: "主力区", tagVariant: "primary", note: "重点关注", items: ["B大学"] },
    { key: "safe", title: "保底", tagLabel: "安全垫", tagVariant: "success", note: "兜底选择", items: ["C大学"] }
  ],
  subjectBars: [{ label: "物理", value: 92, percent: 92 }],
  warnings: ["正式填报前需复核当年招生章程。"],
  resultSource: {
    mode: "real",
    label: "真实招生结果",
    isRealData: true,
    matchedCandidateCount: 3,
    rankSource: "正式位次",
    latestAdmissionYear: 2024,
    notice: "当前结果已命中真实招生数据。"
  },
  derivedProfile,
  policyHighlights: [],
  ruleSummary: {
    scoreLevel: "本科批稳妥区",
    scoreComment: "位次与历史录取区间匹配。",
    riskLevel: "review",
    riskItems: [],
    studentSubjects: ["物理", "化学", "生物"],
    strategy: { rush_ratio: 20, steady_ratio: 50, safe_ratio: 30 },
    topMajors: [{ name: "计算机类" }]
  }
};

const recommendation = {
  institutionName: "河南科技大学",
  majorName: "计算机科学与技术",
  planGroupCode: "506",
  batchCode: "本科批",
  city: "洛阳",
  cityText: "洛阳",
  province: "河南",
  bucket: "steady",
  bucketLabel: "稳",
  minScore: 598,
  minRank: 22100,
  rankGap: 3600,
  scoreGap: 14,
  riskLevel: "low",
  riskLabel: "低风险",
  riskNotes: ["需复核当年招生计划。"],
  recommendationReason: "分数位次与历史录取区间匹配。"
};

const reportData = {
  hasStudent: true,
  studentId: STUDENT_ID,
  activeProductCode: "399",
  activeProductLabel: "399 元正式报告",
  reportProducts: [
    {
      code: "99",
      label: "99 元轻量报告",
      description: "画像与方向建议",
      targetUser: "初步咨询",
      deliveryChannels: ["web"]
    },
    {
      code: "399",
      label: "399 元正式报告",
      description: "正式推荐表与交付留痕",
      targetUser: "正式交付",
      deliveryChannels: ["web", "pdf", "word"]
    },
    {
      code: "999",
      label: "999 元深度报告",
      description: "深度复核",
      targetUser: "高端咨询",
      deliveryChannels: ["web", "pdf", "word"]
    }
  ],
  outline: ["报告版本说明", "正式院校专业推荐表"],
  sections: [{ title: "风险复核", body: "正式填报前复核招生章程。", warning: true }],
  reportTitle: "测试学生正式推荐报告",
  reportSubtitle: "河南本科批 / 399 元正式报告",
  disclaimer: "本报告不保证录取结果。",
  boundaryNote: "画像只作为解释层。",
  resultSource: {
    mode: "real",
    label: "真实招生结果",
    isRealData: true,
    matchedCandidateCount: 3,
    rankSource: "正式位次",
    latestAdmissionYear: 2024,
    notice: "当前报告已命中真实招生数据。"
  },
  reportJson: {
    product: { description: "正式推荐表与交付留痕", targetUser: "正式交付" },
    delivery: { suggestedTotalPages: 12, manualReviewModules: ["风险复核"] },
    modules: []
  },
  recommendationTable: [recommendation],
  firstChoice: recommendation,
  alternatives: [{ ...recommendation, institutionName: "郑州轻工业大学", majorName: "软件工程" }],
  notRecommended: [{ ...recommendation, institutionName: "高风险大学", majorName: "热门实验班", reason: "位次差距过大" }],
  derivedProfile: {
    ...derivedProfile,
    interestDirections: ["计算机", "数据分析"],
    regionPreferences: ["省内优先"],
    developmentGoals: ["计算机方向"],
    personalityTraits: ["反应快", "表达强"],
    learningStyle: "项目驱动"
  },
  portraitRecommendation: {
    preferredDirection: "计算机方向",
    recommendedMajorDirections: ["计算机类", "数据科学"],
    majorFitReasons: ["与兴趣和成绩结构匹配"],
    parentConcernMatch: { label: "就业稳定", details: "兼顾省内和就业方向。" },
    auxiliaryExplanation: ["画像辅助推荐仅用于解释专业方向。"]
  },
  policyHighlights: [],
  advisorNotes: [],
  generationRecords: [],
  deliveryRecords: [],
  ruleSummary: {
    scoreLevel: "本科批稳妥区",
    strategy: { rush_ratio: 20, steady_ratio: 50, safe_ratio: 30 },
    topMajors: [{ name: "计算机类" }],
    topRisks: ["专业热度波动"],
    preferredDirection: "计算机方向"
  }
};

function resolveBrowserExecutable() {
  const candidates = [
    process.env.PRODUCT_FLOW_E2E_BROWSER,
    process.env.FRONTEND_TEST_BROWSER,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"
  ].filter(Boolean);

  const resolved = candidates.find((candidate) => fs.existsSync(candidate));
  if (!resolved) {
    throw new Error("未找到可用浏览器。请安装 Chrome/Edge，或通过 PRODUCT_FLOW_E2E_BROWSER 指定路径。");
  }

  return resolved;
}

function routeApi(requestUrl, method) {
  const pathname = requestUrl.pathname;
  if (method === "GET" && pathname === "/api/dashboard") {
    return ok(dashboardData);
  }
  if (method === "GET" && pathname === "/api/intake/template") {
    return ok(intakeTemplate);
  }
  if (method === "GET" && pathname === "/api/intake/derive-profile") {
    return ok(derivedProfile);
  }
  if (method === "POST" && pathname === "/api/students") {
    return ok({ id: STUDENT_ID });
  }
  if (method === "GET" && pathname === `/api/students/${STUDENT_ID}`) {
    return ok(studentDetail);
  }
  if (method === "GET" && pathname === `/api/students/${STUDENT_ID}/scores`) {
    return ok({ rows: [] });
  }
  if (method === "GET" && pathname === `/api/analysis/student/${STUDENT_ID}`) {
    return ok(analysisData);
  }
  if (method === "GET" && pathname === `/api/reports/student/${STUDENT_ID}`) {
    return ok(reportData);
  }
  if (method === "GET" && pathname === "/api/students") {
    return ok({ rows: [studentDetail], total: 1 });
  }
  return null;
}

function createSpaServer() {
  return http.createServer((req, res) => {
    const requestUrl = new URL(req.url, "http://127.0.0.1");
    if (requestUrl.pathname.startsWith("/api")) {
      const body = routeApi(requestUrl, req.method || "GET");
      if (body) {
        res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
        res.end(body);
        return;
      }
      res.writeHead(404, { "Content-Type": "application/json; charset=utf-8" });
      res.end(JSON.stringify({ code: 404, message: `Unhandled E2E API: ${req.method} ${requestUrl.pathname}` }));
      return;
    }

    const requestedPath = decodeURIComponent(requestUrl.pathname);
    const localPath = path.join(DIST_DIR, requestedPath);
    const shouldServeFile =
      requestedPath.startsWith("/assets/") ||
      (requestedPath !== "/" && fs.existsSync(localPath) && fs.statSync(localPath).isFile());
    const targetPath = shouldServeFile ? localPath : path.join(DIST_DIR, "index.html");
    const extname = path.extname(targetPath).toLowerCase();

    res.writeHead(200, {
      "Content-Type": CONTENT_TYPES[extname] || "application/octet-stream"
    });
    fs.createReadStream(targetPath).pipe(res);
  });
}

async function listen(server) {
  const firstPort = Number(process.env.PRODUCT_FLOW_E2E_PORT || 4274);
  const candidatePorts = Array.from({ length: 40 }, (_, index) => firstPort + index).filter(
    (port) => !UNSAFE_BROWSER_PORTS.has(port)
  );

  for (const port of candidatePorts) {
    try {
      await new Promise((resolve, reject) => {
        server.once("error", reject);
        server.listen(port, "127.0.0.1", resolve);
      });
      break;
    } catch (error) {
      server.removeAllListeners("error");
      if (error.code !== "EADDRINUSE") {
        throw error;
      }
    }
  }

  assert(server.listening, "无法启动产品流 E2E 本地服务，请检查 4274-4313 端口占用。");
  return server.address().port;
}

async function closeServer(server) {
  await new Promise((resolve) => server.close(resolve));
}

async function expectText(page, text, context) {
  await page.getByText(text, { exact: false }).first().waitFor({ state: "visible", timeout: 10000 });
  console.log(`- ${context}: ${text}`);
}

async function main() {
  assert(fs.existsSync(DIST_DIR), "未找到 dist 目录，请先执行前端构建。");

  const browserExecutable = resolveBrowserExecutable();
  const server = createSpaServer();
  const port = await listen(server);
  const baseUrl = `http://127.0.0.1:${port}`;
  let browser;

  try {
    browser = await chromium.launch({
      headless: true,
      executablePath: browserExecutable,
      args: ["--disable-dev-shm-usage", "--disable-gpu"]
    });
    const page = await browser.newPage({ viewport: { width: 1440, height: 1200 } });

    await page.goto(`${baseUrl}/dashboard`, { waitUntil: "networkidle", timeout: 30000 });
    await expectText(page, "首次进入产品流", "dashboard guide visible");
    await page.getByRole("button", { name: "开始建档" }).click();
    await page.waitForURL("**/intake", { timeout: 10000 });
    await expectText(page, "学生录入", "intake reached");
    await expectText(page, "正式基础档案", "intake template loaded");

    await page.getByRole("button", { name: "保存学生档案" }).click();
    await page.waitForURL(`**/students/${STUDENT_ID}`, { timeout: 10000 });
    await expectText(page, "测试学生", "student detail reached");
    await expectText(page, "首次进入产品流", "student guide visible");
    await page.getByRole("button", { name: "确认" }).click();

    await page.getByRole("button", { name: "查看换算" }).click();
    await page.waitForURL(`**/analysis?studentId=${STUDENT_ID}`, { timeout: 10000 });
    await expectText(page, "评估分析", "analysis reached");
    await expectText(page, "当前结果已命中真实招生数据", "analysis real-data banner");

    await page.getByRole("button", { name: "生成报告" }).click();
    await page.waitForURL(`**/reports?studentId=${STUDENT_ID}`, { timeout: 10000 });
    await expectText(page, "报告生成", "reports reached");
    await expectText(page, "当前报告已命中真实招生数据", "reports real-data banner");
    await expectText(page, "冲稳保推荐表", "formal report table visible");
    await expectText(page, "河南科技大学", "recommendation row visible");

    console.log("Product-flow E2E regression passed.");
  } finally {
    if (browser) {
      await browser.close();
    }
    await closeServer(server);
  }
}

main().catch((error) => {
  console.error("Product-flow E2E regression failed.");
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
});
