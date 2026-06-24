from __future__ import annotations

from typing import Any

from backend.database import db_session
from backend.admissions_strategy import resolve_strategy_mode
from backend.rules_engine import infer_student_subjects, safe_int, safe_number


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
        "admissions_strategy_mode": resolve_strategy_mode(student.get("strategy_type")),
        **batch_context,
    }
