from __future__ import annotations

import json
import re
from typing import Any

from fastapi import HTTPException

from backend.database import db_session
from backend.foundation_constants import (
    COMPLIANCE_DISCLAIMER,
    ELEMENT_RULES,
    INTERFACE_BOUNDARY_NOTE,
    REPORT_PRODUCT_LABELS,
)
from backend.repository import now_text, normalize_text


def _serialize_row(row: dict[str, Any]) -> str:
    return json.dumps(row, ensure_ascii=False, separators=(",", ":"))


def _parse_multi_value(value: str | None, split_pattern: str = r"[、,，/|]+") -> list[str]:
    if not value:
        return []
    return [item.strip() for item in re.split(split_pattern, value) if item.strip()]


def _parse_element_tags(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in re.split(r"[+＋/、,，|]+", value) if item.strip()]


def _query_rows(
    table_name: str,
    select_sql: str,
    query: str | None = None,
    filters: list[str] | None = None,
    values: list[Any] | None = None,
) -> dict[str, Any]:
    conditions = list(filters or [])
    params = list(values or [])

    if query:
        conditions.append(query)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    with db_session() as connection:
        rows = connection.execute(f"{select_sql} {where_clause} ORDER BY id ASC", params).fetchall()
    return {"rows": [dict(row) for row in rows], "total": len(rows)}


def upsert_major_categories(rows: list[dict[str, str]]) -> int:
    timestamp = now_text()
    with db_session() as connection:
        for row in rows:
            category_name = normalize_text(row.get("专业大类"))
            if not category_name:
                continue
            connection.execute(
                """
                INSERT INTO major_categories (
                    category_name,
                    representative_majors,
                    suitable_traits,
                    subject_requirement_reference,
                    matching_cities_industries,
                    career_paths,
                    risk_notes,
                    helper_tags,
                    recommendation_index,
                    raw_json,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(category_name) DO UPDATE SET
                    representative_majors = excluded.representative_majors,
                    suitable_traits = excluded.suitable_traits,
                    subject_requirement_reference = excluded.subject_requirement_reference,
                    matching_cities_industries = excluded.matching_cities_industries,
                    career_paths = excluded.career_paths,
                    risk_notes = excluded.risk_notes,
                    helper_tags = excluded.helper_tags,
                    recommendation_index = excluded.recommendation_index,
                    raw_json = excluded.raw_json,
                    updated_at = excluded.updated_at
                """,
                [
                    category_name,
                    normalize_text(row.get("代表专业")),
                    normalize_text(row.get("适合学生特质")),
                    normalize_text(row.get("常见选科要求参考")),
                    normalize_text(row.get("适配城市/产业")),
                    normalize_text(row.get("就业方向")),
                    normalize_text(row.get("主要风险")),
                    normalize_text(row.get("前六字/五行辅助标签")),
                    int(float(row["推荐指数"])) if normalize_text(row.get("推荐指数")) else None,
                    _serialize_row(row),
                    timestamp,
                    timestamp,
                ],
            )
    return len(rows)


def upsert_city_industries(rows: list[dict[str, str]]) -> int:
    timestamp = now_text()
    with db_session() as connection:
        for row in rows:
            city_name = normalize_text(row.get("城市/城市群"))
            if not city_name:
                continue
            connection.execute(
                """
                INSERT INTO city_industries (
                    city_name,
                    region,
                    pace,
                    leading_industries,
                    suitable_major_directions,
                    suitable_student_types,
                    risk_tips,
                    raw_json,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(city_name) DO UPDATE SET
                    region = excluded.region,
                    pace = excluded.pace,
                    leading_industries = excluded.leading_industries,
                    suitable_major_directions = excluded.suitable_major_directions,
                    suitable_student_types = excluded.suitable_student_types,
                    risk_tips = excluded.risk_tips,
                    raw_json = excluded.raw_json,
                    updated_at = excluded.updated_at
                """,
                [
                    city_name,
                    normalize_text(row.get("区域")),
                    normalize_text(row.get("节奏")),
                    normalize_text(row.get("主导产业")),
                    normalize_text(row.get("适合专业方向")),
                    normalize_text(row.get("适合学生类型")),
                    normalize_text(row.get("风险提示")),
                    _serialize_row(row),
                    timestamp,
                    timestamp,
                ],
            )
    return len(rows)


def upsert_sample_students(rows: list[dict[str, str]]) -> int:
    timestamp = now_text()
    with db_session() as connection:
        for row in rows:
            sample_code = normalize_text(row.get("编号"))
            if not sample_code:
                continue
            estimated_score = normalize_text(row.get("预估分"))
            estimated_rank = normalize_text(row.get("预估位次"))
            connection.execute(
                """
                INSERT INTO sample_students (
                    sample_code,
                    name,
                    province,
                    subject_track,
                    estimated_score,
                    estimated_rank,
                    personality_tags,
                    auxiliary_tendency,
                    region_preference,
                    family_focus,
                    recommended_major_directions,
                    recommended_cities,
                    strategy_type,
                    suggested_product,
                    raw_json,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(sample_code) DO UPDATE SET
                    name = excluded.name,
                    province = excluded.province,
                    subject_track = excluded.subject_track,
                    estimated_score = excluded.estimated_score,
                    estimated_rank = excluded.estimated_rank,
                    personality_tags = excluded.personality_tags,
                    auxiliary_tendency = excluded.auxiliary_tendency,
                    region_preference = excluded.region_preference,
                    family_focus = excluded.family_focus,
                    recommended_major_directions = excluded.recommended_major_directions,
                    recommended_cities = excluded.recommended_cities,
                    strategy_type = excluded.strategy_type,
                    suggested_product = excluded.suggested_product,
                    raw_json = excluded.raw_json,
                    updated_at = excluded.updated_at
                """,
                [
                    sample_code,
                    normalize_text(row.get("姓名")),
                    normalize_text(row.get("省份")),
                    normalize_text(row.get("选科/科类")),
                    float(estimated_score) if estimated_score else None,
                    int(float(estimated_rank)) if estimated_rank else None,
                    normalize_text(row.get("性格标签")),
                    normalize_text(row.get("前六字辅助倾向")),
                    normalize_text(row.get("地域偏好")),
                    normalize_text(row.get("家庭关注点")),
                    normalize_text(row.get("推荐专业方向")),
                    normalize_text(row.get("推荐城市")),
                    normalize_text(row.get("策略类型")),
                    normalize_text(row.get("建议产品")),
                    _serialize_row(row),
                    timestamp,
                    timestamp,
                ],
            )
    return len(rows)


def upsert_report_template_fields(rows: list[dict[str, str]]) -> int:
    timestamp = now_text()
    with db_session() as connection:
        for row in rows:
            product_name = normalize_text(row.get("产品"))
            module_name = normalize_text(row.get("模块"))
            if not product_name or not module_name:
                continue
            connection.execute(
                """
                INSERT INTO report_template_fields (
                    product_name,
                    module_name,
                    suggested_pages,
                    core_content,
                    requires_manual_review,
                    raw_json,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(product_name, module_name) DO UPDATE SET
                    suggested_pages = excluded.suggested_pages,
                    core_content = excluded.core_content,
                    requires_manual_review = excluded.requires_manual_review,
                    raw_json = excluded.raw_json,
                    updated_at = excluded.updated_at
                """,
                [
                    product_name,
                    module_name,
                    normalize_text(row.get("页数建议")),
                    normalize_text(row.get("核心内容")),
                    1 if str(row.get("是否必须人工复核", "")).strip() == "是" else 0,
                    _serialize_row(row),
                    timestamp,
                    timestamp,
                ],
            )
    return len(rows)


def list_major_categories(keyword: str | None = None) -> dict[str, Any]:
    filters: list[str] = []
    values: list[Any] = []
    if keyword:
        like_value = f"%{keyword.strip()}%"
        filters.append(
            "(category_name LIKE ? OR representative_majors LIKE ? OR suitable_traits LIKE ? OR matching_cities_industries LIKE ?)"
        )
        values.extend([like_value, like_value, like_value, like_value])

    with db_session() as connection:
        rows = connection.execute(
            f"""
            SELECT *
            FROM major_categories
            {"WHERE " + " AND ".join(filters) if filters else ""}
            ORDER BY recommendation_index DESC, id ASC
            """,
            values,
        ).fetchall()

    return {
        "total": len(rows),
        "rows": [dict(row) for row in rows],
        "disclaimer": COMPLIANCE_DISCLAIMER,
        "boundary_note": INTERFACE_BOUNDARY_NOTE,
    }


def list_city_industries(keyword: str | None = None, region: str | None = None) -> dict[str, Any]:
    filters: list[str] = []
    values: list[Any] = []
    if keyword:
        like_value = f"%{keyword.strip()}%"
        filters.append(
            "(city_name LIKE ? OR leading_industries LIKE ? OR suitable_major_directions LIKE ? OR suitable_student_types LIKE ?)"
        )
        values.extend([like_value, like_value, like_value, like_value])
    if region:
        filters.append("region LIKE ?")
        values.append(f"%{region.strip()}%")

    with db_session() as connection:
        rows = connection.execute(
            f"""
            SELECT *
            FROM city_industries
            {"WHERE " + " AND ".join(filters) if filters else ""}
            ORDER BY id ASC
            """,
            values,
        ).fetchall()

    return {
        "total": len(rows),
        "rows": [dict(row) for row in rows],
        "disclaimer": COMPLIANCE_DISCLAIMER,
        "boundary_note": INTERFACE_BOUNDARY_NOTE,
    }


def list_sample_students(keyword: str | None = None, suggested_product: str | None = None) -> dict[str, Any]:
    filters: list[str] = []
    values: list[Any] = []
    if keyword:
        like_value = f"%{keyword.strip()}%"
        filters.append(
            "(name LIKE ? OR province LIKE ? OR subject_track LIKE ? OR recommended_major_directions LIKE ?)"
        )
        values.extend([like_value, like_value, like_value, like_value])
    if suggested_product:
        filters.append("suggested_product = ?")
        values.append(suggested_product.strip())

    with db_session() as connection:
        rows = connection.execute(
            f"""
            SELECT *
            FROM sample_students
            {"WHERE " + " AND ".join(filters) if filters else ""}
            ORDER BY CAST(sample_code AS INTEGER) ASC, id ASC
            """,
            values,
        ).fetchall()

    return {
        "total": len(rows),
        "rows": [dict(row) for row in rows],
        "disclaimer": COMPLIANCE_DISCLAIMER,
        "boundary_note": INTERFACE_BOUNDARY_NOTE,
    }


def list_report_template_fields(product: str | None = None) -> dict[str, Any]:
    filters: list[str] = []
    values: list[Any] = []
    if product:
        filters.append("product_name LIKE ?")
        values.append(f"%{product.strip()}%")

    with db_session() as connection:
        rows = connection.execute(
            f"""
            SELECT *
            FROM report_template_fields
            {"WHERE " + " AND ".join(filters) if filters else ""}
            ORDER BY product_name ASC, id ASC
            """,
            values,
        ).fetchall()

    return {
        "total": len(rows),
        "rows": [dict(row) for row in rows],
        "disclaimer": COMPLIANCE_DISCLAIMER,
        "boundary_note": INTERFACE_BOUNDARY_NOTE,
    }


def _fetch_sample_student_or_404(sample_student_id: int) -> dict[str, Any]:
    with db_session() as connection:
        row = connection.execute(
            "SELECT * FROM sample_students WHERE id = ?",
            (sample_student_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Sample student not found")
    return dict(row)


def _fetch_template_modules(product_code: str) -> list[dict[str, Any]]:
    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM report_template_fields
            WHERE product_name LIKE ?
            ORDER BY id ASC
            """,
            (f"{product_code}%",),
        ).fetchall()
    return [dict(row) for row in rows]


def _match_major_categories(student: dict[str, Any]) -> list[dict[str, Any]]:
    keywords = _parse_multi_value(student.get("recommended_major_directions"))
    with db_session() as connection:
        rows = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM major_categories ORDER BY recommendation_index DESC, id ASC"
            ).fetchall()
        ]

    if not keywords:
        return rows[:3]

    matched: list[dict[str, Any]] = []
    for row in rows:
        haystack = " ".join(
            str(row.get(key) or "")
            for key in ("category_name", "representative_majors", "matching_cities_industries")
        )
        if any(keyword in haystack for keyword in keywords):
            matched.append(row)

    return matched[:4] or rows[:4]


def _match_city_industries(student: dict[str, Any]) -> list[dict[str, Any]]:
    keywords = _parse_multi_value(student.get("recommended_cities"))
    with db_session() as connection:
        rows = [
            dict(row)
            for row in connection.execute("SELECT * FROM city_industries ORDER BY id ASC").fetchall()
        ]

    if not keywords:
        return rows[:3]

    matched: list[dict[str, Any]] = []
    for row in rows:
        city_name = str(row.get("city_name") or "")
        if any(keyword in city_name for keyword in keywords):
            matched.append(row)

    return matched[:4] or rows[:4]


def _split_demo_keywords(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in re.split(r"[、，,；;/|+\s]+", value) if item.strip()]


def _unique_non_empty(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _infer_demo_subject_tracks(student: dict[str, Any]) -> list[str]:
    subject_track = str(student.get("subject_track") or "")
    if "物理" in subject_track:
        return ["物理类", "理科"]
    if "历史" in subject_track:
        return ["历史类", "文科"]
    return ["物理类", "理科", "历史类", "文科"]


def _build_demo_major_keywords(student: dict[str, Any], major_rows: list[dict[str, Any]]) -> list[str]:
    keywords: list[str] = []
    keywords.extend(_split_demo_keywords(student.get("recommended_major_directions")))
    for row in major_rows:
        keywords.extend(_split_demo_keywords(row.get("category_name")))
        keywords.extend(_split_demo_keywords(row.get("representative_majors")))

    expanded_keywords: list[str] = []
    for keyword in keywords:
        expanded_keywords.append(keyword)
        if keyword.endswith("类") and len(keyword) > 1:
            expanded_keywords.append(keyword[:-1])
    return _unique_non_empty(expanded_keywords)


def _classify_demo_match_level(rank_delta: int | None, score_delta: float | None) -> tuple[str, str]:
    if rank_delta is not None:
        if -18000 <= rank_delta <= 3000:
            return "rush", "冲刺"
        if 3000 < rank_delta <= 15000:
            return "steady", "稳妥"
        if rank_delta > 15000:
            return "safe", "保底"
    if score_delta is not None:
        if -8 <= score_delta <= 3:
            return "rush", "冲刺"
        if 3 < score_delta <= 15:
            return "steady", "稳妥"
        if score_delta > 15:
            return "safe", "保底"
    return "steady", "稳妥"


def _build_demo_reason(
    student: dict[str, Any],
    candidate: dict[str, Any],
    level_label: str,
    preferred_cities: list[str],
) -> str:
    major_text = candidate.get("major_name") or "目标专业"
    fragments = [f"{major_text} 与学生当前推荐方向较贴合"]

    if candidate.get("rank_delta") is not None:
        rank_delta = int(candidate["rank_delta"])
        if rank_delta < 0:
            fragments.append(f"近年最低位次约 {candidate['min_rank']}，比学生预估位次更靠前 {abs(rank_delta)} 名，适合放在{level_label}位")
        else:
            fragments.append(f"近年最低位次约 {candidate['min_rank']}，相对学生预估位次留有 {rank_delta} 名空间")
    elif candidate.get("score_delta") is not None and candidate.get("min_score") is not None:
        score_delta = round(float(candidate["score_delta"]), 1)
        fragments.append(f"按分数口径看，较历史最低分大约留有 {score_delta} 分安全边界")

    city_name = candidate.get("city") or ""
    if city_name and any(keyword in city_name for keyword in preferred_cities):
        fragments.append(f"{city_name} 也在学生偏好的城市方向内")

    return "；".join(fragments)


def _build_demo_risk_tip(candidate: dict[str, Any], level_label: str) -> str:
    if level_label == "冲刺":
        return "历史位次略优于当前预估，存在够线但专业被调剂或未录取的风险。"
    if level_label == "稳妥":
        return "位次区间接近，仍需关注当年招生计划波动、专业冷热变化和调剂规则。"
    return "安全边界相对更大，但也要确认学校城市、专业内容和培养成本是否能接受。"


def _score_demo_candidate(
    candidate: dict[str, Any],
    bucket_key: str,
    major_keywords: list[str],
    preferred_cities: list[str],
) -> float:
    haystack = " ".join(
        [
            str(candidate.get("institution_name") or ""),
            str(candidate.get("major_name") or ""),
            str(candidate.get("city") or ""),
        ]
    )
    keyword_hits = sum(1 for keyword in major_keywords if keyword and keyword in haystack)
    city_hits = sum(1 for city in preferred_cities if city and city in str(candidate.get("city") or ""))
    target_rank_delta = {"rush": -6000, "steady": 9000, "safe": 26000}[bucket_key]
    rank_component = 0.0
    if candidate.get("rank_delta") is not None:
        rank_component = max(0.0, 80.0 - abs(float(candidate["rank_delta"]) - target_rank_delta) / 1200)
        if bucket_key == "safe" and float(candidate["rank_delta"]) < 10000:
            rank_component -= 18.0
        if bucket_key == "steady" and float(candidate["rank_delta"]) > 18000:
            rank_component -= 12.0
        if bucket_key == "safe":
            rank_component *= 1.8
        elif bucket_key == "steady":
            rank_component *= 1.2
    score_component = 0.0
    if candidate.get("score_delta") is not None:
        target_score_delta = {"rush": -2.0, "steady": 8.0, "safe": 24.0}[bucket_key]
        score_component = max(0.0, 30.0 - abs(float(candidate["score_delta"]) - target_score_delta) * 2)
    year_component = float(candidate.get("exam_year") or 0) / 1000
    return rank_component + score_component + keyword_hits * 18 + city_hits * 6 + year_component


def _fetch_demo_recommendation_pool(student: dict[str, Any]) -> list[dict[str, Any]]:
    subject_tracks = _infer_demo_subject_tracks(student)
    placeholders = ", ".join(["?"] * len(subject_tracks))
    params: list[Any] = [*subject_tracks, 2024]

    filters = [
        f"mas.subject_track IN ({placeholders})",
        "mas.min_rank IS NOT NULL",
        "mas.exam_year >= ?",
    ]

    estimated_rank = int(student.get("estimated_rank") or 0)
    if estimated_rank > 0:
        filters.append("mas.min_rank BETWEEN ? AND ?")
        params.extend([max(1, estimated_rank - 25000), estimated_rank + 120000])
    else:
        estimated_score = float(student.get("estimated_score") or 0)
        if estimated_score > 0:
            filters.append("mas.min_score BETWEEN ? AND ?")
            params.extend([estimated_score - 35, estimated_score + 60])

    with db_session() as connection:
        rows = connection.execute(
            f"""
            SELECT
                mas.exam_year,
                mas.subject_track,
                mas.batch_code,
                mas.min_score,
                mas.min_rank,
                mas.avg_score,
                mas.avg_rank,
                i.institution_name,
                i.city,
                i.institution_level,
                i.institution_tags,
                m.major_name
            FROM major_admission_scores mas
            JOIN institutions i ON i.id = mas.institution_id
            JOIN majors m ON m.id = mas.major_id
            WHERE {' AND '.join(filters)}
            ORDER BY mas.exam_year DESC, mas.min_rank ASC, i.institution_name ASC
            LIMIT 8000
            """,
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def _select_demo_bucket(
    candidates: list[dict[str, Any]],
    bucket_key: str,
    major_keywords: list[str],
    preferred_cities: list[str],
) -> list[dict[str, Any]]:
    filtered = [candidate for candidate in candidates if candidate.get("bucket_key") == bucket_key]
    if bucket_key == "safe":
        filtered.sort(
            key=lambda item: (
                -int(item.get("rank_delta") or 0),
                -_score_demo_candidate(item, bucket_key, major_keywords, preferred_cities),
                -int(item.get("exam_year") or 0),
                str(item.get("institution_name") or ""),
            )
        )
    else:
        filtered.sort(
            key=lambda item: (
                -_score_demo_candidate(item, bucket_key, major_keywords, preferred_cities),
                -int(item.get("exam_year") or 0),
                abs(int(item.get("rank_delta") or 0)),
                str(item.get("institution_name") or ""),
            )
        )

    selected: list[dict[str, Any]] = []
    used_institutions: set[str] = set()
    for item in filtered:
        institution_name = str(item.get("institution_name") or "")
        if not institution_name or institution_name in used_institutions:
            continue
        used_institutions.add(institution_name)
        selected.append(item)
        if len(selected) == 3:
            break

    if len(selected) < 3:
        if bucket_key == "rush":
            overflow = [
                candidate
                for candidate in candidates
                if candidate.get("bucket_key") != bucket_key and (candidate.get("rank_delta") is None or int(candidate["rank_delta"]) <= 6000)
            ]
        elif bucket_key == "steady":
            overflow = [
                candidate
                for candidate in candidates
                if candidate.get("bucket_key") != bucket_key and (candidate.get("rank_delta") is None or -3000 <= int(candidate["rank_delta"]) <= 22000)
            ]
        else:
            overflow = [
                candidate
                for candidate in candidates
                if candidate.get("bucket_key") != bucket_key and (candidate.get("rank_delta") is None or int(candidate["rank_delta"]) > 0)
            ]
        overflow.sort(
            key=lambda item: (
                -_score_demo_candidate(item, bucket_key, major_keywords, preferred_cities),
                -int(item.get("exam_year") or 0),
                abs(int(item.get("rank_delta") or 0)),
                str(item.get("institution_name") or ""),
            )
        )
        for item in overflow:
            institution_name = str(item.get("institution_name") or "")
            if not institution_name or institution_name in used_institutions:
                continue
            used_institutions.add(institution_name)
            fallback_item = dict(item)
            fallback_item["bucket_key"] = bucket_key
            fallback_item["match_level"] = {"rush": "冲刺", "steady": "稳妥", "safe": "保底"}[bucket_key]
            selected.append(fallback_item)
            if len(selected) == 3:
                break

    return selected[:3]


def _build_demo_volunteer_recommendation(
    student: dict[str, Any],
    major_rows: list[dict[str, Any]],
    city_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    preferred_cities = _unique_non_empty([row.get("city_name") or "" for row in city_rows])
    major_keywords = _build_demo_major_keywords(student, major_rows)
    pool = _fetch_demo_recommendation_pool(student)

    normalized_candidates: list[dict[str, Any]] = []
    estimated_rank = int(student.get("estimated_rank") or 0) or None
    estimated_score = float(student.get("estimated_score") or 0) or None
    for row in pool:
        min_rank = int(row["min_rank"]) if row.get("min_rank") is not None else None
        min_score = float(row["min_score"]) if row.get("min_score") is not None else None
        rank_delta = (min_rank - estimated_rank) if min_rank is not None and estimated_rank is not None else None
        score_delta = (estimated_score - min_score) if min_score is not None and estimated_score is not None else None
        bucket_key, match_level = _classify_demo_match_level(rank_delta, score_delta)
        normalized_candidates.append(
            {
                **row,
                "rank_delta": rank_delta,
                "score_delta": score_delta,
                "bucket_key": bucket_key,
                "match_level": match_level,
            }
        )

    rush_rows = _select_demo_bucket(normalized_candidates, "rush", major_keywords, preferred_cities)
    steady_rows = _select_demo_bucket(normalized_candidates, "steady", major_keywords, preferred_cities)
    safe_rows = _select_demo_bucket(normalized_candidates, "safe", major_keywords, preferred_cities)

    def format_rows(rows: list[dict[str, Any]], level_label: str) -> list[dict[str, Any]]:
        return [
            {
                "institution_name": row.get("institution_name") or "待补充院校",
                "recommended_major": row.get("major_name") or "待补充专业",
                "recommended_reason": _build_demo_reason(student, row, level_label, preferred_cities),
                "risk_tip": _build_demo_risk_tip(row, level_label),
                "match_level": level_label,
                "historical_min_score": row.get("min_score"),
                "historical_min_rank": row.get("min_rank"),
                "admission_year": row.get("exam_year"),
            }
            for row in rows
        ]

    rush = format_rows(rush_rows, "冲刺")
    steady = format_rows(steady_rows, "稳妥")
    safe = format_rows(safe_rows, "保底")
    ordered_recommendations = [*rush, *steady, *safe]
    first_choice = steady[0] if steady else rush[0] if rush else safe[0] if safe else None

    if first_choice is None:
        return {
            "title": "具体志愿推荐方案",
            "rush": [],
            "steady": [],
            "safe": [],
            "first_choice_advice": "当前暂无足够的河南院校候选数据，建议先补充近年位次与专业录取样本后再生成首选方案。",
            "final_order_advice": "建议优先补齐院校录取位次数据后，再输出正式的冲稳保顺序。",
            "ordered_recommendations": [],
        }

    first_choice_advice = (
        f"第一志愿建议优先考虑 {first_choice['institution_name']} - {first_choice['recommended_major']}，"
        f"把它放在稳妥组最前，有利于兼顾专业匹配和录取安全边界。"
    )
    final_order_text = " → ".join(
        f"{index}. {item['institution_name']}（{item['recommended_major']}）"
        for index, item in enumerate(ordered_recommendations, start=1)
    )
    final_order_advice = (
        "最终志愿顺序建议按“先冲 3 所、再稳 3 所、最后保 3 所”的结构排布，"
        f"组内优先按专业匹配度排序。建议顺序：{final_order_text}。"
    )

    return {
        "title": "具体志愿推荐方案",
        "rush": rush,
        "steady": steady,
        "safe": safe,
        "first_choice_advice": first_choice_advice,
        "final_order_advice": final_order_advice,
        "ordered_recommendations": ordered_recommendations,
    }


def _score_level(student: dict[str, Any]) -> tuple[str, str]:
    score = float(student.get("estimated_score") or 0)
    if score >= 630:
        return "高分冲刺段", "可在名校与强专业之间做组合比较，但仍要控制冲刺比例。"
    if score >= 600:
        return "高分稳进段", "更适合做城市、专业与院校层次的三角平衡，保持稳中带冲。"
    if score >= 560:
        return "中上稳妥段", "宜优先保障专业适配度，再适度争取平台与城市资源。"
    if score >= 520:
        return "中段优化段", "要更重视保底和专业接受度，避免只看学校名气。"
    return "基础保稳段", "建议把滑档风险控制放在前面，确保结果可接受。"


def _build_element_summary(auxiliary_tendency: str | None) -> dict[str, str]:
    tags = _parse_element_tags(auxiliary_tendency)
    rules = [ELEMENT_RULES[tag] for tag in tags if tag in ELEMENT_RULES]
    if not rules:
        return {
            "trait": "当前以前六字辅助倾向做演示解读，实际使用时仍需结合学生真实表现校验。",
            "learning": "建议以学生平时学习习惯和反馈节奏为主做判断。",
            "city": "城市建议仍应结合家庭预算、距离、产业机会和学生意愿。",
            "avoid": "不建议把任何辅助标签当成唯一决策依据。",
            "parent": "建议家长把辅助结论作为沟通切口，而不是定论。",
        }

    return {
        "trait": "；".join(rule["trait"] for rule in rules),
        "learning": "；".join(rule["learning"] for rule in rules),
        "city": "；".join(rule["city"] for rule in rules),
        "avoid": "；".join(rule["avoid"] for rule in rules),
        "parent": "；".join(rule["parent"] for rule in rules),
    }


def _build_one_sentence_advice(student: dict[str, Any], major_rows: list[dict[str, Any]], city_rows: list[dict[str, Any]]) -> str:
    major_name = major_rows[0]["category_name"] if major_rows else "适配专业"
    city_name = city_rows[0]["city_name"] if city_rows else "目标城市"
    family_focus = student.get("family_focus") or "综合平衡"
    return (
        f"优先围绕“{major_name} + {city_name}”做稳中带冲组合，同时把“{family_focus}”作为最终筛选条件。"
    )


def _build_risk_notice(student: dict[str, Any], major_rows: list[dict[str, Any]]) -> list[str]:
    risk_items = [row.get("risk_notes") for row in major_rows if row.get("risk_notes")]
    notices = []
    if student.get("estimated_rank"):
        notices.append("当前位次为样例预估值，正式方案必须以当年官方位次和一分一段表复核。")
    if risk_items:
        notices.append(f"专业方向风险提示：{'；'.join(risk_items[:2])}。")
    notices.append("城市、专业和院校选择都需要与家庭预算、地域接受度和学生真实意愿交叉确认。")
    notices.append(COMPLIANCE_DISCLAIMER)
    return notices


def generate_demo_report(sample_student_id: int, product_code: str) -> dict[str, Any]:
    if product_code not in REPORT_PRODUCT_LABELS:
        raise HTTPException(status_code=400, detail="Unsupported report product")

    student = _fetch_sample_student_or_404(sample_student_id)
    template_modules = _fetch_template_modules(product_code)
    major_rows = _match_major_categories(student)
    city_rows = _match_city_industries(student)
    volunteer_recommendation = _build_demo_volunteer_recommendation(student, major_rows, city_rows)
    element_summary = _build_element_summary(student.get("auxiliary_tendency"))
    score_level, score_comment = _score_level(student)
    one_sentence_advice = _build_one_sentence_advice(student, major_rows, city_rows)
    risk_notices = _build_risk_notice(student, major_rows)

    major_names = [row["category_name"] for row in major_rows]
    city_names = [row["city_name"] for row in city_rows]
    common_summary = (
        f"{student['name']}，{student.get('province') or '未知省份'}考生，"
        f"选科/科类为{student.get('subject_track') or '待确认'}，"
        f"样例预估分{student.get('estimated_score') or '待确认'}，"
        f"样例预估位次{student.get('estimated_rank') or '待确认'}。"
    )

    if product_code == "99":
        sections = [
            {
                "title": "学生基础信息",
                "body": common_summary,
                "bullets": [
                    f"性格标签：{student.get('personality_tags') or '待补充'}",
                    f"地域偏好：{student.get('region_preference') or '待补充'}",
                    f"家庭关注点：{student.get('family_focus') or '待补充'}",
                ],
            },
            {
                "title": "性格与学习方式画像",
                "body": f"{student.get('personality_tags') or '暂无标签'}，结合样例分层判断，当前更适合“稳节奏、强反馈、可复盘”的学习推进方式。",
                "bullets": [
                    element_summary["trait"],
                    element_summary["learning"],
                ],
            },
            {
                "title": "前六字/五行辅助分析",
                "body": f"辅助倾向为 {student.get('auxiliary_tendency') or '待补充'}，仅作辅助理解，不作为唯一决策依据。",
                "bullets": [
                    element_summary["trait"],
                    element_summary["city"],
                ],
            },
            {
                "title": "适合专业方向",
                "body": f"优先关注：{'、'.join(major_names[:3]) or '待确认'}。",
                "bullets": [row.get("representative_majors") or "" for row in major_rows[:3]],
            },
            {
                "title": "不建议盲选方向",
                "body": "以下内容用于提醒“看起来热门但未必适配”的风险点。",
                "bullets": [element_summary["avoid"], *(row.get("risk_notes") or "" for row in major_rows[:2])],
            },
            {
                "title": "城市与环境建议",
                "body": f"优先考虑 {'、'.join(city_names[:3]) or '待确认'} 这类更匹配学生节奏与产业机会的城市。",
                "bullets": [
                    *(f"{row['city_name']}：{row.get('leading_industries') or '产业信息待补充'}" for row in city_rows[:3]),
                    element_summary["city"],
                ],
            },
            {
                "title": "家长沟通建议",
                "body": "家长沟通重点应从“孩子是否适配”出发，而不是只看热门程度。",
                "bullets": [
                    element_summary["parent"],
                    f"建议产品：{student.get('suggested_product') or '待确认'}，样例策略：{student.get('strategy_type') or '待确认'}。",
                ],
            },
            {
                "title": "一句话建议",
                "body": one_sentence_advice,
                "bullets": [COMPLIANCE_DISCLAIMER],
                "warning": True,
            },
        ]
    else:
        sections = [
            {
                "title": "学生画像总览",
                "body": common_summary,
                "bullets": [
                    f"性格标签：{student.get('personality_tags') or '待补充'}",
                    f"建议策略：{student.get('strategy_type') or '待补充'}",
                    f"建议产品：{student.get('suggested_product') or '待补充'}",
                ],
            },
            {
                "title": "前六字与性格分析",
                "body": f"辅助倾向为 {student.get('auxiliary_tendency') or '待补充'}，用于辅助理解学生节奏、表达方式和环境适配度。",
                "bullets": [
                    element_summary["trait"],
                    element_summary["learning"],
                    element_summary["avoid"],
                ],
            },
            {
                "title": "学科能力与专业方向",
                "body": f"结合样例标签与推荐方向，当前更适合 {'、'.join(major_names[:4]) or '待确认'}。",
                "bullets": [row.get("subject_requirement_reference") or "" for row in major_rows[:3]],
            },
            {
                "title": "分数与位次初步判断",
                "body": f"当前位于“{score_level}”，{score_comment}",
                "bullets": [
                    f"样例预估分：{student.get('estimated_score') or '待确认'}",
                    f"样例预估位次：{student.get('estimated_rank') or '待确认'}",
                ],
            },
            {
                "title": "可考虑专业大类",
                "body": "以下为优先考虑的大类方向，仍需结合选科要求、院校专业组和招生计划复核。",
                "bullets": [
                    *(f"{row['category_name']}：{row.get('career_paths') or row.get('representative_majors') or ''}" for row in major_rows[:4]),
                ],
            },
            {
                "title": "城市与区域建议",
                "body": f"可优先看 {'、'.join(city_names[:4]) or '待确认'} 等区域。",
                "bullets": [
                    *(f"{row['city_name']}：{row.get('suitable_major_directions') or ''}；风险：{row.get('risk_tips') or '需复核'}" for row in city_rows[:4]),
                ],
            },
            {
                "title": "冲稳保思路",
                "body": f"围绕“{student.get('strategy_type') or '稳中带冲'}”配置志愿结构，主体以稳与保为主，冲刺位次只做少量尝试。",
                "bullets": [
                    "冲：少量争取上限，但不能影响整体安全性。",
                    "稳：以适配专业和可接受城市作为主体。",
                    "保：确保结果可接受，避免只为保底而忽略专业体验。",
                ],
            },
            {
                "title": "名校/专业取舍策略",
                "body": "当学校平台和专业适配发生冲突时，优先看学生长期学习意愿和行业匹配度。",
                "bullets": [
                    f"家庭关注点：{student.get('family_focus') or '综合平衡'}",
                    "若要冲名校，必须评估是否接受调剂、冷门专业或后续转专业难度。",
                ],
            },
            {
                "title": "家长沟通建议",
                "body": "建议先统一“底线要求”，再讨论院校层次、专业热度和城市资源。",
                "bullets": [
                    element_summary["parent"],
                    "沟通时尽量把“热门”转换成“是否适合、是否能坚持、是否有后续路径”。",
                ],
            },
            {
                "title": "未来发展路径",
                "body": "从本科阶段就要预留继续深造、技能证书、项目经历和城市实习的成长通道。",
                "bullets": [
                    f"可围绕 {'、'.join(major_names[:2]) or '目标专业'} 提前了解课程难度、考研需求和就业方向。",
                    f"城市优先级可参考 {'、'.join(city_names[:2]) or '目标城市'} 的产业资源和实习机会。",
                ],
            },
            {
                "title": "风险提醒与免责声明",
                "body": "以下提醒必须在正式交付前再次核验。",
                "bullets": risk_notices,
                "warning": True,
            },
        ]

    return {
        "sample_student": student,
        "product_code": product_code,
        "product_label": REPORT_PRODUCT_LABELS[product_code],
        "report_title": f"{student['name']} - {REPORT_PRODUCT_LABELS[product_code]}",
        "report_summary": one_sentence_advice,
        "template_modules": template_modules,
        "matched_major_categories": major_rows,
        "matched_city_industries": city_rows,
        "volunteer_recommendation": volunteer_recommendation,
        "sections": sections,
        "disclaimer": COMPLIANCE_DISCLAIMER,
        "boundary_note": INTERFACE_BOUNDARY_NOTE,
    }
