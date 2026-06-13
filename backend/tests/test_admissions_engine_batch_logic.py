from __future__ import annotations

import unittest
from unittest.mock import patch

from backend.admissions_engine import (
    _batch_matches_declared_batch,
    _batch_sql_condition,
    _pick_effective_batch_codes,
    build_admissions_context,
)


class AdmissionsEngineBatchLogicTest(unittest.TestCase):
    def test_undergraduate_declared_batch_matches_only_regular_undergraduate_batches(self) -> None:
        self.assertTrue(_batch_matches_declared_batch("本科批", "本科一批"))
        self.assertTrue(_batch_matches_declared_batch("本科批", "本科二批"))
        self.assertFalse(_batch_matches_declared_batch("本科批", "专项计划本科批"))
        self.assertFalse(_batch_matches_declared_batch("本科批", "体育类本科"))
        self.assertFalse(_batch_matches_declared_batch("本科批", "专科批"))

    def test_pick_effective_batch_codes_uses_batch_lines_to_refine_undergraduate_scope(self) -> None:
        rows = [
            {"batch_code": "本科一批", "score_line": 509},
            {"batch_code": "本科二批", "score_line": 405},
            {"batch_code": "专科批", "score_line": 190},
        ]

        codes, met = _pick_effective_batch_codes("本科批", 500, rows)
        self.assertEqual(codes, ["本科二批"])
        self.assertTrue(met)

        codes, met = _pick_effective_batch_codes("本科批", 560, rows)
        self.assertEqual(codes, ["本科一批", "本科二批"])
        self.assertTrue(met)

    def test_pick_effective_batch_codes_marks_below_line_as_unmet(self) -> None:
        rows = [
            {"batch_code": "本科二批", "score_line": 405},
            {"batch_code": "专科批", "score_line": 190},
        ]

        codes, met = _pick_effective_batch_codes("本科批", 390, rows)
        self.assertEqual(codes, [])
        self.assertFalse(met)

    def test_batch_sql_condition_uses_exact_codes_when_batch_lines_are_available(self) -> None:
        clause, params = _batch_sql_condition(
            {
                "declared_batch": "本科批",
                "effective_batch_codes": ["本科一批", "本科二批"],
                "batch_requirement_met": True,
            }
        )

        self.assertEqual(clause, "mas.batch_code IN (%s, %s)".replace("%s", "?"))
        self.assertEqual(params, ["本科一批", "本科二批"])

    def test_batch_sql_condition_blocks_regular_batch_when_score_is_below_line(self) -> None:
        clause, params = _batch_sql_condition(
            {
                "declared_batch": "本科批",
                "effective_batch_codes": [],
                "batch_requirement_met": False,
            }
        )

        self.assertEqual(clause, "1 = 0")
        self.assertEqual(params, [])

    def test_build_admissions_context_includes_effective_batch_codes(self) -> None:
        student = {
            "province": "河南",
            "subject_group": "物理类",
            "admission_batch": "本科批",
            "final_score": 500,
            "final_rank": 120000,
        }
        province_batch_rows = [
            {"batch_code": "本科一批", "score_line": 509},
            {"batch_code": "本科二批", "score_line": 405},
            {"batch_code": "专科批", "score_line": 190},
        ]

        with patch("backend.admissions_engine._latest_admission_year", return_value=2023), patch(
            "backend.admissions_engine._fetch_latest_province_batch_rows",
            return_value=(province_batch_rows, 2022),
        ):
            context = build_admissions_context(student)

        self.assertEqual(context["declared_batch"], "本科批")
        self.assertEqual(context["effective_batch_codes"], ["本科二批"])
        self.assertTrue(context["batch_requirement_met"])
        self.assertEqual(context["province_batch_reference_year"], 2022)


if __name__ == "__main__":
    unittest.main()
