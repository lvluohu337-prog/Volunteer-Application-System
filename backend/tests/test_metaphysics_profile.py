import unittest
from unittest.mock import patch

from backend.metaphysics_bridge import MetaphysicsBridgeError
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

    def test_jieqi_month_boundary_switches_exact_month_pillar(self) -> None:
        payload = {
            "engineVersion": "bazi_lunar_v1",
            "normalizedBirthDate": "2006-03-06",
            "normalizedBirthTime": "00:30",
            "trueSolarTime": "00:12",
            "pillars": {
                "year": "丙戌",
                "month": "辛卯",
                "day": "丙辰",
                "hour": "戊子",
            },
            "wuxing": {
                "counts": {"木": 2, "火": 2, "土": 2, "金": 1, "水": 1},
                "dominant": "木",
                "secondary": "火",
            },
            "normalizationNotes": ["jieqi-exact-month"],
        }
        with patch("backend.metaphysics_profile.run_bazi_bridge", return_value=payload):
            result = derive_birth_profile_v2("2006-03-06", "00:30")

        self.assertEqual(result["pillars"]["month"], "辛卯")
        self.assertIn("jieqi-exact-month", result["normalizationNotes"])

    def test_missing_birth_time_keeps_hour_pillar_none(self) -> None:
        payload = {
            "engineVersion": "bazi_lunar_v1",
            "normalizedBirthDate": "2006-06-22",
            "normalizedBirthTime": None,
            "trueSolarTime": None,
            "pillars": {
                "year": "丙戌",
                "month": "甲午",
                "day": "辛酉",
                "hour": None,
            },
            "wuxing": {
                "counts": {"木": 1, "火": 2, "土": 1, "金": 3, "水": 1},
                "dominant": "金",
                "secondary": "火",
            },
            "normalizationNotes": [],
        }
        with patch("backend.metaphysics_profile.run_bazi_bridge", return_value=payload):
            result = derive_birth_profile_v2("2006-06-22", None)

        self.assertIsNone(result["birthTime"])
        self.assertIsNone(result["pillars"]["hour"])
        self.assertIsNone(result["normalizedBirthTime"])


class MetaphysicsFailurePolicyTest(unittest.TestCase):
    def test_production_mode_raises_when_bridge_fails(self) -> None:
        with patch("backend.metaphysics_profile.run_bazi_bridge", side_effect=MetaphysicsBridgeError("bridge down")):
            with self.assertRaises(MetaphysicsBridgeError):
                derive_birth_profile_v2("2006-06-22", "08:00", runtime_mode="production")

    def test_explicit_legacy_mode_marks_engine_version(self) -> None:
        with patch("backend.metaphysics_profile.run_bazi_bridge", side_effect=MetaphysicsBridgeError("bridge down")):
            result = derive_birth_profile_v2(
                "2006-06-22",
                "08:00",
                runtime_mode="development",
                fallback_mode="legacy",
            )

        self.assertEqual(result["engineVersion"], "legacy_fallback")
        self.assertIn("bridge down", result["normalizationNotes"][0])
