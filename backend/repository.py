from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from fastapi import HTTPException

from backend.database import db_session
from backend.intake_inference import derive_birth_profile
from backend.schemas import ScoreRecordPayload, StudentListQuery, StudentPayload


COMMON_SCORE_FIELDS = ("chinese", "math", "english")
GAOKAO_SCORE_FIELDS = ("physics", "chemistry", "biology")
ZHONGKAO_SCORE_FIELDS = ("politics", "history", "geography", "pe", "experiment", "info_tech")
ALL_SCORE_FIELDS = COMMON_SCORE_FIELDS + GAOKAO_SCORE_FIELDS + ZHONGKAO_SCORE_FIELDS

STATUS_LABELS = {
    "draft": "草稿",
    "review_pending": "待复核",
    "reviewed": "已复核",
}

STATUS_VARIANTS = {
    "draft": "warning",
    "review_pending": "review",
    "reviewed": "success",
}

EXAM_TYPE_LABELS = {
    "gaokao": "高考",
    "zhongkao": "中考",
}


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def normalize_text(value: Any) -> Any:
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


def infer_constellation(birthday: str | None) -> str | None:
    value = normalize_text(birthday)
    if not value:
        return None
    try:
        month_text, day_text = value.split("-")[1:]
        month = int(month_text)
        day = int(day_text)
    except (ValueError, IndexError):
        return None

    constellation_ranges = (
        ((1, 20), "摩羯座", "水瓶座"),
        ((2, 19), "水瓶座", "双鱼座"),
        ((3, 21), "双鱼座", "白羊座"),
        ((4, 20), "白羊座", "金牛座"),
        ((5, 21), "金牛座", "双子座"),
        ((6, 22), "双子座", "巨蟹座"),
        ((7, 23), "巨蟹座", "狮子座"),
        ((8, 23), "狮子座", "处女座"),
        ((9, 23), "处女座", "天秤座"),
        ((10, 24), "天秤座", "天蝎座"),
        ((11, 23), "天蝎座", "射手座"),
        ((12, 22), "射手座", "摩羯座"),
    )
    for (range_month, boundary_day), before_label, after_label in constellation_ranges:
        if month == range_month:
            return before_label if day < boundary_day else after_label
    return None


def calculate_total_score(payload: StudentPayload) -> float:
    return float(sum(float(getattr(payload, field) or 0) for field in ALL_SCORE_FIELDS))


def normalize_subject_scores(subject_scores: dict[str, Any] | None) -> dict[str, float]:
    normalized: dict[str, float] = {}
    for key, value in (subject_scores or {}).items():
        if value in ("", None):
            continue
        try:
            normalized[key] = float(value)
        except (TypeError, ValueError):
            continue
    return normalized


def calculate_record_total_score(payload: ScoreRecordPayload) -> float:
    if payload.total_score is not None:
        return float(payload.total_score)
    return float(sum(normalize_subject_scores(payload.subject_scores).values()))


def has_score_snapshot(payload: StudentPayload) -> bool:
    return any(getattr(payload, field) is not None for field in ALL_SCORE_FIELDS) or payload.rank is not None


def serialize_subject_scores(subject_scores: dict[str, Any] | None) -> str:
    return json.dumps(normalize_subject_scores(subject_scores), ensure_ascii=False, separators=(",", ":"))


def parse_subject_scores(subject_scores_json: str | None) -> dict[str, Any]:
    if not subject_scores_json:
        return {}
    try:
        parsed = json.loads(subject_scores_json)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def require_student(connection, student_id: int) -> dict[str, Any]:
    row = connection.execute(
        "SELECT * FROM students WHERE id = ?",
        (student_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return dict(row)


def build_student_record(record: dict[str, Any]) -> dict[str, Any]:
    status = record.get("status") or "draft"
    exam_type = record.get("exam_type") or "gaokao"
    derived_profile = derive_birth_profile(record.get("birthday"), record.get("birth_time"))
    return {
        "id": record["id"],
        "name": record["name"],
        "gender": record.get("gender"),
        "birthday": record.get("birthday"),
        "birth_time": record.get("birth_time"),
        "constellation": record.get("constellation"),
        "bazi_year_pillar": record.get("bazi_year_pillar"),
        "bazi_month_pillar": record.get("bazi_month_pillar"),
        "bazi_day_pillar": record.get("bazi_day_pillar"),
        "bazi_hour_pillar": record.get("bazi_hour_pillar"),
        "exam_type": exam_type,
        "exam_type_label": EXAM_TYPE_LABELS.get(exam_type, exam_type),
        "province": record.get("province"),
        "city": record.get("city"),
        "district": record.get("district"),
        "school": record.get("school"),
        "phone": record.get("phone"),
        "parent_phone": record.get("parent_phone"),
        "exam_year": record.get("exam_year"),
        "admission_batch": record.get("admission_batch"),
        "subject_group": record.get("subject_group"),
        "target_direction": record.get("target_direction"),
        "interest_preferences": record.get("interest_preferences"),
        "school_preference": record.get("school_preference"),
        "region_preference": record.get("region_preference"),
        "family_preferences": record.get("family_preferences"),
        "parent_focus": record.get("parent_focus"),
        "development_goal": record.get("development_goal"),
        "accept_adjustment": record.get("accept_adjustment"),
        "accept_high_fee_programs": record.get("accept_high_fee_programs"),
        "communication_notes": record.get("communication_notes"),
        "status": status,
        "status_label": STATUS_LABELS.get(status, status),
        "status_variant": STATUS_VARIANTS.get(status, "primary"),
        "remark": record.get("remark"),
        "created_at": record.get("created_at"),
        "updated_at": record.get("updated_at"),
        "mock_score": record.get("mock_score"),
        "estimated_score": record.get("estimated_score"),
        "final_score": record.get("final_score"),
        "estimated_rank": record.get("estimated_rank"),
        "final_rank": record.get("final_rank"),
        "chinese": record.get("chinese"),
        "math": record.get("math"),
        "english": record.get("english"),
        "physics": record.get("physics"),
        "chemistry": record.get("chemistry"),
        "biology": record.get("biology"),
        "politics": record.get("politics"),
        "history": record.get("history"),
        "geography": record.get("geography"),
        "pe": record.get("pe"),
        "experiment": record.get("experiment"),
        "info_tech": record.get("info_tech"),
        "total_score": record.get("total_score") or 0,
        "rank": record.get("rank"),
        "score_type": record.get("score_type"),
        "derived_profile": derived_profile,
    }


def build_score_record(record: dict[str, Any]) -> dict[str, Any]:
    exam_type = record.get("exam_type") or "gaokao"
    subject_scores_json = record.get("subject_scores_json") or "{}"
    return {
        "id": record["id"],
        "student_id": record["student_id"],
        "exam_type": exam_type,
        "exam_type_label": EXAM_TYPE_LABELS.get(exam_type, exam_type),
        "total_score": record.get("total_score") or 0,
        "subject_scores_json": subject_scores_json,
        "subject_scores": parse_subject_scores(subject_scores_json),
        "ranking": record.get("ranking"),
        "score_source": record.get("score_source"),
        "note": record.get("note"),
        "created_at": record.get("created_at"),
        "updated_at": record.get("updated_at"),
    }


def resolve_profile_autofill(payload: StudentPayload) -> dict[str, Any]:
    derived = derive_birth_profile(payload.birthday, payload.birth_time)
    autofill = derived.get("autofill", {})
    return {
        "constellation": normalize_text(payload.constellation) or autofill.get("constellation"),
        "bazi_year_pillar": normalize_text(payload.bazi_year_pillar) or autofill.get("bazi_year_pillar"),
        "bazi_month_pillar": normalize_text(payload.bazi_month_pillar) or autofill.get("bazi_month_pillar"),
        "bazi_day_pillar": normalize_text(payload.bazi_day_pillar) or autofill.get("bazi_day_pillar"),
        "bazi_hour_pillar": normalize_text(payload.bazi_hour_pillar) or autofill.get("bazi_hour_pillar"),
        "interest_preferences": normalize_text(payload.interest_preferences) or autofill.get("interest_preferences"),
        "region_preference": normalize_text(payload.region_preference) or autofill.get("region_preference"),
        "development_goal": normalize_text(payload.development_goal) or autofill.get("development_goal"),
    }


def fetch_student_or_404(student_id: int) -> dict[str, Any]:
    with db_session() as connection:
        row = connection.execute(
            """
            SELECT
                students.*,
                scores.chinese,
                scores.math,
                scores.english,
                scores.physics,
                scores.chemistry,
                scores.biology,
                scores.politics,
                scores.history,
                scores.geography,
                scores.pe,
                scores.experiment,
                scores.info_tech,
                scores.total_score,
                scores.rank,
                scores.score_type
            FROM students
            LEFT JOIN scores ON scores.student_id = students.id
            WHERE students.id = ?
            """,
            (student_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Student not found")

    return build_student_record(dict(row))


def list_students(query: StudentListQuery) -> dict[str, Any]:
    filters = []
    values: list[Any] = []

    if query.keyword:
        filters.append("(students.name LIKE ? OR students.school LIKE ? OR students.phone LIKE ?)")
        keyword = f"%{query.keyword.strip()}%"
        values.extend([keyword, keyword, keyword])

    if query.exam_type:
        filters.append("students.exam_type = ?")
        values.append(query.exam_type)

    if query.province:
        filters.append("students.province = ?")
        values.append(query.province)

    if query.status:
        filters.append("students.status = ?")
        values.append(query.status)

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    offset = (query.page - 1) * query.page_size

    with db_session() as connection:
        total = connection.execute(
            f"SELECT COUNT(*) AS total FROM students {where_clause}",
            values,
        ).fetchone()["total"]

        rows = connection.execute(
            f"""
            SELECT
                students.*,
                scores.total_score,
                scores.rank,
                scores.score_type
            FROM students
            LEFT JOIN scores ON scores.student_id = students.id
            {where_clause}
            ORDER BY students.updated_at DESC, students.id DESC
            LIMIT ? OFFSET ?
            """,
            [*values, query.page_size, offset],
        ).fetchall()

        provinces = [
            row["province"]
            for row in connection.execute(
                "SELECT DISTINCT province FROM students WHERE province IS NOT NULL AND province <> '' ORDER BY province"
            ).fetchall()
        ]
        statuses = [
            row["status"]
            for row in connection.execute(
                "SELECT DISTINCT status FROM students WHERE status IS NOT NULL AND status <> '' ORDER BY status"
            ).fetchall()
        ]

    return {
        "total": total,
        "page": query.page,
        "page_size": query.page_size,
        "rows": [build_student_record(dict(row)) for row in rows],
        "provinces": provinces,
        "statuses": statuses,
        "exam_types": [
            {"value": "gaokao", "label": "高考"},
            {"value": "zhongkao", "label": "中考"},
        ],
    }


def upsert_score(connection, student_id: int, payload: StudentPayload, timestamp: str) -> None:
    total_score = calculate_total_score(payload)
    existing = connection.execute(
        "SELECT id FROM scores WHERE student_id = ?",
        (student_id,),
    ).fetchone()

    score_values = [
        payload.exam_type,
        *(getattr(payload, field) for field in ALL_SCORE_FIELDS),
        total_score,
        payload.rank,
        normalize_text(payload.score_type) or "manual",
    ]

    if existing is None:
        connection.execute(
            """
            INSERT INTO scores (
                student_id,
                exam_type,
                chinese,
                math,
                english,
                physics,
                chemistry,
                biology,
                politics,
                history,
                geography,
                pe,
                experiment,
                info_tech,
                total_score,
                rank,
                score_type,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [student_id, *score_values, timestamp, timestamp],
        )
        return

    connection.execute(
        """
        UPDATE scores
        SET
            exam_type = ?,
            chinese = ?,
            math = ?,
            english = ?,
            physics = ?,
            chemistry = ?,
            biology = ?,
            politics = ?,
            history = ?,
            geography = ?,
            pe = ?,
            experiment = ?,
            info_tech = ?,
            total_score = ?,
            rank = ?,
            score_type = ?,
            updated_at = ?
        WHERE student_id = ?
        """,
        [*score_values, timestamp, student_id],
    )


def create_student(payload: StudentPayload) -> dict[str, Any]:
    timestamp = now_text()
    profile_autofill = resolve_profile_autofill(payload)

    with db_session() as connection:
        cursor = connection.execute(
            """
            INSERT INTO students (
                name,
                gender,
                birthday,
                birth_time,
                constellation,
                bazi_year_pillar,
                bazi_month_pillar,
                bazi_day_pillar,
                bazi_hour_pillar,
                exam_type,
                province,
                city,
                district,
                school,
                phone,
                parent_phone,
                exam_year,
                admission_batch,
                subject_group,
                target_direction,
                interest_preferences,
                school_preference,
                region_preference,
                family_preferences,
                parent_focus,
                development_goal,
                accept_adjustment,
                accept_high_fee_programs,
                communication_notes,
                status,
                remark,
                mock_score,
                estimated_score,
                final_score,
                estimated_rank,
                final_rank,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                payload.name,
                normalize_text(payload.gender),
                normalize_text(payload.birthday),
                normalize_text(payload.birth_time),
                profile_autofill["constellation"],
                profile_autofill["bazi_year_pillar"],
                profile_autofill["bazi_month_pillar"],
                profile_autofill["bazi_day_pillar"],
                profile_autofill["bazi_hour_pillar"],
                payload.exam_type,
                normalize_text(payload.province),
                normalize_text(payload.city),
                normalize_text(payload.district),
                normalize_text(payload.school),
                normalize_text(payload.phone),
                normalize_text(payload.parent_phone),
                payload.exam_year,
                normalize_text(payload.admission_batch),
                normalize_text(payload.subject_group),
                normalize_text(payload.target_direction),
                profile_autofill["interest_preferences"],
                normalize_text(payload.school_preference),
                profile_autofill["region_preference"],
                normalize_text(payload.family_preferences),
                normalize_text(payload.parent_focus),
                profile_autofill["development_goal"],
                normalize_text(payload.accept_adjustment),
                normalize_text(payload.accept_high_fee_programs),
                normalize_text(payload.communication_notes),
                normalize_text(payload.status) or "draft",
                normalize_text(payload.remark),
                payload.mock_score,
                payload.estimated_score,
                payload.final_score,
                payload.estimated_rank,
                payload.final_rank,
                timestamp,
                timestamp,
            ],
        )
        student_id = cursor.lastrowid
        if has_score_snapshot(payload):
            upsert_score(connection, student_id, payload, timestamp)

    return fetch_student_or_404(student_id)


def update_student(student_id: int, payload: StudentPayload) -> dict[str, Any]:
    timestamp = now_text()
    profile_autofill = resolve_profile_autofill(payload)

    with db_session() as connection:
        existing = connection.execute(
            "SELECT id FROM students WHERE id = ?",
            (student_id,),
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Student not found")

        connection.execute(
            """
            UPDATE students
            SET
                name = ?,
                gender = ?,
                birthday = ?,
                birth_time = ?,
                constellation = ?,
                bazi_year_pillar = ?,
                bazi_month_pillar = ?,
                bazi_day_pillar = ?,
                bazi_hour_pillar = ?,
                exam_type = ?,
                province = ?,
                city = ?,
                district = ?,
                school = ?,
                phone = ?,
                parent_phone = ?,
                exam_year = ?,
                admission_batch = ?,
                subject_group = ?,
                target_direction = ?,
                interest_preferences = ?,
                school_preference = ?,
                region_preference = ?,
                family_preferences = ?,
                parent_focus = ?,
                development_goal = ?,
                accept_adjustment = ?,
                accept_high_fee_programs = ?,
                communication_notes = ?,
                status = ?,
                remark = ?,
                mock_score = ?,
                estimated_score = ?,
                final_score = ?,
                estimated_rank = ?,
                final_rank = ?,
                updated_at = ?
            WHERE id = ?
            """,
            [
                payload.name,
                normalize_text(payload.gender),
                normalize_text(payload.birthday),
                normalize_text(payload.birth_time),
                profile_autofill["constellation"],
                profile_autofill["bazi_year_pillar"],
                profile_autofill["bazi_month_pillar"],
                profile_autofill["bazi_day_pillar"],
                profile_autofill["bazi_hour_pillar"],
                payload.exam_type,
                normalize_text(payload.province),
                normalize_text(payload.city),
                normalize_text(payload.district),
                normalize_text(payload.school),
                normalize_text(payload.phone),
                normalize_text(payload.parent_phone),
                payload.exam_year,
                normalize_text(payload.admission_batch),
                normalize_text(payload.subject_group),
                normalize_text(payload.target_direction),
                profile_autofill["interest_preferences"],
                normalize_text(payload.school_preference),
                profile_autofill["region_preference"],
                normalize_text(payload.family_preferences),
                normalize_text(payload.parent_focus),
                profile_autofill["development_goal"],
                normalize_text(payload.accept_adjustment),
                normalize_text(payload.accept_high_fee_programs),
                normalize_text(payload.communication_notes),
                normalize_text(payload.status) or "draft",
                normalize_text(payload.remark),
                payload.mock_score,
                payload.estimated_score,
                payload.final_score,
                payload.estimated_rank,
                payload.final_rank,
                timestamp,
                student_id,
            ],
        )
        if has_score_snapshot(payload):
            upsert_score(connection, student_id, payload, timestamp)

    return fetch_student_or_404(student_id)


def delete_student(student_id: int) -> None:
    with db_session() as connection:
        existing = connection.execute(
            "SELECT id FROM students WHERE id = ?",
            (student_id,),
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Student not found")

        connection.execute(
            "DELETE FROM students WHERE id = ?",
            (student_id,),
        )


def list_score_records(student_id: int) -> list[dict[str, Any]]:
    with db_session() as connection:
        require_student(connection, student_id)
        rows = connection.execute(
            """
            SELECT *
            FROM score_records
            WHERE student_id = ?
            ORDER BY updated_at DESC, id DESC
            """,
            (student_id,),
        ).fetchall()

    return [build_score_record(dict(row)) for row in rows]


def create_score_record(student_id: int, payload: ScoreRecordPayload) -> dict[str, Any]:
    timestamp = now_text()

    with db_session() as connection:
        student = require_student(connection, student_id)
        if student["exam_type"] != payload.exam_type:
            raise HTTPException(status_code=400, detail="Exam type does not match the student record")

        cursor = connection.execute(
            """
            INSERT INTO score_records (
                student_id,
                exam_type,
                total_score,
                subject_scores_json,
                ranking,
                score_source,
                note,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                student_id,
                payload.exam_type,
                calculate_record_total_score(payload),
                serialize_subject_scores(payload.subject_scores),
                payload.ranking,
                normalize_text(payload.score_source),
                normalize_text(payload.note),
                timestamp,
                timestamp,
            ],
        )
        score_id = cursor.lastrowid
        row = connection.execute(
            "SELECT * FROM score_records WHERE id = ?",
            (score_id,),
        ).fetchone()

    return build_score_record(dict(row))


def update_score_record(score_id: int, payload: ScoreRecordPayload) -> dict[str, Any]:
    timestamp = now_text()

    with db_session() as connection:
        existing = connection.execute(
            """
            SELECT score_records.*, students.exam_type AS student_exam_type
            FROM score_records
            INNER JOIN students ON students.id = score_records.student_id
            WHERE score_records.id = ?
            """,
            (score_id,),
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Score record not found")

        if existing["student_exam_type"] != payload.exam_type:
            raise HTTPException(status_code=400, detail="Exam type does not match the student record")

        connection.execute(
            """
            UPDATE score_records
            SET
                exam_type = ?,
                total_score = ?,
                subject_scores_json = ?,
                ranking = ?,
                score_source = ?,
                note = ?,
                updated_at = ?
            WHERE id = ?
            """,
            [
                payload.exam_type,
                calculate_record_total_score(payload),
                serialize_subject_scores(payload.subject_scores),
                payload.ranking,
                normalize_text(payload.score_source),
                normalize_text(payload.note),
                timestamp,
                score_id,
            ],
        )
        row = connection.execute(
            "SELECT * FROM score_records WHERE id = ?",
            (score_id,),
        ).fetchone()

    return build_score_record(dict(row))


def delete_score_record(score_id: int) -> None:
    with db_session() as connection:
        cursor = connection.execute(
            "DELETE FROM score_records WHERE id = ?",
            (score_id,),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Score record not found")
