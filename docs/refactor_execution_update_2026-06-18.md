# 2026-06-18 Refactor Execution Update

## Scope

This update records the later refactor steps executed after the initial architecture alignment document:

- Split report page display blocks.
- Split admissions engine presentation, scoring, and query responsibilities.
- Add the first-entry product flow aligned with the colleague architecture: entry/profile analysis -> score conversion -> formal recommendation report.

## Completed Steps

| Step | Commit | Main change | Verification |
|---|---|---|---|
| Step 6A | `02c9ad8 refactor: extract report product catalog` | Extracted `ReportProductCatalog.vue` from `ReportsPage.vue`. | `npm run lint`, `npm run build`, `npm run test:backend`, `npm run test:frontend:error-states` passed. |
| Step 6B | `548a862 refactor: extract report recommendation table` | Extracted `ReportRecommendationTable.vue`. | Same quality gates passed. |
| Step 6C | `d713d44 refactor: extract report traceability panel` | Extracted advisor notes, generation records, export records, and download actions into `ReportTraceabilityPanel.vue`. | Same quality gates passed. |
| Step 7A | `777f3f3 refactor: extract admissions risk logic` | Extracted risk rule matching and risk collection into `backend/admissions_risk.py`. | Admissions focused tests, py_compile, and full quality gates passed. |
| Step 7B | `4342cc0 refactor: extract admissions presenter logic` | Extracted recommendation display, bucketed output, first-choice, alternatives, and rejection formatting into `backend/admissions_presenter.py`. | Admissions focused tests, py_compile, and full quality gates passed. |
| Step 7C | `e134863 refactor: extract admissions scoring logic` | Extracted bucket constants, rank/score bucket scoring, bucket resolution, and gap calculation into `backend/admissions_scoring.py`. | New scoring regression, 66 backend tests, and full quality gates passed. |
| Step 7D | `8153efc refactor: extract admissions query logic` | Extracted candidate SQL, history map, explicit rule map, and candidate pair clause into `backend/admissions_query.py`. | New query regression, 67 backend tests, and full quality gates passed. |
| Step 8 | Pending commit | Added `ProductFlowGuide.vue`, `productFlow.js`, and `check_product_flow.cjs`; mounted the first-entry flow on Dashboard, Student Detail, Analysis, and Reports. | `npm run test:product-flow`, `npm run lint`, `npm run test:backend`, `npm run build`, and `npm run test:frontend:error-states` passed. |

## Current Structure

`ReportsPage.vue` no longer owns all report display blocks directly. The following report components now isolate major UI responsibilities:

- `ReportResultSourceBanner.vue`
- `ReportOutlineCard.vue`
- `ReportProductCatalog.vue`
- `ReportRecommendationTable.vue`
- `ReportTraceabilityPanel.vue`

`admissions_engine.py` is now mainly orchestration. It delegates to:

- `admissions_context.py` for student context, track, batch, and rank resolution.
- `admissions_risk.py` for explicit and heuristic risk logic.
- `admissions_presenter.py` for recommendation output shaping.
- `admissions_scoring.py` for bucket scoring and gap calculation.
- `admissions_query.py` for candidate data access.

## Product Flow

The first-entry product flow is now explicit and reusable:

1. Entry guidance / profile analysis: build the student file and profile context.
2. Score conversion: convert formal score/rank into explainable bucket and risk context.
3. Formal recommendation report: select a formal report product and export delivery artifacts.

The flow is defined in `src/constants/productFlow.js` and rendered by `src/components/ProductFlowGuide.vue`.

## Remaining Recommendations

- Add a Playwright happy-path smoke test for the first-entry flow once stable fixture data is available.
- Continue splitting large frontend pages only where a block has a clear responsibility boundary.
- Avoid further backend splitting until a concrete behavior change requires it; the current admissions engine boundary is now serviceable.
