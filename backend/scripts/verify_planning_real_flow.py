from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from backend.database import db_session
from backend.planning_repository import (
    _get_real_admissions_bundle,
    get_student_analysis,
    get_student_plan,
    get_student_report,
)
from backend.repository import create_student, delete_student
from backend.schemas import StudentPayload


REQUIRED_TABLES = (
    "institutions",
    "majors",
    "admission_plans",
    "major_admission_scores",
    "score_segments",
)


CASES = (
    {
        "label": "history_with_rank",
        "payload": {
            "name": "codex-verify-history-rank",
            "exam_type": "gaokao",
            "province": "\u6cb3\u5357",
            "exam_year": 2025,
            "subject_group": "\u5386\u53f2\u7c7b",
            "final_score": 650,
            "final_rank": 100000,
        },
        "expected_strategy": "rank_and_score",
    },
    {
        "label": "physics_with_rank",
        "payload": {
            "name": "codex-verify-physics-rank",
            "exam_type": "gaokao",
            "province": "\u6cb3\u5357",
            "exam_year": 2025,
            "subject_group": "\u7269\u7406\u7c7b",
            "final_score": 650,
            "final_rank": 5000,
        },
        "expected_strategy": "rank_and_score",
    },
    {
        "label": "physics_score_relaxed",
        "payload": {
            "name": "codex-verify-physics-score-only",
            "exam_type": "gaokao",
            "province": "\u6cb3\u5357",
            "exam_year": 2025,
            "subject_group": "\u7269\u7406\u7c7b",
            "final_score": 590,
        },
        "expected_strategy": "score_relaxed_real_data",
    },
)


def _assert_real_tables_ready() -> dict[str, int]:
    counts: dict[str, int] = {}
    with db_session() as connection:
        for table_name in REQUIRED_TABLES:
            total = connection.execute(f"SELECT COUNT(*) AS total FROM {table_name}").fetchone()["total"]
            counts[table_name] = int(total)
    missing = {table_name: total for table_name, total in counts.items() if total <= 0}
    if missing:
        raise RuntimeError(f"Real admissions tables are not ready: {missing}")
    return counts


def _run_case(case: dict[str, object]) -> dict[str, object]:
    payload = StudentPayload(**case["payload"])
    student = create_student(payload)
    student_id = int(student["id"])
    try:
        bundle = _get_real_admissions_bundle(student)
        plan = get_student_plan(student_id)
        report = get_student_report(student_id)
        analysis = get_student_analysis(student_id)

        candidate_count = len(bundle.get("candidates") or [])
        recommendation_count = len(plan.get("recommendationTable") or [])
        report_recommendation_count = len(report.get("recommendationTable") or [])
        if candidate_count <= 0:
            raise AssertionError(f"{case['label']} did not produce real candidates")
        if "recommendationTable" not in plan or recommendation_count <= 0:
            raise AssertionError(f"{case['label']} plan fell back to non-real-data shape")
        if not plan.get("firstChoice"):
            raise AssertionError(f"{case['label']} plan did not produce firstChoice")
        if "recommendationTable" not in report or report_recommendation_count <= 0:
            raise AssertionError(f"{case['label']} report fell back to non-real-data shape")
        if not report.get("firstChoice"):
            raise AssertionError(f"{case['label']} report did not produce firstChoice")

        context = bundle.get("context") or {}
        expected_strategy = case.get("expected_strategy")
        actual_strategy = context.get("candidate_strategy")
        if expected_strategy and actual_strategy != expected_strategy:
            raise AssertionError(
                f"{case['label']} candidate_strategy mismatch: expected {expected_strategy}, got {actual_strategy}"
            )

        return {
            "label": case["label"],
            "student_id": student_id,
            "candidate_count": candidate_count,
            "recommendation_count": recommendation_count,
            "report_recommendation_count": report_recommendation_count,
            "candidate_strategy": actual_strategy,
            "rank_source": context.get("rank_source"),
            "latest_year": context.get("latest_year"),
            "raw_row_count": context.get("raw_row_count"),
            "first_choice": {
                "institution": (plan.get("firstChoice") or {}).get("institutionName"),
                "major": (plan.get("firstChoice") or {}).get("majorName"),
            },
            "analysis_metrics": [item.get("title") for item in analysis.get("metrics") or []],
        }
    finally:
        delete_student(student_id)


def main() -> None:
    table_counts = _assert_real_tables_ready()
    print("=== REAL TABLE COUNTS ===")
    print(json.dumps(table_counts, ensure_ascii=False, indent=2))

    results = []
    for case in CASES:
        result = _run_case(case)
        results.append(result)
        print(f"=== CASE {case['label']} ===")
        print(json.dumps(result, ensure_ascii=False, indent=2))

    print("=== VERIFICATION PASSED ===")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
