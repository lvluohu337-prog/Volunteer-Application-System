# Family-Facing Report Experience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rework the report page into a family-facing final report experience using the "formal report document" direction, while absorbing risk/evidence metrics from the dashboard concept.

**Architecture:** Keep existing backend report payloads stable and add only small computed front-end presentation layers. Split the report page into focused Vue components: hero summary, core conclusion, formal plan table, evidence metrics, and review checklist. Move advisor/delivery traceability lower so the first half of the page reads like a final report rather than a management dashboard.

**Tech Stack:** Vue 3 Composition API, Element Plus, existing `src/api/planning.js`, current backend report endpoints, `npm run build`, `npm run test:product-flow`, and backend unittest verification.

---

## Selected Visual Direction

Use **方案 1：正式报告书** as the primary direction:

- full-width report-document header
- calm white/ink surface, subtle separators, limited status colors
- first screen emphasizes conclusion, score/rank context, data credibility, and export actions
- main body centers the 48 college-major-group plan

Absorb from **方案 2：决策驾驶舱**:

- compact evidence metrics
- visible top risks
- manual review checklist
- data-source confidence indicators

Do not use the narrative-heavy方案 3 as the main page.

## File Structure

Create:

- `src/components/reports/ReportHeroSummary.vue`
  - Family-facing report header with student context, strategy, data-source chips, and export actions.
- `src/components/reports/ReportCoreConclusion.vue`
  - First-choice, strategy distribution, top risks, and confirmation tasks.
- `src/components/reports/ReportEvidencePanel.vue`
  - Evidence metrics from recommendation table, result source, and rule summary.
- `src/components/reports/ReportReviewChecklist.vue`
  - Read-only manual review checklist for v1.

Modify:

- `src/pages/ReportsPage.vue`
  - Orchestrates the new report-document flow and moves admin-like content lower.
- `src/components/reports/ReportRecommendationTable.vue`
  - Adjusts from backend-like tables to formal plan sections with six-tier emphasis.
- `src/components/reports/ReportTraceabilityPanel.vue`
  - Makes advisor notes/export history secondary; no API behavior changes.
- `backend/planning_repository.py`
  - Additive only if needed: emit `ruleSummary.finalConclusion` and `ruleSummary.reviewChecklist`.
- `backend/tests/test_planning_repository_structured_report.py`
  - Add backend contract coverage if new fields are emitted.
- `scripts/check_product_flow.cjs`
  - Extend smoke assertions to look for report hero/final plan language.

Do not delete old report components in the first pass. Keep old data contracts compatible.

---

### Task 1: Add Backend-Friendly Family Summary Contract

**Files:**
- Modify: `backend/planning_repository.py`
- Test: `backend/tests/test_planning_repository_structured_report.py`

- [ ] **Step 1: Write the failing backend test**

Add a test that asserts the real structured report summary includes a family-facing conclusion and review checklist when recommendation data exists:

```python
def test_real_rule_summary_includes_family_facing_conclusion_and_review_checklist(self):
    bundle = {
        "context": {"latest_year": 2025, "rank_source": "official", "candidate_strategy": "rank_and_score"},
        "candidates": [{"institution_name": "测试大学", "major_name": "计算机科学与技术", "risks": []}],
        "recommendation_table": [
            {
                "institutionName": "测试大学",
                "majorName": "计算机科学与技术",
                "displayTierLabel": "稳",
                "displayTierTitle": "稳妥主力",
                "riskLabel": "中等风险",
                "probabilityLabel": "录取概率中高",
                "recommendationReason": "位次具备一定优势。",
            }
        ],
        "first_choice": {
            "institutionName": "测试大学",
            "majorName": "计算机科学与技术",
            "displayTierLabel": "稳",
            "riskLabel": "中等风险",
            "recommendationReason": "位次具备一定优势。",
        },
        "alternatives": [],
        "not_recommended": [],
    }
    strategy = {
        "name": "稳妥型",
        "mode": "conservative",
        "total_choice_target": 48,
        "display_tier_counts": {"risk": 5, "sprint": 5, "steady": 16, "protect": 12, "cushion": 5, "fallback": 5},
    }

    summary = planning_repository._build_real_rule_summary(
        {"name": "测试学生", "province": "河南"},
        bundle,
        strategy,
        [],
        None,
    )

    self.assertIn("finalConclusion", summary)
    self.assertIn("稳妥型", summary["finalConclusion"])
    self.assertIn("reviewChecklist", summary)
    self.assertIn("招生章程", summary["reviewChecklist"])
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
rtk python -m unittest backend.tests.test_planning_repository_structured_report -v
```

Expected: FAIL because `finalConclusion` and `reviewChecklist` are not emitted yet.

- [ ] **Step 3: Implement minimal backend fields**

In `backend/planning_repository.py`, add helpers near `_build_real_rule_summary`:

```python
def _build_family_final_conclusion(strategy: dict[str, Any], first_choice: dict[str, Any] | None) -> str:
    strategy_name = strategy.get("name") or "当前策略"
    target = strategy.get("total_choice_target") or 48
    if first_choice:
        return (
            f"建议采用{strategy_name}，围绕 {target} 个院校专业组形成正式方案；"
            f"第一志愿优先关注 {first_choice.get('institutionName') or '目标院校'} - "
            f"{first_choice.get('majorName') or '目标专业'}。"
        )
    return f"建议采用{strategy_name}，围绕 {target} 个院校专业组形成正式方案，正式填报前继续完成关键复核。"


def _build_family_review_checklist() -> list[str]:
    return [
        "招生章程",
        "组内 6 个专业接受度",
        "是否服从调剂",
        "体检/单科/语种/性别限制",
        "当年招生计划变化",
        "最终志愿系统录入顺序",
    ]
```

Then add to the `summary` dict inside `_build_real_rule_summary`:

```python
"finalConclusion": _build_family_final_conclusion(strategy, first_choice),
"reviewChecklist": _build_family_review_checklist(),
```

- [ ] **Step 4: Run backend focused tests**

Run:

```powershell
rtk python -m unittest backend.tests.test_planning_repository_structured_report -v
```

Expected: PASS.

---

### Task 2: Create Report Hero Summary Component

**Files:**
- Create: `src/components/reports/ReportHeroSummary.vue`
- Modify: `src/pages/ReportsPage.vue`

- [ ] **Step 1: Create component with existing props only**

Create `ReportHeroSummary.vue`:

```vue
<script setup>
defineProps({
  title: { type: String, default: "" },
  subtitle: { type: String, default: "" },
  activeProductLabel: { type: String, default: "" },
  ruleSummary: { type: Object, required: true },
  resultSource: { type: Object, required: true },
  resultSourceFacts: { type: Array, default: () => [] },
  hasFormalReportResult: { type: Boolean, default: false },
  exporting: { type: String, default: "" },
  activeDeliveryChannels: { type: Array, default: () => [] }
});

const emit = defineEmits(["export-pdf", "export-word", "view-student"]);
</script>

<template>
  <section class="report-hero-summary">
    <div class="report-kicker">正式志愿规划报告</div>
    <div class="report-hero-grid">
      <div class="report-hero-main">
        <h1>{{ title || "高考志愿规划报告" }}</h1>
        <p>{{ ruleSummary.finalConclusion || subtitle || "当前报告已生成正式推荐结构，正式填报前仍需完成人工复核。" }}</p>
        <div class="hero-chip-row">
          <span>{{ activeProductLabel }}</span>
          <span>{{ ruleSummary.strategy?.name || "策略待确认" }}</span>
          <span>{{ resultSource.label || "数据状态待确认" }}</span>
        </div>
      </div>
      <div class="report-hero-actions">
        <button type="button" class="ghost-action" @click="emit('view-student')">学生档案</button>
        <button
          v-if="activeDeliveryChannels.includes('word')"
          type="button"
          class="ghost-action"
          :disabled="!hasFormalReportResult || exporting === 'word'"
          @click="emit('export-word')"
        >
          导出 Word
        </button>
        <button
          v-if="activeDeliveryChannels.includes('pdf')"
          type="button"
          class="primary-action"
          :disabled="!hasFormalReportResult || exporting === 'pdf'"
          @click="emit('export-pdf')"
        >
          导出 PDF
        </button>
      </div>
    </div>
    <div class="report-evidence-strip">
      <div>
        <span>分层判断</span>
        <strong>{{ ruleSummary.scoreLevel || "待补充" }}</strong>
      </div>
      <div>
        <span>推荐规模</span>
        <strong>{{ ruleSummary.strategy?.total_choice_target || 48 }} 个专业组</strong>
      </div>
      <div>
        <span>数据依据</span>
        <strong>{{ resultSourceFacts.join(" / ") || "待补充" }}</strong>
      </div>
    </div>
  </section>
</template>

<style scoped>
.report-hero-summary {
  padding: 28px 32px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  background: #ffffff;
  border-radius: 8px;
}

.report-kicker {
  margin-bottom: 12px;
  color: #64748b;
  font-size: 13px;
}

.report-hero-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 24px;
}

.report-hero-main h1 {
  margin: 0;
  color: #0f172a;
  font-size: 30px;
  line-height: 1.2;
}

.report-hero-main p {
  max-width: 820px;
  margin: 12px 0 0;
  color: #334155;
  line-height: 1.8;
}

.hero-chip-row,
.report-hero-actions,
.report-evidence-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.hero-chip-row {
  margin-top: 16px;
}

.hero-chip-row span,
.report-evidence-strip div {
  border: 1px solid rgba(15, 23, 42, 0.1);
  background: #f8fafc;
  border-radius: 8px;
}

.hero-chip-row span {
  padding: 7px 10px;
  color: #475569;
  font-size: 13px;
}

.report-hero-actions {
  align-content: flex-start;
  justify-content: flex-end;
}

.primary-action,
.ghost-action {
  min-height: 38px;
  padding: 0 14px;
  border-radius: 6px;
  cursor: pointer;
}

.primary-action {
  border: 1px solid #0f766e;
  background: #0f766e;
  color: #ffffff;
}

.ghost-action {
  border: 1px solid rgba(15, 23, 42, 0.16);
  background: #ffffff;
  color: #334155;
}

.primary-action:disabled,
.ghost-action:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.report-evidence-strip {
  margin-top: 22px;
}

.report-evidence-strip div {
  min-width: 180px;
  padding: 10px 12px;
}

.report-evidence-strip span,
.report-evidence-strip strong {
  display: block;
}

.report-evidence-strip span {
  color: #64748b;
  font-size: 12px;
}

.report-evidence-strip strong {
  margin-top: 4px;
  color: #0f172a;
  font-size: 15px;
}

@media (max-width: 900px) {
  .report-hero-grid {
    grid-template-columns: 1fr;
  }

  .report-hero-actions {
    justify-content: flex-start;
  }
}
</style>
```

- [ ] **Step 2: Wire hero into `ReportsPage.vue`**

Import:

```js
import ReportHeroSummary from "../components/reports/ReportHeroSummary.vue";
```

Place it after `ProductFlowGuide` and before `ReportResultSourceBanner`:

```vue
<ReportHeroSummary
  :title="reportTitle"
  :subtitle="reportSubtitle"
  :active-product-label="activeProductLabel"
  :rule-summary="ruleSummary"
  :result-source="resultSource"
  :result-source-facts="resultSourceFacts"
  :has-formal-report-result="hasFormalReportResult"
  :exporting="exporting"
  :active-delivery-channels="activeDeliveryChannels"
  @view-student="goToStudentDetail"
  @export-pdf="runExport('pdf')"
  @export-word="runExport('word')"
/>
```

- [ ] **Step 3: Run frontend build**

Run:

```powershell
rtk npm run build
```

Expected: PASS.

---

### Task 3: Add Core Conclusion Component

**Files:**
- Create: `src/components/reports/ReportCoreConclusion.vue`
- Modify: `src/pages/ReportsPage.vue`

- [ ] **Step 1: Create component**

Create `ReportCoreConclusion.vue`:

```vue
<script setup>
defineProps({
  firstChoice: { type: Object, default: null },
  ruleSummary: { type: Object, required: true },
  topRiskNotes: { type: Array, default: () => [] },
  formatScore: { type: Function, required: true },
  formatRank: { type: Function, required: true },
  formatRankGap: { type: Function, required: true }
});
</script>

<template>
  <section class="report-core-conclusion">
    <header>
      <span>核心结论</span>
      <h2>先看结论，再看细表</h2>
    </header>
    <div class="conclusion-grid">
      <article class="primary-conclusion">
        <span>第一志愿建议</span>
        <h3>{{ firstChoice?.institutionName || "待补充院校" }}</h3>
        <p>
          {{ firstChoice?.majorName || "待补充专业" }}
          <template v-if="firstChoice?.planGroupCode"> / {{ firstChoice.planGroupCode }}</template>
        </p>
        <dl>
          <div>
            <dt>最低分</dt>
            <dd>{{ formatScore(firstChoice?.minScore) }}</dd>
          </div>
          <div>
            <dt>最低位次</dt>
            <dd>{{ formatRank(firstChoice?.minRank) }}</dd>
          </div>
          <div>
            <dt>位次差</dt>
            <dd>{{ formatRankGap(firstChoice?.rankGap) }}</dd>
          </div>
        </dl>
      </article>
      <article>
        <span>策略分布</span>
        <h3>{{ ruleSummary.strategy?.name || "策略待确认" }}</h3>
        <p>{{ ruleSummary.strategy?.note || "当前策略说明待补充。" }}</p>
      </article>
      <article>
        <span>重点风险</span>
        <ul>
          <li v-for="item in topRiskNotes.slice(0, 3)" :key="item">{{ item }}</li>
          <li v-if="!topRiskNotes.length">正式填报前仍需复核招生章程、专业组和调剂规则。</li>
        </ul>
      </article>
    </div>
  </section>
</template>

<style scoped>
.report-core-conclusion {
  padding: 24px 0;
}

.report-core-conclusion header {
  margin-bottom: 16px;
}

.report-core-conclusion header span,
.conclusion-grid article > span {
  color: #64748b;
  font-size: 13px;
}

.report-core-conclusion h2,
.conclusion-grid h3 {
  margin: 4px 0 0;
  color: #0f172a;
}

.conclusion-grid {
  display: grid;
  grid-template-columns: minmax(280px, 1.2fr) repeat(2, minmax(220px, 1fr));
  gap: 16px;
}

.conclusion-grid article {
  padding: 18px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  border-radius: 8px;
  background: #ffffff;
}

.primary-conclusion {
  border-color: rgba(15, 118, 110, 0.28) !important;
}

.conclusion-grid p,
.conclusion-grid li {
  color: #475569;
  line-height: 1.7;
}

dl {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin: 16px 0 0;
}

dt {
  color: #64748b;
  font-size: 12px;
}

dd {
  margin: 4px 0 0;
  color: #0f172a;
  font-weight: 700;
}

@media (max-width: 1100px) {
  .conclusion-grid {
    grid-template-columns: 1fr;
  }
}
</style>
```

- [ ] **Step 2: Wire into `ReportsPage.vue`**

Import:

```js
import ReportCoreConclusion from "../components/reports/ReportCoreConclusion.vue";
```

Place it after `ReportResultSourceBanner` and before `ReportOutlineCard`:

```vue
<ReportCoreConclusion
  :first-choice="firstChoice"
  :rule-summary="ruleSummary"
  :top-risk-notes="topRiskNotes"
  :format-score="formatScore"
  :format-rank="formatRank"
  :format-rank-gap="formatRankGap"
/>
```

- [ ] **Step 3: Build**

Run:

```powershell
rtk npm run build
```

Expected: PASS.

---

### Task 4: Reframe Formal Plan Table

**Files:**
- Modify: `src/components/reports/ReportRecommendationTable.vue`

- [ ] **Step 1: Change section heading and summary copy**

Replace the table block heading text with family-facing wording:

```vue
<strong>48 个院校专业组正式方案</strong>
<span>按险、冲、稳、保、垫、兜分层阅读。每一行都保留分数、位次、专业组和风险依据，便于正式填报前逐项复核。</span>
```

- [ ] **Step 2: Add row order and tier label display**

In each table row’s school column, include:

```vue
<small>{{ row.displayTierLabel || row.bucketLabel }}</small>
```

In each bucket section header, keep count and purpose text prominent:

```vue
<strong>{{ bucket.title }}</strong>
<span>{{ bucket.description }}</span>
```

- [ ] **Step 3: Mark first choice**

Add a helper in `<script setup>`:

```js
function isFirstChoiceRow(row, firstChoice) {
  if (!row || !firstChoice) return false;
  return (
    row.institutionName === firstChoice.institutionName &&
    row.majorName === firstChoice.majorName &&
    (row.planGroupCode || "") === (firstChoice.planGroupCode || "")
  );
}
```

Add a tag in the row template:

```vue
<el-tag v-if="isFirstChoiceRow(row, firstChoice)" type="success" size="small">第一志愿</el-tag>
```

- [ ] **Step 4: Build**

Run:

```powershell
rtk npm run build
```

Expected: PASS.

---

### Task 5: Add Evidence Metrics Panel

**Files:**
- Create: `src/components/reports/ReportEvidencePanel.vue`
- Modify: `src/pages/ReportsPage.vue`

- [ ] **Step 1: Create component**

Create `ReportEvidencePanel.vue`:

```vue
<script setup>
defineProps({
  resultSource: { type: Object, required: true },
  resultSourceFacts: { type: Array, default: () => [] },
  recommendationTable: { type: Array, default: () => [] },
  topRiskNotes: { type: Array, default: () => [] }
});
</script>

<template>
  <section class="report-evidence-panel">
    <header>
      <span>数据依据</span>
      <h2>为什么这份方案可信</h2>
    </header>
    <div class="evidence-grid">
      <article>
        <span>数据来源</span>
        <strong>{{ resultSource.label || "待确认" }}</strong>
        <p>{{ resultSourceFacts.join(" / ") || "暂未形成完整数据依据。" }}</p>
      </article>
      <article>
        <span>推荐样本</span>
        <strong>{{ recommendationTable.length }} 条</strong>
        <p>当前表格用于正式填报前逐项复核院校专业组、专业接受度和风险边界。</p>
      </article>
      <article>
        <span>重点复核</span>
        <strong>{{ topRiskNotes.length || 1 }} 项</strong>
        <p>{{ topRiskNotes[0] || "招生章程、专业组和调剂规则仍需人工复核。" }}</p>
      </article>
    </div>
  </section>
</template>

<style scoped>
.report-evidence-panel {
  padding: 24px 0;
}

.report-evidence-panel header {
  margin-bottom: 14px;
}

.report-evidence-panel header span,
.evidence-grid span {
  color: #64748b;
  font-size: 13px;
}

.report-evidence-panel h2 {
  margin: 4px 0 0;
  color: #0f172a;
}

.evidence-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.evidence-grid article {
  padding: 16px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  border-radius: 8px;
  background: #ffffff;
}

.evidence-grid strong {
  display: block;
  margin-top: 4px;
  color: #0f172a;
  font-size: 18px;
}

.evidence-grid p {
  margin: 8px 0 0;
  color: #475569;
  line-height: 1.7;
}

@media (max-width: 900px) {
  .evidence-grid {
    grid-template-columns: 1fr;
  }
}
</style>
```

- [ ] **Step 2: Wire below recommendation table**

Import and place after `ReportRecommendationTable`:

```vue
<ReportEvidencePanel
  :result-source="resultSource"
  :result-source-facts="resultSourceFacts"
  :recommendation-table="recommendationTable"
  :top-risk-notes="topRiskNotes"
/>
```

- [ ] **Step 3: Build**

Run:

```powershell
rtk npm run build
```

Expected: PASS.

---

### Task 6: Add Review Checklist And Lower Operations

**Files:**
- Create: `src/components/reports/ReportReviewChecklist.vue`
- Modify: `src/pages/ReportsPage.vue`
- Modify: `src/components/reports/ReportTraceabilityPanel.vue`

- [ ] **Step 1: Create checklist component**

Create `ReportReviewChecklist.vue`:

```vue
<script setup>
defineProps({
  items: {
    type: Array,
    default: () => [
      "招生章程",
      "组内 6 个专业接受度",
      "是否服从调剂",
      "体检/单科/语种/性别限制",
      "当年招生计划变化",
      "最终志愿系统录入顺序"
    ]
  }
});
</script>

<template>
  <section class="report-review-checklist">
    <header>
      <span>正式提交前</span>
      <h2>人工复核清单</h2>
    </header>
    <ul>
      <li v-for="item in items" :key="item">
        <span></span>
        <strong>{{ item }}</strong>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.report-review-checklist {
  padding: 22px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  border-radius: 8px;
  background: #ffffff;
}

header span {
  color: #64748b;
  font-size: 13px;
}

h2 {
  margin: 4px 0 16px;
  color: #0f172a;
}

ul {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 18px;
  margin: 0;
  padding: 0;
  list-style: none;
}

li {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #334155;
}

li span {
  width: 10px;
  height: 10px;
  border: 2px solid #0f766e;
  border-radius: 50%;
}

@media (max-width: 700px) {
  ul {
    grid-template-columns: 1fr;
  }
}
</style>
```

- [ ] **Step 2: Wire checklist before traceability**

Import and place before `ReportTraceabilityPanel`:

```vue
<ReportReviewChecklist :items="ruleSummary.reviewChecklist" />
```

- [ ] **Step 3: Demote traceability visually**

In `ReportTraceabilityPanel.vue`, change wrapper heading text to make it operational:

```vue
<strong>交付留痕与顾问补充</strong>
```

Keep existing form and records; do not remove features.

- [ ] **Step 4: Build**

Run:

```powershell
rtk npm run build
```

Expected: PASS.

---

### Task 7: Update Smoke Checks

**Files:**
- Modify: `scripts/check_product_flow.cjs`

- [ ] **Step 1: Add report-page text assertions**

Find the report-page assertion block and add checks for new family-facing labels:

```js
assertIncludes(reportHtml, "正式志愿规划报告", "report hero title");
assertIncludes(reportHtml, "核心结论", "core conclusion section");
assertIncludes(reportHtml, "48 个院校专业组正式方案", "formal plan heading");
assertIncludes(reportHtml, "人工复核清单", "review checklist");
```

If the script uses browser DOM instead of raw HTML, query visible text with its current helper style.

- [ ] **Step 2: Run smoke**

Run:

```powershell
rtk npm run test:product-flow
```

Expected: PASS.

---

### Task 8: Final Verification

**Files:**
- No new files beyond previous tasks.

- [ ] **Step 1: Run backend tests**

```powershell
rtk python -m unittest discover -s backend/tests
```

Expected: PASS.

- [ ] **Step 2: Run frontend build**

```powershell
rtk npm run build
```

Expected: PASS.

- [ ] **Step 3: Run product flow smoke**

```powershell
rtk npm run test:product-flow
```

Expected: PASS.

- [ ] **Step 4: Run diff check**

```powershell
rtk git diff --check -- backend/planning_repository.py backend/tests/test_planning_repository_structured_report.py src/pages/ReportsPage.vue src/components/reports/ReportHeroSummary.vue src/components/reports/ReportCoreConclusion.vue src/components/reports/ReportEvidencePanel.vue src/components/reports/ReportReviewChecklist.vue src/components/reports/ReportRecommendationTable.vue src/components/reports/ReportTraceabilityPanel.vue scripts/check_product_flow.cjs
```

Expected: PASS.

## Self-Review Notes

- Spec coverage: the plan covers report cover summary, core conclusion, 48-group plan, evidence/risk explanation, human review checklist, and delivery/advisor demotion.
- Scope control: shareable public report URLs and persistent checklist state are intentionally left out.
- Compatibility: backend changes are additive; frontend falls back if new fields are missing.
- Verification: every phase has a build or test command, and final verification includes backend, frontend, product flow, and diff checks.
