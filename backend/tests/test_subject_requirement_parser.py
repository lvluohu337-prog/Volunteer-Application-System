from __future__ import annotations

import unittest

from backend.subject_requirement_parser import parse_subject_requirement


class SubjectRequirementParserTest(unittest.TestCase):
    def test_unrestricted_requirement(self) -> None:
        result = parse_subject_requirement("不限")
        self.assertEqual(result["match_mode"], "unrestricted")
        self.assertIsNone(result["required_subjects"])

    def test_first_subject_only_requirement(self) -> None:
        result = parse_subject_requirement("首选物理，再选不限")
        self.assertEqual(result["match_mode"], "first_subject_only")
        self.assertEqual(result["required_subjects"], "物理")

    def test_first_plus_one_of_requirement(self) -> None:
        result = parse_subject_requirement("首选物理，再选化学/生物(2选1)")
        self.assertEqual(result["match_mode"], "first_plus_one_of")
        self.assertEqual(result["required_subjects"], "物理")
        self.assertEqual(result["optional_subjects"], "化学;生物")

    def test_all_of_requirement(self) -> None:
        result = parse_subject_requirement("化学、生物2科必选")
        self.assertEqual(result["match_mode"], "all_of")
        self.assertEqual(result["required_subjects"], "化学;生物")


if __name__ == "__main__":
    unittest.main()
