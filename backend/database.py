from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
STUDENT_EXTRA_COLUMNS = {
    "birth_time": "TEXT",
    "constellation": "TEXT",
    "bazi_year_pillar": "TEXT",
    "bazi_month_pillar": "TEXT",
    "bazi_day_pillar": "TEXT",
    "bazi_hour_pillar": "TEXT",
    "admission_batch": "TEXT",
    "interest_preferences": "TEXT",
    "school_preference": "TEXT",
    "region_preference": "TEXT",
    "family_preferences": "TEXT",
    "parent_focus": "TEXT",
    "development_goal": "TEXT",
    "accept_adjustment": "TEXT",
    "accept_high_fee_programs": "TEXT",
    "communication_notes": "TEXT",
    "mock_score": "REAL",
    "estimated_score": "REAL",
    "final_score": "REAL",
    "estimated_rank": "INTEGER",
    "final_rank": "INTEGER",
}

ADMISSIONS_CORE_TABLES = {
    "institutions": "院校基础信息表",
    "majors": "专业基础信息表",
    "province_batches": "省份批次表",
    "score_segments": "一分一段表",
    "admission_plans": "院校专业招生计划表",
    "institution_admission_scores": "历年院校录取分数位次表",
    "major_admission_scores": "历年专业录取分数位次表",
    "subject_requirements": "选科要求表",
    "institution_rules": "院校章程与特殊规则表",
    "admission_risk_rules": "调剂退档身体条件限制规则表",
    "policy_trends": "政策趋势与备注表",
}


BASE_SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    gender TEXT,
    birthday TEXT,
    exam_type TEXT NOT NULL CHECK (exam_type IN ('gaokao', 'zhongkao')),
    province TEXT,
    city TEXT,
    district TEXT,
    school TEXT,
    phone TEXT,
    parent_phone TEXT,
    exam_year INTEGER,
    subject_group TEXT,
    target_direction TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    remark TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_students_exam_type ON students (exam_type);
CREATE INDEX IF NOT EXISTS idx_students_name ON students (name);
CREATE INDEX IF NOT EXISTS idx_students_status ON students (status);
CREATE INDEX IF NOT EXISTS idx_students_updated_at ON students (updated_at DESC);

CREATE TABLE IF NOT EXISTS scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL UNIQUE,
    exam_type TEXT NOT NULL CHECK (exam_type IN ('gaokao', 'zhongkao')),
    chinese REAL,
    math REAL,
    english REAL,
    physics REAL,
    chemistry REAL,
    biology REAL,
    politics REAL,
    history REAL,
    geography REAL,
    pe REAL,
    experiment REAL,
    info_tech REAL,
    total_score REAL,
    rank INTEGER,
    score_type TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_scores_exam_type ON scores (exam_type);
CREATE INDEX IF NOT EXISTS idx_scores_total_score ON scores (total_score DESC);

CREATE TABLE IF NOT EXISTS score_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    exam_type TEXT NOT NULL CHECK (exam_type IN ('gaokao', 'zhongkao')),
    total_score REAL NOT NULL DEFAULT 0,
    subject_scores_json TEXT NOT NULL DEFAULT '{}',
    ranking INTEGER,
    score_source TEXT,
    note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_score_records_student_id ON score_records (student_id);
CREATE INDEX IF NOT EXISTS idx_score_records_exam_type ON score_records (exam_type);
CREATE INDEX IF NOT EXISTS idx_score_records_updated_at ON score_records (updated_at DESC);

CREATE TABLE IF NOT EXISTS major_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name TEXT NOT NULL UNIQUE,
    representative_majors TEXT,
    suitable_traits TEXT,
    subject_requirement_reference TEXT,
    matching_cities_industries TEXT,
    career_paths TEXT,
    risk_notes TEXT,
    helper_tags TEXT,
    recommendation_index INTEGER,
    raw_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_major_categories_name ON major_categories (category_name);
CREATE INDEX IF NOT EXISTS idx_major_categories_recommendation ON major_categories (recommendation_index DESC);

CREATE TABLE IF NOT EXISTS city_industries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    city_name TEXT NOT NULL UNIQUE,
    region TEXT,
    pace TEXT,
    leading_industries TEXT,
    suitable_major_directions TEXT,
    suitable_student_types TEXT,
    risk_tips TEXT,
    raw_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_city_industries_city_name ON city_industries (city_name);
CREATE INDEX IF NOT EXISTS idx_city_industries_region ON city_industries (region);

CREATE TABLE IF NOT EXISTS sample_students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sample_code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    province TEXT,
    subject_track TEXT,
    estimated_score REAL,
    estimated_rank INTEGER,
    personality_tags TEXT,
    auxiliary_tendency TEXT,
    region_preference TEXT,
    family_focus TEXT,
    recommended_major_directions TEXT,
    recommended_cities TEXT,
    strategy_type TEXT,
    suggested_product TEXT,
    raw_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sample_students_code ON sample_students (sample_code);
CREATE INDEX IF NOT EXISTS idx_sample_students_product ON sample_students (suggested_product);

CREATE TABLE IF NOT EXISTS report_template_fields (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL,
    module_name TEXT NOT NULL,
    suggested_pages TEXT,
    core_content TEXT,
    requires_manual_review INTEGER NOT NULL DEFAULT 0,
    raw_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(product_name, module_name)
);

CREATE INDEX IF NOT EXISTS idx_report_template_fields_product ON report_template_fields (product_name);

CREATE TABLE IF NOT EXISTS report_advisor_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    product_code TEXT NOT NULL,
    note_type TEXT NOT NULL DEFAULT 'advisor_comment',
    note_title TEXT,
    note_content TEXT NOT NULL,
    author_name TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_report_advisor_notes_lookup
    ON report_advisor_notes (student_id, product_code, updated_at DESC);

CREATE TABLE IF NOT EXISTS report_generation_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    product_code TEXT NOT NULL,
    report_title TEXT,
    schema_version TEXT,
    generation_mode TEXT NOT NULL DEFAULT 'preview',
    generated_by TEXT,
    summary_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_report_generation_records_lookup
    ON report_generation_records (student_id, product_code, created_at DESC);

CREATE TABLE IF NOT EXISTS report_delivery_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    product_code TEXT NOT NULL,
    export_format TEXT NOT NULL,
    report_title TEXT,
    artifact_name TEXT,
    artifact_path TEXT,
    delivery_status TEXT NOT NULL DEFAULT 'generated',
    generated_by TEXT,
    include_signature INTEGER NOT NULL DEFAULT 0,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_report_delivery_records_lookup
    ON report_delivery_records (student_id, product_code, created_at DESC);

CREATE TABLE IF NOT EXISTS institutions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    institution_code TEXT NOT NULL,
    institution_name TEXT NOT NULL,
    institution_short_name TEXT,
    institution_type TEXT,
    institution_level TEXT,
    institution_tags TEXT,
    affiliation TEXT,
    public_private TEXT,
    province TEXT,
    city TEXT,
    campus_city TEXT,
    website_url TEXT,
    admission_office_phone TEXT,
    overview TEXT,
    raw_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(institution_code, institution_name)
);

CREATE INDEX IF NOT EXISTS idx_institutions_name ON institutions (institution_name);
CREATE INDEX IF NOT EXISTS idx_institutions_code ON institutions (institution_code);
CREATE INDEX IF NOT EXISTS idx_institutions_province ON institutions (province);

CREATE TABLE IF NOT EXISTS majors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    major_code TEXT NOT NULL,
    major_name TEXT NOT NULL,
    major_category TEXT,
    degree_level TEXT,
    study_years TEXT,
    degree_awarded TEXT,
    discipline_tags TEXT,
    study_features TEXT,
    employment_directions TEXT,
    raw_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(major_code, major_name)
);

CREATE INDEX IF NOT EXISTS idx_majors_name ON majors (major_name);
CREATE INDEX IF NOT EXISTS idx_majors_code ON majors (major_code);
CREATE INDEX IF NOT EXISTS idx_majors_category ON majors (major_category);

CREATE TABLE IF NOT EXISTS province_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_year INTEGER NOT NULL,
    province TEXT NOT NULL,
    exam_type TEXT NOT NULL DEFAULT 'gaokao',
    subject_track TEXT,
    batch_code TEXT NOT NULL,
    batch_name TEXT NOT NULL,
    score_line REAL,
    rank_line INTEGER,
    notes TEXT,
    raw_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(exam_year, province, exam_type, subject_track, batch_code)
);

CREATE INDEX IF NOT EXISTS idx_province_batches_lookup
    ON province_batches (province, exam_year DESC, batch_code);

CREATE TABLE IF NOT EXISTS score_segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_year INTEGER NOT NULL,
    province TEXT NOT NULL,
    exam_type TEXT NOT NULL DEFAULT 'gaokao',
    subject_track TEXT,
    batch_code TEXT,
    control_line REAL,
    score_text TEXT NOT NULL,
    score_value REAL,
    segment_count INTEGER,
    cumulative_count INTEGER,
    rank_range TEXT,
    historical_same_rank_score TEXT,
    raw_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(exam_year, province, exam_type, subject_track, batch_code, score_text)
);

CREATE INDEX IF NOT EXISTS idx_score_segments_lookup
    ON score_segments (province, exam_year DESC, subject_track, batch_code);
CREATE INDEX IF NOT EXISTS idx_score_segments_value
    ON score_segments (score_value DESC, cumulative_count);

CREATE TABLE IF NOT EXISTS subject_requirements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_year INTEGER,
    province TEXT,
    subject_track TEXT,
    institution_id INTEGER,
    major_id INTEGER,
    requirement_code TEXT,
    requirement_text TEXT NOT NULL,
    required_subjects TEXT,
    optional_subjects TEXT,
    forbidden_subjects TEXT,
    match_mode TEXT,
    notes TEXT,
    raw_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(exam_year, province, institution_id, major_id, requirement_code),
    FOREIGN KEY (institution_id) REFERENCES institutions (id) ON DELETE CASCADE,
    FOREIGN KEY (major_id) REFERENCES majors (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_subject_requirements_lookup
    ON subject_requirements (province, exam_year DESC, institution_id, major_id);

CREATE TABLE IF NOT EXISTS admission_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_year INTEGER NOT NULL,
    province TEXT NOT NULL,
    exam_type TEXT NOT NULL DEFAULT 'gaokao',
    subject_track TEXT,
    batch_code TEXT,
    institution_id INTEGER NOT NULL,
    major_id INTEGER,
    plan_group_code TEXT,
    plan_group_name TEXT,
    subject_requirement_id INTEGER,
    planned_count INTEGER,
    tuition_yearly REAL,
    study_years TEXT,
    campus_city TEXT,
    plan_notes TEXT,
    raw_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(exam_year, province, institution_id, major_id, batch_code, plan_group_code),
    FOREIGN KEY (institution_id) REFERENCES institutions (id) ON DELETE CASCADE,
    FOREIGN KEY (major_id) REFERENCES majors (id) ON DELETE CASCADE,
    FOREIGN KEY (subject_requirement_id) REFERENCES subject_requirements (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_admission_plans_lookup
    ON admission_plans (province, exam_year DESC, institution_id, major_id);
CREATE INDEX IF NOT EXISTS idx_admission_plans_batch
    ON admission_plans (batch_code, subject_track);

CREATE TABLE IF NOT EXISTS institution_admission_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_year INTEGER NOT NULL,
    province TEXT NOT NULL,
    exam_type TEXT NOT NULL DEFAULT 'gaokao',
    subject_track TEXT,
    batch_code TEXT,
    institution_id INTEGER NOT NULL,
    min_score REAL,
    min_rank INTEGER,
    avg_score REAL,
    avg_rank INTEGER,
    max_score REAL,
    max_rank INTEGER,
    planned_count INTEGER,
    admitted_count INTEGER,
    score_line REAL,
    notes TEXT,
    raw_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(exam_year, province, institution_id, batch_code, subject_track),
    FOREIGN KEY (institution_id) REFERENCES institutions (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_institution_admission_scores_lookup
    ON institution_admission_scores (province, exam_year DESC, institution_id);
CREATE INDEX IF NOT EXISTS idx_institution_admission_scores_rank
    ON institution_admission_scores (min_rank, avg_rank);

CREATE TABLE IF NOT EXISTS major_admission_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_year INTEGER NOT NULL,
    province TEXT NOT NULL,
    exam_type TEXT NOT NULL DEFAULT 'gaokao',
    subject_track TEXT,
    batch_code TEXT,
    institution_id INTEGER NOT NULL,
    major_id INTEGER NOT NULL,
    plan_group_code TEXT,
    min_score REAL,
    min_rank INTEGER,
    avg_score REAL,
    avg_rank INTEGER,
    max_score REAL,
    max_rank INTEGER,
    planned_count INTEGER,
    admitted_count INTEGER,
    notes TEXT,
    raw_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(exam_year, province, institution_id, major_id, batch_code, subject_track, plan_group_code),
    FOREIGN KEY (institution_id) REFERENCES institutions (id) ON DELETE CASCADE,
    FOREIGN KEY (major_id) REFERENCES majors (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_major_admission_scores_lookup
    ON major_admission_scores (province, exam_year DESC, institution_id, major_id);
CREATE INDEX IF NOT EXISTS idx_major_admission_scores_rank
    ON major_admission_scores (min_rank, avg_rank);

CREATE TABLE IF NOT EXISTS institution_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_year INTEGER,
    province TEXT,
    institution_id INTEGER NOT NULL,
    rule_type TEXT NOT NULL,
    rule_title TEXT,
    rule_content TEXT NOT NULL,
    source_url TEXT,
    notes TEXT,
    raw_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(exam_year, province, institution_id, rule_type, rule_title),
    FOREIGN KEY (institution_id) REFERENCES institutions (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_institution_rules_lookup
    ON institution_rules (institution_id, exam_year DESC, province, rule_type);

CREATE TABLE IF NOT EXISTS admission_risk_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_year INTEGER,
    province TEXT,
    institution_id INTEGER,
    major_id INTEGER,
    risk_type TEXT NOT NULL,
    risk_level TEXT,
    trigger_condition TEXT,
    risk_message TEXT NOT NULL,
    mitigation_suggestion TEXT,
    raw_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(exam_year, province, institution_id, major_id, risk_type, risk_message),
    FOREIGN KEY (institution_id) REFERENCES institutions (id) ON DELETE CASCADE,
    FOREIGN KEY (major_id) REFERENCES majors (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_admission_risk_rules_lookup
    ON admission_risk_rules (province, exam_year DESC, institution_id, major_id, risk_type);

CREATE TABLE IF NOT EXISTS policy_trends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_year INTEGER NOT NULL,
    province TEXT,
    policy_key TEXT NOT NULL,
    policy_title TEXT NOT NULL,
    trend_type TEXT,
    trend_summary TEXT NOT NULL,
    impact_scope TEXT,
    source_url TEXT,
    notes TEXT,
    raw_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(exam_year, province, policy_key)
);

CREATE INDEX IF NOT EXISTS idx_policy_trends_lookup
    ON policy_trends (exam_year DESC, province, policy_key);
"""


DATABASE_SCHEMA = BASE_SCHEMA.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "BIGSERIAL PRIMARY KEY")


def load_local_env() -> None:
    for env_path in (PROJECT_ROOT / ".env", PROJECT_ROOT / ".env.local"):
        if not env_path.exists():
            continue

        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if not key:
                continue

            if value and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]

            os.environ.setdefault(key, value)


load_local_env()


class ResultAdapter:
    def __init__(self, cursor, lastrowid: int | None = None):
        self._cursor = cursor
        self.lastrowid = lastrowid

    def fetchone(self):
        row = self._cursor.fetchone()
        return row

    def fetchall(self):
        return self._cursor.fetchall()


class PostgresConnectionAdapter:
    def __init__(self, connection: psycopg.Connection):
        self._connection = connection

    @staticmethod
    def _convert_sql(sql: str) -> str:
        return sql.replace("?", "%s")

    def execute(self, sql: str, params: list[Any] | tuple[Any, ...] | None = None):
        cursor = self._connection.cursor()
        cursor.execute(self._convert_sql(sql), params or [])

        lastrowid = None
        if sql.lstrip().upper().startswith("INSERT INTO") and "RETURNING" not in sql.upper():
            with self._connection.cursor() as seq_cursor:
                seq_cursor.execute("SELECT LASTVAL()")
                row = seq_cursor.fetchone()
                if row:
                    if isinstance(row, dict):
                        lastrowid = next(iter(row.values()))
                    else:
                        lastrowid = row[0]

        return ResultAdapter(cursor, lastrowid=lastrowid)

    def executescript(self, script: str):
        statements = [item.strip() for item in script.split(";") if item.strip()]
        for statement in statements:
            with self._connection.cursor() as cursor:
                cursor.execute(statement)

    def commit(self):
        self._connection.commit()

    def rollback(self):
        self._connection.rollback()

    def close(self):
        self._connection.close()


def get_database_url() -> str | None:
    return os.environ.get("DATABASE_URL") or os.environ.get("APP_DATABASE_URL")


def get_postgres_conninfo() -> str | None:
    direct_url = get_database_url()
    if direct_url:
        return direct_url

    host = os.environ.get("POSTGRES_HOST")
    database = os.environ.get("POSTGRES_DB")
    user = os.environ.get("POSTGRES_USER")
    password = os.environ.get("POSTGRES_PASSWORD")
    port = os.environ.get("POSTGRES_PORT") or "5432"

    if host and database and user and password:
        return f"host={host} port={port} dbname={database} user={user} password={password}"

    return None


def ensure_postgres_configured() -> None:
    conninfo = get_postgres_conninfo()
    if not conninfo:
        raise RuntimeError(
            "PostgreSQL connection info is required. Set DATABASE_URL or POSTGRES_HOST / POSTGRES_DB / POSTGRES_USER / POSTGRES_PASSWORD."
        )
    engine = (os.environ.get("DB_ENGINE") or "").strip().lower()
    if engine and engine != "postgres":
        raise RuntimeError("SQLite compatibility has been removed. Please use PostgreSQL configuration only.")


def get_postgres_connection() -> PostgresConnectionAdapter:
    ensure_postgres_configured()
    conninfo = get_postgres_conninfo()
    connection = psycopg.connect(
        conninfo,
        row_factory=dict_row,
        autocommit=False,
    )
    return PostgresConnectionAdapter(connection)


def get_connection():
    return get_postgres_connection()


@contextmanager
def db_session():
    connection = get_connection()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _get_table_columns_for_connection(connection, table_name: str) -> list[str]:
    rows = connection.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = ?
        ORDER BY ordinal_position
        """,
        [table_name],
    ).fetchall()
    return [row["column_name"] for row in rows]


def get_table_columns(table_name: str) -> list[str]:
    with db_session() as connection:
        return _get_table_columns_for_connection(connection, table_name)


def _ensure_student_extra_columns(connection) -> None:
    existing_columns = set(_get_table_columns_for_connection(connection, "students"))
    for column_name, column_type in STUDENT_EXTRA_COLUMNS.items():
        if column_name in existing_columns:
            continue
        connection.execute(f"ALTER TABLE students ADD COLUMN {column_name} {column_type}")


def init_db() -> None:
    with db_session() as connection:
        connection.executescript(DATABASE_SCHEMA)
        _ensure_student_extra_columns(connection)
