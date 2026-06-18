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

RECOMMENDATION_TARGETS = {
    "rush": 3,
    "steady": 5,
    "safe": 3,
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


def _bucket_gap(left: str, right: str) -> int:
    return abs(BUCKET_INDEX.get(left, 0) - BUCKET_INDEX.get(right, 0))


def _candidate_sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
    probability_score = safe_int((item.get("probability") or {}).get("score"))
    plan_count = safe_int(item.get("plan_count"))
    risk_level = str(item.get("risk_level") or "")
    risk_score = {
        "low": 4,
        "medium": 3,
        "review": 2,
        "high": 1,
    }.get(risk_level, 0)
    return (
        safe_number(item.get("composite_score")),
        probability_score,
        risk_score,
        plan_count,
    )


def _candidate_family_key(item: dict[str, Any]) -> tuple[int, int]:
    return (
        safe_int(item.get("institution_id")),
        safe_int(item.get("major_id")),
    )


def _dedupe_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen_family_keys: set[tuple[int, int]] = set()
    for item in sorted(candidates, key=_candidate_sort_key, reverse=True):
        family_key = _candidate_family_key(item)
        if family_key in seen_family_keys:
            continue
        seen_family_keys.add(family_key)
        deduped.append(item)
    return deduped


def _assign_bucket(item: dict[str, Any], display_bucket: str) -> dict[str, Any]:
    assigned = dict(item)
    assigned["display_bucket"] = display_bucket
    assigned["source_bucket"] = item.get("bucket")
    assigned["bucket_adjusted"] = display_bucket != item.get("bucket")
    return assigned


def _select_bucketed_recommendations(
    candidates: list[dict[str, Any]],
    targets: dict[str, int] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    selected: dict[str, list[dict[str, Any]]] = {bucket: [] for bucket in BUCKET_ORDER}
    targets = targets or RECOMMENDATION_TARGETS
    grouped: dict[str, list[dict[str, Any]]] = {bucket: [] for bucket in BUCKET_ORDER}

    for item in _dedupe_candidates(candidates):
        bucket = str(item.get("bucket") or "rush")
        if bucket in grouped:
            grouped[bucket].append(item)

    for bucket in BUCKET_ORDER:
        grouped[bucket].sort(key=_candidate_sort_key, reverse=True)
        while grouped[bucket] and len(selected[bucket]) < targets.get(bucket, 0):
            selected[bucket].append(_assign_bucket(grouped[bucket].pop(0), bucket))

    for bucket in BUCKET_ORDER:
        while len(selected[bucket]) < targets.get(bucket, 0):
            moved = False
            for source_bucket in BUCKET_FALLBACKS[bucket]:
                if not grouped[source_bucket]:
                    continue
                selected[bucket].append(_assign_bucket(grouped[source_bucket].pop(0), bucket))
                moved = True
                break
            if not moved:
                break

    return selected


def _candidate_reason(item: dict[str, Any]) -> str:
    parts = [
        (item.get("rank_result") or {}).get("note"),
        (item.get("score_result") or {}).get("note"),
        (item.get("plan_risk") or {}).get("note"),
    ]
    text = " ".join(part for part in parts if part)
    if item.get("bucket_adjusted"):
        text = f"{text} 当前为保证正式方案完整性，已按冲稳保配额做邻档补位。".strip()
    risk_labels = [risk.get("label") for risk in (item.get("risks") or [])[:2] if risk.get("label")]
    if risk_labels:
        text = f"{text} 重点复核：{'、'.join(risk_labels)}。".strip()
    return text or "当前候选满足基本选科与录取门槛要求，适合作为正式志愿筛选样本。"


def _candidate_risk_level(item: dict[str, Any]) -> str:
    source_bucket = str(item.get("bucket") or "rush")
    plan_risk_level = str((item.get("plan_risk") or {}).get("level") or "medium")
    risk_levels = {str(risk.get("level") or "medium").lower() for risk in (item.get("risks") or [])}
    score_bucket = str((item.get("score_result") or {}).get("bucket") or "rush")
    rank_bucket = str((item.get("rank_result") or {}).get("bucket") or "rush")

    if "high" in risk_levels or plan_risk_level == "high":
        return "high"
    if _bucket_gap(rank_bucket, score_bucket) >= 2:
        return "review"
    if source_bucket == "rush" or "medium" in risk_levels or plan_risk_level == "medium":
        return "medium"
    return "low"


def _recommendation_item(item: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    display_bucket = str(item.get("display_bucket") or item.get("bucket") or "rush")
    risk_level = str(item.get("risk_level") or _candidate_risk_level(item))
    rank_gap = item.get("rank_gap")
    score_gap = item.get("score_gap")
    risk_notes = [risk.get("note") for risk in (item.get("risks") or []) if risk.get("note")]
    plan_risk = item.get("plan_risk") or {}
    if plan_risk.get("note"):
        risk_notes.insert(0, plan_risk["note"])

    return {
        "bucket": display_bucket,
        "bucketLabel": BUCKET_META[display_bucket]["title"],
        "sourceBucket": item.get("source_bucket") or item.get("bucket") or display_bucket,
        "bucketAdjusted": bool(item.get("bucket_adjusted")),
        "institutionId": safe_int(item.get("institution_id")) or None,
        "institutionName": item.get("institution_name") or "目标院校",
        "institutionCode": item.get("institution_code") or "",
        "majorId": safe_int(item.get("major_id")) or None,
        "majorName": item.get("major_name") or "目标专业",
        "majorCode": item.get("major_code") or "",
        "planGroupCode": item.get("plan_group_code") or "",
        "planGroupName": item.get("plan_group_name") or "",
        "batchCode": item.get("batch_code") or "",
        "city": item.get("institution_city") or "",
        "province": item.get("institution_province") or "",
        "cityText": item.get("city_text") or "",
        "examYear": safe_int(item.get("exam_year")) or safe_int(context.get("latest_year")) or None,
        "minScore": safe_number(item.get("min_score")) or None,
        "minRank": safe_int(item.get("min_rank")) or None,
        "rankGap": rank_gap,
        "scoreGap": score_gap,
        "planCount": safe_int(item.get("plan_count")) or None,
        "subjectRequirement": item.get("requirement_text") or "",
        "probabilityLabel": (item.get("probability") or {}).get("label") or "",
        "probabilityScore": safe_int((item.get("probability") or {}).get("score")) or None,
        "riskLevel": risk_level,
        "riskLabel": RISK_LEVEL_LABELS.get(risk_level, "待复核"),
        "planRiskLevel": str(plan_risk.get("level") or "medium"),
        "planRiskLabel": plan_risk.get("label") or "",
        "recommendationReason": _candidate_reason(item),
        "riskNotes": risk_notes[:4],
        "subjectStatus": (item.get("subject_result") or {}).get("status") or "review",
        "subjectLabel": (item.get("subject_result") or {}).get("label") or "",
        "compositeScore": round(safe_number(item.get("composite_score")), 1),
    }


def _rejection_item(
    row: dict[str, Any],
    context: dict[str, Any],
    reason: str,
    *,
    subject_result: dict[str, Any] | None = None,
    rank_result: dict[str, Any] | None = None,
    score_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    notes = [reason]
    for payload in (subject_result, rank_result, score_result):
        note = (payload or {}).get("note")
        if note:
            notes.append(note)
    return {
        "institutionName": row.get("institution_name") or "目标院校",
        "institutionCode": row.get("institution_code") or "",
        "majorName": row.get("major_name") or "目标专业",
        "majorCode": row.get("major_code") or "",
        "planGroupCode": row.get("plan_group_code") or "",
        "cityText": row.get("institution_city") or row.get("institution_province") or "",
        "examYear": safe_int(row.get("exam_year")) or safe_int(context.get("latest_year")) or None,
        "minScore": safe_number(row.get("min_score")) or None,
        "minRank": safe_int(row.get("min_rank")) or None,
        "reason": reason,
        "notes": notes[:3],
        "riskLevel": "high" if subject_result and subject_result.get("status") == "mismatch" else "review",
        "riskLabel": "不建议当前批次直接报考",
    }


def _unique_rejections(items: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen = set()
    for item in items:
        key = (
            item.get("institutionName"),
            item.get("majorName"),
            item.get("planGroupCode"),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
        if len(deduped) >= limit:
            break
    return deduped


def _first_choice_sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
    bucket_score = {
        "steady": 3,
        "safe": 2,
        "rush": 1,
    }.get(str(item.get("bucket") or ""), 0)
    risk_score = {
        "low": 4,
        "medium": 3,
        "review": 2,
        "high": 1,
    }.get(str(item.get("riskLevel") or ""), 0)
    return (
        bucket_score,
        risk_score,
        safe_number(item.get("compositeScore")),
        safe_int(item.get("probabilityScore")),
    )


def _select_first_choice(recommendations: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not recommendations:
        return None
    return max(recommendations, key=_first_choice_sort_key)


def _select_alternatives(recommendations: list[dict[str, Any]], first_choice: dict[str, Any] | None, limit: int = 5) -> list[dict[str, Any]]:
    if not recommendations:
        return []
    excluded = {
        (
            (first_choice or {}).get("institutionName"),
            (first_choice or {}).get("majorName"),
            (first_choice or {}).get("planGroupCode"),
        )
    }
    rows = [
        item
        for item in sorted(recommendations, key=_first_choice_sort_key, reverse=True)
        if (
            item.get("institutionName"),
            item.get("majorName"),
            item.get("planGroupCode"),
        ) not in excluded
    ]
    return rows[:limit]


def _prepare_recommendation_outputs(
    candidates: list[dict[str, Any]],
    context: dict[str, Any],
) -> dict[str, Any]:
    deduped_candidates = _dedupe_candidates(candidates)
    bucketed_candidates = _select_bucketed_recommendations(deduped_candidates)
    recommendation_table = [
        _recommendation_item(item, context)
        for bucket in BUCKET_ORDER
        for item in bucketed_candidates[bucket]
    ]
    first_choice = _select_first_choice(recommendation_table)
    alternatives = _select_alternatives(recommendation_table, first_choice)
    return {
        "candidates": deduped_candidates,
        "bucketed_candidates": bucketed_candidates,
        "recommendation_table": recommendation_table,
        "first_choice": first_choice,
        "alternatives": alternatives,
    }
