from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from backend.admissions_importer import iter_sheet_records
from backend.excel_importer import write_csv, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[2]
HENAN_HISTORY_ROOT = PROJECT_ROOT / "河南-2026志愿填报资料" / "3、河南高考历史数据" / "河南_专业分数线"
IMPORTED_DIR = PROJECT_ROOT / "data_assets" / "imported" / "henan_major_admission_scores"
SOURCE_YEARS = [2017, 2018, 2019, 2020, 2021]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import Henan major admission scores datasets into the planning database."
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


def _normalize_batch(value: Any) -> str | None:
    text = _normalize_text(value)
    if not text:
        return None
    alias_map = {
        "本一": "本科一批",
        "本二": "本科二批",
        "本三": "本科三批",
        "高职高专": "专科批",
        "高职高专批": "专科批",
    }
    return alias_map.get(text, text)


def _institution_meta_row(row: dict[str, str]) -> dict[str, object] | None:
    institution_name = _normalize_text(row.get("学校"))
    institution_code = _normalize_text(row.get("全国统一招生代码"))
    if not institution_name:
        return None
    return {
        "institution_code": institution_code,
        "institution_name": institution_name,
        "province": _normalize_text(row.get("省份")),
        "city": _normalize_text(row.get("城市")),
        "public_private": _normalize_text(row.get("办学性质")),
        "institution_level": _normalize_text(row.get("学校类别")),
    }


def _major_meta_row(row: dict[str, str]) -> dict[str, object] | None:
    major_name = _normalize_text(row.get("专业"))
    if not major_name:
        return None
    return {
        "major_code": _normalize_text(row.get("专业代码")) or "",
        "major_name": major_name,
        "major_category": _normalize_text(row.get("门类")) or _normalize_text(row.get("一级学科")),
        "degree_level": _normalize_text(row.get("学历类别")),
    }


def _major_score_row(row: dict[str, str]) -> dict[str, object] | None:
    exam_year = _parse_int(row.get("年份"))
    institution_name = _normalize_text(row.get("学校"))
    major_name = _normalize_text(row.get("专业"))
    subject_track = _normalize_subject_track(row.get("科类"))
    batch_code = _normalize_batch(row.get("批次"))
    min_score = _parse_float(row.get("最低分"))
    if not (exam_year and institution_name and major_name and subject_track and batch_code and min_score is not None):
        return None
    return {
        "exam_year": exam_year,
        "province": "河南",
        "exam_type": "gaokao",
        "subject_track": subject_track,
        "batch_code": batch_code,
        "institution_code": _normalize_text(row.get("全国统一招生代码")) or "",
        "institution_name": institution_name,
        "major_code": _normalize_text(row.get("专业代码")) or "",
        "major_name": major_name,
        "plan_group_code": None,
        "min_score": min_score,
        "min_rank": _parse_int(row.get("最低分排名")),
        "avg_score": _parse_float(row.get("平均分")),
        "avg_rank": None,
        "max_score": _parse_float(row.get("最高分")),
        "max_rank": None,
        "planned_count": None,
        "admitted_count": None,
        "notes": _normalize_text(row.get("招生类型")),
    }


def load_henan_historical_major_scores(
    limit_per_file: int | None = None,
) -> tuple[dict[str, list[dict[str, object]]], dict[str, object]]:
    institutions: dict[tuple[str, str], dict[str, object]] = {}
    majors: dict[tuple[str, str], dict[str, object]] = {}
    rows: list[dict[str, object]] = []
    source_selection: list[dict[str, object]] = []

    for year in SOURCE_YEARS:
        path = HENAN_HISTORY_ROOT / f"河南_专业分数线_{year}.xlsx"
        normalized_count = 0
        for _, row in iter_sheet_records(path, limit=limit_per_file):
            institution_meta = _institution_meta_row(row)
            if institution_meta:
                institutions[
                    (
                        str(institution_meta.get("institution_code") or ""),
                        str(institution_meta["institution_name"]),
                    )
                ] = institution_meta
            major_meta = _major_meta_row(row)
            if major_meta:
                majors[
                    (
                        str(major_meta.get("major_code") or ""),
                        str(major_meta["major_name"]),
                    )
                ] = major_meta
            normalized = _major_score_row(row)
            if not normalized:
                continue
            normalized["source_file"] = str(path)
            rows.append(normalized)
            normalized_count += 1

        source_selection.append(
            {
                "exam_year": year,
                "source_file": str(path),
                "normalized_row_count": normalized_count,
            }
        )

    datasets = {
        "institutions": list(institutions.values()),
        "majors": list(majors.values()),
        "major_admission_scores": rows,
    }
    metadata = {
        "source_selection": source_selection,
        "target_years": SOURCE_YEARS,
        "import_scope": "supplement_2017_2021_only",
    }
    return datasets, metadata


def _write_normalized_files(datasets: dict[str, list[dict[str, object]]]) -> None:
    IMPORTED_DIR.mkdir(parents=True, exist_ok=True)
    for key, rows in datasets.items():
        sample_rows = rows[:200]
        write_json(IMPORTED_DIR / f"{key}.sample.json", sample_rows)
        write_csv(IMPORTED_DIR / f"{key}.sample.csv", sample_rows)


def main() -> None:
    args = parse_args()
    if not args.dry_run:
        from backend.admissions_repository import (
            get_admissions_schema_overview,
            upsert_institutions,
            upsert_major_admission_scores,
            upsert_majors,
        )
        from backend.database import init_db

        init_db()

    datasets, metadata = load_henan_historical_major_scores(limit_per_file=args.limit)
    _write_normalized_files(datasets)

    summary: dict[str, object] = {
        "scope": "henan_major_admission_scores",
        "normalized_counts": {key: len(value) for key, value in datasets.items()},
        "limit_per_file": args.limit,
        "dry_run": args.dry_run,
        "source_selection": metadata,
    }

    if not args.dry_run:
        import_counts = {
            "institutions": upsert_institutions(datasets["institutions"]),
            "majors": upsert_majors(datasets["majors"]),
            "major_admission_scores": upsert_major_admission_scores(
                datasets["major_admission_scores"]
            ),
        }
        summary["import_counts"] = import_counts
        summary["schema_overview"] = get_admissions_schema_overview()

    write_json(IMPORTED_DIR / "henan_major_admission_scores_import_summary.json", summary)

    print("=== HENAN MAJOR ADMISSION SCORES IMPORT SUMMARY ===")
    for key, count in summary["normalized_counts"].items():
        print(f"{key}: normalized={count}")
    if not args.dry_run:
        print("=== DATABASE UPSERT COUNTS ===")
        for key, count in summary["import_counts"].items():
            print(f"{key}: upserted={count}")
    else:
        print("Dry run completed. No database rows were written.")


if __name__ == "__main__":
    main()
