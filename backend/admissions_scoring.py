from __future__ import annotations

from typing import Any

from backend.rules_engine import safe_int, safe_number


BUCKET_PRIORITY = {
    "out": 0,
    "rush": 1,
    "steady": 2,
    "safe": 3,
}

BUCKET_META = {
    "rush": {"title": "冲一冲", "tag": "风险较高", "variant": "warning"},
    "steady": {"title": "稳一稳", "tag": "建议主力", "variant": "primary"},
    "safe": {"title": "保一保", "tag": "相对安全", "variant": "success"},
}

BUCKET_ORDER = ("rush", "steady", "safe")
BUCKET_INDEX = {name: index for index, name in enumerate(BUCKET_ORDER)}
BUCKET_FALLBACKS = {
    "rush": ("steady", "safe"),
    "steady": ("safe", "rush"),
    "safe": ("steady", "rush"),
}

RISK_LEVEL_LABELS = {
    "low": "低风险",
    "medium": "中风险",
    "high": "高风险",
    "review": "待人工复核",
}


def _evaluate_rank_bucket(student_rank: int | None, row: dict[str, Any]) -> dict[str, Any]:
    min_rank = safe_int(row.get("min_rank"))
    if not student_rank or min_rank <= 0:
        return {"bucket": "rush", "score": 66, "label": "位次待复核", "note": "位次信息不完整，先按谨慎可冲处理。"}

    margin = min_rank - student_rank
    margin_pct = margin / max(student_rank, 1)

    if margin_pct >= 0.20:
        return {"bucket": "safe", "score": 97, "label": "位次保底", "note": "学生当前位次大幅优于近年最低录取位次，可作为保底层候选。"}
    if margin_pct >= 0.10:
        return {"bucket": "safe", "score": 95, "label": "位次安全", "note": "学生当前位次明显优于近年最低录取位次。"}
    if margin_pct >= -0.05:
        return {"bucket": "steady", "score": 84, "label": "位次稳妥", "note": "学生当前位次略优于近年最低录取位次，适合稳妥关注。"}
    if margin_pct >= -0.10:
        return {"bucket": "rush", "score": 70, "label": "位次可冲", "note": "学生当前位次接近往年门槛，可作为冲刺尝试。"}
    return {"bucket": "out", "score": 35, "label": "位次压力大", "note": "学生当前位次明显落后于往年门槛，正式填报风险较高。"}


def _evaluate_score_bucket(student_score: float, row: dict[str, Any]) -> dict[str, Any]:
    min_score = safe_number(row.get("min_score"))
    if student_score <= 0 or min_score <= 0:
        return {"bucket": "rush", "score": 66, "label": "分数待复核", "note": "分数信息不完整，先按谨慎可冲处理。"}

    margin = round(student_score - min_score, 1)
    if margin >= 15:
        return {"bucket": "safe", "score": 93, "label": "分数安全", "note": "当前分数明显高于近年最低录取分。"}
    if margin >= 6:
        return {"bucket": "steady", "score": 82, "label": "分数稳妥", "note": "当前分数高于近年最低录取分，可作为稳妥选择。"}
    if margin >= -5:
        return {"bucket": "rush", "score": 69, "label": "分数可冲", "note": "当前分数接近近年最低录取分，可作为冲刺关注。"}
    return {"bucket": "out", "score": 34, "label": "分数压力大", "note": "当前分数低于近年最低录取分较多，风险较高。"}


def _combine_bucket(*items: dict[str, Any]) -> str:
    valid = [item["bucket"] for item in items if item.get("bucket") in BUCKET_PRIORITY]
    if not valid:
        return "rush"
    priorities = [BUCKET_PRIORITY[name] for name in valid]
    if 0 in priorities and max(priorities) <= 1:
        return "out"

    average_priority = sum(priorities) / len(priorities)
    if average_priority >= 2.6:
        return "safe"
    if average_priority >= 1.8:
        return "steady"
    if average_priority >= 1.0:
        return "rush"
    return "out"


def _shift_bucket(bucket: str, offset: int) -> str:
    index = BUCKET_INDEX.get(bucket)
    if index is None:
        return bucket
    next_index = max(0, min(len(BUCKET_ORDER) - 1, index + offset))
    return BUCKET_ORDER[next_index]


def _bucket_gap(left: str, right: str) -> int:
    return abs(BUCKET_INDEX.get(left, 0) - BUCKET_INDEX.get(right, 0))


def _resolve_candidate_bucket(rank_result: dict[str, Any], score_result: dict[str, Any], probability: dict[str, Any]) -> str:
    rank_bucket = str(rank_result.get("bucket") or "rush")
    score_bucket = str(score_result.get("bucket") or "rush")
    probability_score = safe_int(probability.get("score"))

    if rank_bucket == "out":
        return _combine_bucket(rank_result, score_result)

    final_bucket = rank_bucket
    if score_bucket == "safe" and final_bucket == "steady":
        final_bucket = "safe"
    elif score_bucket == "steady" and final_bucket == "rush":
        final_bucket = "steady"
    elif score_bucket == "rush" and final_bucket == "safe":
        final_bucket = "steady"
    elif score_bucket == "out":
        final_bucket = _shift_bucket(final_bucket, -1)

    if probability_score >= 88 and score_bucket in {"steady", "safe"}:
        final_bucket = _shift_bucket(final_bucket, 1)
    elif probability_score <= 45:
        final_bucket = _shift_bucket(final_bucket, -1)
    return final_bucket


def _calculate_rank_gap(student_rank: int | None, row: dict[str, Any]) -> int | None:
    min_rank = safe_int(row.get("min_rank"))
    if not student_rank or min_rank <= 0:
        return None
    return min_rank - student_rank


def _calculate_score_gap(student_score: float, row: dict[str, Any]) -> float | None:
    min_score = safe_number(row.get("min_score"))
    if student_score <= 0 or min_score <= 0:
        return None
    return round(student_score - min_score, 1)
