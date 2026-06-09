from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from backend.admissions_importer import iter_sheet_records
from backend.excel_importer import write_csv, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = (
    PROJECT_ROOT
    / "data_assets"
    / "data-needed-standardized"
    / "metadata"
    / "05_admission_plans_inventory.csv"
)
IMPORTED_DIR = PROJECT_ROOT / "data_assets" / "imported" / "henan_admission_plans"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import Henan admission_plans datasets into the planning database."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only process the first N data rows from each selected workbook.",
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


def _normalize_province(value: Any) -> str:
    text = _normalize_text(value) or "河南"
    return text.replace("H", "").strip() or "河南"


def _normalize_optional_text(value: Any) -> str | None:
    text = _normalize_text(value)
    if not text or text in {"-", "--", "0"}:
        return None
    return text


def _normalize_subject_track(value: Any) -> str | None:
    text = _normalize_text(value)
    if not text:
        return None
    alias_map = {
        "文科": "文科",
        "理科": "理科",
        "文史": "文科",
        "理工": "理科",
    }
    return alias_map.get(text, text)


def _normalize_batch(value: Any) -> str | None:
    text = _normalize_text(value)
    if not text:
        return None
    alias_map = {
        "本科第一批": "本科一批",
        "本科第二批": "本科二批",
        "本科第三批": "本科三批",
        "高职高专批": "专科批",
    }
    return alias_map.get(text, text)


def _normalize_school_name(value: Any) -> str | None:
    return _normalize_text(value)


def _split_major_name_and_notes(value: Any) -> tuple[str | None, str | None]:
    text = _normalize_text(value)
    if not text:
        return None, None
    normalized = text.replace("（", "(").replace("）", ")")
    base = normalized.split("(", 1)[0].strip()
    notes = normalized[len(base) :].strip() if base and len(normalized) > len(base) else ""
    return base or normalized, notes or None


def _infer_degree_level(batch_code: str | None) -> str | None:
    text = batch_code or ""
    if "本科" in text:
        return "本科"
    if "专科" in text or "高职" in text:
        return "专科"
    return None


def _major_key(code: str | None, name: str | None) -> tuple[str, str]:
    return (code or "", name or "")


def _choose_file_for_year(rows: list[dict[str, str]]) -> dict[str, str]:
    def score(item: dict[str, str]) -> tuple[int, int, str]:
        path = item["file_path"]
        if "高考录取数据-2024年" in path:
            priority = 0
        elif "高考录取数据-17-23年" in path:
            priority = 1
        elif "河南17-23年" in path:
            priority = 2
        else:
            priority = 3
        return (priority, len(path), path)

    return sorted(rows, key=score)[0]


def _load_henan_plan_sources() -> tuple[list[dict[str, str]], dict[str, list[str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    with INVENTORY_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row.get("province") != "河南":
                continue
            if row.get("file_type") != ".xlsx":
                continue
            grouped[row["year"]].append(row)

    selected: list[dict[str, str]] = []
    skipped: dict[str, list[str]] = {}
    for year in sorted(grouped):
        chosen = _choose_file_for_year(grouped[year])
        selected.append(chosen)
        skipped[year] = [
            item["file_path"]
            for item in grouped[year]
            if item["file_path"] != chosen["file_path"]
        ]
    return selected, skipped


def _detect_schema(row: dict[str, str]) -> str:
    headers = set(row.keys())
    if "全国统一招生代码" in headers and "招生人数" in headers and "学校" in headers:
        return "henan_2017_2022"
    if "院校代码" in headers and "院校名称" in headers and "计划数" in headers:
        return "henan_2023"
    if "招生代码" in headers and "学校" in headers and "计划人数" in headers:
        return "henan_2024"
    raise ValueError(f"Unsupported Henan admission_plans schema with headers: {sorted(headers)}")


def _schema_field(row: dict[str, str], schema: str, field: str) -> str | None:
    field_map = {
        "henan_2017_2022": {
            "institution_code": "全国统一招生代码",
            "institution_name": "学校",
            "major_name": "专业",
            "major_code": "专业代码",
            "batch_code": "批次",
            "subject_track": "科类",
            "planned_count": "招生人数",
            "study_years": "学制",
            "tuition_yearly": "学费",
            "province": "省份",
        },
        "henan_2023": {
            "institution_code": "院校代码",
            "institution_name": "院校名称",
            "major_name": "专业名称",
            "major_code": "专业代码",
            "batch_code": "批次",
            "subject_track": "科类",
            "planned_count": "计划数",
            "study_years": "学制",
            "tuition_yearly": "学费",
            "province": None,
            "institution_total": "校计划数",
        },
        "henan_2024": {
            "institution_code": "招生代码",
            "institution_name": "学校",
            "major_name": "专业",
            "major_code": "专业代码",
            "batch_code": "批次",
            "subject_track": "科目",
            "planned_count": "计划人数",
            "study_years": "学制",
            "tuition_yearly": "学费",
            "province": "省份",
            "institution_total": "计划总数",
            "school_direction": "学校方向",
        },
    }
    column = field_map[schema].get(field)
    if not column:
        return None
    return _normalize_text(row.get(column))


def _institution_province_from_row(schema: str, row: dict[str, str]) -> str | None:
    if schema == "henan_2017_2022":
        return _normalize_optional_text(row.get("省份"))
    return None


def _parse_tuition(value: Any) -> float | None:
    text = _normalize_optional_text(value)
    if not text:
        return None
    parsed = _parse_float(text)
    if parsed == 0:
        return None
    return parsed


def _institution_row(
    institution_code: str | None,
    institution_name: str | None,
    province: str,
) -> dict[str, object]:
    return {
        "institution_code": institution_code,
        "institution_name": institution_name,
        "province": province,
    }


def _major_row(
    major_code: str | None,
    major_name: str | None,
    study_years: str | None,
    degree_level: str | None,
) -> dict[str, object]:
    return {
        "major_code": major_code,
        "major_name": major_name,
        "study_years": study_years,
        "degree_level": degree_level,
    }


def _build_plan_notes(schema: str, row: dict[str, str], major_notes: str | None) -> str | None:
    notes: list[str] = []
    if major_notes:
        notes.append(major_notes)
    institution_total = _schema_field(row, schema, "institution_total")
    if institution_total:
        notes.append(f"校计划数:{institution_total}")
    school_direction = _schema_field(row, schema, "school_direction")
    if school_direction and school_direction != _schema_field(row, schema, "institution_name"):
        notes.append(f"学校方向:{school_direction}")
    return "；".join(notes) if notes else None


def _build_requirement_code(institution_code: str | None, major_code: str | None, major_name: str | None) -> str:
    if major_code and major_code not in {"0", "00", "-"}:
        return f"major-{major_code}"
    digest = hashlib.md5(
        f"{institution_code or 'na'}|{major_name or 'na'}".encode("utf-8")
    ).hexdigest()[:12]
    return f"major-name-{digest}"


def load_henan_admission_plan_datasets(
    limit_per_file: int | None = None,
) -> tuple[dict[str, list[dict[str, object]]], dict[str, object]]:
    selected_files, skipped_duplicates = _load_henan_plan_sources()
    institutions: dict[tuple[str, str], dict[str, object]] = {}
    majors: dict[tuple[str, str], dict[str, object]] = {}
    admission_plans: list[dict[str, object]] = []
    source_summary: list[dict[str, object]] = []

    for file_info in selected_files:
        path = Path(file_info["file_path"])
        schema_name: str | None = None
        row_count = 0
        for _, row in iter_sheet_records(path, limit=limit_per_file):
            schema_name = schema_name or _detect_schema(row)
            row_count += 1

            exam_year = _parse_int(row.get("年份"))
            institution_code = _schema_field(row, schema_name, "institution_code")
            institution_name = _normalize_school_name(_schema_field(row, schema_name, "institution_name"))
            raw_major_name = _schema_field(row, schema_name, "major_name")
            major_name, major_notes = _split_major_name_and_notes(raw_major_name)
            major_code = _schema_field(row, schema_name, "major_code")
            batch_code = _normalize_batch(_schema_field(row, schema_name, "batch_code"))
            subject_track = _normalize_subject_track(_schema_field(row, schema_name, "subject_track"))
            study_years = _normalize_optional_text(_schema_field(row, schema_name, "study_years"))
            tuition_yearly = _parse_tuition(_schema_field(row, schema_name, "tuition_yearly"))
            planned_count = _parse_int(_schema_field(row, schema_name, "planned_count"))
            province = "河南"
            institution_province = _institution_province_from_row(schema_name, row)

            if not (exam_year and institution_name and major_name and batch_code and subject_track):
                continue

            institutions[
                (institution_code or "", institution_name)
            ] = _institution_row(institution_code, institution_name, institution_province)
            majors[_major_key(major_code, major_name)] = _major_row(
                major_code,
                major_name,
                study_years,
                _infer_degree_level(batch_code),
            )

            requirement_code = _build_requirement_code(
                institution_code=institution_code,
                major_code=major_code,
                major_name=major_name,
            )
            admission_plans.append(
                {
                    "exam_year": exam_year,
                    "province": province,
                    "exam_type": "gaokao",
                    "subject_track": subject_track,
                    "batch_code": batch_code,
                    "institution_code": institution_code,
                    "institution_name": institution_name,
                    "major_code": major_code,
                    "major_name": major_name,
                    "plan_group_code": None,
                    "plan_group_name": None,
                    "requirement_code": requirement_code,
                    "planned_count": planned_count,
                    "tuition_yearly": tuition_yearly,
                    "study_years": study_years,
                    "campus_city": None,
                    "plan_notes": _build_plan_notes(schema_name, row, major_notes),
                    "source_file": str(path),
                    "source_schema": schema_name,
                }
            )

        source_summary.append(
            {
                "year": file_info["year"],
                "selected_file": str(path),
                "schema": schema_name,
                "normalized_row_count": row_count,
                "skipped_duplicate_files": skipped_duplicates.get(file_info["year"], []),
            }
        )

    datasets = {
        "institutions": list(institutions.values()),
        "majors": list(majors.values()),
        "admission_plans": admission_plans,
    }
    metadata = {
        "selected_files": source_summary,
        "years": [item["year"] for item in source_summary],
        "skipped_duplicates": skipped_duplicates,
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
            upsert_admission_plans,
            upsert_institutions,
            upsert_majors,
        )
        from backend.database import init_db

        init_db()

    datasets, metadata = load_henan_admission_plan_datasets(limit_per_file=args.limit)
    _write_normalized_files(datasets)

    counts = {key: len(rows) for key, rows in datasets.items()}
    summary: dict[str, object] = {
        "scope": "henan_admission_plans",
        "normalized_counts": counts,
        "limit_per_file": args.limit,
        "dry_run": args.dry_run,
        "source_selection": metadata,
    }

    if not args.dry_run:
        import_counts = {
            "institutions": upsert_institutions(datasets["institutions"]),
            "majors": upsert_majors(datasets["majors"]),
            "admission_plans": upsert_admission_plans(datasets["admission_plans"]),
        }
        summary["import_counts"] = import_counts
        summary["schema_overview"] = get_admissions_schema_overview()

    write_json(IMPORTED_DIR / "henan_admission_plans_import_summary.json", summary)

    print("=== HENAN ADMISSION PLANS IMPORT SUMMARY ===")
    for key, count in counts.items():
        print(f"{key}: normalized={count}")
    if not args.dry_run:
        print("=== DATABASE UPSERT COUNTS ===")
        for key, count in summary["import_counts"].items():
            print(f"{key}: upserted={count}")
    else:
        print("Dry run completed. No database rows were written.")


if __name__ == "__main__":
    main()
