from __future__ import annotations

import unittest

from backend.province_readiness import build_province_readiness_summary


class ProvinceReadinessSummaryTest(unittest.TestCase):
    def test_henan_is_currently_the_only_formal_province(self):
        summary = build_province_readiness_summary(as_of_date="2026-06-12")
        provinces = {item["province"]: item for item in summary["provinces"]}

        self.assertEqual(summary["formalProvinces"], ["河南"])
        self.assertEqual(provinces["河南"]["status"], "formal")
        self.assertTrue(provinces["河南"]["sameLevelAsHenan"])
        self.assertIn("henan_admission_plans", provinces["河南"]["importedScopes"])
        self.assertEqual(provinces["河南"]["missingRequiredImportedScopes"], [])

    def test_zhejiang_is_raw_only_not_formal(self):
        summary = build_province_readiness_summary(as_of_date="2026-06-12")
        provinces = {item["province"]: item for item in summary["provinces"]}
        zhejiang = provinces["浙江"]

        self.assertEqual(zhejiang["status"], "raw_only")
        self.assertFalse(zhejiang["sameLevelAsHenan"])
        self.assertEqual(zhejiang["importedScopes"], [])
        self.assertEqual(zhejiang["explicitImportScripts"], [])
        self.assertIn("admission_plans", zhejiang["standardizedDomains"])


if __name__ == "__main__":
    unittest.main()
