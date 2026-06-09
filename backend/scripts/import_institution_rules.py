from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.admissions_repository import get_admissions_schema_overview, upsert_institution_rules
from backend.database import db_session, init_db
from backend.excel_importer import load_workbook, write_csv, write_json
from backend.institution_rule_parser import build_institution_rule_rows


IMPORTED_DIR = PROJECT_ROOT / "data_assets" / "imported" / "henan_institution_rules"
CHARTER_ROOT = PROJECT_ROOT / "data_assets" / "data-needed-standardized" / "06_policy_rules" / "from_province_firstlook"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import Henan institution rules from historical charter workbooks.")
    parser.add_argument("--dry-run", action="store_true", help="Build normalized outputs without writing to the database.")
    return parser.parse_args()


def _locate_charter_workbook() -> Path:
    match = next(CHARTER_ROOT.rglob("*2021*招生简章2.xlsx"), None)
    if not match:
        raise FileNotFoundError("Could not locate Henan 2021 charter workbook.")
    return match


def _institution_name_set() -> set[str]:
    with db_session() as connection:
        rows = connection.execute("SELECT institution_name FROM institutions").fetchall()
    return {str(row["institution_name"]).strip() for row in rows if row.get("institution_name")}


def _write_normalized_files(rows: list[dict[str, object]]) -> None:
    IMPORTED_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(IMPORTED_DIR / "institution_rules.sample.csv", rows[:300])
    write_json(IMPORTED_DIR / "institution_rules.sample.json", rows[:120])


def _delete_existing_source_rows(source_url: str) -> int:
    with db_session() as connection:
        before = connection.execute(
            "SELECT COUNT(*) AS total FROM institution_rules WHERE source_url = ?",
            [source_url],
        ).fetchone()
        connection.execute(
            "DELETE FROM institution_rules WHERE source_url = ?",
            [source_url],
        )
    return int(before["total"]) if before else 0


def main() -> None:
    args = parse_args()
    if not args.dry_run:
        init_db()

    workbook_path = _locate_charter_workbook()
    workbook = load_workbook(workbook_path)
    records = workbook["sheets"][0]["records"]
    rows = build_institution_rule_rows(records, source_path=str(workbook_path))
    _write_normalized_files(rows)

    known_names = _institution_name_set()
    normalized_names = {str(row.get("institution_name") or "").strip() for row in rows}
    matched_names = normalized_names & known_names
    unmatched_names = sorted(name for name in normalized_names if name and name not in known_names)

    summary = {
        "source_workbook": str(workbook_path),
        "normalized_count": len(rows),
        "rule_type_distribution": dict(sorted(Counter(row.get("rule_type") for row in rows).items())),
        "source_exam_year_distribution": dict(sorted(Counter(row.get("source_exam_year") for row in rows).items())),
        "institution_name_coverage": {
            "normalized_institutions": len(normalized_names),
            "matched_institutions": len(matched_names),
            "unmatched_institutions": len(unmatched_names),
        },
        "unmatched_name_samples": unmatched_names[:100],
        "dry_run": args.dry_run,
    }

    if not args.dry_run:
        summary["replaced_rows"] = _delete_existing_source_rows(str(workbook_path))
        summary["import_count"] = upsert_institution_rules(rows)
        summary["schema_overview"] = get_admissions_schema_overview()

    write_json(IMPORTED_DIR / "henan_institution_rules_import_summary.json", summary)

    print("=== HENAN INSTITUTION RULES IMPORT SUMMARY ===")
    print(f"institution_rules: normalized={summary['normalized_count']}")
    if not args.dry_run:
        print(f"institution_rules: upserted={summary['import_count']}")
    else:
        print("Dry run completed. No database rows were written.")


if __name__ == "__main__":
    main()
