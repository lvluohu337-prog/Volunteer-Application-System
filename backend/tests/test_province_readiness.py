from __future__ import annotations

import unittest
from unittest.mock import patch

from backend.province_readiness import (
    REQUIRED_IMPORTED_SCOPE_SUFFIXES,
    TARGET_PROVINCE_ORDER,
    build_province_readiness_summary,
)


HENAN = TARGET_PROVINCE_ORDER[0]
ZHEJIANG = TARGET_PROVINCE_ORDER[1]


def _empty_by_province() -> dict[str, list[str]]:
    return {province: [] for province in TARGET_PROVINCE_ORDER}


class ProvinceReadinessSummaryTest(unittest.TestCase):
    def setUp(self) -> None:
        henan_scopes = [f"henan_{suffix}" for suffix in REQUIRED_IMPORTED_SCOPE_SUFFIXES]

        imported_scopes = _empty_by_province()
        imported_scopes[HENAN] = henan_scopes

        explicit_scripts = _empty_by_province()
        explicit_scripts[HENAN] = ["import_henan_admission_plans.py"]

        standardized_domains = _empty_by_province()
        standardized_domains[HENAN] = ["admission_plans", "policy_rules"]
        standardized_domains[ZHEJIANG] = ["admission_plans"]

        raw_roots = _empty_by_province()
        raw_roots[ZHEJIANG] = ["zhejiang_raw_admission_plans"]

        self._patches = [
            patch(
                "backend.province_readiness._collect_imported_scopes_by_province",
                return_value=imported_scopes,
            ),
            patch(
                "backend.province_readiness._collect_explicit_import_scripts_by_province",
                return_value=explicit_scripts,
            ),
            patch(
                "backend.province_readiness._collect_standardized_domains_by_province",
                return_value=standardized_domains,
            ),
            patch(
                "backend.province_readiness._collect_raw_roots_by_province",
                return_value=raw_roots,
            ),
        ]
        for patcher in self._patches:
            patcher.start()

    def tearDown(self) -> None:
        for patcher in reversed(self._patches):
            patcher.stop()

    def test_henan_is_currently_the_only_formal_province(self):
        summary = build_province_readiness_summary(as_of_date="2026-06-12")
        provinces = {item["province"]: item for item in summary["provinces"]}

        self.assertEqual(summary["formalProvinces"], [HENAN])
        self.assertEqual(provinces[HENAN]["status"], "formal")
        self.assertTrue(provinces[HENAN]["sameLevelAsHenan"])
        self.assertIn("henan_admission_plans", provinces[HENAN]["importedScopes"])
        self.assertEqual(provinces[HENAN]["missingRequiredImportedScopes"], [])

    def test_zhejiang_is_raw_only_not_formal(self):
        summary = build_province_readiness_summary(as_of_date="2026-06-12")
        provinces = {item["province"]: item for item in summary["provinces"]}
        zhejiang = provinces[ZHEJIANG]

        self.assertEqual(zhejiang["status"], "raw_only")
        self.assertFalse(zhejiang["sameLevelAsHenan"])
        self.assertEqual(zhejiang["importedScopes"], [])
        self.assertEqual(zhejiang["explicitImportScripts"], [])
        self.assertIn("admission_plans", zhejiang["standardizedDomains"])


if __name__ == "__main__":
    unittest.main()
