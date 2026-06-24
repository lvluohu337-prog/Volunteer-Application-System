const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

(async () => {
  const { FIRST_ENTRY_PRODUCT_FLOW } = await import("../src/constants/productFlow.js");
  const productFlowGuidePath = path.resolve(__dirname, "..", "src", "components", "ProductFlowGuide.vue");
  const reportRecommendationTablePath = path.resolve(
    __dirname,
    "..",
    "src",
    "components",
    "reports",
    "ReportRecommendationTable.vue",
  );
  const reportEvidencePanelPath = path.resolve(
    __dirname,
    "..",
    "src",
    "components",
    "reports",
    "ReportEvidencePanel.vue",
  );
  const reportHeroSummaryPath = path.resolve(
    __dirname,
    "..",
    "src",
    "components",
    "reports",
    "ReportHeroSummary.vue",
  );
  const reportReviewChecklistPath = path.resolve(
    __dirname,
    "..",
    "src",
    "components",
    "reports",
    "ReportReviewChecklist.vue",
  );
  const reportsPagePath = path.resolve(__dirname, "..", "src", "pages", "ReportsPage.vue");
  const productFlowGuideSource = fs.readFileSync(productFlowGuidePath, "utf8");
  const reportRecommendationTableSource = fs.readFileSync(reportRecommendationTablePath, "utf8");
  const reportsPageSource = fs.readFileSync(reportsPagePath, "utf8");

  assert.equal(FIRST_ENTRY_PRODUCT_FLOW.length, 3);
  assert.deepEqual(
    FIRST_ENTRY_PRODUCT_FLOW.map((item) => item.key),
    ["entry_profile", "score_conversion", "formal_report"],
  );
  assert.deepEqual(
    FIRST_ENTRY_PRODUCT_FLOW.map((item) => item.routeName),
    ["intake", "analysis", "reports"],
  );
  assert.ok(FIRST_ENTRY_PRODUCT_FLOW.every((item) => item.title && item.description && item.primaryAction));
  assert.match(productFlowGuideSource, /product-flow-guide-compact/);
  assert.match(productFlowGuideSource, /product-flow-guide-compact\s+\.product-flow-steps/);
  assert.match(productFlowGuideSource, /product-flow-guide-compact\s+\.product-flow-step/);

  assert.match(reportRecommendationTableSource, /48 个院校专业组正式方案/);
  assert.match(reportRecommendationTableSource, /displayTierLabel/);
  assert.match(reportRecommendationTableSource, /第一志愿/);
  assert.match(reportRecommendationTableSource, /recommendation-card-list/);
  assert.doesNotMatch(reportRecommendationTableSource, /<el-table/);
  assert.doesNotMatch(reportRecommendationTableSource, /<el-table-column/);

  assert.ok(fs.existsSync(reportEvidencePanelPath), "ReportEvidencePanel.vue should exist");
  assert.ok(fs.existsSync(reportHeroSummaryPath), "ReportHeroSummary.vue should exist");
  assert.ok(fs.existsSync(reportReviewChecklistPath), "ReportReviewChecklist.vue should exist");
  const reportHeroSummarySource = fs.readFileSync(reportHeroSummaryPath, "utf8");
  assert.match(reportHeroSummarySource, /河南 2026 高考志愿正式规划报告/);
  assert.match(reportHeroSummarySource, /真实招生数据/);
  assert.match(reportHeroSummarySource, /48 专业组方案/);
  const reportEvidencePanelSource = fs.readFileSync(reportEvidencePanelPath, "utf8");
  assert.match(reportEvidencePanelSource, /为什么这份方案可信/);
  assert.match(reportEvidencePanelSource, /证据链审阅/);
  assert.match(reportEvidencePanelSource, /数据来源/);
  assert.match(reportEvidencePanelSource, /重点复核/);
  const reportReviewChecklistSource = fs.readFileSync(reportReviewChecklistPath, "utf8");
  assert.match(reportReviewChecklistSource, /人工复核清单/);
  assert.match(reportsPageSource, /ReportEvidencePanel/);
  assert.match(reportsPageSource, /ReportReviewChecklist/);
  assert.match(reportsPageSource, /paper-recommendation-list/);
  assert.doesNotMatch(reportsPageSource, /paper-table-wrapper/);
  assert.match(reportsPageSource, /previewInNewTab/);
})();
