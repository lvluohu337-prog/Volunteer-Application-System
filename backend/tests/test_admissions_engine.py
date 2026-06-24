from __future__ import annotations

import unittest
from unittest.mock import patch

from backend.admissions_engine import (
    _build_candidate_match_result,
    _summarize_plan_risk,
    build_plan_columns_from_candidates,
)
from backend.admissions_presenter import _prepare_recommendation_outputs
from backend.admissions_query import _candidate_pair_clause
from backend.admissions_scoring import (
    _evaluate_rank_bucket,
    _evaluate_score_bucket,
    _resolve_candidate_bucket,
)
from backend.admissions_strategy import resolve_strategy_profile


def _candidate(index: int, bucket: str, composite_score: float, risk_level: str = "medium") -> dict:
    return {
        "institution_id": index,
        "major_id": index,
        "institution_name": f"学校{index}",
        "institution_code": f"I{index:03d}",
        "major_name": f"专业{index}",
        "major_code": f"M{index:03d}",
        "plan_group_code": f"G{index:03d}",
        "plan_group_name": f"专业组{index}",
        "exam_year": 2025,
        "batch_code": "本科批",
        "institution_city": "郑州",
        "institution_province": "河南",
        "city_text": "郑州",
        "min_score": 600 - index,
        "min_rank": 12000 + index * 100,
        "plan_count": 12,
        "requirement_text": "不限",
        "bucket": bucket,
        "bucket_meta": {"title": bucket, "tag": bucket, "variant": "primary"},
        "subject_result": {"status": "match", "label": "选科匹配", "note": "选科要求满足。", "score": 92},
        "rank_result": {"bucket": bucket if bucket != "safe" else "steady", "label": "位次匹配", "note": "位次具备一定优势。", "score": 82},
        "score_result": {"bucket": "steady", "label": "分数匹配", "note": "分数具备参考价值。", "score": 78},
        "probability": {"label": "录取概率中高", "note": "近年门槛相对稳定。", "score": 80},
        "plan_risk": {"level": "medium", "label": "计划基本稳定", "note": "计划波动可控。"},
        "risks": [],
        "has_high_risk": False,
        "keyword_hits": [],
        "preference_score": 0,
        "composite_score": composite_score,
        "rank_gap": 1000 + index * 10,
        "score_gap": 8.0 - index * 0.1,
        "risk_level": risk_level,
    }


def _many_candidates(bucket: str, start: int, count: int) -> list[dict]:
    return [
        _candidate(start + index, bucket, 90.0 - index * 0.1, risk_level="low")
        for index in range(count)
    ]


class AdmissionsEngineTest(unittest.TestCase):
    def test_build_candidate_match_result_assigns_risk_level_for_real_candidates(self):
        student = {
            "province": "河南",
            "subject_group": "物理类",
        }
        context = {
            "province": "河南",
            "latest_year": 2025,
            "track_labels": ["物理类"],
            "track_code": "physics",
            "score": 602,
            "rank": 11800,
        }
        row = {
            "institution_id": 1,
            "major_id": 11,
            "institution_name": "测试大学",
            "institution_code": "10001",
            "major_name": "计算机科学与技术",
            "major_code": "080901",
            "institution_city": "郑州",
            "institution_province": "河南",
            "min_score": 590,
            "min_rank": 12600,
            "planned_count": 12,
            "latest_plan_count": 12,
            "batch_code": "本科批",
            "plan_group_code": "101",
            "requirement_text": "物理、化学",
        }

        with (
            patch("backend.admissions_engine._fetch_candidate_rows", return_value=[row]),
            patch("backend.admissions_engine._fetch_history_map", return_value={(1, 11): []}),
            patch("backend.admissions_engine._fetch_explicit_rule_map", return_value={(1, 11): []}),
        ):
            result = _build_candidate_match_result(
                student,
                context,
                lambda requirement, subjects, track: {
                    "status": "match",
                    "score": 86,
                    "label": "选科匹配",
                    "note": "当前选科满足要求。",
                },
                10,
            )

        self.assertEqual(len(result["candidates"]), 1)
        self.assertEqual(result["candidates"][0]["risk_level"], "medium")
        self.assertEqual(len(result["recommendation_table"]), 1)
        self.assertEqual(result["recommendation_table"][0]["riskLevel"], "medium")

    def test_query_module_builds_unique_candidate_pair_clause(self):
        rows = [
            {"institution_id": 1, "major_id": 10},
            {"institution_id": 1, "major_id": 10},
            {"institution_id": 2, "major_id": 20},
            {"institution_id": None, "major_id": 30},
        ]

        clause, values = _candidate_pair_clause(rows, "mas.institution_id", "mas.major_id")

        self.assertEqual(
            clause,
            "(mas.institution_id = ? AND mas.major_id = ?) OR (mas.institution_id = ? AND mas.major_id = ?)",
        )
        self.assertEqual(values, [1, 10, 2, 20])

    def test_scoring_module_resolves_candidate_bucket_from_rank_score_and_probability(self):
        row = {"min_rank": 15000, "min_score": 560}

        rank_result = _evaluate_rank_bucket(9000, row)
        score_result = _evaluate_score_bucket(580, row)
        self.assertEqual(_resolve_candidate_bucket(rank_result, score_result, {"score": 90}), "safe")

        weak_rank_result = _evaluate_rank_bucket(30000, row)
        weak_score_result = _evaluate_score_bucket(540, row)
        self.assertEqual(_resolve_candidate_bucket(weak_rank_result, weak_score_result, {"score": 30}), "out")

    def test_rank_bucket_uses_henan_2026_rank_percentage_bands(self):
        student_rank = 50000

        self.assertEqual(_evaluate_rank_bucket(student_rank, {"min_rank": 45000})["bucket"], "rush")
        self.assertEqual(_evaluate_rank_bucket(student_rank, {"min_rank": 48500})["bucket"], "steady")
        self.assertEqual(_evaluate_rank_bucket(student_rank, {"min_rank": 51500})["bucket"], "steady")
        self.assertEqual(_evaluate_rank_bucket(student_rank, {"min_rank": 55000})["bucket"], "safe")
        self.assertEqual(_evaluate_rank_bucket(student_rank, {"min_rank": 57500})["bucket"], "safe")

    def test_plan_risk_flags_large_rank_volatility(self):
        result = _summarize_plan_risk(
            [
                {"exam_year": 2023, "planned_count": 12, "min_rank": 50000},
                {"exam_year": 2024, "planned_count": 12, "min_rank": 56000},
                {"exam_year": 2025, "planned_count": 12, "min_rank": 43000},
            ]
        )

        self.assertEqual(result["level"], "high")
        self.assertIn("大小年", result["label"])

    def test_prepare_recommendation_outputs_balances_to_henan_2026_48_group_targets(self):
        candidates = (
            _many_candidates("rush", 1, 20)
            + _many_candidates("steady", 101, 30)
            + _many_candidates("safe", 201, 20)
        )

        prepared = _prepare_recommendation_outputs(candidates, {"latest_year": 2025, "score": 580, "rank": 12000})
        bucketed = prepared["bucketed_candidates"]

        self.assertEqual(len(bucketed["rush"]), 14)
        self.assertEqual(len(bucketed["steady"]), 24)
        self.assertEqual(len(bucketed["safe"]), 10)
        self.assertEqual(len(prepared["recommendation_table"]), 48)

    def test_conservative_strategy_exposes_six_tier_targets(self):
        profile = resolve_strategy_profile("conservative")

        self.assertEqual(profile["mode"], "conservative")
        self.assertEqual(profile["bucket_targets"], {"rush": 10, "steady": 16, "safe": 22})
        self.assertEqual(
            {tier["key"]: tier["target"] for tier in profile["tiers"]},
            {
                "risk": 5,
                "sprint": 5,
                "steady": 16,
                "protect": 12,
                "cushion": 5,
                "fallback": 5,
            },
        )

    def test_conservative_strategy_splits_recommendations_into_six_display_tiers(self):
        candidates = (
            _many_candidates("rush", 1, 20)
            + _many_candidates("steady", 101, 30)
            + _many_candidates("safe", 201, 30)
        )

        prepared = _prepare_recommendation_outputs(
            candidates,
            {
                "latest_year": 2025,
                "score": 580,
                "rank": 12000,
                "admissions_strategy_mode": "conservative",
            },
        )
        tiered = prepared["tiered_candidates"]

        self.assertEqual([len(tiered[key]) for key in ("risk", "sprint", "steady", "protect", "cushion", "fallback")], [5, 5, 16, 12, 5, 5])
        self.assertEqual(len(prepared["recommendation_table"]), 48)
        self.assertEqual(prepared["recommendation_table"][0]["displayTier"], "risk")
        self.assertEqual(prepared["recommendation_table"][0]["displayTierLabel"], "险")
        self.assertEqual(prepared["recommendation_table"][-1]["displayTier"], "fallback")

    def test_prepare_recommendation_outputs_dedupes_same_college_major_group(self):
        first = _candidate(1, "steady", 80.0)
        second = _candidate(2, "steady", 92.0)
        second["institution_id"] = first["institution_id"]
        second["plan_group_code"] = first["plan_group_code"]

        prepared = _prepare_recommendation_outputs([first, second], {"latest_year": 2025, "score": 580, "rank": 12000})

        self.assertEqual(len(prepared["recommendation_table"]), 1)
        self.assertEqual(prepared["recommendation_table"][0]["majorName"], second["major_name"])

    def test_prepare_recommendation_outputs_balances_available_candidates_without_overfilling_rush(self):
        candidates = [
            _candidate(1, "rush", 70.0),
            _candidate(2, "steady", 82.0),
            _candidate(3, "steady", 81.0),
            _candidate(4, "steady", 80.0),
            _candidate(5, "steady", 79.0),
            _candidate(6, "steady", 78.0),
            _candidate(7, "steady", 77.0),
            _candidate(8, "steady", 76.0),
            _candidate(9, "steady", 75.0),
            _candidate(10, "safe", 88.0, risk_level="low"),
            _candidate(11, "safe", 87.0, risk_level="low"),
        ]

        prepared = _prepare_recommendation_outputs(candidates, {"latest_year": 2025, "score": 580, "rank": 12000})
        bucketed = prepared["bucketed_candidates"]

        self.assertEqual(len(bucketed["rush"]), 1)
        self.assertEqual(len(bucketed["steady"]), 8)
        self.assertEqual(len(bucketed["safe"]), 2)
        self.assertIsNotNone(prepared["first_choice"])
        self.assertEqual(prepared["first_choice"]["bucket"], "steady")
        self.assertEqual(len(prepared["alternatives"]), 5)

    def test_build_plan_columns_uses_balanced_bucket_counts(self):
        candidates = [
            _candidate(1, "rush", 70.0),
            _candidate(2, "steady", 82.0),
            _candidate(3, "steady", 81.0),
            _candidate(4, "steady", 80.0),
            _candidate(5, "steady", 79.0),
            _candidate(6, "steady", 78.0),
            _candidate(7, "steady", 77.0),
            _candidate(8, "steady", 76.0),
            _candidate(9, "steady", 75.0),
            _candidate(10, "safe", 88.0, risk_level="low"),
            _candidate(11, "safe", 87.0, risk_level="low"),
        ]

        columns, strategy = build_plan_columns_from_candidates(candidates, {"latest_year": 2025, "score": 580, "rank": 12000})

        self.assertEqual([len(column["cards"]) for column in columns], [1, 8, 2])
        self.assertEqual(strategy["rush_ratio"], 29)
        self.assertEqual(strategy["steady_ratio"], 50)
        self.assertEqual(strategy["safe_ratio"], 21)
        self.assertEqual(strategy["total_choice_target"], 48)
        self.assertIn("48 个院校专业组", strategy["note"])

    def test_build_plan_columns_uses_conservative_six_tier_columns_when_requested(self):
        candidates = (
            _many_candidates("rush", 1, 20)
            + _many_candidates("steady", 101, 30)
            + _many_candidates("safe", 201, 30)
        )

        columns, strategy = build_plan_columns_from_candidates(
            candidates,
            {
                "latest_year": 2025,
                "score": 580,
                "rank": 12000,
                "admissions_strategy_mode": "conservative",
            },
        )

        self.assertEqual([column["key"] for column in columns], ["risk", "sprint", "steady", "protect", "cushion", "fallback"])
        self.assertEqual([len(column["cards"]) for column in columns], [5, 5, 16, 12, 5, 5])
        self.assertEqual(strategy["mode"], "conservative")
        self.assertEqual(strategy["display_tier_counts"], {"risk": 5, "sprint": 5, "steady": 16, "protect": 12, "cushion": 5, "fallback": 5})
        self.assertIn("险5 / 冲5 / 稳16 / 保12 / 垫5 / 兜5", strategy["note"])


if __name__ == "__main__":
    unittest.main()
