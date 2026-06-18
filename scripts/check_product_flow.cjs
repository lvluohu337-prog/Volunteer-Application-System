const assert = require("node:assert/strict");

(async () => {
  const { FIRST_ENTRY_PRODUCT_FLOW } = await import("../src/constants/productFlow.js");

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
})();
