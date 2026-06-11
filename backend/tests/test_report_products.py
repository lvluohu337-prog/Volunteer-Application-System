from __future__ import annotations

import unittest

from backend.planning_repository import _build_report_product_catalog
from backend.report_products import (
    DEFAULT_REPORT_PRODUCT_CODE,
    PLANNED_REPORT_PRODUCTS,
    REPORT_PRODUCT_CONFIG,
    get_report_product_label,
    normalize_report_product_code,
)


class ReportProductsDefinitionTest(unittest.TestCase):
    def test_formal_product_definition_is_single_source_and_complete(self):
        self.assertEqual(DEFAULT_REPORT_PRODUCT_CODE, "399")
        self.assertEqual(list(REPORT_PRODUCT_CONFIG.keys()), ["99", "399", "999"])
        self.assertEqual(REPORT_PRODUCT_CONFIG["399"]["label"], "399 元标准版报告")
        self.assertEqual(REPORT_PRODUCT_CONFIG["399"]["delivery_channels"], ["web", "pdf", "word"])

    def test_planned_product_is_not_treated_as_formal_product(self):
        self.assertIn("699", PLANNED_REPORT_PRODUCTS)
        self.assertEqual(normalize_report_product_code("699"), DEFAULT_REPORT_PRODUCT_CODE)
        self.assertEqual(get_report_product_label("699"), "399 元标准版报告")

    def test_report_product_catalog_returns_formal_delivery_channels(self):
        catalog = _build_report_product_catalog("399")
        by_code = {item["code"]: item for item in catalog}

        self.assertEqual(by_code["99"]["deliveryChannels"], ["web", "pdf"])
        self.assertEqual(by_code["399"]["shortLabel"], "399 元标准版")
        self.assertEqual(by_code["999"]["deliveryChannels"], ["web", "pdf", "word"])
        self.assertNotIn("699", by_code)


if __name__ == "__main__":
    unittest.main()
