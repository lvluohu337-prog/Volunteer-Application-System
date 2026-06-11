from __future__ import annotations

import unittest
from unittest.mock import patch

from backend import planning_repository


class PlanningResultSourceTest(unittest.TestCase):
    def test_build_result_source_marks_real_relaxed_results(self):
        student = {"province": "河南", "final_score": 590, "subject_group": "物理类"}
        bundle = {
            "candidates": [{"institution_name": "湖北大学"}],
            "context": {
                "candidate_strategy": "score_relaxed_real_data",
                "rank_source": "score_relaxed_real_data",
                "latest_year": 2021,
            },
        }

        result = planning_repository._build_result_source(student, bundle, used_real_candidates=True)

        self.assertEqual(result["mode"], "real_relaxed")
        self.assertTrue(result["isRealData"])
        self.assertEqual(result["matchedCandidateCount"], 1)
        self.assertEqual(result["candidateStrategy"], "score_relaxed_real_data")
        self.assertIn("放宽位次硬门槛", result["notice"])

    def test_build_result_source_marks_fallback_reason(self):
        student = {"province": "河南", "final_score": 590, "subject_group": "物理类"}
        bundle = {
            "candidates": [],
            "context": {
                "candidate_strategy": "rank_and_score",
                "rank_source": "missing",
                "latest_year": 2021,
                "track_labels": ["物理类", "理科"],
                "score": 590,
            },
        }

        result = planning_repository._build_result_source(student, bundle, used_real_candidates=False)

        self.assertEqual(result["mode"], "fallback")
        self.assertFalse(result["isRealData"])
        self.assertIn("未命中已入库真实招生候选", result["fallbackReason"])

    @patch.object(planning_repository, "_build_real_rule_summary", return_value={"scoreLevel": "可冲可稳"})
    @patch.object(planning_repository, "_build_structured_recommendations")
    @patch.object(planning_repository, "_build_real_major_cards", return_value=[{"title": "自动化类"}])
    @patch.object(planning_repository, "build_plan_columns_from_candidates")
    @patch.object(planning_repository, "_build_portrait_major_recommendation", return_value={"preferredDirection": "工科"})
    @patch.object(planning_repository, "_get_real_admissions_bundle")
    @patch.object(planning_repository, "fetch_student_or_404")
    def test_get_student_plan_returns_result_source_for_real_results(
        self,
        fetch_student_or_404_mock,
        admissions_bundle_mock,
        portrait_mock,
        plan_columns_mock,
        real_major_cards_mock,
        structured_recommendations_mock,
        real_rule_summary_mock,
    ):
        fetch_student_or_404_mock.return_value = {
            "id": 1,
            "name": "测试学生",
            "province": "河南",
            "exam_year": 2025,
            "subject_group": "历史类",
            "exam_type": "gaokao",
            "status": "draft",
        }
        admissions_bundle_mock.return_value = {
            "candidates": [{"institution_name": "郑州大学"}],
            "context": {
                "candidate_strategy": "rank_and_score",
                "rank_source": "final_rank",
                "latest_year": 2021,
            },
        }
        plan_columns_mock.return_value = (
            [{"title": "冲一冲", "cards": []}],
            {"rush_ratio": 30, "steady_ratio": 40, "safe_ratio": 30},
        )
        structured_recommendations_mock.return_value = {
            "recommendationTable": [{"institutionName": "郑州大学", "majorName": "自动化类"}],
            "firstChoice": {"institutionName": "郑州大学", "majorName": "自动化类"},
            "alternatives": [],
            "notRecommended": [],
        }

        result = planning_repository.get_student_plan(1)

        self.assertIn("resultSource", result)
        self.assertEqual(result["resultSource"]["mode"], "real")
        self.assertTrue(result["resultSource"]["isRealData"])
        self.assertEqual(result["resultSource"]["candidateStrategy"], "rank_and_score")
        self.assertEqual(result["recommendationTable"][0]["institutionName"], "郑州大学")

    @patch.object(planning_repository, "_build_plan_columns")
    @patch.object(planning_repository, "_city_rule_results", return_value=[{"row": {"city_name": "郑州"}}])
    @patch.object(
        planning_repository,
        "_major_rule_results",
        return_value=[
            {
                "row": {"category_name": "计算机类"},
                "score_fit": {"label": "可冲"},
                "subject_fit": {"label": "待复核"},
                "composite_score": 82,
            }
        ],
    )
    @patch.object(planning_repository, "_build_portrait_major_recommendation", return_value={"preferredDirection": "工科"})
    @patch.object(planning_repository, "_get_real_admissions_bundle")
    @patch.object(planning_repository, "fetch_student_or_404")
    def test_get_student_plan_returns_result_source_for_fallback_results(
        self,
        fetch_student_or_404_mock,
        admissions_bundle_mock,
        portrait_mock,
        major_rule_results_mock,
        city_rule_results_mock,
        build_plan_columns_mock,
    ):
        fetch_student_or_404_mock.return_value = {
            "id": 1,
            "name": "测试学生",
            "province": "河南",
            "exam_year": 2025,
            "subject_group": "物理类",
            "exam_type": "gaokao",
            "status": "draft",
        }
        admissions_bundle_mock.return_value = {
            "candidates": [],
            "context": {
                "candidate_strategy": "rank_and_score",
                "rank_source": "missing",
                "latest_year": 2021,
                "track_labels": ["物理类", "理科"],
                "score": 590,
            },
        }
        build_plan_columns_mock.return_value = (
            [{"title": "稳一稳", "cards": []}],
            {"rush_ratio": 20, "steady_ratio": 50, "safe_ratio": 30},
        )

        result = planning_repository.get_student_plan(1)

        self.assertIn("resultSource", result)
        self.assertEqual(result["resultSource"]["mode"], "fallback")
        self.assertFalse(result["resultSource"]["isRealData"])
        self.assertIn("未命中已入库真实招生候选", result["resultSource"]["fallbackReason"])


if __name__ == "__main__":
    unittest.main()
