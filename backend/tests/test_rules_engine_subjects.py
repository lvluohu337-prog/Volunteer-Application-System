from __future__ import annotations

import unittest

from backend.rules_engine import infer_student_subjects


class RulesEngineSubjectsTest(unittest.TestCase):
    def test_infer_subjects_from_shorthand_group(self) -> None:
        student = {"subject_group": "物化生"}
        subjects = infer_student_subjects(student)
        self.assertIn("物理", subjects)
        self.assertIn("化学", subjects)
        self.assertIn("生物", subjects)

    def test_infer_subjects_from_history_group(self) -> None:
        student = {"subject_group": "史政地"}
        subjects = infer_student_subjects(student)
        self.assertIn("历史", subjects)
        self.assertIn("思想政治", subjects)
        self.assertIn("地理", subjects)


if __name__ == "__main__":
    unittest.main()
