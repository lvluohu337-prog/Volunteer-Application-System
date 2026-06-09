from __future__ import annotations

import unittest

from backend.planning_repository import _build_formal_report_json, _build_structured_recommendations


class PlanningRepositoryStructuredReportTest(unittest.TestCase):
    def test_build_structured_recommendations_adds_adjustment_and_risk_fields(self):
        student = {
            "accept_adjustment": "reject",
        }
        recommendation = {
            "bucket": "steady",
            "institutionName": "郑州大学",
            "majorName": "自动化类",
            "planGroupCode": "（104）",
            "batchCode": "本科批",
            "cityText": "郑州",
            "riskLevel": "review",
            "riskNotes": ["计划波动待补充"],
            "recommendationReason": "当前位次具备参考优势。",
        }
        bundle = {
            "recommendation_table": [recommendation],
            "first_choice": recommendation,
            "alternatives": [recommendation],
            "not_recommended": [{"institutionName": "某大学", "majorName": "某专业"}],
        }

        result = _build_structured_recommendations(student, bundle)

        self.assertEqual(len(result["recommendationTable"]), 1)
        self.assertEqual(result["firstChoice"]["adjustmentAdvice"]["label"], "不接受调剂")
        self.assertIn("当前明确不接受调剂", result["firstChoice"]["adjustmentAdvice"]["detail"])
        self.assertEqual(result["firstChoice"]["riskSummary"], "计划波动待补充")
        self.assertEqual(len(result["alternatives"]), 1)
        self.assertEqual(len(result["notRecommended"]), 1)

    def test_build_formal_report_json_contains_structured_recommendation_fields(self):
        structured_recommendations = {
            "recommendationTable": [
                {
                    "institutionName": "郑州大学",
                    "majorName": "自动化类",
                    "recommendationReason": "适合作为主力志愿。",
                    "riskSummary": "计划波动待补充",
                    "adjustmentAdvice": {"label": "不接受调剂", "detail": "正式填报前需确认边界。"},
                }
            ],
            "firstChoice": {
                "institutionName": "郑州大学",
                "majorName": "自动化类",
                "recommendationReason": "适合作为第一志愿。",
            },
            "alternatives": [{"institutionName": "武汉理工大学", "majorName": "化工与制药类"}],
            "notRecommended": [{"institutionName": "某大学", "majorName": "某专业"}],
        }

        report_json = _build_formal_report_json(
            student={"name": "胡祥荟", "province": "河南", "exam_year": 2026, "subject_group": "物理类", "status": "draft"},
            product_code="399",
            sections=[{"title": "学生基本信息", "body": "示例"}],
            rule_summary={"scoreLevel": "可冲可稳", "topRisks": ["计划波动待补充"]},
            derived_profile={"constellation": "金牛座", "pillars": {}, "interestDirections": [], "regionPreferences": [], "developmentGoals": []},
            matched_majors=["自动化类"],
            matched_cities=["郑州"],
            portrait_recommendation={"preferredDirection": "工科"},
            structured_recommendations=structured_recommendations,
        )

        self.assertIn("recommendationTable", report_json)
        self.assertIn("firstChoice", report_json)
        self.assertIn("alternatives", report_json)
        self.assertIn("notRecommended", report_json)
        self.assertEqual(report_json["firstChoice"]["institutionName"], "郑州大学")
        self.assertEqual(report_json["recommendationTable"][0]["majorName"], "自动化类")


if __name__ == "__main__":
    unittest.main()
