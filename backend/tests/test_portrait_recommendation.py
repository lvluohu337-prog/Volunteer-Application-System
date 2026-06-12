from __future__ import annotations

import unittest

from backend.compliance import PORTRAIT_DISCLAIMER
from backend.intake_inference import derive_birth_profile
from backend.planning_repository import _build_derived_profile_summary, _build_portrait_major_recommendation


class PortraitRecommendationTest(unittest.TestCase):
    def test_derived_profile_summary_keeps_personality_and_interest_fields(self):
        student = {
            "derived_profile": derive_birth_profile("2008-05-13", "23:30"),
            "bazi_year_pillar": None,
            "bazi_month_pillar": None,
            "bazi_day_pillar": None,
            "bazi_hour_pillar": None,
        }

        summary = _build_derived_profile_summary(student)

        self.assertEqual(summary["constellation"], "金牛座")
        self.assertTrue(summary["personalityTraits"])
        self.assertTrue(summary["interestDirections"])
        self.assertTrue(summary["developmentGoals"])
        self.assertTrue(summary["learningStyle"])

    def test_portrait_recommendation_returns_primary_direction_and_boundary_note(self):
        student = {
            "subject_group": "物理类",
            "target_direction": "计算机",
            "interest_preferences": "计算机、数据方向",
            "family_preferences": "好就业",
            "parent_focus": "考研",
            "development_goal": "技术研发",
            "derived_profile": derive_birth_profile("2008-05-13", "23:30"),
        }
        bundle = {
            "candidates": [
                {"major_name": "计算机类"},
                {"major_name": "计算机科学与技术"},
                {"major_name": "电子信息类"},
            ]
        }

        result = _build_portrait_major_recommendation(student, bundle)

        self.assertEqual(result["preferredDirection"], "计算机类")
        self.assertIn("计算机类", result["recommendedMajorDirections"])
        self.assertTrue(result["majorFitReasons"])
        self.assertEqual(result["disclaimer"], PORTRAIT_DISCLAIMER)
        self.assertTrue(result["hardEvidence"])

    def test_portrait_recommendation_prompts_for_more_profile_when_missing(self):
        student = {
            "subject_group": "物理类",
            "derived_profile": derive_birth_profile(None, None),
        }

        result = _build_portrait_major_recommendation(student)

        self.assertFalse(result["hasPortraitData"])
        self.assertEqual(result["preferredDirection"], "待补充画像信息")
        self.assertEqual(result["recommendedMajorDirections"], [])


if __name__ == "__main__":
    unittest.main()
