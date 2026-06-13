from __future__ import annotations

import unittest

from backend.main import get_intake_template
from backend.province_support import (
    FORMAL_SUPPORTED_PROVINCES,
    build_province_support_options,
    build_province_support_summary,
    is_formally_supported_province,
)


class ProvinceSupportDefinitionTest(unittest.TestCase):
    def test_formal_supported_provinces_is_currently_henan_only(self):
        self.assertEqual(list(FORMAL_SUPPORTED_PROVINCES), ["河南"])
        self.assertTrue(is_formally_supported_province("河南"))
        self.assertFalse(is_formally_supported_province("浙江"))

    def test_province_support_summary_marks_pending_provinces_disabled(self):
        summary = build_province_support_summary()
        options_by_value = {item["value"]: item for item in build_province_support_options()}

        self.assertEqual(summary["formalSupportedLabel"], "河南")
        self.assertIn("浙江", summary["pendingProvinces"])
        self.assertFalse(options_by_value["河南"]["disabled"])
        self.assertTrue(options_by_value["浙江"]["disabled"])
        self.assertEqual(options_by_value["浙江"]["status"], "raw_only")

    def test_intake_template_only_exposes_formal_supported_provinces(self):
        response = get_intake_template()
        data = response["data"]

        self.assertEqual(data["provinces"], ["河南"])
        self.assertEqual(data["province_support"]["formalSupportedProvinces"], ["河南"])
        self.assertIn("浙江", data["province_support"]["pendingProvinces"])


if __name__ == "__main__":
    unittest.main()
