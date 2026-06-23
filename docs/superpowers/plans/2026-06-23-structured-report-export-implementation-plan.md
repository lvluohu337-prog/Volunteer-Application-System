# Structured Report Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade PDF and Word export so the formal recommendation section renders as a stable 7-column structured table suitable for delivery.

**Architecture:** Keep the existing export pipeline and `report_data` contract unchanged. Only refine table-building helpers in `backend/report_exporters.py`, then lock the behavior with exporter unit tests and integration tests.

**Tech Stack:** Python 3, existing custom PDF renderer, DOCX XML writer, `unittest`, existing export fixtures.

---

## File Structure

- Modify: `backend/report_exporters.py` - stabilize the formal recommendation table headers and cell formatting, reusing existing table rendering code.
- Modify: `backend/tests/test_report_exporter_unit.py` - assert the new core table headers and exported content.
- Modify: `backend/tests/test_report_export_integration.py` - keep delivery-path regression coverage after exporter changes.
- Optional Modify: `backend/tests/report_export_fixtures.py` - only if fixture data needs one more stable field for tests.

### Task 1: Lock the 7-column export contract with failing tests

**Files:**
- Modify: `backend/tests/test_report_exporter_unit.py`

- [ ] **Step 1: Write the failing exporter assertions**

Add assertions for the fixed 7-column headers in both PDF text extraction and DOCX XML:

```python
        self.assertIn("院校", extracted_text)
        self.assertIn("专业", extracted_text)
        self.assertIn("专业组 / 代码", extracted_text)
        self.assertIn("城市", extracted_text)
        self.assertIn("最低分 / 位次", extracted_text)
        self.assertIn("录取概率", extracted_text)
        self.assertIn("风险提示", extracted_text)
```

- [ ] **Step 2: Run the focused exporter unit tests to verify red**

Run: `python -m unittest backend.tests.test_report_exporter_unit -v`

Expected: FAIL because the current exported headers still use the older mixed columns such as `院校 / 专业 / 城市` and `推荐理由`.

- [ ] **Step 3: Commit the red test only if you are working in a red/green branch workflow**

```bash
git add backend/tests/test_report_exporter_unit.py
git commit -m "test: lock structured report export headers"
```

### Task 2: Implement the 7-column structured export

**Files:**
- Modify: `backend/report_exporters.py`

- [ ] **Step 1: Refine the recommendation table helper**

Update the main structured recommendation table builder so it emits the 7 fixed headers:

```python
    headers = (
        "院校",
        "专业",
        "专业组 / 代码",
        "城市",
        "最低分 / 位次",
        "录取概率",
        "风险提示",
    )
```

- [ ] **Step 2: Add focused value-formatting helpers**

Use small helpers for:

- institution text
- major text
- city text
- merged score/rank text
- probability label text
- merged risk summary text

Keep these helpers inside `backend/report_exporters.py` and reuse existing risk-text builders where possible.

- [ ] **Step 3: Keep the existing table rendering path unchanged**

Do not rewrite `_build_docx_table_xml()` or `_build_pdf_page_streams()`. Only change the data fed into `ReportBlock("table", ...)`.

- [ ] **Step 4: Run the focused exporter unit tests to verify green**

Run: `python -m unittest backend.tests.test_report_exporter_unit -v`

Expected: PASS

- [ ] **Step 5: Commit the exporter implementation**

```bash
git add backend/report_exporters.py backend/tests/test_report_exporter_unit.py
git commit -m "feat: export structured recommendation core table"
```

### Task 3: Verify delivery-path compatibility

**Files:**
- Modify: `backend/tests/test_report_export_integration.py` (only if needed)

- [ ] **Step 1: Re-run integration regression before editing**

Run: `python -m unittest backend.tests.test_report_export_integration -v`

Expected: PASS, or a focused failure if exporter output changed an integration assumption.

- [ ] **Step 2: Fix only the broken integration assertions if required**

If the test fails, only update assertions that now need to recognize the stable structured export output. Do not weaken file-generation checks.

- [ ] **Step 3: Run both exporter suites together**

Run: `python -m unittest backend.tests.test_report_exporter_unit backend.tests.test_report_export_integration -v`

Expected: PASS

- [ ] **Step 4: Commit the compatibility adjustments**

```bash
git add backend/tests/test_report_export_integration.py
git commit -m "test: keep structured export delivery regression green"
```

### Task 4: Final backend verification and docs sync

**Files:**
- Optional Modify: `README.md` only if status wording needs to change after implementation

- [ ] **Step 1: Run the export-related backend regression cluster**

Run: `python -m unittest backend.tests.test_report_exporter_unit backend.tests.test_report_export_integration backend.tests.test_report_delivery_download -v`

Expected: PASS

- [ ] **Step 2: Run the full backend suite**

Run: `python -m unittest discover -s backend/tests`

Expected: PASS

- [ ] **Step 3: Update README export status if the implementation closes the previous gap**

If the 7-column structured table is truly shipped, update README wording so it no longer says the exporter is only paragraph-based.

- [ ] **Step 4: Commit the final documentation/status sync**

```bash
git add README.md
git commit -m "docs: update structured export delivery status"
```

## Self-Review

### 1. Spec coverage

- Main 7-column structured table: covered by Task 1 and Task 2
- Separate tables for first choice / alternatives / not recommended: preserved by Task 2 and checked through regression in Task 3
- Delivery-path stability: covered by Task 3
- Full backend verification: covered by Task 4

### 2. Placeholder scan

No `TODO` / `TBD` placeholders remain. Commands and touched files are explicit.

### 3. Type consistency

The plan consistently keeps all changes inside the existing `report_data -> ReportBlock("table") -> PDF/DOCX renderer` path and does not introduce a parallel export contract.
