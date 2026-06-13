from __future__ import annotations

from collections import defaultdict
import json
from typing import Any

from backend.database import db_session
from backend.rules_engine import infer_student_subjects, safe_int, safe_number, split_keywords


TRACK_LABELS = {
    "physics": ("物理类", "理科"),
    "history": ("历史类", "文科"),
}

DECLARED_BATCH_ALIASES = {
    "本科": "本科批",
    "普通本科": "本科批",
    "本科批": "本科批",
    "本科提前批": "本科提前批",
    "提前批": "本科提前批",
    "专科": "专科批",
    "高职高专": "专科批",
    "高职(专科)": "专科批",
    "高职专科": "专科批",
    "专科批": "专科批",
    "综合评价": "综合评价",
    "待定": "待定",
}

BATCH_PRIORITY = {
    "本科提前批": 100,
    "专项计划本科批": 96,
    "本科一批": 92,
    "本科二批": 88,
    "本科三批": 84,
    "体育类本科": 80,
    "艺术类本科": 78,
    "专科批": 60,
    "体育类高职专科": 56,
    "体育类专科": 54,
    "艺术类专科": 52,
}

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


def detect_track_code(student: dict[str, Any]) -> str | None:
    subject_group = str(student.get("subject_group") or "")
    if "物理" in subject_group or "物化" in subject_group:
        return "physics"
    if "历史" in subject_group or "史政" in subject_group or "史地" in subject_group:
        return "history"

    subjects = infer_student_subjects(student)
    if "物理" in subjects:
        return "physics"
    if "历史" in subjects:
        return "history"
    return None


def get_track_labels(student: dict[str, Any]) -> list[str]:
    track_code = detect_track_code(student)
    return list(TRACK_LABELS.get(track_code or "", ()))


def resolve_effective_score(student: dict[str, Any]) -> tuple[float, str]:
    candidates = (
        ("final_score", student.get("final_score")),
        ("total_score", student.get("total_score")),
    )
    for source, value in candidates:
        score = safe_number(value)
        if score > 0:
            return round(score, 1), source
    return 0.0, "missing"


def resolve_effective_rank(student: dict[str, Any]) -> tuple[int | None, str]:
    candidates = (
        ("final_rank", student.get("final_rank")),
        ("rank", student.get("rank")),
    )
    for source, value in candidates:
        rank = safe_int(value)
        if rank > 0:
            return rank, source
    return None, "missing"


def _normalize_declared_batch(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    return DECLARED_BATCH_ALIASES.get(text, text)


def _batch_group(batch_code: Any) -> str:
    text = str(batch_code or "").strip()
    if not text:
        return "other"
    if "综合" in text:
        return "integrated"
    if any(token in text for token in ("提前批", "军队", "军校", "军士", "公安", "飞行")):
        return "early"
    if "体育类本科" in text:
        return "sports_undergraduate"
    if "体育类高职" in text or "体育类专科" in text:
        return "sports_junior"
    if "艺术类本科" in text:
        return "arts_undergraduate"
    if "艺术类专科" in text:
        return "arts_junior"
    if "专项计划" in text:
        return "special_undergraduate"
    if "本科" in text:
        return "undergraduate"
    if "专科" in text or "高职" in text:
        return "junior"
    return "other"


def _batch_matches_declared_batch(declared_batch: str | None, batch_code: Any) -> bool:
    if not declared_batch:
        return True

    group = _batch_group(batch_code)
    if declared_batch == "本科批":
        return group == "undergraduate"
    if declared_batch == "本科提前批":
        return group in {
            "early",
            "sports_undergraduate",
            "arts_undergraduate",
            "special_undergraduate",
        }
    if declared_batch == "专科批":
        return group == "junior"
    if declared_batch == "综合评价":
        return group == "integrated"
    if declared_batch == "待定":
        return True
    return str(batch_code or "").strip() == declared_batch


def _batch_sort_key(batch_code: Any) -> tuple[int, str]:
    text = str(batch_code or "").strip()
    return (-BATCH_PRIORITY.get(text, 0), text)


def _pick_effective_batch_codes(
    declared_batch: str | None,
    score: float,
    province_batch_rows: list[dict[str, Any]],
) -> tuple[list[str], bool | None]:
    relevant_rows = [
        row for row in province_batch_rows
        if row.get("batch_code") and _batch_matches_declared_batch(declared_batch, row.get("batch_code"))
    ]
    if not declared_batch or declared_batch == "待定":
        return [], None
    if declared_batch in {"本科提前批", "综合评价"}:
        return [], None
    if not relevant_rows:
        return [], None
    if score <= 0:
        codes = sorted({str(row.get("batch_code") or "").strip() for row in relevant_rows if row.get("batch_code")}, key=_batch_sort_key)
        return codes, None

    eligible_rows = [row for row in relevant_rows if safe_number(row.get("score_line")) > 0 and score >= safe_number(row.get("score_line"))]
    if not eligible_rows:
        return [], False
    codes = sorted({str(row.get("batch_code") or "").strip() for row in eligible_rows if row.get("batch_code")}, key=_batch_sort_key)
    return codes, True


def _fetch_latest_province_batch_rows(province: str | None, track_labels: list[str]) -> tuple[list[dict[str, Any]], int | None]:
    if not province or not track_labels:
        return [], None
    clause, params = _in_clause("subject_track", track_labels)
    with db_session() as connection:
        latest_row = connection.execute(
            f"""
            SELECT MAX(exam_year) AS latest_year
            FROM province_batches
            WHERE province = ? AND {clause}
            """,
            [province, *params],
        ).fetchone()
        latest_year = latest_row["latest_year"] if latest_row else None
        if latest_year in (None, ""):
            return [], None
        rows = connection.execute(
            f"""
            SELECT exam_year, subject_track, batch_code, batch_name, score_line, rank_line, notes
            FROM province_batches
            WHERE province = ?
              AND exam_year = ?
              AND {clause}
            ORDER BY score_line DESC NULLS LAST, batch_code ASC
            """,
            [province, latest_year, *params],
        ).fetchall()
    return [dict(row) for row in rows], int(latest_year)


def _resolve_batch_filter_context(student: dict[str, Any], province: str | None, track_labels: list[str], score: float) -> dict[str, Any]:
    declared_batch = _normalize_declared_batch(student.get("admission_batch"))
    province_batch_rows, reference_year = _fetch_latest_province_batch_rows(province, track_labels)
    effective_batch_codes, batch_requirement_met = _pick_effective_batch_codes(
        declared_batch,
        score,
        province_batch_rows,
    )
    return {
        "declared_batch": declared_batch,
        "province_batch_reference_year": reference_year,
        "effective_batch_codes": effective_batch_codes,
        "batch_requirement_met": batch_requirement_met,
    }


def _batch_sql_condition(context: dict[str, Any], column: str = "mas.batch_code") -> tuple[str | None, list[Any]]:
    declared_batch = str(context.get("declared_batch") or "").strip()
    effective_batch_codes = [str(item).strip() for item in (context.get("effective_batch_codes") or []) if str(item).strip()]
    batch_requirement_met = context.get("batch_requirement_met")

    if effective_batch_codes:
        clause, params = _in_clause(column, effective_batch_codes)
        return clause, params
    if batch_requirement_met is False and declared_batch in {"本科批", "专科批"}:
        return "1 = 0", []
    if not declared_batch or declared_batch == "待定":
        return None, []
    if declared_batch == "本科批":
        return f"({column} LIKE ? OR {column} LIKE ? OR {column} LIKE ?) ", ["本科一批", "本科二批", "本科三批"]
    if declared_batch == "专科批":
        return f"({column} = ? OR {column} LIKE ? OR {column} LIKE ?)", ["专科批", "%高职%", "%专科%"]
    if declared_batch == "本科提前批":
        likes = ["%提前批%", "%军队%", "%军校%", "%军士%", "%公安%", "%飞行%", "%体育类本科%", "%艺术类本科%", "%专项计划%"]
        clause = " OR ".join(f"{column} LIKE ?" for _ in likes)
        return f"({clause})", likes
    if declared_batch == "综合评价":
        return f"{column} LIKE ?", ["%综合%"]
    return f"{column} = ?", [declared_batch]


def _in_clause(column: str, values: list[str]) -> tuple[str, list[Any]]:
    placeholders = ", ".join(["?"] * len(values))
    return f"{column} IN ({placeholders})", list(values)


def _latest_admission_year(province: str | None, track_labels: list[str]) -> int | None:
    if not province or not track_labels:
        return None
    clause, params = _in_clause("subject_track", track_labels)
    with db_session() as connection:
        row = connection.execute(
            f"""
            SELECT MAX(exam_year) AS latest_year
            FROM major_admission_scores
            WHERE province = ? AND {clause}
            """,
            [province, *params],
        ).fetchone()
    if not row or row["latest_year"] in (None, ""):
        return None
    return int(row["latest_year"])


def estimate_rank_from_segments(province: str | None, track_labels: list[str], score: float) -> dict[str, Any] | None:
    if not province or score <= 0 or not track_labels:
        return None

    clause, params = _in_clause("subject_track", track_labels)
    with db_session() as connection:
        latest_row = connection.execute(
            f"""
            SELECT MAX(exam_year) AS latest_year
            FROM score_segments
            WHERE province = ? AND {clause}
            """,
            [province, *params],
        ).fetchone()
        latest_year = latest_row["latest_year"] if latest_row else None
        if latest_year in (None, ""):
            return None

        row = connection.execute(
            f"""
            SELECT exam_year, subject_track, batch_code, score_value, cumulative_count, control_line
            FROM score_segments
            WHERE province = ?
              AND exam_year = ?
              AND {clause}
              AND score_value IS NOT NULL
              AND score_value <= ?
            ORDER BY score_value DESC
            LIMIT 1
            """,
            [province, latest_year, *params, score],
        ).fetchone()

        if row is None:
            row = connection.execute(
                f"""
                SELECT exam_year, subject_track, batch_code, score_value, cumulative_count, control_line
                FROM score_segments
                WHERE province = ?
                  AND exam_year = ?
                  AND {clause}
                  AND score_value IS NOT NULL
                ORDER BY ABS(score_value - ?) ASC
                LIMIT 1
                """,
                [province, latest_year, *params, score],
            ).fetchone()

    if row is None or row["cumulative_count"] in (None, ""):
        return None

    return {
        "rank": int(row["cumulative_count"]),
        "exam_year": int(row["exam_year"]),
        "subject_track": row["subject_track"],
        "batch_code": row["batch_code"],
        "reference_score": safe_number(row["score_value"]),
        "control_line": safe_number(row["control_line"]),
    }


def build_admissions_context(student: dict[str, Any]) -> dict[str, Any]:
    province = student.get("province")
    score, score_source = resolve_effective_score(student)
    rank, rank_source = resolve_effective_rank(student)
    track_code = detect_track_code(student)
    track_labels = get_track_labels(student)
    latest_year = _latest_admission_year(province, track_labels)
    estimated_rank = None
    batch_context = _resolve_batch_filter_context(student, province, track_labels, score)

    if rank is None and score > 0:
        estimated_rank = estimate_rank_from_segments(province, track_labels, score)
        if estimated_rank:
            rank = estimated_rank["rank"]
            rank_source = "score_segments_estimate"

    return {
        "province": province,
        "exam_year": student.get("exam_year"),
        "latest_year": latest_year,
        "track_code": track_code,
        "track_labels": track_labels,
        "score": score,
        "score_source": score_source,
        "rank": rank,
        "rank_source": rank_source,
        "estimated_rank": estimated_rank,
        **batch_context,
    }


def _keyword_hits(student: dict[str, Any], row: dict[str, Any]) -> list[str]:
    keywords = split_keywords(
        student.get("school_preference"),
        student.get("target_direction"),
        student.get("interest_preferences"),
        student.get("development_goal"),
        student.get("region_preference"),
        student.get("family_preferences"),
        student.get("parent_focus"),
        student.get("remark"),
    )
    haystack = " ".join(
        str(row.get(field) or "")
        for field in (
            "institution_name",
            "major_name",
            "major_category",
            "batch_code",
            "institution_city",
            "institution_province",
            "plan_notes",
        )
    )
    return list(dict.fromkeys([keyword for keyword in keywords if keyword and keyword in haystack]))


def _evaluate_rank_bucket(student_rank: int | None, row: dict[str, Any]) -> dict[str, Any]:
    min_rank = safe_int(row.get("min_rank"))
    if not student_rank or min_rank <= 0:
        return {"bucket": "rush", "score": 66, "label": "位次待复核", "note": "位次信息不完整，先按谨慎可冲处理。"}

    margin = min_rank - student_rank
    margin_pct = margin / max(min_rank, 1)

    if margin_pct >= 0.16 or margin >= 5000:
        return {"bucket": "safe", "score": 95, "label": "位次安全", "note": "学生当前位次明显优于近年最低录取位次。"}
    if margin_pct >= 0.05 or margin >= 1200:
        return {"bucket": "steady", "score": 84, "label": "位次稳妥", "note": "学生当前位次略优于近年最低录取位次，适合稳妥关注。"}
    if margin_pct >= -0.08 or margin >= -1800:
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


def _region_bonus(student: dict[str, Any], row: dict[str, Any]) -> int:
    preference = str(student.get("region_preference") or "")
    institution_province = str(row.get("institution_province") or "")
    student_province = str(student.get("province") or "")
    bonus = 0
    if "本省" in preference and institution_province and institution_province == student_province:
        bonus += 6
    if "外省" in preference and institution_province and institution_province != student_province:
        bonus += 6
    if "省会" in preference and row.get("institution_city"):
        bonus += 2
    return bonus


def _candidate_pair_clause(rows: list[dict[str, Any]], institution_field: str, major_field: str) -> tuple[str, list[Any]]:
    parts: list[str] = []
    values: list[Any] = []
    seen_pairs = set()
    for row in rows:
        pair = (row.get("institution_id"), row.get("major_id"))
        if pair in seen_pairs or not pair[0] or not pair[1]:
            continue
        seen_pairs.add(pair)
        parts.append(f"({institution_field} = ? AND {major_field} = ?)")
        values.extend([pair[0], pair[1]])
    if not parts:
        return "", []
    return " OR ".join(parts), values


def _fetch_history_map(rows: list[dict[str, Any]], context: dict[str, Any]) -> dict[tuple[int, int], list[dict[str, Any]]]:
    province = context.get("province")
    track_labels = context.get("track_labels") or []
    if not rows or not province or not track_labels:
        return {}

    pair_clause, pair_values = _candidate_pair_clause(rows, "mas.institution_id", "mas.major_id")
    if not pair_clause:
        return {}

    track_clause, track_values = _in_clause("mas.subject_track", track_labels)
    with db_session() as connection:
        history_rows = connection.execute(
            f"""
            SELECT
                mas.institution_id,
                mas.major_id,
                mas.exam_year,
                mas.subject_track,
                mas.batch_code,
                mas.min_score,
                mas.min_rank,
                ap.planned_count
            FROM major_admission_scores mas
            LEFT JOIN admission_plans ap
                ON ap.exam_year = mas.exam_year
               AND ap.province = mas.province
               AND ap.institution_id = mas.institution_id
               AND ap.major_id = mas.major_id
               AND COALESCE(ap.batch_code, '') = COALESCE(mas.batch_code, '')
            WHERE mas.province = ?
              AND {track_clause}
              AND ({pair_clause})
            ORDER BY mas.exam_year DESC, mas.min_rank ASC
            """,
            [province, *track_values, *pair_values],
        ).fetchall()

    history_map: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    seen_years: set[tuple[int, int, int]] = set()
    for row in history_rows:
        key = (int(row["institution_id"]), int(row["major_id"]))
        year_key = (key[0], key[1], int(row["exam_year"]))
        if year_key in seen_years:
            continue
        seen_years.add(year_key)
        history_map[key].append(dict(row))
    return history_map


def _summarize_probability(student_rank: int | None, student_score: float, history_rows: list[dict[str, Any]]) -> dict[str, Any]:
    ranks = [safe_int(item.get("min_rank")) for item in history_rows if safe_int(item.get("min_rank")) > 0]
    scores = [safe_number(item.get("min_score")) for item in history_rows if safe_number(item.get("min_score")) > 0]
    if not ranks and not scores:
        return {
            "score": 58,
            "label": "待补充概率",
            "note": "历史录取样本不足，当前只做基础冲稳保分层。",
        }

    rank_score = None
    if student_rank and ranks:
        best_rank = min(ranks)
        median_rank = sorted(ranks)[len(ranks) // 2]
        worst_rank = max(ranks)
        if student_rank <= best_rank:
            rank_score = 92
        elif student_rank <= median_rank:
            rank_score = 82
        elif student_rank <= worst_rank:
            rank_score = 68
        elif student_rank <= int(worst_rank * 1.08):
            rank_score = 56
        else:
            rank_score = 36

    score_score = None
    if student_score > 0 and scores:
        best_score = max(scores)
        median_score = sorted(scores)[len(scores) // 2]
        worst_score = min(scores)
        if student_score >= best_score:
            score_score = 90
        elif student_score >= median_score:
            score_score = 80
        elif student_score >= worst_score:
            score_score = 66
        elif student_score >= worst_score - 3:
            score_score = 54
        else:
            score_score = 34

    base_score = 0
    pieces = [item for item in (rank_score, score_score) if item is not None]
    if pieces:
        base_score = round(sum(pieces) / len(pieces))
    else:
        base_score = 58

    if base_score >= 86:
        label = "录取概率较高"
    elif base_score >= 74:
        label = "录取概率中高"
    elif base_score >= 60:
        label = "录取概率中等"
    elif base_score >= 48:
        label = "录取概率偏低"
    else:
        label = "录取风险较高"

    rank_text = f"历史最低位次区间 {min(ranks)} - {max(ranks)}" if ranks else "位次样本不足"
    score_text = f"历史最低分区间 {min(scores):.0f} - {max(scores):.0f}" if scores else "分数样本不足"
    return {
        "score": int(base_score),
        "label": label,
        "note": f"{rank_text}；{score_text}。",
    }


def _summarize_plan_risk(history_rows: list[dict[str, Any]]) -> dict[str, Any]:
    planned = [(int(item["exam_year"]), safe_int(item.get("planned_count"))) for item in history_rows if safe_int(item.get("planned_count")) > 0]
    if len(planned) < 2:
        return {
            "level": "medium",
            "label": "计划波动待补充",
            "note": "可比招生计划样本不足，当前暂按中性风险处理。",
        }

    planned.sort()
    latest_year, latest_count = planned[-1]
    previous_counts = [count for _, count in planned[:-1]]
    previous_avg = sum(previous_counts) / len(previous_counts)
    diff_ratio = (latest_count - previous_avg) / max(previous_avg, 1)

    if diff_ratio <= -0.35:
        return {
            "level": "high",
            "label": "计划缩减风险",
            "note": f"{latest_year} 年计划人数较历史均值下降明显，需警惕竞争加剧。",
        }
    if diff_ratio <= -0.12:
        return {
            "level": "medium",
            "label": "计划略有收缩",
            "note": f"{latest_year} 年计划人数较历史均值略有下降，建议提高稳妥度。",
        }
    if diff_ratio >= 0.35:
        return {
            "level": "low",
            "label": "计划扩招机会",
            "note": f"{latest_year} 年计划人数较历史均值增加明显，可视为积极信号。",
        }
    return {
        "level": "low",
        "label": "计划基本稳定",
        "note": f"{latest_year} 年计划人数与历史均值接近，计划波动相对可控。",
    }


def _fetch_explicit_rule_map(rows: list[dict[str, Any]], context: dict[str, Any]) -> dict[tuple[int, int], list[dict[str, Any]]]:
    province = context.get("province")
    latest_year = context.get("latest_year")
    if not rows or not province or not latest_year:
        return {}

    pair_clause, pair_values = _candidate_pair_clause(rows, "institution_id", "major_id")
    if not pair_clause:
        return {}

    institution_ids = sorted({int(row["institution_id"]) for row in rows if row.get("institution_id")})
    if not institution_ids:
        return {}

    institution_clause, institution_values = _in_clause("institution_id", institution_ids)
    with db_session() as connection:
        institution_rows = connection.execute(
            f"""
            SELECT institution_id, rule_type, rule_title, rule_content, notes, raw_json, source_url
            FROM institution_rules
            WHERE province = ?
              AND (exam_year = ? OR exam_year IS NULL)
              AND {institution_clause}
            """,
            [province, latest_year, *institution_values],
        ).fetchall()
        risk_rows = connection.execute(
            f"""
            SELECT institution_id, major_id, risk_type, risk_level, trigger_condition, risk_message, mitigation_suggestion, raw_json
            FROM admission_risk_rules
            WHERE province = ?
              AND (exam_year = ? OR exam_year IS NULL)
              AND (
                institution_id IS NULL
                OR ({pair_clause})
                OR (major_id IS NULL AND {institution_clause})
              )
            """,
            [province, latest_year, *pair_values, *institution_values],
        ).fetchall()

    institution_rule_map: dict[int, list[dict[str, Any]]] = defaultdict(list)
    institution_risk_map: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    global_risk_rows: list[dict[str, Any]] = []
    for row in institution_rows:
        institution_rule_map[int(row["institution_id"])].append(dict(row))

    for row in risk_rows:
        payload = dict(row)
        if row["institution_id"] is None:
            global_risk_rows.append(payload)
            continue
        key = (int(row["institution_id"]), int(row["major_id"]) if row["major_id"] is not None else -1)
        institution_risk_map[key].append(payload)

    merged: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for row in rows:
        inst_id = int(row["institution_id"])
        major_id = int(row["major_id"])
        matched_global = [rule for rule in global_risk_rows if _explicit_rule_applies(rule, row)]
        merged[(inst_id, major_id)] = [
            *institution_rule_map.get(inst_id, []),
            *institution_risk_map.get((inst_id, major_id), []),
            *institution_risk_map.get((inst_id, -1), []),
            *matched_global,
        ]
    return merged


def _matches_condition_value(value: str, condition: dict[str, Any]) -> bool:
    contains_any = condition.get("contains_any") or []
    if contains_any and not any(token and token in value for token in contains_any):
        return False

    equals_any = condition.get("equals_any") or []
    if equals_any and value not in equals_any:
        return False

    not_contains_any = condition.get("not_contains_any") or []
    if not_contains_any and any(token and token in value for token in not_contains_any):
        return False

    return True


def _explicit_rule_applies(rule: dict[str, Any], row: dict[str, Any]) -> bool:
    trigger_text = str(rule.get("trigger_condition") or "").strip()
    if not trigger_text:
        return True

    try:
        trigger = json.loads(trigger_text)
    except json.JSONDecodeError:
        return True

    match_any = trigger.get("match_any") or []
    if match_any and not any(
        _matches_condition_value(str(row.get(item.get("field")) or ""), item)
        for item in match_any
    ):
        return False

    match_all = trigger.get("match_all") or []
    if match_all and not all(
        _matches_condition_value(str(row.get(item.get("field")) or ""), item)
        for item in match_all
    ):
        return False

    return True


def _heuristic_risks(row: dict[str, Any]) -> list[dict[str, Any]]:
    risks: list[dict[str, Any]] = []
    batch_code = str(row.get("batch_code") or "")
    notes = str(row.get("plan_notes") or "")
    public_private = str(row.get("public_private") or "")

    def add_risk(risk_type: str, level: str, label: str, note: str, source: str = "heuristic") -> None:
        risks.append(
            {
                "type": risk_type,
                "level": level,
                "label": label,
                "note": note,
                "source": source,
            }
        )

    if "提前批" in batch_code:
        add_risk("batch", "medium", "提前批规则", "该专业处于提前批或提前批相关层次，填报和录取节奏与普通批不同。")
    if "专项" in batch_code or "专项" in notes:
        add_risk("eligibility", "high", "专项资格要求", "该候选涉及国家专项、高校专项或地方专项，需先确认是否具备专项报考资格。")
    if "中外合作办学" in notes or "中外合作办学" in public_private or "港澳台地区合作办学" in public_private:
        add_risk("tuition", "high", "合作办学成本", "该候选涉及合作办学，学费和培养模式通常明显不同，需重点确认费用与培养方案。")
    if "只招英语" in notes or "只招英语语种考生" in notes or "只招英语,俄语语种的考生" in notes:
        add_risk("language", "high", "语种限制", "该候选对外语语种有限制，需确认考生语种是否满足院校要求。")
    if any(token in notes for token in ["不招色盲", "不招色弱", "单色识别不全", "无复视", "裸视力", "矫正视力", "身高", "不宜女生报考", "不适宜女生报考"]):
        add_risk("physical", "high", "身体条件限制", "该候选包含视力、色觉、身高或性别相关限制，必须逐条核对招生章程。")
    if "招生章程" in notes or "详见院校招生章程" in notes or "其它见招生章程" in notes:
        add_risk("charter", "medium", "需复核招生章程", "该候选明确要求以院校招生章程为准，正式填报前必须人工复核。")
    if "单列专业" in notes:
        add_risk("special_track", "medium", "单列专业规则", "该候选为单列专业，培养方式或录取规则可能与普通专业不同。")
    if "定向培养军士" in notes or "军队院校" in batch_code or "飞行学员" in batch_code:
        add_risk("special_review", "high", "特殊审核要求", "该候选涉及军事或特殊培养方向，通常还会叠加政审、体检或面试要求。")
    if "5+3" in notes or "本硕" in notes:
        add_risk("study_years", "medium", "学制特殊", "该候选学制或培养路径较特殊，需确认培养周期、分流和后续要求。")

    return risks


def _normalize_explicit_rule(rule: dict[str, Any]) -> dict[str, Any]:
    if "risk_type" in rule:
        return {
            "type": rule.get("risk_type") or "explicit_rule",
            "level": str(rule.get("risk_level") or "medium").lower(),
            "label": rule.get("risk_type") or "规则风险",
            "note": rule.get("risk_message") or rule.get("mitigation_suggestion") or "需结合院校规则人工复核。",
            "source": "risk_table",
            "policy_key": meta.get("policy_key"),
            "policy_topic": meta.get("policy_topic"),
        }

    return {
        "type": rule.get("rule_type") or "institution_rule",
        "level": "medium",
        "label": rule.get("rule_title") or rule.get("rule_type") or "院校规则",
        "note": rule.get("rule_content") or rule.get("notes") or "需结合院校章程人工复核。",
        "source": "institution_rule",
        "policy_key": meta.get("policy_key"),
        "policy_topic": meta.get("policy_topic"),
    }


def _normalize_explicit_rule_v2(rule: dict[str, Any]) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    raw_json = str(rule.get("raw_json") or "").strip()
    if raw_json:
        try:
            meta = json.loads(raw_json)
        except json.JSONDecodeError:
            meta = {}

    source_url = str(meta.get("source_url") or rule.get("source_url") or "").strip()
    source_name = source_url.replace("/", "\\").split("\\")[-1] if source_url else ""

    if "risk_type" in rule:
        label = meta.get("display_label") or rule.get("risk_type") or "规则风险"
        note = rule.get("risk_message") or rule.get("mitigation_suggestion") or "需结合院校规则人工复核。"
        if source_name:
            note = f"{note} 来源：{source_name}"
        return {
            "type": rule.get("risk_type") or "explicit_rule",
            "level": str(rule.get("risk_level") or "medium").lower(),
            "label": label,
            "note": note,
            "source": "risk_table",
            "policy_key": meta.get("policy_key"),
            "policy_topic": meta.get("policy_topic"),
        }

    note = rule.get("rule_content") or rule.get("notes") or "需结合院校招生章程人工复核。"
    if source_name:
        note = f"{note} 来源：{source_name}"
    return {
        "type": rule.get("rule_type") or "institution_rule",
        "level": "medium",
        "label": rule.get("rule_title") or rule.get("rule_type") or "院校规则",
        "note": note,
        "source": "institution_rule",
        "policy_key": meta.get("policy_key"),
        "policy_topic": meta.get("policy_topic"),
    }


def _collect_risks(row: dict[str, Any], explicit_rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items = [_normalize_explicit_rule_v2(rule) for rule in explicit_rules]
    items.extend(_heuristic_risks(row))
    deduped: list[dict[str, Any]] = []
    seen = set()
    for item in items:
        key = (item["type"], item["label"], item["note"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _fetch_candidate_rows(context: dict[str, Any], limit: int = 800) -> list[dict[str, Any]]:
    province = context.get("province")
    latest_year = context.get("latest_year")
    track_labels = context.get("track_labels") or []
    if not province or not latest_year or not track_labels:
        return []

    clause, params = _in_clause("mas.subject_track", track_labels)
    conditions = [
        "mas.province = ?",
        "mas.exam_year = ?",
        clause,
    ]
    values: list[Any] = [province, latest_year, *params]
    batch_clause, batch_values = _batch_sql_condition(context)
    if batch_clause:
        conditions.append(batch_clause)
        values.extend(batch_values)

    student_rank = safe_int(context.get("rank"))
    student_score = safe_number(context.get("score"))
    if student_rank > 0:
        lower_rank = max(1, int(student_rank * 0.55))
        upper_rank = max(lower_rank + 1, int(student_rank * 1.55))
        conditions.append("mas.min_rank BETWEEN ? AND ?")
        values.extend([lower_rank, upper_rank])
    elif student_score > 0:
        conditions.append("mas.min_score BETWEEN ? AND ?")
        values.extend([max(0, student_score - 60), min(750, student_score + 35)])

    with db_session() as connection:
        rows = connection.execute(
            f"""
            SELECT
                mas.exam_year,
                mas.subject_track,
                mas.batch_code,
                mas.plan_group_code,
                mas.min_score,
                mas.min_rank,
                mas.avg_score,
                mas.avg_rank,
                mas.max_score,
                mas.max_rank,
                mas.admitted_count,
                mas.planned_count,
                i.id AS institution_id,
                i.institution_code,
                i.institution_name,
                i.province AS institution_province,
                i.city AS institution_city,
                i.institution_level,
                i.public_private,
                m.id AS major_id,
                m.major_code,
                m.major_name,
                m.major_category,
                m.degree_level,
                COALESCE(ap.study_years, m.study_years) AS study_years,
                ap.tuition_yearly,
                ap.plan_notes,
                ap.plan_group_name,
                ap.planned_count AS latest_plan_count,
                ias.min_score AS institution_min_score,
                ias.min_rank AS institution_min_rank,
                COALESCE(
                    (
                        SELECT sr.requirement_text
                        FROM subject_requirements sr
                        WHERE sr.id = ap.subject_requirement_id
                        LIMIT 1
                    ),
                    (
                        SELECT sr2.requirement_text
                        FROM subject_requirements sr2
                        WHERE sr2.exam_year = mas.exam_year
                          AND sr2.province = mas.province
                          AND sr2.institution_id = mas.institution_id
                          AND sr2.major_id = mas.major_id
                        ORDER BY sr2.id DESC
                        LIMIT 1
                    )
                ) AS requirement_text
            FROM major_admission_scores mas
            INNER JOIN institutions i ON i.id = mas.institution_id
            INNER JOIN majors m ON m.id = mas.major_id
            LEFT JOIN admission_plans ap
                ON ap.exam_year = mas.exam_year
               AND ap.province = mas.province
               AND ap.institution_id = mas.institution_id
               AND ap.major_id = mas.major_id
               AND COALESCE(ap.batch_code, '') = COALESCE(mas.batch_code, '')
               AND COALESCE(ap.plan_group_code, '') = COALESCE(mas.plan_group_code, '')
            LEFT JOIN institution_admission_scores ias
                ON ias.exam_year = mas.exam_year
               AND ias.province = mas.province
               AND ias.institution_id = mas.institution_id
               AND COALESCE(ias.batch_code, '') = COALESCE(mas.batch_code, '')
               AND COALESCE(ias.subject_track, '') = COALESCE(mas.subject_track, '')
            WHERE {" AND ".join(conditions)}
            ORDER BY
                CASE WHEN mas.min_rank IS NULL THEN 1 ELSE 0 END,
                mas.min_rank ASC,
                mas.min_score DESC
            LIMIT ?
            """,
            [*values, limit],
        ).fetchall()
    return [dict(row) for row in rows]


def _build_candidate_match_result(
    student: dict[str, Any],
    context: dict[str, Any],
    evaluate_subject_requirement,
    limit: int,
) -> dict[str, Any]:
    raw_rows = _fetch_candidate_rows(context)
    history_map = _fetch_history_map(raw_rows, context)
    explicit_rule_map = _fetch_explicit_rule_map(raw_rows, context)
    student_subjects = infer_student_subjects(student)
    track_code = context.get("track_code")
    score = safe_number(context.get("score"))
    rank = safe_int(context.get("rank"))

    candidates: list[dict[str, Any]] = []
    rejected_candidates: list[dict[str, Any]] = []
    for row in raw_rows:
        subject_result = evaluate_subject_requirement(row.get("requirement_text"), student_subjects, track_code)
        if subject_result["status"] == "mismatch":
            rejected_candidates.append(
                _rejection_item(
                    row,
                    context,
                    "选科要求不匹配，当前不建议直接报考。",
                    subject_result=subject_result,
                )
            )
            continue

        rank_result = _evaluate_rank_bucket(rank or None, row)
        score_result = _evaluate_score_bucket(score, row)
        history_rows = history_map.get((int(row["institution_id"]), int(row["major_id"])), [])
        explicit_rules = explicit_rule_map.get((int(row["institution_id"]), int(row["major_id"])), [])
        probability = _summarize_probability(rank or None, score, history_rows)
        final_bucket = _resolve_candidate_bucket(rank_result, score_result, probability)
        if final_bucket == "out":
            rejected_candidates.append(
                _rejection_item(
                    row,
                    context,
                    "与当前分数/位次门槛差距较大，当前批次不建议作为正式志愿。",
                    rank_result=rank_result,
                    score_result=score_result,
                )
            )
            continue
        plan_risk = _summarize_plan_risk(history_rows)
        risks = _collect_risks(row, explicit_rules)
        has_high_risk = any(item["level"] == "high" for item in risks)
        keyword_hits = []
        preference_score = 0
        plan_count = safe_int(row.get("latest_plan_count") or row.get("planned_count"))
        region_bonus = _region_bonus(student, row)
        stability_bonus = 4 if plan_count >= 10 else 0
        composite_score = round(
            subject_result["score"] * 0.28
            + rank_result["score"] * 0.38
            + score_result["score"] * 0.14
            + probability["score"] * 0.12
            + region_bonus
            + stability_bonus,
            1,
        )
        rank_gap = _calculate_rank_gap(rank or None, row)
        score_gap = _calculate_score_gap(score, row)
        city_text = row.get("institution_city") or row.get("institution_province") or "院校所在地区"
        candidate = {
            **row,
            "bucket": final_bucket,
            "bucket_meta": BUCKET_META[final_bucket],
            "subject_result": subject_result,
            "rank_result": rank_result,
            "score_result": score_result,
            "probability": probability,
            "plan_risk": plan_risk,
            "history_rows": history_rows,
            "risks": risks,
            "has_high_risk": has_high_risk,
            "keyword_hits": keyword_hits,
            "preference_score": preference_score,
            "composite_score": max(35.0, min(99.0, composite_score)),
            "city_text": city_text,
            "plan_count": plan_count,
            "rank_gap": rank_gap,
            "score_gap": score_gap,
        }
        candidate["risk_level"] = _candidate_risk_level(candidate)
        candidates.append(candidate)

    prepared = _prepare_recommendation_outputs(candidates, context)
    result_context = dict(context)
    result_context["raw_row_count"] = len(raw_rows)
    return {
        "context": result_context,
        "candidates": prepared["candidates"][:limit],
        "bucketed_candidates": prepared["bucketed_candidates"],
        "recommendation_table": prepared["recommendation_table"],
        "first_choice": prepared["first_choice"],
        "alternatives": prepared["alternatives"],
        "not_recommended": _unique_rejections(rejected_candidates),
    }


def _should_retry_with_score_relaxed_context(context: dict[str, Any]) -> bool:
    if safe_number(context.get("score")) <= 0:
        return False
    if context.get("rank_source") == "score_segments_estimate":
        return True

    latest_year = safe_int(context.get("latest_year"))
    exam_year = safe_int(context.get("exam_year"))
    track_code = str(context.get("track_code") or "")
    return bool(latest_year and exam_year and exam_year > latest_year and track_code in {"physics", "history"})


def _score_relaxed_context(context: dict[str, Any]) -> dict[str, Any]:
    relaxed = dict(context)
    relaxed["rank"] = None
    relaxed["rank_source"] = "score_relaxed_real_data"
    relaxed["candidate_strategy"] = "score_relaxed_real_data"
    return relaxed


def match_admissions_candidates(
    student: dict[str, Any],
    evaluate_subject_requirement,
    limit: int = 180,
) -> dict[str, Any]:
    context = build_admissions_context(student)
    context["candidate_strategy"] = "rank_and_score"
    result = _build_candidate_match_result(student, context, evaluate_subject_requirement, limit)
    if result["candidates"] or not _should_retry_with_score_relaxed_context(context):
        return result

    relaxed_result = _build_candidate_match_result(
        student,
        _score_relaxed_context(context),
        evaluate_subject_requirement,
        limit,
    )
    if relaxed_result["candidates"]:
        return relaxed_result
    return result


def group_major_recommendations(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        grouped[str(candidate.get("major_name") or "专业方向")].append(candidate)

    rows: list[dict[str, Any]] = []
    for major_name, items in grouped.items():
        items.sort(key=lambda item: item["composite_score"], reverse=True)
        top = items[0]
        sample_schools = [item.get("institution_name") for item in items[:3] if item.get("institution_name")]
        avg_score = round(sum(item["composite_score"] for item in items[:3]) / min(3, len(items)), 1)
        rows.append(
            {
                "title": major_name,
                "type": f"{top.get('degree_level') or '专业'} / {top.get('major_category') or top.get('batch_code') or '招生方向'}",
                "score": int(round(avg_score)),
                "reason": (
                    f"优先命中 {len(items)} 条真实招生记录，当前最佳样本来自 {top.get('institution_name') or '目标院校'}，"
                    f"{top['rank_result']['note']}"
                ),
                "meta": [
                    f"推荐院校：{' / '.join(sample_schools) if sample_schools else '待补充'}",
                    f"选科判断：{top['subject_result']['label']}；{top['subject_result']['note']}",
                    f"近年门槛：最低分 {safe_number(top.get('min_score')) or '待补充'} / 最低位次 {safe_int(top.get('min_rank')) or '待补充'}",
                    f"录取概率：{top['probability']['label']}；{top['probability']['note']}",
                    f"计划风险：{top['plan_risk']['label']}；{top.get('batch_code') or '待补充'} / 计划人数 {top.get('plan_count') or '待补充'}",
                    f"特殊风险：{'；'.join(risk['label'] for risk in top['risks'][:3]) if top['risks'] else '当前未识别到显性特殊限制'}",
                ],
                "tagLabel": top["risks"][0]["label"] if top["has_high_risk"] and top["risks"] else top["bucket_meta"]["tag"],
                "tagVariant": "warning" if top["has_high_risk"] else top["bucket_meta"]["variant"],
                "footer": (
                    f"优先城市：{top.get('city_text')}；排序依据："
                    "选科要求、正式分数位次、历年门槛和计划稳定度"
                ),
            }
        )

    rows.sort(key=lambda item: item["score"], reverse=True)
    return rows


def build_plan_columns_from_candidates(candidates: list[dict[str, Any]], context: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    prepared = _prepare_recommendation_outputs(candidates, context)
    grouped = prepared["bucketed_candidates"]
    recommendation_table = prepared["recommendation_table"]
    counts = {bucket: len(items) for bucket, items in grouped.items()}
    total = sum(counts.values()) or 1
    strategy = {
        "rush_ratio": round(counts["rush"] / total * 100),
        "steady_ratio": round(counts["steady"] / total * 100),
        "safe_ratio": round(counts["safe"] / total * 100),
        "average_major_score": round(sum(item["compositeScore"] for item in recommendation_table[:6]) / max(1, min(6, len(recommendation_table))), 1) if recommendation_table else 0,
        "note": "本轮正式方案已按 3/5/3 的冲稳保目标配比做去重和邻档补位，正式填报前仍需复核院校专业组、调剂与年度计划。",
    }

    columns: list[dict[str, Any]] = []
    for bucket in BUCKET_ORDER:
        bucket_meta = BUCKET_META[bucket]
        cards = []
        for item in grouped[bucket]:
            rank_gap = item.get("rank_gap")
            score_gap = item.get("score_gap")
            risk_note = f"重点风险：{'；'.join(risk['label'] for risk in item['risks'][:2])}" if item["risks"] else ""
            adjusted_note = "（由相邻档补位）" if item.get("bucket_adjusted") else ""
            cards.append(
                {
                    "school": item.get("institution_name") or "目标院校",
                    "detail": (
                        f"{item.get('major_name') or '目标专业'} / "
                        f"{item.get('plan_group_code') or item.get('batch_code') or '招生批次'} / "
                        f"{item.get('city_text')}{adjusted_note}"
                    ),
                    "metrics": [
                        f"参考年份：{item.get('exam_year') or context.get('latest_year') or '待补充'}",
                        f"最低分：{safe_number(item.get('min_score')) or '待补充'}",
                        f"最低位次：{safe_int(item.get('min_rank')) or '待补充'}",
                        f"录取概率：{item['probability']['label']}",
                        f"计划人数：{item.get('plan_count') or '待补充'}",
                        f"位次差：{rank_gap if rank_gap is not None else '待补充'}",
                        f"分差：{score_gap if score_gap is not None else '待补充'}",
                        f"风险等级：{RISK_LEVEL_LABELS.get(item.get('risk_level') or 'review', '待复核')}",
                    ],
                    "major": f"选科要求：{item.get('requirement_text') or '待结合院校章程复核'}",
                    "reason": (
                        f"{item['rank_result']['note']} {item['score_result']['note']} {item['plan_risk']['note']}"
                        f"{f' {risk_note}' if risk_note else ''}"
                    ),
                }
            )

        columns.append(
            {
                "title": bucket_meta["title"],
                "note": (
                    f"当前正式推荐 {counts[bucket]} 条，建议按 {bucket_meta['title']} 思路配置志愿，"
                    "并继续复核院校专业组、调剂和计划波动。"
                ),
                "tagLabel": bucket_meta["tag"],
                "tagVariant": bucket_meta["variant"],
                "cards": cards,
            }
        )

    return columns, strategy
