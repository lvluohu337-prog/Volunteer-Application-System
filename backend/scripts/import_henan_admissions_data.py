from __future__ import annotations

import argparse
from pathlib import Path

from backend.admissions_importer import build_henan_dataset_overview, load_henan_normalized_datasets
from backend.admissions_repository import (
    get_admissions_schema_overview,
    upsert_admission_plans,
    upsert_institution_admission_scores,
    upsert_institutions,
    upsert_majors,
    upsert_major_admission_scores,
    upsert_score_segments,
    upsert_subject_requirements,
)
from backend.database import init_db
from backend.excel_importer import write_csv, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[2]
IMPORTED_DIR = PROJECT_ROOT / "data_assets" / "imported" / "henan_admissions"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import Henan admissions data into the planning database.")
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N rows from each source workbook.")
    parser.add_argument("--dry-run", action="store_true", help="Only build normalized outputs and summaries without writing to the database.")
    return parser.parse_args()


def _write_normalized_files(datasets: dict[str, list[dict[str, object]]]) -> None:
    IMPORTED_DIR.mkdir(parents=True, exist_ok=True)
    for key, rows in datasets.items():
        sample_rows = rows[:200]
        write_json(IMPORTED_DIR / f"{key}.sample.json", sample_rows)
        write_csv(IMPORTED_DIR / f"{key}.sample.csv", sample_rows)


def main() -> None:
    args = parse_args()
    if not args.dry_run:
        init_db()

    overview = build_henan_dataset_overview()
    datasets = load_henan_normalized_datasets(limit_per_file=args.limit)
    _write_normalized_files(datasets)

    counts = {key: len(rows) for key, rows in datasets.items()}
    summary = {
        "overview": overview,
        "normalized_counts": counts,
        "limit_per_file": args.limit,
        "dry_run": args.dry_run,
    }

    if not args.dry_run:
        import_counts = {
            "institutions": upsert_institutions(datasets["institutions"]),
            "majors": upsert_majors(datasets["majors"]),
            "subject_requirements": upsert_subject_requirements(datasets["subject_requirements"]),
            "admission_plans": upsert_admission_plans(datasets["admission_plans"]),
            "institution_admission_scores": upsert_institution_admission_scores(datasets["institution_admission_scores"]),
            "major_admission_scores": upsert_major_admission_scores(datasets["major_admission_scores"]),
            "score_segments": upsert_score_segments(datasets["score_segments"]),
        }
        summary["import_counts"] = import_counts
        summary["schema_overview"] = get_admissions_schema_overview()

    write_json(IMPORTED_DIR / "henan_admissions_import_summary.json", summary)

    print("=== HENAN ADMISSIONS IMPORT SUMMARY ===")
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
