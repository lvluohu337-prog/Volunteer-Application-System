const fs = require("fs");
const http = require("http");
const path = require("path");
const { chromium } = require("playwright");

const DIST_DIR = path.resolve(__dirname, "..", "dist");
const EXPECTED_ERROR_MESSAGE = "后端服务暂时不可用，请稍后重试。";
const PAGES = [
  {
    key: "intake",
    route: "/intake",
    title: "学生录入页加载失败",
    hint: "录入模板、学生详情或基础配置当前不可用，请先恢复后端接口，再继续正式建档。",
    actions: ["返回学生列表", "重新加载"]
  },
  {
    key: "analysis",
    route: "/analysis",
    title: "评估分析加载失败",
    hint: "在分析接口恢复前，请不要把本页内容视为正式结果，也不要据此继续做正式志愿交付。",
    actions: ["查看学生详情", "重新加载"]
  },
  {
    key: "majors",
    route: "/majors",
    title: "专业推荐加载失败",
    hint: "在专业推荐接口恢复前，请不要把当前方向建议当成正式结论，也不要直接继续生成志愿方案。",
    actions: ["查看学生详情", "重新加载"]
  },
  {
    key: "plan",
    route: "/plan",
    title: "志愿方案加载失败",
    hint: "在方案接口恢复前，请不要把当前冲稳保结构用于正式填报，也不要直接继续生成正式报告。",
    actions: ["查看学生详情", "重新加载"]
  },
  {
    key: "reports",
    route: "/reports",
    title: "报告页面加载失败",
    hint: "在报告接口恢复前，请不要把当前页面视为正式交付版本，也不要继续执行导出或下载。",
    actions: ["查看学生详情", "重新加载"]
  }
];

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

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function resolveBrowserExecutable() {
  const candidates = [
    process.env.FRONTEND_TEST_BROWSER,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe"
  ].filter(Boolean);

  const resolved = candidates.find((candidate) => fs.existsSync(candidate));
  if (!resolved) {
    throw new Error(
      "未找到可用浏览器。请安装 Chrome/Edge，或通过 FRONTEND_TEST_BROWSER 指定浏览器可执行文件路径。"
    );
  }

  return resolved;
}

function createSpaServer() {
  return http.createServer((req, res) => {
    const requestUrl = new URL(req.url, "http://127.0.0.1");
    if (requestUrl.pathname.startsWith("/api")) {
      res.writeHead(503, { "Content-Type": "text/plain; charset=utf-8" });
      res.end("API offline for disconnect regression");
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
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  return server.address().port;
}

async function closeServer(server) {
  await new Promise((resolve) => server.close(resolve));
}

async function collectPageState(browser, baseUrl, pageCase) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1200 } });
  try {
    await page.goto(`${baseUrl}${pageCase.route}`, { waitUntil: "networkidle", timeout: 30000 });
    await page.waitForTimeout(1200);

    const errorCard = page.locator(".request-error-card");
    const visible = await errorCard.isVisible();
    assert(visible, `[${pageCase.key}] 未显示 request-error-card`);

    const title = ((await errorCard.locator("h3").textContent()) || "").trim();
    const message = ((await errorCard.locator(".request-error-head p").textContent()) || "").trim();
    const hint = ((await errorCard.locator(".request-error-body p").textContent()) || "").trim();
    const actions = await errorCard
      .locator(".request-error-actions .el-button")
      .evaluateAll((nodes) => nodes.map((node) => node.textContent.trim()));

    assert(title === pageCase.title, `[${pageCase.key}] 错误标题不匹配: ${title}`);
    assert(
      message === EXPECTED_ERROR_MESSAGE,
      `[${pageCase.key}] 错误主文案不匹配: ${message}`
    );
    assert(hint === pageCase.hint, `[${pageCase.key}] 风险提示不匹配: ${hint}`);
    assert(
      JSON.stringify(actions) === JSON.stringify(pageCase.actions),
      `[${pageCase.key}] 操作按钮不匹配: ${actions.join(" / ")}`
    );

    return {
      page: pageCase.key,
      title,
      message,
      hint,
      actions
    };
  } finally {
    await page.close();
  }
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

    const results = [];
    for (const pageCase of PAGES) {
      results.push(await collectPageState(browser, baseUrl, pageCase));
    }

    console.log("Frontend error-state regression passed.");
    for (const result of results) {
      console.log(
        `- ${result.page}: ${result.title} | ${result.message} | ${result.actions.join(" / ")}`
      );
    }
  } finally {
    if (browser) {
      await browser.close();
    }
    await closeServer(server);
  }
}

main().catch((error) => {
  console.error("Frontend error-state regression failed.");
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
});
