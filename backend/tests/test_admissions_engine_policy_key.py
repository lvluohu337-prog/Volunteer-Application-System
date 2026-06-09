from __future__ import annotations

import unittest

from backend.admissions_engine import _normalize_explicit_rule_v2


class AdmissionsEnginePolicyKeyTest(unittest.TestCase):
    def test_normalize_explicit_rule_keeps_policy_key(self) -> None:
        rule = {
            "risk_type": "special_plan_eligibility",
            "risk_level": "high",
            "risk_message": "需要专项资格审核。",
            "raw_json": '{"policy_key":"henan_2025_special_plan","display_label":"专项计划资格审核"}',
        }
        normalized = _normalize_explicit_rule_v2(rule)
        self.assertEqual(normalized["policy_key"], "henan_2025_special_plan")

    def test_normalize_explicit_rule_keeps_policy_topic(self) -> None:
        rule = {
            "rule_type": "physical_requirement",
            "rule_title": "体检与身体条件限制",
            "rule_content": "录取体检标准按有关规定执行。",
            "raw_json": '{"policy_key":"henan_2026_general_regulation","policy_topic":"physical_requirement"}',
        }
        normalized = _normalize_explicit_rule_v2(rule)
        self.assertEqual(normalized["policy_key"], "henan_2026_general_regulation")
        self.assertEqual(normalized["policy_topic"], "physical_requirement")


if __name__ == "__main__":
    unittest.main()
