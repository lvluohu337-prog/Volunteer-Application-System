# Family-Facing Report Experience Design

## Goal

Turn the current report management page into a final report experience for students and high-cognition parents. The page should help them quickly understand the conclusion, trust the evidence, inspect the 48 college-major-group plan, and know what must be confirmed before submission.

## Audience

- Primary users: 2026 Henan examinees and parents who can understand ranks, admission history, plan counts, and policy constraints.
- Secondary users: teachers or advisors who use the page during explanation and delivery.
- Non-goal: this redesign is not an internal CRM, template editor, or export-record management dashboard.

## Current Problem

The current report page contains useful modules, but the hierarchy still feels like a backend management page:

- product switching, report catalog, profile explanation, recommendation table, alternatives, export buttons, notes, delivery records, and traceability all compete for attention.
- the strongest product value, namely the formal 48 college-major-group plan and why it is credible, is not dominant enough.
- parent-facing confidence is weakened because evidence, risk, and next actions are scattered.
- advisor-only controls appear too early in the reading flow.

## Product Principle

The page should read like a professional final recommendation report:

1. First screen answers: "What is the recommendation and can I trust it?"
2. Main body answers: "What exactly should we fill, and why?"
3. Review section answers: "What must a human verify before final submission?"
4. Operations are available but visually secondary.

## Proposed Page Structure

### 1. Report Cover Summary

Purpose: create immediate confidence and orientation.

Content:

- student name, province, subject track, score, rank, batch, latest reference year
- product version, strategy mode, data source status
- one-sentence conclusion such as "建议采用稳妥型六档方案，以稳妥主力和保底承接为核心"
- primary actions: export PDF, export Word, copy/share summary if available later

Design:

- full-width report header instead of a dashboard card cluster
- restrained professional style, closer to a formal consulting deliverable
- use status chips for "真实招生数据", "位次来源", "人工复核项"

### 2. Core Conclusion

Purpose: tell the family what matters before showing dense tables.

Content:

- first-choice recommendation
- main major direction
- strategy distribution: 险/冲/稳/保/垫/兜 or default冲/稳/保
- top 3 risks
- top 3 confirmation tasks

Behavior:

- each conclusion item links or scrolls to its evidence section
- risk items are concrete, not generic warnings

### 3. Formal 48-Group Plan

Purpose: make the formal plan inspectable and explainable.

Content:

- six-tier tabs or segmented control: 险、冲、稳、保、垫、兜
- each tier shows count, purpose, and a compact table
- row fields:
  - order within tier
  - institution and city
  - major and college-major-group code
  - minimum score/rank
  - rank gap and probability
  - plan count and volatility tag
  - risk/confirmation tag

Behavior:

- default view shows all tiers as grouped sections for reading.
- table can collapse/expand tier details.
- first-choice row is visually marked.
- adjusted rows from neighbor-bucket fill are labeled as "补位".

### 4. Evidence And Risk Explanation

Purpose: support trust without overwhelming the first screen.

Content:

- rank evidence: current rank vs historical minimum rank
- score evidence: current score vs historical minimum score
- plan risk: expansion/shrinkage and volatility
- subject requirement status
- adjustment and professional-group internal acceptance notes
- policy/charter confirmation reminder

Design:

- evidence should be grouped as readable proof blocks, not a wall of small cards.
- each evidence block should explain "what it means", not only display raw values.

### 5. Human Review Checklist

Purpose: prevent overclaiming and show professional responsibility.

Content:

- 招生章程
- 组内 6 个专业接受度
- 是否服从调剂
- 体检/单科/语种/性别限制
- 当年招生计划变化
- 最终志愿系统录入顺序

Behavior:

- checklist is visible before export or confirmation.
- later implementation can support checked state, but v1 may be read-only.

### 6. Delivery And Advisor Area

Purpose: keep operational features without making the page feel like a backend.

Content:

- export history
- advisor notes
- generation records
- traceability details

Placement:

- lower page section or secondary side panel
- collapsed by default on family-facing view unless there is an error or pending action

## Data Contract Changes

Prefer reusing existing report payload fields:

- `ruleSummary.strategy`: already carries strategy mode, display tiers, and counts.
- `recommendationTable`: already carries `displayTier`, `displayTierLabel`, `displayTierTitle`, `bucket`, risk, score, rank, and reason fields.
- `firstChoice`, `alternatives`, and `notRecommended`: keep current contracts.
- `resultSource`: keep current source-status contract.

Possible additive fields if needed:

- `ruleSummary.finalConclusion`: one-sentence family-facing conclusion.
- `ruleSummary.reviewChecklist`: list of required manual review items.
- `recommendationTable[].orderInTier`: display order inside each tier.
- `recommendationTable[].reviewTags`: compact row-level tags such as "调剂需确认", "大小年", "计划缩减".

No destructive API changes should be made. Existing consumers must continue to work if these new fields are absent.

## Frontend Impact

Likely files:

- `src/pages/ReportsPage.vue`: reorganize page sections and computed report groups.
- `src/components/reports/ReportOutlineCard.vue`: replace catalog-style first impression with family-facing report summary or reduce its prominence.
- `src/components/reports/ReportRecommendationTable.vue`: change from backend-like bucket tables to formal plan sections/tabs.
- `src/components/reports/ReportResultSourceBanner.vue`: make it part of trust evidence, not a warning banner unless degraded.
- `src/components/reports/ReportTraceabilityPanel.vue`: move lower or collapse under "数据依据".

Potential new components:

- `ReportHeroSummary.vue`
- `ReportCoreConclusion.vue`
- `ReportEvidencePanel.vue`
- `ReportReviewChecklist.vue`

## Backend Impact

Backend should remain mostly stable. Additive improvements only:

- build family-facing conclusion text from existing strategy and first-choice data
- optionally emit review checklist and row-level tags
- keep PDF/Word export compatible with six display tiers

## Visual Direction

The product should feel:

- professional, calm, credible, and report-like
- dense enough for high-cognition parents, but not visually noisy
- closer to a consulting deliverable than an admin dashboard

Avoid:

- hero marketing style
- decorative gradients dominating the page
- too many cards inside cards
- oversized slogans
- burying the actual 48-group plan below auxiliary content

## Implementation Phases

### Phase 1: First-Screen Reframe

- add report hero summary
- move export actions into hero
- surface result source, strategy mode, score/rank, and core conclusion
- keep old modules lower on the page

### Phase 2: Formal Plan Reading Experience

- redesign recommendation table around six tiers
- add tier counts, purpose text, first-choice marker,补位 marker
- keep responsive behavior for desktop and mobile

### Phase 3: Evidence And Checklist

- add evidence panel and manual review checklist
- move traceability and advisor notes lower
- ensure PDF/Word export still matches the displayed structure

## Acceptance Criteria

- A parent can understand the recommended strategy within 10 seconds of opening the page.
- The first viewport shows student context, strategy mode, recommendation confidence, and export actions.
- The 48 college-major-group plan is visually central and easy to scan by tier.
- Risk and evidence are specific enough to explain why an item is recommended.
- Advisor-only or operational details no longer dominate the first half of the page.
- Existing product flow tests continue to pass.
- Backend tests remain green.
- Frontend build succeeds.

## Open Decisions

- Whether the page should default to "family view" only, or support a teacher/internal toggle.
- Whether manual review checklist should be read-only in v1 or persist checked states.
- Whether to add a shareable public report URL later.
