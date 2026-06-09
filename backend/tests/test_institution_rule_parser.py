from __future__ import annotations

import unittest

from backend.institution_rule_parser import build_institution_rule_rows


class InstitutionRuleParserTest(unittest.TestCase):
    def test_prefers_embedded_2021_year_over_school_code_prefix(self) -> None:
        rows = build_institution_rule_rows(
            [
                {
                    "简章名称": "广州番禺职业技术学院",
                    "时间": "12046-广州番禺职业技术学院-2021年夏季高考招生章程",
                    "内容_2": "公共外语教学为英语。录取体检标准按照体检工作指导意见执行。",
                }
            ],
            source_path="charter.xlsx",
        )
        self.assertEqual(rows[0]["exam_year"], None)
        self.assertEqual(rows[0]["source_exam_year"], 2021)

    def test_normalizes_20201_typo_to_2021(self) -> None:
        rows = build_institution_rule_rows(
            [
                {
                    "简章名称": "广西工程职业学院",
                    "时间": "广西工程职业学院20201年招生章程",
                    "内容_2": "考生不服从专业调剂的，予以退档。",
                }
            ],
            source_path="charter.xlsx",
        )
        self.assertEqual(rows[0]["source_exam_year"], 2021)

    def test_maps_general_rule_topics_to_general_regulation_policy(self) -> None:
        rows = build_institution_rule_rows(
            [
                {
                    "绠€绔犲悕绉?": "测试院校",
                    "鏃堕棿": "测试院校2021年招生章程",
                    "鍐呭_2": "录取体检标准按照有关规定执行。考生不服从专业调剂的，予以退档。中外合作办学专业学费较高。",
                }
            ],
            source_path="charter.xlsx",
        )
        by_type = {row["rule_type"]: row for row in rows}
        self.assertEqual(by_type["physical_requirement"]["policy_key"], "henan_2026_general_regulation")
        self.assertEqual(by_type["physical_requirement"]["policy_topic"], "physical_requirement")
        self.assertEqual(by_type["adjustment_policy"]["policy_key"], "henan_2026_general_regulation")
        self.assertEqual(by_type["adjustment_policy"]["policy_topic"], "adjustment_policy")
        self.assertEqual(by_type["cooperative_education"]["policy_key"], "henan_2026_general_regulation")
        self.assertEqual(by_type["cooperative_education"]["policy_topic"], "cooperative_education")

    def test_maps_special_plan_rules_to_specific_policy_key(self) -> None:
        rows = build_institution_rule_rows(
            [
                {
                    "绠€绔犲悕绉?": "测试院校",
                    "鏃堕棿": "测试院校2021年招生章程",
                    "鍐呭_2": "国家专项计划考生须完成资格审核，未通过资格审核者不予录取。",
                }
            ],
            source_path="charter.xlsx",
        )
        special_rows = [row for row in rows if row["rule_type"] == "special_program"]
        self.assertEqual(len(special_rows), 1)
        self.assertEqual(special_rows[0]["policy_key"], "henan_2025_special_plan")
        self.assertEqual(special_rows[0]["policy_topic"], "special_plan")


if __name__ == "__main__":
    unittest.main()
