from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from backend.admissions_repository import (
    get_admissions_schema_overview,
    upsert_admission_risk_rules,
    upsert_institution_rules,
    upsert_policy_trends,
)
from backend.database import db_session, init_db
from backend.excel_importer import write_csv, write_json
from backend.policy_importer import load_henan_policy_rule_datasets


PROJECT_ROOT = Path(__file__).resolve().parents[2]
IMPORTED_DIR = PROJECT_ROOT / "data_assets" / "imported" / "henan_policy_rules"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import Henan policy and charter rules into the planning database.")
    parser.add_argument("--limit-docs", type=int, default=None, help="Only process the first N policy documents.")
    parser.add_argument("--dry-run", action="store_true", help="Build normalized outputs without writing to the database.")
    return parser.parse_args()


def _write_normalized_files(datasets: dict[str, list[dict[str, object]]]) -> None:
    IMPORTED_DIR.mkdir(parents=True, exist_ok=True)
    for key, rows in datasets.items():
        sample_rows = rows[:300]
        write_json(IMPORTED_DIR / f"{key}.sample.json", sample_rows)
        write_csv(IMPORTED_DIR / f"{key}.sample.csv", sample_rows)


def _replace_existing_policy_trends(policy_rows: list[dict[str, object]]) -> int:
    policy_keys = sorted({str(row.get("policy_key") or "").strip() for row in policy_rows if str(row.get("policy_key") or "").strip()})
    if not policy_keys:
        return 0

    placeholders = ", ".join(["?"] * len(policy_keys))
    with db_session() as connection:
        before = connection.execute(
            f"SELECT COUNT(*) AS total FROM policy_trends WHERE policy_key IN ({placeholders})",
            policy_keys,
        ).fetchone()
        connection.execute(
            f"DELETE FROM policy_trends WHERE policy_key IN ({placeholders})",
            policy_keys,
        )
    return int(before["total"]) if before else 0


def _replace_existing_admission_risk_rules(risk_rows: list[dict[str, object]]) -> int:
    policy_keys = sorted({str(row.get("policy_key") or "").strip() for row in risk_rows if str(row.get("policy_key") or "").strip()})
    if not policy_keys:
        return 0

    deleted_total = 0
    with db_session() as connection:
        for policy_key in policy_keys:
            like_pattern = f'%\"policy_key\":\"{policy_key}\"%'
            before = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM admission_risk_rules
                WHERE raw_json LIKE ?
                """,
                [like_pattern],
            ).fetchone()
            connection.execute(
                """
                DELETE FROM admission_risk_rules
                WHERE raw_json LIKE ?
                """,
                [like_pattern],
            )
            deleted_total += int(before["total"]) if before else 0
    return deleted_total


def main() -> None:
    args = parse_args()
    if not args.dry_run:
        init_db()

    datasets = load_henan_policy_rule_datasets(limit_documents=args.limit_docs)
    _write_normalized_files(datasets)

    counts = {key: len(rows) for key, rows in datasets.items()}
    summary = {
        "normalized_counts": counts,
        "limit_documents": args.limit_docs,
        "dry_run": args.dry_run,
    }

    if not args.dry_run:
        summary["replaced_rows"] = {
            "policy_trends": _replace_existing_policy_trends(datasets["policy_trends"]),
            "admission_risk_rules": _replace_existing_admission_risk_rules(datasets["admission_risk_rules"]),
        }
        import_counts = {
            "policy_trends": upsert_policy_trends(datasets["policy_trends"]),
            "admission_risk_rules": upsert_admission_risk_rules(datasets["admission_risk_rules"]),
            "institution_rules": upsert_institution_rules(datasets["institution_rules"]),
        }
        summary["import_counts"] = import_counts
        summary["schema_overview"] = get_admissions_schema_overview()

    write_json(IMPORTED_DIR / "henan_policy_rules_import_summary.json", summary)

    print("=== HENAN POLICY RULE IMPORT SUMMARY ===")
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
