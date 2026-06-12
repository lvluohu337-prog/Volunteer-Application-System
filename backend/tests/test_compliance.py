from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from backend.compliance import find_prohibited_promise_phrases
from backend.planning_repository import create_report_advisor_note


class ComplianceGuardrailTest(unittest.TestCase):
    def test_find_prohibited_promise_phrases_matches_whitespace_variant(self):
        hits = find_prohibited_promise_phrases("这次方案可以 100% 录取，请放心。", "我们基本稳录。")

        self.assertIn("100%录取", hits)
        self.assertIn("稳录", hits)

    def test_create_report_advisor_note_rejects_prohibited_phrase(self):
        payload = SimpleNamespace(
            product_code="399",
            note_type="advisor_comment",
            note_title="沟通结论",
            note_content="这份方案基本保录，可以直接发给家长。",
            author_name="测试老师",
        )

        with patch("backend.planning_repository.fetch_student_or_404", return_value={"id": 1}):
            with self.assertRaises(HTTPException) as context:
                create_report_advisor_note(1, payload)

        self.assertEqual(context.exception.status_code, 422)
        self.assertIn("保录", str(context.exception.detail))


if __name__ == "__main__":
    unittest.main()
