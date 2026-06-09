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
IMPORTED_DIR = PROJECT_ROOT / "data_assets" / "imported" / "henan_score_segments"
HENAN_ROOT = PROJECT_ROOT / "河南-2026志愿填报资料"

LEGACY_FILE = HENAN_ROOT / "3、河南高考历史数据" / "河南_一分一段" / "河南_一分一段_2023之前.xlsx"
RICH_FILES = {
    2022: HENAN_ROOT / "2、河南录取数据22-25【持续更新】" / "一分一段" / "河南2022年的一分一段表.xlsx",
    2023: HENAN_ROOT / "2、河南录取数据22-25【持续更新】" / "一分一段" / "河南2023年的一分一段表.xlsx",
    2024: HENAN_ROOT / "2、河南录取数据22-25【持续更新】" / "一分一段" / "河南2024年的一分一段表.xlsx",
    2025: HENAN_ROOT / "2、河南录取数据22-25【持续更新】" / "一分一段" / "河南2025年的一分一段表.xlsx",
}

LEGACY_BATCH_CODE = "legacy_total"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import Henan score_segments datasets into the planning database."
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
        "理工": "理科",
        "文史": "文科",
    }
    return alias_map.get(text, text)


def _normalize_batch(value: Any) -> str | None:
    text = _normalize_text(value)
    if not text:
        return None
    alias_map = {
        "本科第一批": "本科一批",
        "本科第二批": "本科二批",
        "高职高专批": "专科批",
    }
    return alias_map.get(text, text)


def _detect_schema(row: dict[str, str]) -> str:
    headers = set(row.keys())
    if {"年份", "科类", "批次", "控制线(分)", "分数(分)", "本段人数(人)", "累计人数(人)"} <= headers:
        return "rich"
    if {"省份", "年份", "科类", "分数", "本段人数", "累计人数"} <= headers:
        return "legacy"
    raise ValueError(f"Unsupported score_segments schema with headers: {sorted(headers)}")


def _legacy_row_to_segment(row: dict[str, str]) -> dict[str, object] | None:
    exam_year = _parse_int(row.get("年份"))
    if exam_year is None or exam_year >= 2022:
        return None
    score_text = _normalize_text(row.get("分数"))
    subject_track = _normalize_subject_track(row.get("科类"))
    cumulative_count = _parse_int(row.get("累计人数"))
    if not (score_text and subject_track and cumulative_count is not None):
        return None
    return {
        "exam_year": exam_year,
        "province": "河南",
        "exam_type": "gaokao",
        "subject_track": subject_track,
        "batch_code": LEGACY_BATCH_CODE,
        "control_line": None,
        "score_text": score_text,
        "score_value": _parse_float(score_text),
        "segment_count": _parse_int(row.get("本段人数")),
        "cumulative_count": cumulative_count,
        "rank_range": None,
        "historical_same_rank_score": None,
        "source_schema": "legacy",
    }


def _rich_row_to_segment(row: dict[str, str]) -> dict[str, object] | None:
    exam_year = _parse_int(row.get("年份"))
    score_text = _normalize_text(row.get("分数(分)"))
    subject_track = _normalize_subject_track(row.get("科类"))
    batch_code = _normalize_batch(row.get("批次"))
    cumulative_count = _parse_int(row.get("累计人数(人)"))
    if not (exam_year and score_text and subject_track and batch_code and cumulative_count is not None):
        return None
    return {
        "exam_year": exam_year,
        "province": "河南",
        "exam_type": "gaokao",
        "subject_track": subject_track,
        "batch_code": batch_code,
        "control_line": _parse_float(row.get("控制线(分)")),
        "score_text": score_text,
        "score_value": _parse_float(score_text),
        "segment_count": _parse_int(row.get("本段人数(人)")),
        "cumulative_count": cumulative_count,
        "rank_range": _normalize_text(row.get("排名区间")),
        "historical_same_rank_score": _normalize_text(row.get("历史同位次考生得分")),
        "source_schema": "rich",
    }


def load_henan_score_segments(limit_per_file: int | None = None) -> tuple[list[dict[str, object]], dict[str, object]]:
    rows: list[dict[str, object]] = []
    sources: list[dict[str, object]] = []

    legacy_count = 0
    for _, row in iter_sheet_records(LEGACY_FILE, limit=limit_per_file):
        schema = _detect_schema(row)
        if schema != "legacy":
            raise ValueError(f"Unexpected schema for legacy file: {schema}")
        normalized = _legacy_row_to_segment(row)
        if normalized:
            normalized["source_file"] = str(LEGACY_FILE)
            rows.append(normalized)
            legacy_count += 1
    sources.append(
        {
            "source_file": str(LEGACY_FILE),
            "schema": "legacy",
            "selected_years": [2017, 2018, 2019, 2020, 2021],
            "normalized_row_count": legacy_count,
        }
    )

    for year, file_path in sorted(RICH_FILES.items()):
        file_count = 0
        for _, row in iter_sheet_records(file_path, limit=limit_per_file):
            schema = _detect_schema(row)
            if schema != "rich":
                raise ValueError(f"Unexpected schema for rich file {file_path.name}: {schema}")
            normalized = _rich_row_to_segment(row)
            if normalized:
                normalized["source_file"] = str(file_path)
                rows.append(normalized)
                file_count += 1
        sources.append(
            {
                "source_file": str(file_path),
                "schema": "rich",
                "selected_years": [year],
                "normalized_row_count": file_count,
            }
        )

    metadata = {
        "source_selection": sources,
        "legacy_batch_code": LEGACY_BATCH_CODE,
    }
    return rows, metadata


def _write_normalized_files(rows: list[dict[str, object]]) -> None:
    IMPORTED_DIR.mkdir(parents=True, exist_ok=True)
    sample_rows = rows[:200]
    write_json(IMPORTED_DIR / "score_segments.sample.json", sample_rows)
    write_csv(IMPORTED_DIR / "score_segments.sample.csv", sample_rows)


def main() -> None:
    args = parse_args()
    if not args.dry_run:
        from backend.admissions_repository import get_admissions_schema_overview, upsert_score_segments
        from backend.database import init_db

        init_db()

    rows, metadata = load_henan_score_segments(limit_per_file=args.limit)
    _write_normalized_files(rows)

    summary: dict[str, object] = {
        "scope": "henan_score_segments",
        "normalized_counts": {"score_segments": len(rows)},
        "limit_per_file": args.limit,
        "dry_run": args.dry_run,
        "source_selection": metadata,
    }

    if not args.dry_run:
        import_counts = {
            "score_segments": upsert_score_segments(rows),
        }
        summary["import_counts"] = import_counts
        summary["schema_overview"] = get_admissions_schema_overview()

    write_json(IMPORTED_DIR / "henan_score_segments_import_summary.json", summary)

    print("=== HENAN SCORE SEGMENTS IMPORT SUMMARY ===")
    print(f"score_segments: normalized={len(rows)}")
    if not args.dry_run:
        print("=== DATABASE UPSERT COUNTS ===")
        print(f"score_segments: upserted={summary['import_counts']['score_segments']}")
    else:
        print("Dry run completed. No database rows were written.")


if __name__ == "__main__":
    main()
