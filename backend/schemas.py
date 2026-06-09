from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


ExamType = Literal["gaokao", "zhongkao"]


class StudentPayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=64)
    gender: str | None = None
    birthday: str | None = None
    birth_time: str | None = None
    constellation: str | None = None
    bazi_year_pillar: str | None = None
    bazi_month_pillar: str | None = None
    bazi_day_pillar: str | None = None
    bazi_hour_pillar: str | None = None
    exam_type: ExamType
    province: str | None = None
    city: str | None = None
    district: str | None = None
    school: str | None = None
    phone: str | None = None
    parent_phone: str | None = None
    exam_year: int | None = None
    admission_batch: str | None = None
    subject_group: str | None = None
    target_direction: str | None = None
    interest_preferences: str | None = None
    school_preference: str | None = None
    region_preference: str | None = None
    family_preferences: str | None = None
    parent_focus: str | None = None
    development_goal: str | None = None
    accept_adjustment: str | None = None
    accept_high_fee_programs: str | None = None
    communication_notes: str | None = None
    status: str = "draft"
    remark: str | None = None
    mock_score: float | None = None
    estimated_score: float | None = None
    final_score: float | None = None
    estimated_rank: int | None = None
    final_rank: int | None = None
    chinese: float | None = None
    math: float | None = None
    english: float | None = None
    physics: float | None = None
    chemistry: float | None = None
    biology: float | None = None
    politics: float | None = None
    history: float | None = None
    geography: float | None = None
    pe: float | None = None
    experiment: float | None = None
    info_tech: float | None = None
    rank: int | None = None
    score_type: str | None = "manual"


class StudentListQuery(BaseModel):
    keyword: str | None = None
    exam_type: ExamType | None = None
    province: str | None = None
    status: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)


class ScoreRecordPayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    exam_type: ExamType
    total_score: float | None = Field(default=None, ge=0)
    subject_scores: dict[str, Any] = Field(default_factory=dict)
    ranking: int | None = Field(default=None, ge=0)
    score_source: str | None = None
    note: str | None = None


class ReportAdvisorNotePayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    product_code: str = Field(..., min_length=2, max_length=16)
    note_type: str = Field(default="advisor_comment", min_length=2, max_length=32)
    note_title: str | None = Field(default=None, max_length=80)
    note_content: str = Field(..., min_length=1, max_length=4000)
    author_name: str | None = Field(default=None, max_length=40)


class ReportExportPayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    reportVersion: str | None = Field(default=None, max_length=16)
    reviewedBy: str | None = Field(default=None, max_length=40)
    includeSignature: bool = False
