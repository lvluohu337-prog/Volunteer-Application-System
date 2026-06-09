from __future__ import annotations

from typing import Any

from backend.database import ADMISSIONS_CORE_TABLES, db_session, get_table_columns
from backend.repository import normalize_text, now_text
import json


ADMISSIONS_TABLE_FIELDS = {
    "institutions": ["institution_code", "institution_name", "province", "city", "institution_level"],
    "majors": ["major_code", "major_name", "major_category", "degree_level"],
    "province_batches": ["exam_year", "province", "subject_track", "batch_code", "batch_name"],
    "score_segments": ["exam_year", "province", "subject_track", "score_text", "cumulative_count"],
    "admission_plans": ["exam_year", "province", "institution_id", "major_id", "planned_count"],
    "institution_admission_scores": ["exam_year", "province", "institution_id", "min_score", "min_rank"],
    "major_admission_scores": ["exam_year", "province", "institution_id", "major_id", "min_score", "min_rank"],
    "subject_requirements": ["exam_year", "province", "institution_id", "major_id", "requirement_text"],
    "institution_rules": ["exam_year", "province", "institution_id", "rule_type", "rule_title"],
    "admission_risk_rules": ["exam_year", "province", "institution_id", "major_id", "risk_type"],
    "policy_trends": ["exam_year", "province", "policy_key", "policy_title", "trend_type"],
}


def _serialize_row(row: dict[str, Any]) -> str:
    return json.dumps(row, ensure_ascii=False, separators=(",", ":"))


def _key_text(value: Any) -> str:
    return normalize_text(value) or ""


def _table_count(connection, table_name: str) -> int:
    row = connection.execute(f"SELECT COUNT(*) AS total FROM {table_name}").fetchone()
    return int(row["total"]) if row else 0


def _table_columns(connection, table_name: str) -> list[str]:
    del connection
    return get_table_columns(table_name)


def get_admissions_schema_overview() -> dict[str, Any]:
    with db_session() as connection:
        tables = []
        for table_name, label in ADMISSIONS_CORE_TABLES.items():
            columns = _table_columns(connection, table_name)
            tables.append(
                {
                    "table_name": table_name,
                    "label": label,
                    "row_count": _table_count(connection, table_name),
                    "column_count": len(columns),
                    "key_fields": ADMISSIONS_TABLE_FIELDS.get(table_name, []),
                    "columns": columns,
                    "status": "ready",
                }
            )

    return {
        "table_count": len(tables),
        "tables": tables,
        "notes": [
            "当前阶段已完成招生核心表结构落地，下一步应补正式导入模板、字段映射和 upsert 逻辑。",
            "这些表是后续位次筛选、选科过滤、录取概率与招生计划风险判断的基础数据层。",
        ],
    }


def _build_institution_lookup(connection) -> dict[tuple[str | None, str | None], int]:
    rows = connection.execute(
        "SELECT id, institution_code, institution_name FROM institutions"
    ).fetchall()
    return {
        (_key_text(row["institution_code"]), _key_text(row["institution_name"])): int(row["id"])
        for row in rows
    }


def _build_institution_name_lookup(connection) -> dict[str, int]:
    rows = connection.execute(
        "SELECT id, institution_name FROM institutions"
    ).fetchall()
    lookup: dict[str, int] = {}
    for row in rows:
        name = _key_text(row["institution_name"])
        if name and name not in lookup:
            lookup[name] = int(row["id"])
    return lookup


def _build_major_lookup(connection) -> dict[tuple[str | None, str | None], int]:
    rows = connection.execute(
        "SELECT id, major_code, major_name FROM majors"
    ).fetchall()
    return {
        (_key_text(row["major_code"]), _key_text(row["major_name"])): int(row["id"])
        for row in rows
    }


def _build_major_name_lookup(connection) -> dict[str, int]:
    rows = connection.execute(
        "SELECT id, major_name FROM majors"
    ).fetchall()
    lookup: dict[str, int] = {}
    for row in rows:
        name = _key_text(row["major_name"])
        if name and name not in lookup:
            lookup[name] = int(row["id"])
    return lookup


def _build_subject_requirement_lookup(connection) -> dict[tuple[Any, ...], int]:
    rows = connection.execute(
        """
        SELECT id, exam_year, province, institution_id, major_id, requirement_code
        FROM subject_requirements
        """
    ).fetchall()
    return {
        (
            row["exam_year"],
            _key_text(row["province"]),
            row["institution_id"],
            row["major_id"],
            _key_text(row["requirement_code"]),
        ): int(row["id"])
        for row in rows
    }


def _find_subject_requirement_without_major(
    connection,
    exam_year: Any,
    province: str,
    institution_id: int | None,
    requirement_code: str,
    requirement_text: str,
) -> int | None:
    row = connection.execute(
        """
        SELECT id
        FROM subject_requirements
        WHERE exam_year = ?
          AND province = ?
          AND institution_id = ?
          AND major_id IS NULL
          AND requirement_code = ?
          AND requirement_text = ?
        LIMIT 1
        """,
        [
            exam_year,
            province,
            institution_id,
            requirement_code,
            requirement_text,
        ],
    ).fetchone()
    return int(row["id"]) if row else None


def upsert_institutions(rows: list[dict[str, Any]]) -> int:
    timestamp = now_text()
    processed = 0
    with db_session() as connection:
        for row in rows:
            code = _key_text(row.get("institution_code"))
            name = normalize_text(row.get("institution_name"))
            if not name:
                continue
            connection.execute(
                """
                INSERT INTO institutions (
                    institution_code,
                    institution_name,
                    institution_short_name,
                    institution_type,
                    institution_level,
                    institution_tags,
                    affiliation,
                    public_private,
                    province,
                    city,
                    campus_city,
                    website_url,
                    admission_office_phone,
                    overview,
                    raw_json,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(institution_code, institution_name) DO UPDATE SET
                    institution_short_name = excluded.institution_short_name,
                    institution_type = excluded.institution_type,
                    institution_level = excluded.institution_level,
                    institution_tags = excluded.institution_tags,
                    affiliation = excluded.affiliation,
                    public_private = excluded.public_private,
                    province = excluded.province,
                    city = excluded.city,
                    campus_city = excluded.campus_city,
                    website_url = excluded.website_url,
                    admission_office_phone = excluded.admission_office_phone,
                    overview = excluded.overview,
                    raw_json = excluded.raw_json,
                    updated_at = excluded.updated_at
                """,
                [
                    code,
                    name,
                    normalize_text(row.get("institution_short_name")),
                    normalize_text(row.get("institution_type")),
                    normalize_text(row.get("institution_level")),
                    normalize_text(row.get("institution_tags")),
                    normalize_text(row.get("affiliation")),
                    normalize_text(row.get("public_private")),
                    normalize_text(row.get("province")),
                    normalize_text(row.get("city")),
                    normalize_text(row.get("campus_city")),
                    normalize_text(row.get("website_url")),
                    normalize_text(row.get("admission_office_phone")),
                    normalize_text(row.get("overview")),
                    _serialize_row(row),
                    timestamp,
                    timestamp,
                ],
            )
            processed += 1
    return processed


def upsert_majors(rows: list[dict[str, Any]]) -> int:
    timestamp = now_text()
    processed = 0
    with db_session() as connection:
        for row in rows:
            code = _key_text(row.get("major_code"))
            name = normalize_text(row.get("major_name"))
            if not name:
                continue
            connection.execute(
                """
                INSERT INTO majors (
                    major_code,
                    major_name,
                    major_category,
                    degree_level,
                    study_years,
                    degree_awarded,
                    discipline_tags,
                    study_features,
                    employment_directions,
                    raw_json,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(major_code, major_name) DO UPDATE SET
                    major_category = excluded.major_category,
                    degree_level = excluded.degree_level,
                    study_years = excluded.study_years,
                    degree_awarded = excluded.degree_awarded,
                    discipline_tags = excluded.discipline_tags,
                    study_features = excluded.study_features,
                    employment_directions = excluded.employment_directions,
                    raw_json = excluded.raw_json,
                    updated_at = excluded.updated_at
                """,
                [
                    code,
                    name,
                    normalize_text(row.get("major_category")),
                    normalize_text(row.get("degree_level")),
                    normalize_text(row.get("study_years")),
                    normalize_text(row.get("degree_awarded")),
                    normalize_text(row.get("discipline_tags")),
                    normalize_text(row.get("study_features")),
                    normalize_text(row.get("employment_directions")),
                    _serialize_row(row),
                    timestamp,
                    timestamp,
                ],
            )
            processed += 1
    return processed


def upsert_province_batches(rows: list[dict[str, Any]]) -> int:
    timestamp = now_text()
    processed = 0
    with db_session() as connection:
        for row in rows:
            batch_code = _key_text(row.get("batch_code"))
            batch_name = normalize_text(row.get("batch_name"))
            if not batch_code or not batch_name:
                continue
            connection.execute(
                """
                INSERT INTO province_batches (
                    exam_year,
                    province,
                    exam_type,
                    subject_track,
                    batch_code,
                    batch_name,
                    score_line,
                    rank_line,
                    notes,
                    raw_json,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(exam_year, province, exam_type, subject_track, batch_code) DO UPDATE SET
                    batch_name = excluded.batch_name,
                    score_line = excluded.score_line,
                    rank_line = excluded.rank_line,
                    notes = excluded.notes,
                    raw_json = excluded.raw_json,
                    updated_at = excluded.updated_at
                """,
                [
                    row.get("exam_year"),
                    _key_text(row.get("province")),
                    normalize_text(row.get("exam_type")) or "gaokao",
                    normalize_text(row.get("subject_track")),
                    batch_code,
                    batch_name,
                    row.get("score_line"),
                    row.get("rank_line"),
                    normalize_text(row.get("notes")),
                    _serialize_row(row),
                    timestamp,
                    timestamp,
                ],
            )
            processed += 1
    return processed


def upsert_score_segments(rows: list[dict[str, Any]]) -> int:
    timestamp = now_text()
    processed = 0
    with db_session() as connection:
        for row in rows:
            score_text = normalize_text(row.get("score_text"))
            if not score_text:
                continue
            connection.execute(
                """
                INSERT INTO score_segments (
                    exam_year,
                    province,
                    exam_type,
                    subject_track,
                    batch_code,
                    control_line,
                    score_text,
                    score_value,
                    segment_count,
                    cumulative_count,
                    rank_range,
                    historical_same_rank_score,
                    raw_json,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(exam_year, province, exam_type, subject_track, batch_code, score_text) DO UPDATE SET
                    control_line = excluded.control_line,
                    score_value = excluded.score_value,
                    segment_count = excluded.segment_count,
                    cumulative_count = excluded.cumulative_count,
                    rank_range = excluded.rank_range,
                    historical_same_rank_score = excluded.historical_same_rank_score,
                    raw_json = excluded.raw_json,
                    updated_at = excluded.updated_at
                """,
                [
                    row.get("exam_year"),
                    _key_text(row.get("province")),
                    normalize_text(row.get("exam_type")) or "gaokao",
                    _key_text(row.get("subject_track")),
                    _key_text(row.get("batch_code")),
                    row.get("control_line"),
                    score_text,
                    row.get("score_value"),
                    row.get("segment_count"),
                    row.get("cumulative_count"),
                    normalize_text(row.get("rank_range")),
                    normalize_text(row.get("historical_same_rank_score")),
                    _serialize_row(row),
                    timestamp,
                    timestamp,
                ],
            )
            processed += 1
    return processed


def upsert_subject_requirements(rows: list[dict[str, Any]]) -> int:
    timestamp = now_text()
    processed = 0
    with db_session() as connection:
        institution_lookup = _build_institution_lookup(connection)
        major_lookup = _build_major_lookup(connection)
        for row in rows:
            requirement_text = normalize_text(row.get("requirement_text"))
            if not requirement_text:
                continue
            province = _key_text(row.get("province"))
            requirement_code = _key_text(row.get("requirement_code"))
            institution_id = institution_lookup.get(
                (
                    _key_text(row.get("institution_code")),
                    _key_text(row.get("institution_name")),
                )
            )
            major_id = major_lookup.get(
                (
                    _key_text(row.get("major_code")),
                    _key_text(row.get("major_name")),
                )
            )
            if major_id is None:
                existing_id = _find_subject_requirement_without_major(
                    connection,
                    row.get("exam_year"),
                    province,
                    institution_id,
                    requirement_code,
                    requirement_text,
                )
                if existing_id is not None:
                    connection.execute(
                        """
                        UPDATE subject_requirements
                        SET subject_track = ?,
                            requirement_text = ?,
                            required_subjects = ?,
                            optional_subjects = ?,
                            forbidden_subjects = ?,
                            match_mode = ?,
                            notes = ?,
                            raw_json = ?,
                            updated_at = ?
                        WHERE id = ?
                        """,
                        [
                            normalize_text(row.get("subject_track")),
                            requirement_text,
                            normalize_text(row.get("required_subjects")),
                            normalize_text(row.get("optional_subjects")),
                            normalize_text(row.get("forbidden_subjects")),
                            normalize_text(row.get("match_mode")),
                            normalize_text(row.get("notes")),
                            _serialize_row(row),
                            timestamp,
                            existing_id,
                        ],
                    )
                    processed += 1
                    continue
            connection.execute(
                """
                INSERT INTO subject_requirements (
                    exam_year,
                    province,
                    subject_track,
                    institution_id,
                    major_id,
                    requirement_code,
                    requirement_text,
                    required_subjects,
                    optional_subjects,
                    forbidden_subjects,
                    match_mode,
                    notes,
                    raw_json,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(exam_year, province, institution_id, major_id, requirement_code) DO UPDATE SET
                    requirement_text = excluded.requirement_text,
                    required_subjects = excluded.required_subjects,
                    optional_subjects = excluded.optional_subjects,
                    forbidden_subjects = excluded.forbidden_subjects,
                    match_mode = excluded.match_mode,
                    notes = excluded.notes,
                    raw_json = excluded.raw_json,
                    updated_at = excluded.updated_at
                """,
                [
                    row.get("exam_year"),
                    province,
                    normalize_text(row.get("subject_track")),
                    institution_id,
                    major_id,
                    requirement_code,
                    requirement_text,
                    normalize_text(row.get("required_subjects")),
                    normalize_text(row.get("optional_subjects")),
                    normalize_text(row.get("forbidden_subjects")),
                    normalize_text(row.get("match_mode")),
                    normalize_text(row.get("notes")),
                    _serialize_row(row),
                    timestamp,
                    timestamp,
                ],
            )
            processed += 1
    return processed


def upsert_admission_plans(rows: list[dict[str, Any]]) -> int:
    timestamp = now_text()
    processed = 0
    with db_session() as connection:
        institution_lookup = _build_institution_lookup(connection)
        major_lookup = _build_major_lookup(connection)
        subject_lookup = _build_subject_requirement_lookup(connection)
        for row in rows:
            institution_id = institution_lookup.get(
                (
                    _key_text(row.get("institution_code")),
                    _key_text(row.get("institution_name")),
                )
            )
            if not institution_id:
                continue
            major_id = major_lookup.get(
                (
                    _key_text(row.get("major_code")),
                    _key_text(row.get("major_name")),
                )
            )
            requirement_key = (
                row.get("exam_year"),
                _key_text(row.get("province")),
                institution_id,
                major_id,
                _key_text(row.get("requirement_code")),
            )
            subject_requirement_id = subject_lookup.get(requirement_key)
            connection.execute(
                """
                INSERT INTO admission_plans (
                    exam_year,
                    province,
                    exam_type,
                    subject_track,
                    batch_code,
                    institution_id,
                    major_id,
                    plan_group_code,
                    plan_group_name,
                    subject_requirement_id,
                    planned_count,
                    tuition_yearly,
                    study_years,
                    campus_city,
                    plan_notes,
                    raw_json,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(exam_year, province, institution_id, major_id, batch_code, plan_group_code) DO UPDATE SET
                    exam_type = excluded.exam_type,
                    subject_track = excluded.subject_track,
                    plan_group_name = excluded.plan_group_name,
                    subject_requirement_id = excluded.subject_requirement_id,
                    planned_count = excluded.planned_count,
                    tuition_yearly = excluded.tuition_yearly,
                    study_years = excluded.study_years,
                    campus_city = excluded.campus_city,
                    plan_notes = excluded.plan_notes,
                    raw_json = excluded.raw_json,
                    updated_at = excluded.updated_at
                """,
                [
                    row.get("exam_year"),
                    _key_text(row.get("province")),
                    normalize_text(row.get("exam_type")) or "gaokao",
                    normalize_text(row.get("subject_track")),
                    _key_text(row.get("batch_code")),
                    institution_id,
                    major_id,
                    _key_text(row.get("plan_group_code")),
                    normalize_text(row.get("plan_group_name")),
                    subject_requirement_id,
                    row.get("planned_count"),
                    row.get("tuition_yearly"),
                    normalize_text(row.get("study_years")),
                    normalize_text(row.get("campus_city")),
                    normalize_text(row.get("plan_notes")),
                    _serialize_row(row),
                    timestamp,
                    timestamp,
                ],
            )
            processed += 1
    return processed


def upsert_institution_admission_scores(rows: list[dict[str, Any]]) -> int:
    timestamp = now_text()
    processed = 0
    with db_session() as connection:
        institution_lookup = _build_institution_lookup(connection)
        for row in rows:
            institution_id = institution_lookup.get(
                (
                    _key_text(row.get("institution_code")),
                    _key_text(row.get("institution_name")),
                )
            )
            if not institution_id:
                continue
            connection.execute(
                """
                INSERT INTO institution_admission_scores (
                    exam_year,
                    province,
                    exam_type,
                    subject_track,
                    batch_code,
                    institution_id,
                    min_score,
                    min_rank,
                    avg_score,
                    avg_rank,
                    max_score,
                    max_rank,
                    planned_count,
                    admitted_count,
                    score_line,
                    notes,
                    raw_json,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(exam_year, province, institution_id, batch_code, subject_track) DO UPDATE SET
                    exam_type = excluded.exam_type,
                    min_score = excluded.min_score,
                    min_rank = excluded.min_rank,
                    avg_score = excluded.avg_score,
                    avg_rank = excluded.avg_rank,
                    max_score = excluded.max_score,
                    max_rank = excluded.max_rank,
                    planned_count = excluded.planned_count,
                    admitted_count = excluded.admitted_count,
                    score_line = excluded.score_line,
                    notes = excluded.notes,
                    raw_json = excluded.raw_json,
                    updated_at = excluded.updated_at
                """,
                [
                    row.get("exam_year"),
                    _key_text(row.get("province")),
                    normalize_text(row.get("exam_type")) or "gaokao",
                    _key_text(row.get("subject_track")),
                    _key_text(row.get("batch_code")),
                    institution_id,
                    row.get("min_score"),
                    row.get("min_rank"),
                    row.get("avg_score"),
                    row.get("avg_rank"),
                    row.get("max_score"),
                    row.get("max_rank"),
                    row.get("planned_count"),
                    row.get("admitted_count"),
                    row.get("score_line"),
                    normalize_text(row.get("notes")),
                    _serialize_row(row),
                    timestamp,
                    timestamp,
                ],
            )
            processed += 1
    return processed


def upsert_major_admission_scores(rows: list[dict[str, Any]]) -> int:
    timestamp = now_text()
    processed = 0
    with db_session() as connection:
        institution_lookup = _build_institution_lookup(connection)
        major_lookup = _build_major_lookup(connection)
        for row in rows:
            institution_id = institution_lookup.get(
                (
                    _key_text(row.get("institution_code")),
                    _key_text(row.get("institution_name")),
                )
            )
            major_id = major_lookup.get(
                (
                    _key_text(row.get("major_code")),
                    _key_text(row.get("major_name")),
                )
            )
            if not institution_id or not major_id:
                continue
            connection.execute(
                """
                INSERT INTO major_admission_scores (
                    exam_year,
                    province,
                    exam_type,
                    subject_track,
                    batch_code,
                    institution_id,
                    major_id,
                    plan_group_code,
                    min_score,
                    min_rank,
                    avg_score,
                    avg_rank,
                    max_score,
                    max_rank,
                    planned_count,
                    admitted_count,
                    notes,
                    raw_json,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(exam_year, province, institution_id, major_id, batch_code, subject_track, plan_group_code) DO UPDATE SET
                    exam_type = excluded.exam_type,
                    min_score = excluded.min_score,
                    min_rank = excluded.min_rank,
                    avg_score = excluded.avg_score,
                    avg_rank = excluded.avg_rank,
                    max_score = excluded.max_score,
                    max_rank = excluded.max_rank,
                    planned_count = excluded.planned_count,
                    admitted_count = excluded.admitted_count,
                    notes = excluded.notes,
                    raw_json = excluded.raw_json,
                    updated_at = excluded.updated_at
                """,
                [
                    row.get("exam_year"),
                    _key_text(row.get("province")),
                    normalize_text(row.get("exam_type")) or "gaokao",
                    _key_text(row.get("subject_track")),
                    _key_text(row.get("batch_code")),
                    institution_id,
                    major_id,
                    _key_text(row.get("plan_group_code")),
                    row.get("min_score"),
                    row.get("min_rank"),
                    row.get("avg_score"),
                    row.get("avg_rank"),
                    row.get("max_score"),
                    row.get("max_rank"),
                    row.get("planned_count"),
                    row.get("admitted_count"),
                    normalize_text(row.get("notes")),
                    _serialize_row(row),
                    timestamp,
                    timestamp,
                ],
            )
            processed += 1
    return processed


def upsert_institution_rules(rows: list[dict[str, Any]]) -> int:
    timestamp = now_text()
    processed = 0
    with db_session() as connection:
        institution_lookup = _build_institution_lookup(connection)
        institution_name_lookup = _build_institution_name_lookup(connection)
        for row in rows:
            institution_id = row.get("institution_id")
            if institution_id is not None:
                institution_id = int(institution_id)
            else:
                institution_id = institution_lookup.get(
                    (
                        _key_text(row.get("institution_code")),
                        _key_text(row.get("institution_name")),
                    )
                ) or institution_name_lookup.get(_key_text(row.get("institution_name")))
            if not institution_id:
                continue

            rule_type = normalize_text(row.get("rule_type"))
            rule_content = normalize_text(row.get("rule_content"))
            if not rule_type or not rule_content:
                continue

            connection.execute(
                """
                INSERT INTO institution_rules (
                    exam_year,
                    province,
                    institution_id,
                    rule_type,
                    rule_title,
                    rule_content,
                    source_url,
                    notes,
                    raw_json,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(exam_year, province, institution_id, rule_type, rule_title) DO UPDATE SET
                    rule_content = excluded.rule_content,
                    source_url = excluded.source_url,
                    notes = excluded.notes,
                    raw_json = excluded.raw_json,
                    updated_at = excluded.updated_at
                """,
                [
                    row.get("exam_year"),
                    _key_text(row.get("province")),
                    institution_id,
                    rule_type,
                    normalize_text(row.get("rule_title")),
                    rule_content,
                    normalize_text(row.get("source_url")),
                    normalize_text(row.get("notes")),
                    _serialize_row(row),
                    timestamp,
                    timestamp,
                ],
            )
            processed += 1
    return processed


def upsert_admission_risk_rules(rows: list[dict[str, Any]]) -> int:
    timestamp = now_text()
    processed = 0
    with db_session() as connection:
        institution_lookup = _build_institution_lookup(connection)
        institution_name_lookup = _build_institution_name_lookup(connection)
        major_lookup = _build_major_lookup(connection)
        major_name_lookup = _build_major_name_lookup(connection)
        for row in rows:
            institution_id = row.get("institution_id")
            if institution_id is not None:
                institution_id = int(institution_id)
            else:
                institution_id = institution_lookup.get(
                    (
                        _key_text(row.get("institution_code")),
                        _key_text(row.get("institution_name")),
                    )
                ) or institution_name_lookup.get(_key_text(row.get("institution_name")))

            major_id = row.get("major_id")
            if major_id is not None:
                major_id = int(major_id)
            else:
                major_id = major_lookup.get(
                    (
                        _key_text(row.get("major_code")),
                        _key_text(row.get("major_name")),
                    )
                ) or major_name_lookup.get(_key_text(row.get("major_name")))

            risk_type = normalize_text(row.get("risk_type"))
            risk_message = normalize_text(row.get("risk_message"))
            if not risk_type or not risk_message:
                continue

            connection.execute(
                """
                INSERT INTO admission_risk_rules (
                    exam_year,
                    province,
                    institution_id,
                    major_id,
                    risk_type,
                    risk_level,
                    trigger_condition,
                    risk_message,
                    mitigation_suggestion,
                    raw_json,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(exam_year, province, institution_id, major_id, risk_type, risk_message) DO UPDATE SET
                    risk_level = excluded.risk_level,
                    trigger_condition = excluded.trigger_condition,
                    mitigation_suggestion = excluded.mitigation_suggestion,
                    raw_json = excluded.raw_json,
                    updated_at = excluded.updated_at
                """,
                [
                    row.get("exam_year"),
                    _key_text(row.get("province")),
                    institution_id,
                    major_id,
                    risk_type,
                    normalize_text(row.get("risk_level")),
                    normalize_text(row.get("trigger_condition")),
                    risk_message,
                    normalize_text(row.get("mitigation_suggestion")),
                    _serialize_row(row),
                    timestamp,
                    timestamp,
                ],
            )
            processed += 1
    return processed


def upsert_policy_trends(rows: list[dict[str, Any]]) -> int:
    timestamp = now_text()
    processed = 0
    with db_session() as connection:
        for row in rows:
            policy_key = _key_text(row.get("policy_key"))
            policy_title = normalize_text(row.get("policy_title"))
            trend_summary = normalize_text(row.get("trend_summary"))
            if not policy_key or not policy_title or not trend_summary:
                continue

            connection.execute(
                """
                INSERT INTO policy_trends (
                    exam_year,
                    province,
                    policy_key,
                    policy_title,
                    trend_type,
                    trend_summary,
                    impact_scope,
                    source_url,
                    notes,
                    raw_json,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(exam_year, province, policy_key) DO UPDATE SET
                    policy_title = excluded.policy_title,
                    trend_type = excluded.trend_type,
                    trend_summary = excluded.trend_summary,
                    impact_scope = excluded.impact_scope,
                    source_url = excluded.source_url,
                    notes = excluded.notes,
                    raw_json = excluded.raw_json,
                    updated_at = excluded.updated_at
                """,
                [
                    row.get("exam_year"),
                    _key_text(row.get("province")),
                    policy_key,
                    policy_title,
                    normalize_text(row.get("trend_type")),
                    trend_summary,
                    normalize_text(row.get("impact_scope")),
                    normalize_text(row.get("source_url")),
                    normalize_text(row.get("notes")),
                    _serialize_row(row),
                    timestamp,
                    timestamp,
                ],
            )
            processed += 1
    return processed
