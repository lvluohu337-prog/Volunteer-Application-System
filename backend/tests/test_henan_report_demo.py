from __future__ import annotations

import unittest

from backend.foundation_repository import generate_demo_report


class HenanReportDemoTest(unittest.TestCase):
    def test_demo_report_99_includes_concrete_volunteer_recommendations(self):
        report = generate_demo_report(1, "99")

        self.assertIn("volunteer_recommendation", report)
        volunteer_recommendation = report["volunteer_recommendation"]

        self.assertEqual(volunteer_recommendation["title"], "具体志愿推荐方案")
        self.assertEqual(len(volunteer_recommendation["rush"]), 3)
        self.assertEqual(len(volunteer_recommendation["steady"]), 3)
        self.assertEqual(len(volunteer_recommendation["safe"]), 3)
        self.assertTrue(volunteer_recommendation["first_choice_advice"])
        self.assertTrue(volunteer_recommendation["final_order_advice"])

        for bucket_key in ("rush", "steady", "safe"):
            for item in volunteer_recommendation[bucket_key]:
                self.assertTrue(item["institution_name"])
                self.assertTrue(item["recommended_major"])
                self.assertTrue(item["recommended_reason"])
                self.assertTrue(item["risk_tip"])
                self.assertTrue(item["match_level"])


if __name__ == "__main__":
    unittest.main()
