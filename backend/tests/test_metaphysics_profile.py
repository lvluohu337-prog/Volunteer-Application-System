import unittest
from unittest.mock import patch

from backend.metaphysics_profile import derive_birth_profile_v2


class MetaphysicsAccuracyTest(unittest.TestCase):
    def test_lichun_boundary_uses_previous_year_before_lichun(self) -> None:
        payload = {
            "engineVersion": "bazi_lunar_v1",
            "normalizedBirthDate": "2006-02-03",
            "normalizedBirthTime": "10:00",
            "trueSolarTime": "09:44",
            "pillars": {
                "year": "乙酉",
                "month": "己丑",
                "day": "甲子",
                "hour": "己巳",
            },
            "wuxing": {
                "counts": {"木": 2, "火": 1, "土": 2, "金": 2, "水": 1},
                "dominant": "土",
                "secondary": "木",
            },
            "normalizationNotes": ["year-pillar-before-lichun"],
        }
        with patch("backend.metaphysics_profile.run_bazi_bridge", return_value=payload):
            result = derive_birth_profile_v2("2006-02-03", "10:00")
        self.assertEqual(result["pillars"]["year"], "乙酉")

    def test_late_zi_hour_rolls_to_next_day(self) -> None:
        payload = {
            "engineVersion": "bazi_lunar_v1",
            "normalizedBirthDate": "2006-02-05",
            "normalizedBirthTime": "23:40",
            "trueSolarTime": "23:22",
            "pillars": {
                "year": "丙戌",
                "month": "庚寅",
                "day": "乙丑",
                "hour": "丙子",
            },
            "wuxing": {
                "counts": {"木": 2, "火": 2, "土": 2, "金": 1, "水": 1},
                "dominant": "木",
                "secondary": "火",
            },
            "normalizationNotes": ["late-zi-hour-next-day"],
        }
        with patch("backend.metaphysics_profile.run_bazi_bridge", return_value=payload):
            result = derive_birth_profile_v2("2006-02-04", "23:40")
        self.assertEqual(result["normalizedBirthDate"], "2006-02-05")
        self.assertIn("late-zi-hour-next-day", result["normalizationNotes"])
