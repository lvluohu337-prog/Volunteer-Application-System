import unittest

from backend.metaphysics_mapping import map_bridge_payload_to_profile


class IntakeInferenceCompatibilityTest(unittest.TestCase):
    def test_map_bridge_payload_preserves_existing_profile_shape(self) -> None:
        payload = {
            "engineVersion": "bazi_lunar_v1",
            "normalizedBirthDate": "2006-06-22",
            "normalizedBirthTime": "08:00",
            "trueSolarTime": "07:43",
            "pillars": {
                "year": "year-pillar",
                "month": "month-pillar",
                "day": "day-pillar",
                "hour": "hour-pillar",
            },
            "wuxing": {
                "counts": {"wood": 1, "fire": 2, "earth": 1, "metal": 3, "water": 1},
                "dominant": "metal",
                "secondary": "fire",
            },
            "normalizationNotes": ["true-solar-time:-17"],
        }

        result = map_bridge_payload_to_profile(
            birthday="2006-06-22",
            birth_time="08:00",
            bridge_payload=payload,
        )

        self.assertEqual(result["birthday"], "2006-06-22")
        self.assertEqual(result["birthTime"], "08:00")
        self.assertEqual(result["pillars"]["hour"], "hour-pillar")
        self.assertIn("personalityTraits", result["profile"])
        self.assertIn("autofill", result)
        self.assertEqual(result["engineVersion"], "bazi_lunar_v1")
        self.assertEqual(result["normalizedBirthTime"], "08:00")

    def test_map_bridge_payload_derives_wuxing_defaults_when_missing(self) -> None:
        payload = {
            "engineVersion": "bazi_lunar_v1",
            "normalizedBirthDate": "2006-06-22",
            "normalizedBirthTime": "08:00",
            "trueSolarTime": "07:43",
            "pillars": {
                "year": "甲子",
                "month": "乙丑",
                "day": "丙寅",
                "hour": "丁卯",
            },
            "normalizationNotes": ["true-solar-time:-17"],
        }

        result = map_bridge_payload_to_profile(
            birthday="2006-06-22",
            birth_time="08:00",
            bridge_payload=payload,
        )

        self.assertGreater(sum(result["wuxing"]["counts"].values()), 0)
        self.assertTrue(result["wuxing"]["dominant"])
        self.assertTrue(result["wuxing"]["secondary"])
