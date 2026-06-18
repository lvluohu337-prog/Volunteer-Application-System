from __future__ import annotations

from collections import defaultdict
from typing import Any

from backend.admissions_context import _batch_sql_condition, _in_clause
from backend.admissions_risk import _explicit_rule_applies
from backend.database import db_session
from backend.rules_engine import safe_int, safe_number


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
