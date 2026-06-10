from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db
from backend.foundation_repository import (
    list_city_industries,
    list_major_categories,
    list_report_template_fields,
    list_sample_students,
)
from backend.intake_inference import derive_birth_profile
from backend.planning_repository import (
    create_report_advisor_note,
    export_report_package,
    get_dashboard_data,
    get_student_analysis,
    get_student_majors,
    get_student_plan,
    get_student_report,
)
from backend.repository import (
    create_score_record,
    create_student,
    delete_score_record,
    delete_student,
    fetch_student_or_404,
    list_score_records,
    list_students,
    update_score_record,
    update_student,
)
from backend.schemas import (
    ReportAdvisorNotePayload,
    ReportExportPayload,
    ScoreRecordPayload,
    StudentListQuery,
    StudentPayload,
)


def success_response(data, message: str = "ok"):
    return {
        "code": 0,
        "message": message,
        "data": data,
    }


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Gaokao Planning Backend",
    version="2.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check():
    return success_response({"status": "ok"})


@app.get("/api/dashboard")
def get_dashboard():
    return success_response(get_dashboard_data())


@app.get("/api/intake/template")
def get_intake_template():
    return success_response(
        {
            "provinces": ["河南", "河北", "山东", "江苏", "安徽", "广东", "浙江", "四川"],
            "exam_types": [
                {"value": "gaokao", "label": "高考"},
                {"value": "zhongkao", "label": "中考"},
            ],
            "genders": ["男", "女"],
            "status_options": [
                {"value": "draft", "label": "草稿"},
                {"value": "review_pending", "label": "待复核"},
                {"value": "reviewed", "label": "已复核"},
            ],
            "score_types": [
                {"value": "manual", "label": "手工录入"},
                {"value": "mock", "label": "模拟成绩"},
                {"value": "official", "label": "正式成绩"},
            ],
            "admission_batches": ["本科提前批", "本科批", "专科批", "综合评价", "待定"],
            "interest_options": ["计算机", "医学", "师范", "财经", "法学", "电子信息", "机械自动化", "设计传媒"],
            "school_preference_options": ["院校层次优先", "城市平台优先", "省内院校优先", "985 / 211 优先", "公办本科优先"],
            "region_preference_options": ["本省优先", "外省优先", "北方", "南方", "一线城市", "省会城市", "离家近"],
            "family_preference_options": ["稳定就业", "考公考编", "赚钱发展", "名校优先", "离家近", "读研深造"],
            "development_goal_options": ["就业优先", "考研深造", "考公考编", "技术研发", "医学发展", "综合待定"],
            "acceptance_options": [
                {"value": "accept", "label": "接受"},
                {"value": "reject", "label": "不接受"},
                {"value": "discuss", "label": "可单独沟通"},
            ],
            "score_source_options": ["一模", "二模", "三模", "平时估分", "正式成绩"],
            "subject_groups": {
                "gaokao": ["物理类", "历史类", "物化生", "物化地", "史政地"],
                "zhongkao": ["中考统招", "指标生", "特长方向"],
            },
            "birth_time_options": [
                {"value": "23:30", "label": "子时 23:00-00:59"},
                {"value": "01:30", "label": "丑时 01:00-02:59"},
                {"value": "03:30", "label": "寅时 03:00-04:59"},
                {"value": "05:30", "label": "卯时 05:00-06:59"},
                {"value": "07:30", "label": "辰时 07:00-08:59"},
                {"value": "09:30", "label": "巳时 09:00-10:59"},
                {"value": "11:30", "label": "午时 11:00-12:59"},
                {"value": "13:30", "label": "未时 13:00-14:59"},
                {"value": "15:30", "label": "申时 15:00-16:59"},
                {"value": "17:30", "label": "酉时 17:00-18:59"},
                {"value": "19:30", "label": "戌时 19:00-20:59"},
                {"value": "21:30", "label": "亥时 21:00-22:59"},
            ],
            "defaults": {
                "name": "",
                "gender": "",
                "birthday": "",
                "birth_time": "",
                "constellation": "",
                "bazi_year_pillar": "",
                "bazi_month_pillar": "",
                "bazi_day_pillar": "",
                "bazi_hour_pillar": "",
                "exam_type": "gaokao",
                "province": "",
                "city": "",
                "district": "",
                "school": "",
                "phone": "",
                "parent_phone": "",
                "exam_year": 2026,
                "admission_batch": "",
                "subject_group": "",
                "target_direction": "",
                "interest_preferences": "",
                "school_preference": "",
                "region_preference": "",
                "family_preferences": "",
                "parent_focus": "",
                "development_goal": "",
                "accept_adjustment": "discuss",
                "accept_high_fee_programs": "reject",
                "communication_notes": "",
                "status": "draft",
                "remark": "",
                "mock_score": None,
                "estimated_score": None,
                "final_score": None,
                "estimated_rank": None,
                "final_rank": None,
                "score_type": "manual",
                "chinese": None,
                "math": None,
                "english": None,
                "physics": None,
                "chemistry": None,
                "biology": None,
                "politics": None,
                "history": None,
                "geography": None,
                "pe": None,
                "experiment": None,
                "info_tech": None,
                "rank": None,
            },
            "birthday_notice": "请输入学生阳历生日与出生时辰，系统会自动辅助推算星座、八字四柱和兴趣倾向。",
            "disclaimer": "系统结果仅作志愿填报辅助参考，正式方案仍需结合分数、位次、招生计划、院校章程和人工复核。",
        }
    )


@app.get("/api/intake/derive-profile")
def get_intake_derived_profile(
    birthday: str = Query(..., min_length=10, max_length=10),
    birth_time: str | None = Query(default=None, min_length=4, max_length=5),
):
    return success_response(derive_birth_profile(birthday, birth_time))


@app.get("/api/students")
def get_students(
    keyword: str | None = Query(default=None),
    exam_type: str | None = Query(default=None),
    province: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
):
    query = StudentListQuery(
        keyword=keyword,
        exam_type=exam_type,
        province=province,
        status=status,
        page=page,
        page_size=page_size,
    )
    return success_response(list_students(query))


@app.post("/api/students")
def post_student(payload: StudentPayload):
    return success_response(create_student(payload), message="student created")


@app.get("/api/students/{student_id}")
def get_student(student_id: int):
    return success_response(fetch_student_or_404(student_id))


@app.put("/api/students/{student_id}")
def put_student(student_id: int, payload: StudentPayload):
    return success_response(update_student(student_id, payload), message="student updated")


@app.delete("/api/students/{student_id}")
def remove_student(student_id: int):
    delete_student(student_id)
    return success_response({"id": student_id}, message="student deleted")


@app.get("/api/students/{student_id}/scores")
def get_student_scores(student_id: int):
    return success_response(list_score_records(student_id))


@app.post("/api/students/{student_id}/scores")
def post_student_score(student_id: int, payload: ScoreRecordPayload):
    return success_response(create_score_record(student_id, payload), message="score record created")


@app.put("/api/scores/{score_id}")
def put_score(score_id: int, payload: ScoreRecordPayload):
    return success_response(update_score_record(score_id, payload), message="score record updated")


@app.delete("/api/scores/{score_id}")
def remove_score(score_id: int):
    delete_score_record(score_id)
    return success_response({"id": score_id}, message="score record deleted")


@app.get("/api/foundation/majors")
def get_foundation_majors(keyword: str | None = Query(default=None)):
    return success_response(list_major_categories(keyword))


@app.get("/api/foundation/cities")
def get_foundation_cities(
    keyword: str | None = Query(default=None),
    region: str | None = Query(default=None),
):
    return success_response(list_city_industries(keyword=keyword, region=region))


@app.get("/api/foundation/sample-students")
def get_foundation_sample_students(
    keyword: str | None = Query(default=None),
    suggested_product: str | None = Query(default=None),
):
    return success_response(list_sample_students(keyword=keyword, suggested_product=suggested_product))


@app.get("/api/foundation/report-template-fields")
def get_foundation_report_template_fields(product: str | None = Query(default=None)):
    return success_response(list_report_template_fields(product))


@app.get("/api/analysis/student/{student_id}")
def get_analysis_detail(student_id: int):
    return success_response(get_student_analysis(student_id))


@app.get("/api/majors/student/{student_id}")
def get_major_detail(student_id: int):
    return success_response(get_student_majors(student_id))


@app.get("/api/plans/student/{student_id}")
def get_plan_detail(student_id: int):
    return success_response(get_student_plan(student_id))


@app.get("/api/reports/student/{student_id}")
def get_report_detail(
    student_id: int,
    product_code: str | None = Query(default=None),
    generated_by: str | None = Query(default=None),
    generation_mode: str = Query(default="preview"),
):
    return success_response(
        get_student_report(
            student_id,
            product_code=product_code,
            generated_by=generated_by,
            generation_mode=generation_mode,
        )
    )


@app.post("/api/reports/student/{student_id}/advisor-notes")
def post_report_advisor_note(student_id: int, payload: ReportAdvisorNotePayload):
    return success_response(
        create_report_advisor_note(student_id, payload),
        message="report advisor note created",
    )


@app.post("/api/reports/student/{student_id}/export/pdf")
def post_report_export_pdf(student_id: int, payload: ReportExportPayload):
    return success_response(
        export_report_package(student_id, payload, export_format="pdf"),
        message="report pdf exported",
    )


@app.post("/api/reports/student/{student_id}/export/word")
def post_report_export_word(student_id: int, payload: ReportExportPayload):
    return success_response(
        export_report_package(student_id, payload, export_format="word"),
        message="report word exported",
    )


