from __future__ import annotations

import unittest

from backend.planning_repository import (
    _build_policy_summary_text,
    _candidate_policy_topics,
    _clean_policy_summary,
    _format_policy_highlight,
    _policy_matches_signal_text,
)


class PolicyHighlightsTest(unittest.TestCase):
    def test_engineering_context_does_not_match_police_policy(self) -> None:
        signal_text = "计算机 电子信息 自动化 首选物理 再选化学 中外合作办学 体检 调剂"
        self.assertFalse(_policy_matches_signal_text("henan_2025_police", signal_text))

    def test_engineering_context_does_not_match_arts_policy(self) -> None:
        signal_text = "计算机 电子信息 自动化 首选物理 再选化学 本科批"
        self.assertFalse(_policy_matches_signal_text("henan_2026_arts_exam", signal_text))

    def test_special_plan_requires_explicit_special_plan_signal(self) -> None:
        plain_signal = "计算机 自动化 本科批 首选物理 再选化学"
        special_signal = "高校专项 国家专项 资格审核 本科批"
        self.assertFalse(_policy_matches_signal_text("henan_2025_special_plan", plain_signal))
        self.assertTrue(_policy_matches_signal_text("henan_2025_special_plan", special_signal))

    def test_general_regulation_always_retained(self) -> None:
        self.assertTrue(_policy_matches_signal_text("henan_2026_general_regulation", ""))

    def test_policy_topics_choose_most_relevant_topic_for_same_policy_key(self) -> None:
        bundle = {
            "candidates": [
                {
                    "risks": [
                        {"policy_key": "henan_2026_general_regulation", "policy_topic": "adjustment_policy"},
                        {"policy_key": "henan_2026_general_regulation", "policy_topic": "physical_requirement"},
                    ]
                },
                {
                    "risks": [
                        {"policy_key": "henan_2026_general_regulation", "policy_topic": "physical_requirement"},
                    ]
                },
            ]
        }
        topics = _candidate_policy_topics(bundle)
        self.assertEqual(topics["henan_2026_general_regulation"], "physical_requirement")

    def test_format_policy_highlight_rewrites_general_regulation_title_by_topic(self) -> None:
        item = {
            "exam_year": 2026,
            "policy_key": "henan_2026_general_regulation",
            "policy_title": "河南省2026年普通高等学校招生工作规定.pdf",
            "trend_type": "admission_regulation",
            "trend_summary": "高校可在通用体检要求基础上提出补充条件。",
            "source_url": "D:\\docs\\henan_rule.pdf",
        }
        result = _format_policy_highlight(item, "physical_requirement")
        self.assertEqual(result["title"], "体检复核")
        self.assertEqual(result["policyTopic"], "physical_requirement")
        self.assertIn("依据《河南省2026年普通高等学校招生工作规定.pdf》提炼", result["summary"])

    def test_clean_policy_summary_trims_broken_fragments_and_limits_sentence_count(self) -> None:
        summary = (
            "依据《河南省2026年普通高等学校招生工作规定.pdf》提炼：四、身体健康状况检查；"
            "9.报考高校的所有考生均须参加身体健康状况检查（以下简；"
            "的说明和解释，并在招生章程中向社会公布。；正式填报前需复核院校补充条件。；"
            "其余补充信息。"
        )
        cleaned = _clean_policy_summary(summary)
        self.assertNotIn("的说明和解释", cleaned)
        self.assertNotIn("以下简", cleaned)
        self.assertIn("正式填报前需复核院校补充条件", cleaned)
        self.assertLessEqual(cleaned.count("。"), 2)

    def test_build_policy_summary_text_outputs_separate_policy_blocks(self) -> None:
        text = _build_policy_summary_text(
            [
                {
                    "year": 2026,
                    "title": "体检复核",
                    "documentTitle": "河南省2026年普通高等学校招生工作规定.pdf",
                    "summary": "依据《河南省2026年普通高等学校招生工作规定.pdf》提炼：所有考生均须参加体检；正式填报前需复核院校补充条件。",
                },
                {
                    "year": 2025,
                    "title": "专项计划资格",
                    "documentTitle": "我省2025年重点高校招生专项计划报名资格审核工作启动.docx",
                    "summary": "依据《我省2025年重点高校招生专项计划报名资格审核工作启动.docx》提炼：专项计划须先通过资格审核。",
                },
            ]
        )
        self.assertIn("2026《体检复核》", text)
        self.assertIn("依据文件：河南省2026年普通高等学校招生工作规定.pdf", text)
        self.assertIn("\n\n2025《专项计划资格》", text)


if __name__ == "__main__":
    unittest.main()
