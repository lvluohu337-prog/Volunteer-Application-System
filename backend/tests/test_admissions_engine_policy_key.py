from __future__ import annotations

import unittest

from backend.admissions_engine import _normalize_explicit_rule_v2
from backend.admissions_risk import _collect_risks, _explicit_rule_applies


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

    def test_risk_module_applies_json_trigger_conditions(self) -> None:
        rule = {
            "trigger_condition": '{"match_all":[{"field":"plan_notes","contains_any":["专项"]}]}',
        }
        self.assertTrue(_explicit_rule_applies(rule, {"plan_notes": "地方专项计划"}))
        self.assertFalse(_explicit_rule_applies(rule, {"plan_notes": "普通类专业"}))

    def test_risk_module_collects_heuristic_and_explicit_risks(self) -> None:
        row = {
            "batch_code": "本科批",
            "plan_notes": "只招英语语种考生；详见院校招生章程",
            "public_private": "",
        }
        explicit_rules = [
            {
                "risk_type": "special_plan_eligibility",
                "risk_level": "high",
                "risk_message": "需要专项资格审核。",
                "raw_json": '{"policy_key":"henan_2025_special_plan"}',
            }
        ]
        risks = _collect_risks(row, explicit_rules)
        risk_types = {item["type"] for item in risks}
        self.assertIn("special_plan_eligibility", risk_types)
        self.assertIn("language", risk_types)
        self.assertIn("charter", risk_types)


if __name__ == "__main__":
    unittest.main()
