from __future__ import annotations

import unittest

from backend.admissions_engine import _prepare_recommendation_outputs, build_plan_columns_from_candidates


def _candidate(index: int, bucket: str, composite_score: float, risk_level: str = "medium") -> dict:
    return {
        "institution_id": index,
        "major_id": index,
        "institution_name": f"学校{index}",
        "institution_code": f"I{index:03d}",
        "major_name": f"专业{index}",
        "major_code": f"M{index:03d}",
        "plan_group_code": f"G{index:03d}",
        "plan_group_name": f"专业组{index}",
        "exam_year": 2025,
        "batch_code": "本科批",
        "institution_city": "郑州",
        "institution_province": "河南",
        "city_text": "郑州",
        "min_score": 600 - index,
        "min_rank": 12000 + index * 100,
        "plan_count": 12,
        "requirement_text": "不限",
        "bucket": bucket,
        "bucket_meta": {"title": bucket, "tag": bucket, "variant": "primary"},
        "subject_result": {"status": "match", "label": "选科匹配", "note": "选科要求满足。", "score": 92},
        "rank_result": {"bucket": bucket if bucket != "safe" else "steady", "label": "位次匹配", "note": "位次具备一定优势。", "score": 82},
        "score_result": {"bucket": "steady", "label": "分数匹配", "note": "分数具备参考价值。", "score": 78},
        "probability": {"label": "录取概率中高", "note": "近年门槛相对稳定。", "score": 80},
        "plan_risk": {"level": "medium", "label": "计划基本稳定", "note": "计划波动可控。"},
        "risks": [],
        "has_high_risk": False,
        "keyword_hits": [],
        "preference_score": 0,
        "composite_score": composite_score,
        "rank_gap": 1000 + index * 10,
        "score_gap": 8.0 - index * 0.1,
        "risk_level": risk_level,
    }


class AdmissionsEngineTest(unittest.TestCase):
    def test_prepare_recommendation_outputs_balances_to_353_targets(self):
        candidates = [
            _candidate(1, "rush", 70.0),
            _candidate(2, "steady", 82.0),
            _candidate(3, "steady", 81.0),
            _candidate(4, "steady", 80.0),
            _candidate(5, "steady", 79.0),
            _candidate(6, "steady", 78.0),
            _candidate(7, "steady", 77.0),
            _candidate(8, "steady", 76.0),
            _candidate(9, "steady", 75.0),
            _candidate(10, "safe", 88.0, risk_level="low"),
            _candidate(11, "safe", 87.0, risk_level="low"),
        ]

        prepared = _prepare_recommendation_outputs(candidates, {"latest_year": 2025, "score": 580, "rank": 12000})
        bucketed = prepared["bucketed_candidates"]

        self.assertEqual(len(bucketed["rush"]), 3)
        self.assertEqual(len(bucketed["steady"]), 5)
        self.assertEqual(len(bucketed["safe"]), 3)
        self.assertIsNotNone(prepared["first_choice"])
        self.assertEqual(prepared["first_choice"]["bucket"], "steady")
        self.assertEqual(len(prepared["alternatives"]), 5)

    def test_build_plan_columns_uses_balanced_bucket_counts(self):
        candidates = [
            _candidate(1, "rush", 70.0),
            _candidate(2, "steady", 82.0),
            _candidate(3, "steady", 81.0),
            _candidate(4, "steady", 80.0),
            _candidate(5, "steady", 79.0),
            _candidate(6, "steady", 78.0),
            _candidate(7, "steady", 77.0),
            _candidate(8, "steady", 76.0),
            _candidate(9, "steady", 75.0),
            _candidate(10, "safe", 88.0, risk_level="low"),
            _candidate(11, "safe", 87.0, risk_level="low"),
        ]

        columns, strategy = build_plan_columns_from_candidates(candidates, {"latest_year": 2025, "score": 580, "rank": 12000})

        self.assertEqual([len(column["cards"]) for column in columns], [3, 5, 3])
        self.assertEqual(strategy["rush_ratio"], 27)
        self.assertEqual(strategy["steady_ratio"], 45)
        self.assertEqual(strategy["safe_ratio"], 27)


if __name__ == "__main__":
    unittest.main()
