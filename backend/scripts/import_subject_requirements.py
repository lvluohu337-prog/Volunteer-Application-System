from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.admissions_importer import load_henan_normalized_datasets
from backend.admissions_repository import (
    get_admissions_schema_overview,
    upsert_institutions,
    upsert_majors,
    upsert_subject_requirements,
)
from backend.database import init_db
from backend.excel_importer import write_csv, write_json
from backend.subject_requirement_parser import parse_subject_requirement


IMPORTED_DIR = PROJECT_ROOT / "data_assets" / "imported" / "henan_subject_requirements"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import Henan subject requirements into the planning database.")
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N rows from each source workbook.")
    parser.add_argument("--dry-run", action="store_true", help="Build normalized outputs without writing to the database.")
    return parser.parse_args()


def _build_rows(limit: int | None = None) -> dict[str, list[dict[str, object]]]:
    datasets = load_henan_normalized_datasets(limit_per_file=limit)
    rows: list[dict[str, object]] = []
    for item in datasets["subject_requirements"]:
        parsed = parse_subject_requirement(str(item.get("requirement_text") or ""))
        rows.append(
            {
                **item,
                **parsed,
            }
        )
    return {
        "institutions": datasets["institutions"],
        "majors": datasets["majors"],
        "subject_requirements": rows,
    }


def _write_normalized_files(rows: list[dict[str, object]]) -> None:
    IMPORTED_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(IMPORTED_DIR / "subject_requirements.sample.csv", rows[:300])
    write_json(IMPORTED_DIR / "subject_requirements.sample.json", rows[:100])


def main() -> None:
    args = parse_args()
    if not args.dry_run:
        init_db()

    datasets = _build_rows(limit=args.limit)
    rows = datasets["subject_requirements"]
    _write_normalized_files(rows)

    summary = {
        "normalized_counts": {
            "institutions": len(datasets["institutions"]),
            "majors": len(datasets["majors"]),
            "subject_requirements": len(rows),
        },
        "year_distribution": dict(sorted(Counter(row.get("exam_year") for row in rows).items())),
        "match_mode_distribution": dict(sorted(Counter(row.get("match_mode") for row in rows).items())),
        "limit": args.limit,
        "dry_run": args.dry_run,
    }

    if not args.dry_run:
        summary["import_counts"] = {
            "institutions": upsert_institutions(datasets["institutions"]),
            "majors": upsert_majors(datasets["majors"]),
            "subject_requirements": upsert_subject_requirements(rows),
        }
        summary["schema_overview"] = get_admissions_schema_overview()

    write_json(IMPORTED_DIR / "henan_subject_requirements_import_summary.json", summary)

    print("=== HENAN SUBJECT REQUIREMENTS IMPORT SUMMARY ===")
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
