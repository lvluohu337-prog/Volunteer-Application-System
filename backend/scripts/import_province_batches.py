from __future__ import annotations

import argparse
import sys
import re
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from backend.admissions_importer import iter_sheet_records
from backend.excel_importer import write_csv, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[2]
IMPORTED_DIR = PROJECT_ROOT / "data_assets" / "imported" / "henan_province_batches"

LEGACY_FILE = PROJECT_ROOT / "data_assets" / "data-needed-standardized" / "02_batches_policies" / "from_province_firstlook" / "各省高考志愿数据【首看】" / "河南" / "河南17-23年" / "河南-历年高考数据" / "2008-2020各省-批次线.xlsx"
RICH_FILE = PROJECT_ROOT / "data_assets" / "data-needed-standardized" / "02_batches_policies" / "from_province_firstlook" / "各省高考志愿数据【首看】" / "河南" / "河南17-23年" / "河南-历年高考数据" / "河南_省控线_批次线_2022_2014.xlsx"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import Henan province_batches datasets into the planning database."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only process the first N rows from each selected workbook.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build normalized outputs and summaries without writing to the database.",
    )
    return parser.parse_args()


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_int(value: Any) -> int | None:
    text = _normalize_text(value)
    if not text:
        return None
    match = re.search(r"-?\d+", text.replace(",", ""))
    if not match:
        return None
    return int(match.group(0))


def _parse_float(value: Any) -> float | None:
    text = _normalize_text(value)
    if not text:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", text.replace(",", ""))
    if not match:
        return None
    return float(match.group(0))


def _normalize_subject_track(value: Any) -> str | None:
    text = _normalize_text(value)
    if not text:
        return None
    alias_map = {
        "文史": "文科",
        "理工": "理科",
    }
    return alias_map.get(text, text)


def _normalize_batch_name(value: Any) -> str | None:
    return _normalize_text(value)


def _normalize_batch_code(value: Any) -> str | None:
    text = _normalize_text(value)
    if not text:
        return None
    alias_map = {
        "一本": "本科一批",
        "二本": "本科二批",
        "三本": "本科三批",
        "专科一批": "专科批",
        "普通本科": "普通本科",
        "普通本科批": "普通本科批",
        "普通专科": "专科批",
        "本科一批": "本科一批",
        "本科二批": "本科二批",
        "本科三批": "本科三批",
        "专科批": "专科批",
        "高职(专科)": "专科批",
        "高职(专科)分数线": "专科批",
        "高职专科": "专科批",
        "高职高专": "专科批",
        "高职高专批": "专科批",
        "高职高专一批": "专科批",
        "高职高专二批录取控制分数线": "专科批",
        "高职高专批次": "专科批",
        "体育类（本科）": "体育类本科",
        "体育类（高职专科）": "体育类高职专科",
    }
    return alias_map.get(text, text)


def _detect_schema(row: dict[str, str]) -> str:
    headers = set(row.keys())
    if {"年份", "省份", "文理", "批次", "分数"} <= headers:
        return "legacy"
    if {"省份", "年份", "类别", "批次", "分数线", "专业分"} <= headers:
        return "rich"
    raise ValueError(f"Unsupported province_batches schema with headers: {sorted(headers)}")


def _legacy_row_to_batch(row: dict[str, str]) -> dict[str, object] | None:
    if row.get("省份") != "河南":
        return None
    exam_year = _parse_int(row.get("年份"))
    subject_track = _normalize_subject_track(row.get("文理"))
    batch_name = _normalize_batch_name(row.get("批次"))
    batch_code = _normalize_batch_code(batch_name)
    score_line = _parse_float(row.get("分数"))
    if not (exam_year and subject_track and batch_name and batch_code and score_line is not None):
        return None
    return {
        "exam_year": exam_year,
        "province": "河南",
        "exam_type": "gaokao",
        "subject_track": subject_track,
        "batch_code": batch_code,
        "batch_name": batch_name,
        "score_line": score_line,
        "rank_line": None,
        "notes": None,
        "source_schema": "legacy",
    }


def _rich_row_to_batch(row: dict[str, str]) -> dict[str, object] | None:
    if row.get("省份") != "河南":
        return None
    exam_year = _parse_int(row.get("年份"))
    subject_track = _normalize_subject_track(row.get("类别"))
    batch_name = _normalize_batch_name(row.get("批次"))
    batch_code = _normalize_batch_code(batch_name)
    score_line = _parse_float(row.get("分数线"))
    if not (exam_year and subject_track and batch_name and batch_code and score_line is not None):
        return None
    professional_line = _parse_float(row.get("专业分"))
    notes = None
    if professional_line not in (None, 0):
        notes = f"专业分:{professional_line:g}"
    return {
        "exam_year": exam_year,
        "province": "河南",
        "exam_type": "gaokao",
        "subject_track": subject_track,
        "batch_code": batch_code,
        "batch_name": batch_name,
        "score_line": score_line,
        "rank_line": None,
        "notes": notes,
        "source_schema": "rich",
    }


def load_henan_province_batches(limit_per_file: int | None = None) -> tuple[list[dict[str, object]], dict[str, object]]:
    rows_by_key: dict[tuple[Any, ...], dict[str, object]] = {}

    legacy_count = 0
    for _, row in iter_sheet_records(LEGACY_FILE, limit=limit_per_file):
        normalized = _legacy_row_to_batch(row)
        if not normalized:
            continue
        normalized["source_file"] = str(LEGACY_FILE)
        key = (
            normalized["exam_year"],
            normalized["province"],
            normalized["subject_track"],
            normalized["batch_code"],
        )
        rows_by_key[key] = normalized
        legacy_count += 1

    rich_count = 0
    for _, row in iter_sheet_records(RICH_FILE, limit=limit_per_file):
        normalized = _rich_row_to_batch(row)
        if not normalized:
            continue
        normalized["source_file"] = str(RICH_FILE)
        key = (
            normalized["exam_year"],
            normalized["province"],
            normalized["subject_track"],
            normalized["batch_code"],
        )
        rows_by_key[key] = normalized
        rich_count += 1

    rows = sorted(
        rows_by_key.values(),
        key=lambda item: (
            int(item["exam_year"]),
            str(item.get("subject_track") or ""),
            str(item.get("batch_code") or ""),
        ),
    )

    existing_pairs = {(int(item["exam_year"]), str(item.get("subject_track") or "")) for item in rows}
    coverage_gaps = [
        {"exam_year": 2021, "subject_track": "文科", "reason": "未发现 2021 河南文科批次线结构化源"},
        {"exam_year": 2022, "subject_track": "文科", "reason": "未发现 2022 河南文科批次线结构化源"},
    ]
    source_selection = {
        "legacy_source": str(LEGACY_FILE),
        "rich_source": str(RICH_FILE),
        "legacy_selected_years": list(range(2008, 2021)),
        "rich_selected_years": list(range(2014, 2023)),
        "override_rule": "2014-2022 河南理科使用 richer file 覆盖 legacy file；其余沿用 legacy",
        "coverage_gaps": [gap for gap in coverage_gaps if (gap["exam_year"], gap["subject_track"]) not in existing_pairs],
        "normalized_row_count": len(rows),
        "legacy_row_count": legacy_count,
        "rich_row_count": rich_count,
    }
    return rows, source_selection


def _write_normalized_files(rows: list[dict[str, object]]) -> None:
    IMPORTED_DIR.mkdir(parents=True, exist_ok=True)
    sample_rows = rows[:200]
    write_json(IMPORTED_DIR / "province_batches.sample.json", sample_rows)
    write_csv(IMPORTED_DIR / "province_batches.sample.csv", sample_rows)


def main() -> None:
    args = parse_args()
    if not args.dry_run:
        from backend.admissions_repository import get_admissions_schema_overview, upsert_province_batches
        from backend.database import init_db

        init_db()

    rows, source_selection = load_henan_province_batches(limit_per_file=args.limit)
    _write_normalized_files(rows)

    summary: dict[str, object] = {
        "scope": "henan_province_batches",
        "normalized_counts": {"province_batches": len(rows)},
        "limit_per_file": args.limit,
        "dry_run": args.dry_run,
        "source_selection": source_selection,
    }

    if not args.dry_run:
        import_counts = {"province_batches": upsert_province_batches(rows)}
        summary["import_counts"] = import_counts
        summary["schema_overview"] = get_admissions_schema_overview()

    write_json(IMPORTED_DIR / "henan_province_batches_import_summary.json", summary)

    print("=== HENAN PROVINCE BATCHES IMPORT SUMMARY ===")
    print(f"province_batches: normalized={len(rows)}")
    if not args.dry_run:
        print("=== DATABASE UPSERT COUNTS ===")
        print(f"province_batches: upserted={summary['import_counts']['province_batches']}")
    else:
        print("Dry run completed. No database rows were written.")


if __name__ == "__main__":
    main()
