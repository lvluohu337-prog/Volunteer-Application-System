from __future__ import annotations

import unittest

from backend.policy_importer import load_henan_policy_rule_datasets


class PolicyImporterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.datasets = load_henan_policy_rule_datasets()
        cls.risk_rows = cls.datasets["admission_risk_rules"]
        cls.policy_rows = cls.datasets["policy_trends"]

    def test_expanded_policy_import_builds_more_than_original_14_risk_rules(self):
        self.assertGreaterEqual(len(self.risk_rows), 22)
        self.assertGreaterEqual(len(self.policy_rows), 12)

    def test_new_single_exam_and_counterpart_risk_types_are_present(self):
        risk_types = {str(row.get("risk_type") or "") for row in self.risk_rows}

        self.assertIn("single_exam_one_choice", risk_types)
        self.assertIn("single_exam_skill_test", risk_types)
        self.assertIn("counterpart_eligibility", risk_types)
        self.assertIn("counterpart_major_alignment", risk_types)
        self.assertIn("counterpart_arts_exam", risk_types)

    def test_risk_messages_use_clean_default_copy_instead_of_noisy_raw_excerpt(self):
        rows_by_type = {str(row.get("risk_type") or ""): row for row in self.risk_rows}

        charter_review = rows_by_type["charter_review"]
        self.assertIn("高校可在通用体检要求基础上提出补充身体条件要求", str(charter_review.get("risk_message") or ""))
        self.assertNotIn("的说明和解释", str(charter_review.get("risk_message") or ""))

        single_exam = rows_by_type["single_exam_skill_test"]
        self.assertIn("职业技能测试", str(single_exam.get("risk_message") or ""))
        self.assertTrue(single_exam.get("source_excerpt"))


if __name__ == "__main__":
    unittest.main()
