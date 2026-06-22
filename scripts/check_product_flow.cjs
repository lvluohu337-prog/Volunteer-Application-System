const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

(async () => {
  const { FIRST_ENTRY_PRODUCT_FLOW } = await import("../src/constants/productFlow.js");
  const productFlowGuidePath = path.resolve(__dirname, "..", "src", "components", "ProductFlowGuide.vue");
  const productFlowGuideSource = fs.readFileSync(productFlowGuidePath, "utf8");

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
})();
