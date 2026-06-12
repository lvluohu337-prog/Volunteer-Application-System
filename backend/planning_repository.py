from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from backend.admissions_engine import (
    build_admissions_context,
    build_plan_columns_from_candidates,
    group_major_recommendations,
    match_admissions_candidates,
)
from backend.compliance import (
    COMPLIANCE_COPY_RULES,
    PORTRAIT_DISCLAIMER,
    PORTRAIT_EXPLANATION_NOTE,
    PORTRAIT_HARD_EVIDENCE,
    find_prohibited_promise_phrases,
)
from backend.database import PROJECT_ROOT, db_session
from backend.foundation_constants import COMPLIANCE_DISCLAIMER, INTERFACE_BOUNDARY_NOTE
from backend.report_products import (
    DEFAULT_REPORT_PRODUCT_CODE as FORMAL_DEFAULT_REPORT_PRODUCT_CODE,
    REPORT_PRODUCT_CONFIG as FORMAL_REPORT_PRODUCT_CONFIG,
)
from backend.report_exporters import export_report_docx, export_report_pdf
from backend.repository import EXAM_TYPE_LABELS, STATUS_LABELS, STATUS_VARIANTS, fetch_student_or_404, now_text, normalize_text
from backend.rules_engine import (
    evaluate_city_fit,
    evaluate_major_score_fit,
    evaluate_score_profile,
    evaluate_strategy,
    evaluate_subject_requirement,
    infer_student_subjects,
    safe_int,
    safe_number,
    split_keywords,
)


SCORE_BAR_FIELDS = (
    ("chinese", "语文"),
    ("math", "数学"),
    ("english", "英语"),
    ("physics", "物理"),
    ("chemistry", "化学"),
    ("biology", "生物"),
    ("politics", "政治"),
    ("history", "历史"),
    ("geography", "地理"),
    ("pe", "体育"),
    ("experiment", "实验"),
    ("info_tech", "信息技术"),
)

KEYWORD_HINTS = {
    "计算机": ("计算机", "人工智能", "电子信息", "软件", "数据"),
    "医学": ("医学", "护理", "药学", "生物"),
    "师范": ("师范", "教育", "语言"),
    "财经": ("财经", "金融", "会计", "经济", "管理"),
    "法学": ("法学", "政治", "公共管理"),
    "机械": ("机械", "自动化", "智能制造", "电气"),
    "电子": ("电子", "通信", "自动化", "信息"),
    "物理": ("计算机", "电子", "自动化", "机械"),
    "化学": ("材料", "化工", "生物", "医学"),
    "生物": ("生物", "医学", "药学"),
    "历史": ("法学", "师范", "汉语言", "新闻"),
    "政治": ("法学", "政治", "管理", "师范"),
    "地理": ("地理", "规划", "管理", "师范"),
}

DIRECTION_CATALOG = (
    {
        "name": "计算机类",
        "keywords": ("计算机", "软件", "人工智能", "AI", "数据", "算法", "网络", "编程", "信息科学", "信息安全"),
        "trait_keywords": ("信息处理快", "理解力强", "逻辑", "系统思维", "独立", "创新"),
        "goal_keywords": ("技术研发", "数据分析", "跨领域创新", "算法", "研发"),
        "physics_required": True,
        "parent_match_tokens": ("好就业", "就业", "发展", "平台", "考研", "深造"),
        "parent_caution_tokens": ("离家近",),
    },
    {
        "name": "电子信息类",
        "keywords": ("电子", "通信", "信息工程", "芯片", "半导体", "微电子", "光电", "信号"),
        "trait_keywords": ("信息处理快", "理解力强", "行动力强", "专注"),
        "goal_keywords": ("技术研发", "硬件", "研发", "工程", "考研"),
        "physics_required": True,
        "parent_match_tokens": ("好就业", "就业", "发展", "平台", "考研", "深造"),
        "parent_caution_tokens": ("离家近",),
    },
    {
        "name": "自动化类",
        "keywords": ("自动化", "电气", "控制", "机器人", "智能制造", "机械", "测控"),
        "trait_keywords": ("行动力强", "稳定务实", "责任感强", "重视秩序"),
        "goal_keywords": ("技术研发", "工程", "制造", "稳定就业"),
        "physics_required": True,
        "parent_match_tokens": ("好就业", "就业", "稳定", "稳定就业", "考研"),
        "parent_caution_tokens": (),
    },
    {
        "name": "医学类",
        "keywords": ("医学", "临床", "口腔", "护理", "药学", "生物医学", "康复", "检验"),
        "trait_keywords": ("责任感强", "专注", "细致", "耐力强", "稳定务实"),
        "goal_keywords": ("医学发展", "稳定就业", "深造", "服务"),
        "physics_required": True,
        "parent_match_tokens": ("稳定", "稳定就业", "名校", "深造", "考研"),
        "parent_caution_tokens": ("离家近",),
    },
    {
        "name": "师范类",
        "keywords": ("师范", "教育", "教学", "汉语言", "数学与应用数学", "英语师范"),
        "trait_keywords": ("责任感强", "表达欲强", "照顾型", "善协调", "稳定务实"),
        "goal_keywords": ("考公考编", "稳定就业", "教育"),
        "physics_required": False,
        "parent_match_tokens": ("稳定", "稳定就业", "考公", "考编", "离家近"),
        "parent_caution_tokens": ("赚钱", "高薪"),
    },
    {
        "name": "财经类",
        "keywords": ("财经", "金融", "会计", "经济", "财务", "税务", "审计"),
        "trait_keywords": ("稳定务实", "理解力强", "平衡感强", "重视秩序"),
        "goal_keywords": ("稳定就业", "赚钱发展", "组织管理路径", "考研"),
        "physics_required": False,
        "parent_match_tokens": ("好就业", "稳定", "赚钱", "发展", "平台"),
        "parent_caution_tokens": (),
    },
    {
        "name": "法学类",
        "keywords": ("法学", "法务", "知识产权", "政治学", "公共政策"),
        "trait_keywords": ("表达欲强", "专注", "平衡感强", "责任感强"),
        "goal_keywords": ("考公考编", "稳定就业", "公共事务", "组织管理路径"),
        "physics_required": False,
        "parent_match_tokens": ("稳定", "考公", "考编", "平台"),
        "parent_caution_tokens": (),
    },
    {
        "name": "管理类",
        "keywords": ("管理", "工商", "公共管理", "行政", "物流", "供应链", "人力资源"),
        "trait_keywords": ("善协调", "稳定务实", "责任感强", "表达欲强"),
        "goal_keywords": ("组织管理路径", "稳定就业", "考公考编", "综合管理"),
        "physics_required": False,
        "parent_match_tokens": ("稳定", "好就业", "考公", "考编", "离家近"),
        "parent_caution_tokens": (),
    },
    {
        "name": "设计艺术类",
        "keywords": ("设计", "艺术", "视觉传达", "产品设计", "数字媒体", "动画", "美术"),
        "trait_keywords": ("想象力强", "感受力强", "表达欲强", "开放"),
        "goal_keywords": ("创意", "跨领域创新", "品牌", "内容"),
        "physics_required": False,
        "parent_match_tokens": ("城市平台", "发展", "创新"),
        "parent_caution_tokens": ("稳定", "考公", "考编"),
    },
    {
        "name": "新闻传播类",
        "keywords": ("新闻", "传播", "广告", "传媒", "编辑", "播音", "新媒体"),
        "trait_keywords": ("表达欲强", "开放", "探索欲强", "善协调"),
        "goal_keywords": ("内容", "传播", "跨领域创新", "快速成长"),
        "physics_required": False,
        "parent_match_tokens": ("城市平台", "发展", "创新"),
        "parent_caution_tokens": ("稳定", "考公", "考编"),
    },
)

DEFAULT_REPORT_PRODUCT_CODE = FORMAL_DEFAULT_REPORT_PRODUCT_CODE
REPORT_PRODUCT_CONFIG = FORMAL_REPORT_PRODUCT_CONFIG

REPORT_TEMPLATE_SECTION_MAP = {
    "99": {
        "一句画像+专业方向": ["学生基本信息", "专业方向建议", "冲稳保策略建议"],
        "基础画像": ["学生基本信息", "八字四柱与星座辅助分析"],
        "专业方向": ["分数与位次分析", "专业方向建议", "专业与学校建议"],
        "城市建议": ["城市与区域建议", "城市产业匹配建议"],
        "家长沟通": ["家长沟通建议", "风险提示与免责说明"],
    },
    "399": {
        "学生画像总览": ["学生基本信息", "八字四柱与星座辅助分析", "未来发展路径建议"],
        "分数位次分析": ["分数与位次分析", "本省政策依据摘要", "冲稳保策略建议"],
        "专业与学校建议": ["专业与学校建议", "专业方向建议", "录取规则与特殊风险提示"],
        "城市产业匹配": ["城市与区域建议", "城市产业匹配建议"],
        "名校策略": ["名校策略建议", "家长沟通建议", "风险提示与免责说明"],
    },
    "999": {
        "多轮调整": ["专业与学校建议", "咨询师补充备注", "人工咨询推进清单", "导出与交付记录"],
    },
}


def _status_tag(student: dict[str, Any]) -> dict[str, str]:
    status = student.get("status") or "draft"
    return {
        "label": STATUS_LABELS.get(status, status),
        "variant": STATUS_VARIANTS.get(status, "primary"),
    }


def _fetch_latest_student_id() -> int | None:
    with db_session() as connection:
        row = connection.execute(
            """
            SELECT id
            FROM students
            ORDER BY updated_at DESC, id DESC
            LIMIT 1
            """
        ).fetchone()
    return int(row["id"]) if row else None


def _fetch_all_major_rows() -> list[dict[str, Any]]:
    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM major_categories
            ORDER BY recommendation_index DESC, id ASC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def _fetch_all_city_rows() -> list[dict[str, Any]]:
    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM city_industries
            ORDER BY id ASC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def _normalize_report_product_code(product_code: str | None) -> str:
    normalized = (product_code or DEFAULT_REPORT_PRODUCT_CODE).strip()
    return normalized if normalized in REPORT_PRODUCT_CONFIG else DEFAULT_REPORT_PRODUCT_CODE


def _match_report_product_code_from_name(product_name: str | None) -> str | None:
    normalized = (product_name or "").strip()
    if not normalized:
        return None
    leading_digits = re.match(r"^(\d+)", normalized)
    if leading_digits:
        code = leading_digits.group(1)
        return code if code in REPORT_PRODUCT_CONFIG else None
    return None


def _fetch_report_template_rows(product_code: str | None = None) -> list[dict[str, Any]]:
    filters = ["1 = 1"]
    params: list[Any] = []
    if product_code:
        filters.append("product_name LIKE ?")
        params.append(f"{product_code}%")

    with db_session() as connection:
        rows = connection.execute(
            f"""
            SELECT product_name, module_name, suggested_pages, core_content, requires_manual_review
            FROM report_template_fields
            WHERE {' AND '.join(filters)}
            ORDER BY product_name ASC, id ASC
            """,
            params,
        ).fetchall()
    result_rows = [dict(row) for row in rows]
    if result_rows:
        return result_rows

    template_path = PROJECT_ROOT / "data_assets" / "templates" / "report_template_fields.json"
    if not template_path.exists():
        return []

    payload = json.loads(template_path.read_text(encoding="utf-8"))
    fallback_rows = []
    for row in payload:
        normalized_row = {
            "product_name": row.get("产品"),
            "module_name": row.get("模块"),
            "suggested_pages": row.get("页数建议"),
            "core_content": row.get("核心内容"),
            "requires_manual_review": 1 if row.get("是否必须人工复核") == "是" else 0,
        }
        matched_code = _match_report_product_code_from_name(normalized_row["product_name"])
        if matched_code is None:
            continue
        if product_code and matched_code != product_code:
            continue
        fallback_rows.append(normalized_row)
    return fallback_rows


def _build_policy_summary_text(policy_highlights: list[dict[str, Any]]) -> str:
    return "；".join(
        f"{item.get('year') or '当年'}《{item.get('title') or '政策依据'}》：{item.get('summary') or '待补充摘要'}"
        for item in policy_highlights[:3]
    ) or "当前暂未提取出可直接引用的本省政策摘要，正式交付前建议继续补充政策原文复核。"


def _clean_policy_summary(summary: str, *, max_sentences: int = 2) -> str:
    text = str(summary or "").strip()
    if not text:
        return "待补充摘要。"

    text = re.sub(r"^依据《[^》]+》提炼[:：]\s*", "", text)
    text = text.replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[；;]{2,}", "；", text)
    text = re.sub(r"[，,]{2,}", "，", text)

    fragments = [fragment.strip(" ，；;。:：") for fragment in re.split(r"[。！？；;]+", text) if fragment.strip()]
    filtered: list[str] = []
    for fragment in fragments:
        fragment = re.sub(r"（[^）。；;]*$", "", fragment).strip(" ，；;。:：")
        if fragment.startswith(("的说明和解释", "并在招生章程中", "以下简称", "以下简")):
            continue
        if len(fragment) < 6 and not re.search(r"\d", fragment):
            continue
        filtered.append(fragment)
        if len(filtered) >= max_sentences:
            break

    if not filtered:
        fallback = text.strip(" ，；;。:：")
        fallback = re.sub(r"(的说明和解释.*|并在招生章程中.*)$", "", fallback).strip(" ，；;。:：")
        if len(fallback) > 120:
            fallback = fallback[:120].rstrip(" ，；;。:：") + "…"
        return fallback or "待补充摘要。"

    cleaned = "。".join(filtered)
    if cleaned and not cleaned.endswith(("。", "！", "？")):
        cleaned += "。"
    return cleaned


def _build_policy_summary_text(policy_highlights: list[dict[str, Any]]) -> str:
    if not policy_highlights:
        return "当前暂未提取出可直接引用的本省政策摘要，正式交付前建议继续补充政策原文复核。"

    blocks: list[str] = []
    for item in policy_highlights[:3]:
        title = str(item.get("title") or "政策依据").strip() or "政策依据"
        year = item.get("year") or "当年"
        document_title = str(item.get("documentTitle") or item.get("source") or "省级政策资料").strip() or "省级政策资料"
        summary = _clean_policy_summary(str(item.get("summary") or ""))
        blocks.append(
            "\n".join(
                [
                    f"{year}《{title}》",
                    f"依据文件：{document_title}",
                    f"摘要：{summary}",
                ]
            )
        )
    return "\n\n".join(blocks)


def _join_display_items(items: list[str], fallback: str = "待补充", separator: str = " / ") -> str:
    values = [str(item).strip() for item in items if str(item).strip()]
    return separator.join(values) if values else fallback


def _school_major_display(institution_name: str | None, major_name: str | None, fallback: str = "待补充") -> str:
    school = str(institution_name or "").strip()
    major = str(major_name or "").strip()
    if school and major:
        return f"{school}-{major}"
    return school or major or fallback


def _polish_section_body(title: str, body: str) -> str:
    text = str(body or "").replace("\r\n", "\n").strip()
    if not text:
        return text

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s*-\s*", "-", text)
    text = re.sub(r"：\s+", "：", text)

    common_replacements = {
        "。 当前": "。\n当前",
        "。 备选": "。\n备选",
        "。 对应": "。\n对应",
        "。这些": "。\n这些",
        "。其中": "。\n其中",
        "。后续": "。\n后续",
        "。当前画像辅助推荐判断": "。\n当前画像辅助推荐判断",
        "。 这些": "。\n这些",
    }
    for source, target in common_replacements.items():
        text = text.replace(source, target)

    title_specific_replacements = {
        "专业方向建议": {
            "画像辅助推荐的优先方向为 ": "画像辅助推荐的优先方向为：",
            "。其中真实数据层面": "。\n其中真实数据层面",
            "；辅助解释层面": "；\n辅助解释层面",
        },
        "专业与学校建议": {
            "当前优先命中的真实专业方向为 ": "当前优先命中的真实专业方向为：",
            "，对应重点院校样本包括 ": "。\n对应重点院校样本包括：",
            "当前第一志愿建议可优先关注 ": "当前第一志愿建议可优先关注：",
        },
        "冲稳保策略建议": {
            "”结构，优先专业方向可参考：": "”结构。\n优先专业方向可参考：",
            "优先专业方向可参考 ": "优先专业方向可参考：",
            "，其中首位候选的录取概率提示为 ": "。\n其中首位候选的录取概率提示为：",
            "，计划风险提示为 ": "；计划风险提示为：",
            "备选志愿可继续围绕 ": "备选志愿可继续围绕：",
        },
        "录取规则与特殊风险提示": {
            "当前真实候选中已识别出的重点规则包括：": "当前真实候选中已识别出的重点规则包括：\n",
            "当前不建议优先报考的方向包括 ": "\n当前不建议优先报考的方向包括：",
        },
        "名校策略建议": {
            "建议先确认是否接受 ": "建议先确认是否接受：",
        },
    }
    for source, target in title_specific_replacements.get(title, {}).items():
        text = text.replace(source, target)

    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _polish_sections_for_export(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    polished: list[dict[str, Any]] = []
    for section in sections:
        if not isinstance(section, dict):
            polished.append(section)
            continue
        updated = dict(section)
        updated["body"] = _polish_section_body(str(section.get("title") or ""), str(section.get("body") or ""))
        polished.append(updated)
    return polished


def _suggest_industries_by_city(city_names: list[str]) -> list[str]:
    if not city_names:
        return []

    placeholders = ", ".join(["?"] * len(city_names))
    with db_session() as connection:
        rows = connection.execute(
            f"""
            SELECT city_name, leading_industries
            FROM city_industries
            WHERE city_name IN ({placeholders})
            ORDER BY id ASC
            """,
            city_names,
        ).fetchall()
    return [
        f"{row['city_name']}：{row.get('leading_industries') or '待补充产业信息'}"
        for row in rows[:3]
    ]


def _build_parent_guidance(student: dict[str, Any], top_major_names: list[str], top_cities: list[str]) -> str:
    family_focus = student.get("family_preferences") or student.get("parent_focus") or "综合平衡"
    target_direction = student.get("target_direction") or "目标专业方向"
    return (
        f"建议家长先围绕“孩子是否适合 {target_direction}、是否接受 {', '.join(top_major_names[:2]) or '当前推荐方向'}、"
        f"是否愿意去 {', '.join(top_cities[:2]) or '目标城市'}”三件事达成一致，再讨论名校、热门和距离。"
        f"当前家庭关注点偏向“{family_focus}”，更适合把选择标准讲清楚，而不是只追单一名气。"
    )


def _build_future_path_text(top_major_names: list[str], top_cities: list[str]) -> str:
    return (
        f"后续成长建议优先围绕 {', '.join(top_major_names[:2]) or '目标专业'} 提前了解课程难度、考研要求与实习路径，"
        f"并尽量把大学阶段的项目经历、证书与实习机会放在 {', '.join(top_cities[:2]) or '目标区域'} 这类资源更集中的城市完成。"
    )


def _build_manual_consultation_sections(
    student: dict[str, Any],
    selected_product_code: str,
    sections: list[dict[str, Any]],
    advisor_notes: list[dict[str, Any]],
    generation_records: list[dict[str, Any]],
    delivery_records: list[dict[str, Any]],
    matched_majors: list[str],
    matched_cities: list[str],
) -> list[dict[str, Any]]:
    if selected_product_code != "999":
        return sections

    updated = list(sections)
    latest_note_text = "；".join(note.get("note_content") or "" for note in advisor_notes[:2]) or "当前尚未录入咨询师补充备注，建议在正式讲解前补上家长沟通重点、专业取舍和风险边界。"
    latest_generation = generation_records[0].get("created_at") if generation_records else "待生成"
    latest_delivery = delivery_records[0].get("created_at") if delivery_records else "待导出"

    updated.extend(
        [
            {
                "title": "咨询师补充备注",
                "body": latest_note_text,
            },
            {
                "title": "人工咨询推进清单",
                "body": (
                    f"建议围绕 {' / '.join(matched_majors[:2]) or '目标专业'}、{' / '.join(matched_cities[:2]) or '目标城市'} 做多轮确认，"
                    "重点核对孩子真实接受度、家长期待底线、是否接受调剂、是否接受外省与培养成本。"
                ),
            },
            {
                "title": "导出与交付记录",
                "body": (
                    f"最近一次系统生成时间：{latest_generation}；最近一次正式导出时间：{latest_delivery}。"
                    "人工咨询版报告建议在每轮沟通后都补充备注并重新导出，确保线上判断与线下交付保持一致。"
                ),
            },
        ]
    )
    return updated


def _inject_policy_section(sections: list[dict[str, Any]], policy_highlights: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not policy_highlights:
        return sections

    updated = list(sections)
    updated.insert(
        5 if len(updated) >= 5 else len(updated),
        {
            "title": "本省政策依据摘要",
            "body": _build_policy_summary_text(policy_highlights),
        },
    )
    return updated


def _report_exports_dir() -> Path:
    export_dir = PROJECT_ROOT / "data_assets" / "generated_reports"
    export_dir.mkdir(parents=True, exist_ok=True)
    return export_dir


def _safe_report_filename(value: str) -> str:
    normalized = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", value.strip())
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-")
    return normalized or "report"


def _render_report_markdown(report_data: dict[str, Any]) -> str:
    lines = [
        f"# {report_data.get('reportTitle') or '志愿规划报告'}",
        "",
        report_data.get("reportSubtitle") or "",
        "",
        f"版本：{report_data.get('activeProductLabel') or '报告版本'}",
        "",
    ]

    for section in report_data.get("sections") or []:
        lines.extend(
            [
                f"## {section.get('title') or '章节'}",
                section.get("body") or "",
                "",
            ]
        )

    advisor_notes = report_data.get("advisorNotes") or []
    if advisor_notes:
        lines.append("## 咨询师补充备注")
        for item in advisor_notes:
            lines.append(f"- {item.get('note_title') or '未命名备注'}：{item.get('note_content') or ''}")
        lines.append("")

    lines.append("## 合规提示")
    lines.append(report_data.get("disclaimer") or COMPLIANCE_DISCLAIMER)
    lines.append("")
    lines.append(f"接口边界：{report_data.get('boundaryNote') or INTERFACE_BOUNDARY_NOTE}")
    lines.extend(f"- {rule}" for rule in COMPLIANCE_COPY_RULES)
    lines.append("")
    return "\n".join(lines)


def _render_report_html(report_data: dict[str, Any]) -> str:
    sections_html = "".join(
        f"<section><h2>{section.get('title') or '章节'}</h2><p>{section.get('body') or ''}</p></section>"
        for section in (report_data.get("sections") or [])
    )
    advisor_notes_html = "".join(
        f"<li><strong>{item.get('note_title') or '未命名备注'}</strong>：{item.get('note_content') or ''}</li>"
        for item in (report_data.get("advisorNotes") or [])
    )
    advisor_block = f"<section><h2>咨询师补充备注</h2><ul>{advisor_notes_html}</ul></section>" if advisor_notes_html else ""
    compliance_rules_html = "".join(f"<li>{rule}</li>" for rule in COMPLIANCE_COPY_RULES)
    return f"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>{report_data.get('reportTitle') or '志愿规划报告'}</title>
  <style>
    body {{ font-family: 'Microsoft YaHei', sans-serif; margin: 32px; color: #1f2937; line-height: 1.75; }}
    h1 {{ color: #123a8f; margin-bottom: 8px; }}
    h2 {{ color: #1d4ed8; margin-top: 24px; }}
    .meta {{ color: #64748b; margin-bottom: 24px; }}
    section {{ padding: 16px 0; border-bottom: 1px solid #dbeafe; }}
    .warning {{ margin-top: 28px; padding: 16px; background: #eff6ff; border-radius: 14px; }}
  </style>
</head>
<body>
  <h1>{report_data.get('reportTitle') or '志愿规划报告'}</h1>
  <div class="meta">{report_data.get('reportSubtitle') or ''} / {report_data.get('activeProductLabel') or '报告版本'}</div>
  {sections_html}
  {advisor_block}
  <div class="warning">
    <p>{report_data.get('disclaimer') or COMPLIANCE_DISCLAIMER}</p>
    <p>接口边界：{report_data.get('boundaryNote') or INTERFACE_BOUNDARY_NOTE}</p>
    <ul>{compliance_rules_html}</ul>
  </div>
</body>
</html>
""".strip()


def _create_report_delivery_record(
    student_id: int,
    product_code: str,
    export_format: str,
    report_title: str,
    artifact_name: str,
    artifact_path: str,
    generated_by: str | None,
    include_signature: bool,
    payload_summary: dict[str, Any],
) -> dict[str, Any]:
    timestamp = now_text()
    payload_json = json.dumps(payload_summary, ensure_ascii=False, separators=(",", ":"))
    with db_session() as connection:
        cursor = connection.execute(
            """
            INSERT INTO report_delivery_records (
                student_id,
                product_code,
                export_format,
                report_title,
                artifact_name,
                artifact_path,
                delivery_status,
                generated_by,
                include_signature,
                payload_json,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                student_id,
                product_code,
                export_format,
                report_title,
                artifact_name,
                artifact_path,
                "generated",
                normalize_text(generated_by) or "system-export",
                1 if include_signature else 0,
                payload_json,
                timestamp,
            ],
        )
        record_id = cursor.lastrowid
        row = connection.execute(
            """
            SELECT id, student_id, product_code, export_format, report_title, artifact_name, artifact_path,
                   delivery_status, generated_by, include_signature, payload_json, created_at
            FROM report_delivery_records
            WHERE id = ?
            """,
            [record_id],
        ).fetchone()

    return _serialize_delivery_record(dict(row), payload_summary=payload_summary)


def _fallback_section_titles_for_module(module_name: str) -> list[str]:
    if "家长" in module_name:
        return ["家长沟通建议", "风险提示与免责说明"]
    if "城市" in module_name or "区域" in module_name:
        return ["城市与区域建议", "城市产业匹配建议"]
    if "学校" in module_name or "名校" in module_name:
        return ["专业与学校建议", "名校策略建议", "录取规则与特殊风险提示"]
    if "分数" in module_name or "位次" in module_name:
        return ["分数与位次分析", "冲稳保策略建议"]
    if "画像" in module_name or "八字" in module_name or "星座" in module_name:
        return ["学生基本信息", "八字四柱与星座辅助分析"]
    if "专业" in module_name:
        return ["专业方向建议", "专业与学校建议"]
    return ["学生基本信息"]


def _build_report_modules(product_code: str, sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    template_rows = _fetch_report_template_rows(product_code)
    section_lookup = {item["title"]: item for item in sections}
    modules: list[dict[str, Any]] = []
    configured_map = REPORT_TEMPLATE_SECTION_MAP.get(product_code, {})

    for index, row in enumerate(template_rows, start=1):
        module_name = str(row.get("module_name") or f"模块 {index}")
        mapped_titles = configured_map.get(module_name) or _fallback_section_titles_for_module(module_name)
        matched_sections = [section_lookup[title] for title in mapped_titles if title in section_lookup]
        if not matched_sections and sections:
            matched_sections = [sections[min(index - 1, len(sections) - 1)]]

        modules.append(
            {
                "moduleId": f"{product_code}-module-{index}",
                "moduleName": module_name,
                "suggestedPages": safe_int(row.get("suggested_pages")) or 0,
                "coreContent": row.get("core_content") or "",
                "requiresManualReview": bool(row.get("requires_manual_review")),
                "status": "ready" if matched_sections else "needs_enrichment",
                "sectionRefs": [item["title"] for item in matched_sections],
                "sections": matched_sections,
            }
        )

    return modules


def _build_report_product_catalog(selected_code: str) -> list[dict[str, Any]]:
    rows = _fetch_report_template_rows()
    grouped: dict[str, list[dict[str, Any]]] = {code: [] for code in REPORT_PRODUCT_CONFIG}
    for row in rows:
        matched_code = _match_report_product_code_from_name(str(row.get("product_name") or ""))
        if matched_code:
            grouped[matched_code].append(row)

    catalog = []
    for code, config in REPORT_PRODUCT_CONFIG.items():
        product_rows = grouped.get(code, [])
        suggested_pages = sum(max(safe_int(item.get("suggested_pages")), 0) for item in product_rows)
        manual_review_count = sum(1 for item in product_rows if item.get("requires_manual_review"))
        catalog.append(
            {
                "code": code,
                "label": config["label"],
                "shortLabel": config.get("short_label") or config["label"],
                "description": config["description"],
                "targetUser": config["target_user"],
                "deliveryChannels": list(config.get("delivery_channels") or []),
                "moduleCount": len(product_rows),
                "suggestedPages": suggested_pages,
                "manualReviewCount": manual_review_count,
                "isSelected": code == selected_code,
            }
        )
    return catalog


def _adjustment_preference_meta(value: str | None) -> tuple[str, str]:
    normalized = str(value or "").strip().lower()
    if normalized == "accept":
        return "接受调剂", "家长/学生可接受调剂，但仍需优先核对调剂去向是否在可接受专业范围内。"
    if normalized == "reject":
        return "不接受调剂", "当前明确不接受调剂，正式填报时需优先保证专业组和专业顺序足够稳妥。"
    return "可单独沟通", "当前对调剂持沟通态度，建议围绕专业底线与院校层次单独确认。"


def _build_adjustment_advice(student: dict[str, Any], recommendation: dict[str, Any]) -> dict[str, Any]:
    preference_label, base_note = _adjustment_preference_meta(student.get("accept_adjustment"))
    risk_level = str(recommendation.get("riskLevel") or "")
    bucket = str(recommendation.get("bucket") or "")
    plan_group = recommendation.get("planGroupCode") or recommendation.get("batchCode") or "当前专业组"

    if bucket == "rush":
        detail = f"{base_note} 该项位于冲刺档，若报考 {plan_group}，建议重点确认是否接受同组内潜在调剂结果。"
    elif risk_level in {"high", "review"}:
        detail = f"{base_note} 该项仍需人工复核调剂与退档规则，正式填报前务必再核对院校章程。"
    else:
        detail = f"{base_note} 该项风险相对可控，但仍建议把调剂接受边界写进最终志愿确认单。"

    return {
        "preference": str(student.get("accept_adjustment") or "discuss"),
        "label": preference_label,
        "detail": detail,
    }


def _build_recommendation_risk_summary(recommendation: dict[str, Any]) -> str:
    risk_notes = recommendation.get("riskNotes") or []
    if risk_notes:
        return "；".join(risk_notes[:3])
    plan_risk_label = recommendation.get("planRiskLabel") or ""
    if plan_risk_label:
        return f"重点关注：{plan_risk_label}"
    return "当前未识别到额外显性风险，但正式填报前仍需复核招生章程与调剂规则。"


def _normalize_report_recommendation(student: dict[str, Any], recommendation: dict[str, Any]) -> dict[str, Any]:
    item = dict(recommendation)
    item["recommendationReason"] = recommendation.get("recommendationReason") or "当前候选适合作为正式志愿筛选样本。"
    item["riskSummary"] = _build_recommendation_risk_summary(recommendation)
    item["adjustmentAdvice"] = _build_adjustment_advice(student, recommendation)
    item["cityPathNote"] = (
        f"{recommendation.get('cityText') or recommendation.get('city') or '目标城市'}"
        f" 可继续围绕 {recommendation.get('majorName') or '目标专业'} 的实习、就业与考研路径做细化比较。"
    )
    return item


def _build_structured_recommendations(student: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    table = [
        _normalize_report_recommendation(student, item)
        for item in (bundle.get("recommendation_table") or [])
    ]
    first_choice_raw = bundle.get("first_choice")
    first_choice = _normalize_report_recommendation(student, first_choice_raw) if first_choice_raw else None
    alternatives = [
        _normalize_report_recommendation(student, item)
        for item in (bundle.get("alternatives") or [])
    ]
    not_recommended = [dict(item) for item in (bundle.get("not_recommended") or [])]
    return {
        "recommendationTable": table,
        "firstChoice": first_choice,
        "alternatives": alternatives,
        "notRecommended": not_recommended,
    }


def _build_formal_report_json(
    student: dict[str, Any],
    product_code: str,
    sections: list[dict[str, Any]],
    rule_summary: dict[str, Any],
    derived_profile: dict[str, Any],
    matched_majors: list[str],
    matched_cities: list[str],
    policy_highlights: list[dict[str, Any]] | None = None,
    advisor_notes: list[dict[str, Any]] | None = None,
    delivery_records: list[dict[str, Any]] | None = None,
    portrait_recommendation: dict[str, Any] | None = None,
    structured_recommendations: dict[str, Any] | None = None,
    result_source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_code = _normalize_report_product_code(product_code)
    product_config = REPORT_PRODUCT_CONFIG[normalized_code]
    modules = _build_report_modules(normalized_code, sections)
    suggested_total_pages = sum(module["suggestedPages"] for module in modules)
    manual_review_modules = [module["moduleName"] for module in modules if module["requiresManualReview"]]

    structured_recommendations = structured_recommendations or {}
    return {
        "schemaVersion": "1.0",
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "product": {
            "code": normalized_code,
            "label": product_config["label"],
            "description": product_config["description"],
            "targetUser": product_config["target_user"],
            "deliveryChannels": product_config["delivery_channels"],
        },
        "boundaryNote": INTERFACE_BOUNDARY_NOTE,
        "complianceRules": list(COMPLIANCE_COPY_RULES),
        "studentSnapshot": {
            "name": student.get("name") or "学生",
            "province": student.get("province") or "",
            "examYear": student.get("exam_year") or datetime.now().year,
            "subjectGroup": student.get("subject_group") or "",
            "admissionBatch": student.get("admission_batch") or "",
            "currentStatus": student.get("status") or "draft",
        },
        "decisionSummary": {
            "scoreLevel": rule_summary.get("scoreLevel") or "",
            "matchedMajors": matched_majors[:4],
            "matchedCities": matched_cities[:4],
            "topRisks": rule_summary.get("topRisks") or rule_summary.get("riskItems") or [],
            "preferredDirection": (portrait_recommendation or {}).get("preferredDirection") or rule_summary.get("preferredDirection") or "",
        },
        "derivedProfile": {
            "constellation": derived_profile.get("constellation") or "",
            "pillars": derived_profile.get("pillars") or {},
            "interestDirections": derived_profile.get("interestDirections") or [],
            "regionPreferences": derived_profile.get("regionPreferences") or [],
            "developmentGoals": derived_profile.get("developmentGoals") or [],
        },
        "portraitRecommendation": portrait_recommendation or {},
        "resultSource": result_source or {},
        "recommendationTable": structured_recommendations.get("recommendationTable") or [],
        "firstChoice": structured_recommendations.get("firstChoice"),
        "alternatives": structured_recommendations.get("alternatives") or [],
        "notRecommended": structured_recommendations.get("notRecommended") or [],
        "policyHighlights": policy_highlights or [],
        "advisorNotes": advisor_notes or [],
        "deliveryRecords": delivery_records or [],
        "modules": modules,
        "delivery": {
            "suggestedTotalPages": suggested_total_pages,
            "moduleCount": len(modules),
            "manualReviewRequired": bool(manual_review_modules),
            "manualReviewModules": manual_review_modules,
            "readyForExport": True,
        },
        "dataBoundary": {
            "disclaimer": COMPLIANCE_DISCLAIMER,
            "boundaryNote": INTERFACE_BOUNDARY_NOTE,
            "copyRules": list(COMPLIANCE_COPY_RULES),
        },
    }


def _list_report_advisor_notes(student_id: int, product_code: str, limit: int = 20) -> list[dict[str, Any]]:
    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT id, student_id, product_code, note_type, note_title, note_content, author_name, created_at, updated_at
            FROM report_advisor_notes
            WHERE student_id = ? AND product_code = ?
            ORDER BY updated_at DESC, id DESC
            LIMIT ?
            """,
            [student_id, product_code, limit],
        ).fetchall()
    return [dict(row) for row in rows]


def _list_report_generation_records(student_id: int, product_code: str, limit: int = 20) -> list[dict[str, Any]]:
    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT id, student_id, product_code, report_title, schema_version, generation_mode, generated_by, summary_json, created_at
            FROM report_generation_records
            WHERE student_id = ? AND product_code = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            [student_id, product_code, limit],
        ).fetchall()

    records: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        try:
            item["summary"] = json.loads(item.get("summary_json") or "{}")
        except json.JSONDecodeError:
            item["summary"] = {}
        records.append(item)
    return records


def _list_report_delivery_records(student_id: int, product_code: str, limit: int = 20) -> list[dict[str, Any]]:
    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT id, student_id, product_code, export_format, report_title, artifact_name, artifact_path,
                   delivery_status, generated_by, include_signature, payload_json, created_at
            FROM report_delivery_records
            WHERE student_id = ? AND product_code = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            [student_id, product_code, limit],
        ).fetchall()

    records: list[dict[str, Any]] = []
    for row in rows:
        records.append(_serialize_delivery_record(dict(row)))
    return records


def _build_report_delivery_download_url(student_id: int, record_id: int | None) -> str:
    return f"/api/reports/student/{student_id}/deliveries/{record_id}/download"


def _serialize_delivery_record(
    item: dict[str, Any],
    *,
    payload_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if payload_summary is not None:
        item["payload"] = payload_summary
    else:
        try:
            item["payload"] = json.loads(item.get("payload_json") or "{}")
        except json.JSONDecodeError:
            item["payload"] = {}

    artifact_path_text = str(item.get("artifact_path") or "").strip()
    item["downloadUrl"] = _build_report_delivery_download_url(
        safe_int(item.get("student_id")) or safe_int(item.get("studentId")) or 0,
        safe_int(item.get("id")) or None,
    )
    item["artifactExists"] = False
    item["artifactPathLabel"] = artifact_path_text
    item["artifactSizeBytes"] = None

    if not artifact_path_text:
        return item

    artifact_path = Path(artifact_path_text)
    export_dir = _report_exports_dir().resolve()
    try:
        resolved_path = artifact_path.resolve()
    except OSError:
        return item

    try:
        relative_path = resolved_path.relative_to(export_dir)
        item["artifactPathLabel"] = str(relative_path)
    except ValueError:
        item["artifactPathLabel"] = str(resolved_path)

    if resolved_path.exists() and resolved_path.is_file():
        item["artifactExists"] = True
        try:
            item["artifactSizeBytes"] = resolved_path.stat().st_size
        except OSError:
            item["artifactSizeBytes"] = None

    return item


def get_report_delivery_download(student_id: int, record_id: int) -> dict[str, Any]:
    with db_session() as connection:
        row = connection.execute(
            """
            SELECT id, student_id, product_code, export_format, report_title, artifact_name, artifact_path,
                   delivery_status, generated_by, include_signature, payload_json, created_at
            FROM report_delivery_records
            WHERE id = ? AND student_id = ?
            """,
            [record_id, student_id],
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Report delivery record not found")

    record = _serialize_delivery_record(dict(row))
    artifact_path_text = str(record.get("artifact_path") or "").strip()
    if not artifact_path_text:
        raise HTTPException(status_code=404, detail="Export artifact path is missing")

    artifact_path = Path(artifact_path_text)
    try:
        resolved_path = artifact_path.resolve()
        export_dir = _report_exports_dir().resolve()
    except OSError as exc:
        raise HTTPException(status_code=404, detail="Export artifact is unavailable") from exc

    try:
        resolved_path.relative_to(export_dir)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Export artifact is unavailable") from exc

    if not resolved_path.exists() or not resolved_path.is_file():
        raise HTTPException(status_code=404, detail="Export artifact file not found")

    export_format = str(record.get("export_format") or "").lower()
    media_type = (
        "application/pdf"
        if export_format == "pdf"
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

    return {
        "recordId": record_id,
        "studentId": student_id,
        "artifactPath": resolved_path,
        "artifactName": str(record.get("artifact_name") or resolved_path.name),
        "mediaType": media_type,
        "downloadUrl": record["downloadUrl"],
    }


def _build_report_record_summary(
    report_title: str,
    product_code: str,
    rule_summary: dict[str, Any],
    matched_majors: list[str],
    matched_cities: list[str],
) -> dict[str, Any]:
    return {
        "reportTitle": report_title,
        "productCode": product_code,
        "scoreLevel": rule_summary.get("scoreLevel"),
        "matchedCount": rule_summary.get("matchedCount"),
        "topRisks": (rule_summary.get("topRisks") or rule_summary.get("riskItems") or [])[:4],
        "matchedMajors": matched_majors[:3],
        "matchedCities": matched_cities[:3],
    }


def _create_report_generation_record(
    student_id: int,
    product_code: str,
    report_title: str,
    rule_summary: dict[str, Any],
    matched_majors: list[str],
    matched_cities: list[str],
    generated_by: str | None = None,
    generation_mode: str = "preview",
) -> None:
    timestamp = now_text()
    summary_json = json.dumps(
        _build_report_record_summary(report_title, product_code, rule_summary, matched_majors, matched_cities),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    with db_session() as connection:
        connection.execute(
            """
            INSERT INTO report_generation_records (
                student_id,
                product_code,
                report_title,
                schema_version,
                generation_mode,
                generated_by,
                summary_json,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                student_id,
                product_code,
                report_title,
                "1.0",
                generation_mode,
                normalize_text(generated_by) or "system-preview",
                summary_json,
                timestamp,
            ],
        )


def create_report_advisor_note(student_id: int, payload: Any) -> dict[str, Any]:
    fetch_student_or_404(student_id)
    timestamp = now_text()
    product_code = _normalize_report_product_code(getattr(payload, "product_code", None))
    note_title = normalize_text(getattr(payload, "note_title", None))
    note_content = normalize_text(getattr(payload, "note_content", None))
    prohibited_phrases = find_prohibited_promise_phrases(note_title, note_content)
    if prohibited_phrases:
        raise HTTPException(
            status_code=422,
            detail=(
                "咨询师备注中包含禁止使用的承诺性表述："
                + "、".join(prohibited_phrases)
                + "。请改为风险提示、条件说明或人工复核建议。"
            ),
        )

    with db_session() as connection:
        cursor = connection.execute(
            """
            INSERT INTO report_advisor_notes (
                student_id,
                product_code,
                note_type,
                note_title,
                note_content,
                author_name,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                student_id,
                product_code,
                normalize_text(getattr(payload, "note_type", None)) or "advisor_comment",
                note_title,
                note_content,
                normalize_text(getattr(payload, "author_name", None)) or "咨询师",
                timestamp,
                timestamp,
            ],
        )
        note_id = cursor.lastrowid
        row = connection.execute(
            """
            SELECT id, student_id, product_code, note_type, note_title, note_content, author_name, created_at, updated_at
            FROM report_advisor_notes
            WHERE id = ?
            """,
            [note_id],
        ).fetchone()
    return dict(row)


def export_report_package(student_id: int, payload: Any, export_format: str) -> dict[str, Any]:
    product_code = _normalize_report_product_code(getattr(payload, "reportVersion", None))
    reviewed_by = normalize_text(getattr(payload, "reviewedBy", None)) or "system-export"
    include_signature = bool(getattr(payload, "includeSignature", False))
    report_data = get_student_report(
        student_id=student_id,
        product_code=product_code,
        generated_by=reviewed_by,
        generation_mode=f"export_{export_format}",
    )

    student_name = report_data.get("reportTitle", "志愿规划报告").replace(" 志愿规划报告预览", "")
    file_stub = _safe_report_filename(
        f"{student_name}-{product_code}-{export_format}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    )
    export_dir = _report_exports_dir()
    if export_format == "pdf":
        artifact_name = f"{file_stub}.pdf"
    else:
        artifact_name = f"{file_stub}.docx"

    artifact_path = export_dir / artifact_name
    if export_format == "pdf":
        export_report_pdf(
            report_data,
            artifact_path,
            reviewed_by=reviewed_by,
            include_signature=include_signature,
        )
    else:
        export_report_docx(
            report_data,
            artifact_path,
            reviewed_by=reviewed_by,
            include_signature=include_signature,
        )

    payload_summary = {
        "reportVersion": product_code,
        "reviewedBy": reviewed_by,
        "includeSignature": include_signature,
        "artifactType": "final_document",
        "renderEngine": "builtin_pdf_renderer" if export_format == "pdf" else "builtin_docx_renderer",
        "note": "当前阶段已直接生成正式交付文件，可用于归档、发送与线下讲解交付。",
    }
    delivery_record = _create_report_delivery_record(
        student_id=student_id,
        product_code=product_code,
        export_format=export_format,
        report_title=report_data.get("reportTitle") or "志愿规划报告",
        artifact_name=artifact_name,
        artifact_path=str(artifact_path),
        generated_by=reviewed_by,
        include_signature=include_signature,
        payload_summary=payload_summary,
    )

    return {
        "studentId": student_id,
        "productCode": product_code,
        "exportFormat": export_format,
        "artifactType": payload_summary["artifactType"],
        "downloadUrl": _build_report_delivery_download_url(student_id, safe_int(delivery_record.get("id")) or None),
        "artifactName": artifact_name,
        "deliveryRecord": delivery_record,
    }


def _student_keywords(student: dict[str, Any]) -> list[str]:
    derived_profile = student.get("derived_profile") or {}
    autofill = derived_profile.get("autofill", {})
    profile = derived_profile.get("profile") or {}

    keywords = split_keywords(
        student.get("target_direction"),
        student.get("interest_preferences"),
        student.get("school_preference"),
        student.get("region_preference"),
        student.get("family_preferences"),
        student.get("parent_focus"),
        student.get("development_goal"),
        student.get("communication_notes"),
        student.get("subject_group"),
        student.get("remark"),
        student.get("province"),
        student.get("constellation"),
        autofill.get("interest_preferences"),
        autofill.get("region_preference"),
        autofill.get("development_goal"),
        "、".join(profile.get("personalityTraits") or []),
        "、".join(profile.get("interestDirections") or []),
        "、".join(profile.get("regionPreferences") or []),
        "、".join(profile.get("developmentGoals") or []),
    )
    expanded = list(keywords)
    for keyword in keywords:
        for hint_key, hint_values in KEYWORD_HINTS.items():
            if hint_key in keyword or keyword in hint_key:
                expanded.extend(hint_values)
    return list(dict.fromkeys(expanded))


def _portrait_text_tokens(student: dict[str, Any]) -> list[str]:
    derived_profile = student.get("derived_profile") or {}
    profile = derived_profile.get("profile") or {}
    return split_keywords(
        student.get("target_direction"),
        student.get("interest_preferences"),
        student.get("school_preference"),
        student.get("region_preference"),
        student.get("family_preferences"),
        student.get("parent_focus"),
        student.get("development_goal"),
        student.get("communication_notes"),
        student.get("remark"),
        derived_profile.get("constellation"),
        derived_profile.get("hourBranchLabel"),
        derived_profile.get("wuxing", {}).get("dominant"),
        derived_profile.get("wuxing", {}).get("secondary"),
        "、".join(profile.get("personalityTraits") or []),
        "、".join(profile.get("interestDirections") or []),
        "、".join(profile.get("regionPreferences") or []),
        "、".join(profile.get("developmentGoals") or []),
    )


def _subject_track_flags(student: dict[str, Any]) -> tuple[bool, bool]:
    subject_group = str(student.get("subject_group") or "")
    subjects = infer_student_subjects(student)
    is_physics = "物理" in subject_group or "物" in subject_group or "physics" in subject_group.lower() or "物理" in subjects
    is_history = "历史" in subject_group or "史" in subject_group or "history" in subject_group.lower() or "历史" in subjects
    return is_physics, is_history


def _candidate_direction_counts(bundle: dict[str, Any] | None) -> dict[str, int]:
    counts = {spec["name"]: 0 for spec in DIRECTION_CATALOG}
    candidates = (bundle or {}).get("candidates") or []
    for item in candidates[:30]:
        major_name = str(item.get("major_name") or "")
        for spec in DIRECTION_CATALOG:
            if any(keyword and keyword in major_name for keyword in spec["keywords"]):
                counts[spec["name"]] += 1
    return counts


def _subject_match_for_direction(student: dict[str, Any], spec: dict[str, Any]) -> tuple[int, str, bool]:
    is_physics, is_history = _subject_track_flags(student)
    subject_group = student.get("subject_group") or "待补充选科组合"
    if spec.get("physics_required"):
        if is_physics:
            return 18, f"{subject_group} 与该方向常见物理向选科要求整体匹配。", False
        if is_history:
            return -10, f"{subject_group} 与该方向常见物理向要求存在明显偏差，正式筛选时需谨慎。", True
        return 4, f"{subject_group} 暂未识别出明确优势，正式筛选时需逐校核对选科要求。", True
    if is_history:
        return 16, f"{subject_group} 与该方向的文史管理型专业适配度较高。", False
    if is_physics:
        return 12, f"{subject_group} 可以覆盖该方向的一部分专业路径，正式筛选时仍需逐校核对专业组。", False
    return 6, f"{subject_group} 需结合具体专业组再做细分判断。", False


def _parent_match_for_direction(student: dict[str, Any], spec: dict[str, Any]) -> tuple[int, str, str]:
    parent_tokens = split_keywords(
        student.get("family_preferences"),
        student.get("parent_focus"),
        student.get("school_preference"),
        student.get("accept_adjustment"),
        student.get("accept_high_fee_programs"),
    )
    if not parent_tokens:
        return 0, "待补充家长诉求", "当前尚未录入明确家长诉求，建议补充后再细化方向排序。"

    matched = [token for token in parent_tokens if any(key in token or token in key for key in spec["parent_match_tokens"])]
    cautions = [token for token in parent_tokens if any(key in token or token in key for key in spec["parent_caution_tokens"])]
    if matched and not cautions:
        return 12, "基本符合家长诉求", f"当前家长关注点偏向“{'、'.join(matched[:3])}”，与该方向的培养或就业特征较一致。"
    if matched and cautions:
        return 6, "部分符合家长诉求", f"该方向能回应“{'、'.join(matched[:2])}”，但还需和“{'、'.join(cautions[:2])}”的顾虑一起沟通。"
    if cautions:
        return -6, "需重点沟通家长诉求", f"家长当前更看重“{'、'.join(cautions[:2])}”，该方向需要先确认是否可以接受。"
    return 2, "与家长诉求关联度一般", "该方向暂未直接命中家长核心诉求，适合保留为补充选项。"


def _has_portrait_inputs(student: dict[str, Any], derived_profile: dict[str, Any]) -> bool:
    profile = derived_profile.get("profile") or {}
    return any(
        [
            normalize_text(student.get("birthday")),
            normalize_text(student.get("birth_time")),
            normalize_text(student.get("target_direction")),
            normalize_text(student.get("interest_preferences")),
            normalize_text(student.get("development_goal")),
            normalize_text(student.get("family_preferences")),
            normalize_text(student.get("parent_focus")),
            profile.get("personalityTraits"),
            profile.get("interestDirections"),
            profile.get("developmentGoals"),
        ]
    )


def _build_portrait_major_recommendation(
    student: dict[str, Any],
    bundle: dict[str, Any] | None = None,
) -> dict[str, Any]:
    derived_profile = student.get("derived_profile") or {}
    profile = derived_profile.get("profile") or {}
    portrait_tokens = _portrait_text_tokens(student)
    preference_tokens = split_keywords(
        student.get("target_direction"),
        student.get("interest_preferences"),
        student.get("remark"),
        "、".join(profile.get("interestDirections") or []),
    )
    trait_tokens = [item for item in profile.get("personalityTraits") or [] if item]
    goal_tokens = split_keywords(
        student.get("development_goal"),
        "、".join(profile.get("developmentGoals") or []),
    )
    candidate_counts = _candidate_direction_counts(bundle)
    has_portrait_data = _has_portrait_inputs(student, derived_profile)

    if not has_portrait_data:
        return {
            "hasPortraitData": False,
            "preferredDirection": "待补充画像信息",
            "recommendedMajorDirections": [],
            "avoidMajorDirections": [],
            "majorFitReasons": [],
            "personalityMatchTags": [],
            "parentConcernMatch": {
                "status": "pending",
                "label": "待补充家长诉求",
                "details": "当前缺少生日、兴趣、发展目标或家长关注点等画像信息，暂无法生成画像辅助推荐。",
            },
            "subjectMatchSummary": "当前仍可继续做录取规则判断，但画像辅助推荐需要补充兴趣、发展目标或出生信息。",
            "auxiliaryExplanation": [
                "画像信息不足时，系统不会给出“待定方向”，而是提示继续补充画像信息。",
            ],
            "hardEvidence": [
                "正式志愿录取判断仍只使用分数、位次、选科、批次、计划和历年录取数据。",
            ],
            "disclaimer": PORTRAIT_DISCLAIMER,
        }

    scored_directions: list[dict[str, Any]] = []
    personality_tags = [item for item in profile.get("personalityTraits") or [] if item][:6]
    for spec in DIRECTION_CATALOG:
        keyword_hits = [token for token in preference_tokens if any(keyword and (keyword in token or token in keyword) for keyword in spec["keywords"])]
        trait_hits = [token for token in trait_tokens if any(keyword and (keyword in token or token in keyword) for keyword in spec["trait_keywords"])]
        goal_hits = [token for token in goal_tokens if any(keyword and (keyword in token or token in keyword) for keyword in spec["goal_keywords"])]
        subject_score, subject_note, subject_risk = _subject_match_for_direction(student, spec)
        parent_score, parent_label, parent_note = _parent_match_for_direction(student, spec)
        candidate_count = candidate_counts.get(spec["name"], 0)

        score = 40
        reasons: list[str] = []
        hard_evidence: list[str] = [subject_note]
        auxiliary_evidence: list[str] = []

        if keyword_hits:
            score += 18 + min(12, len(keyword_hits) * 3)
            unique_hits = list(dict.fromkeys(keyword_hits))
            reasons.append(f"兴趣/目标中直接命中了“{'、'.join(unique_hits[:4])}”，与该方向的课程内容更贴近。")
            auxiliary_evidence.append(f"兴趣与目标关键词：{'、'.join(unique_hits[:4])}")
        if trait_hits:
            score += 8 + min(8, len(trait_hits) * 2)
            unique_hits = list(dict.fromkeys(trait_hits))
            reasons.append(f"画像特质更偏向“{'、'.join(unique_hits[:4])}”，适合该方向常见的学习与实践节奏。")
            auxiliary_evidence.append(f"性格/前六段辅助标签：{'、'.join(unique_hits[:4])}")
        if goal_hits:
            score += 8 + min(8, len(goal_hits) * 2)
            unique_hits = list(dict.fromkeys(goal_hits))
            reasons.append(f"发展目标中强调“{'、'.join(unique_hits[:4])}”，与该方向的后续成长路径较一致。")
            auxiliary_evidence.append(f"发展目标：{'、'.join(unique_hits[:4])}")

        score += subject_score + parent_score
        if candidate_count:
            score += min(14, candidate_count * 2)
            reasons.append(f"当前真实招生候选中已出现 {candidate_count} 条同方向专业样本，可作为正式筛选时的交叉验证。")
            hard_evidence.append(f"真实候选交叉验证：已命中 {candidate_count} 条 {spec['name']} 相关专业样本")

        reasons.append(parent_note)
        if derived_profile.get("constellation"):
            auxiliary_evidence.append(f"星座辅助解释：{derived_profile.get('constellation')}")
        if derived_profile.get("wuxing", {}).get("dominant"):
            auxiliary_evidence.append(
                f"五行辅助倾向：{derived_profile.get('wuxing', {}).get('dominant')}"
                + (
                    f" / {derived_profile.get('wuxing', {}).get('secondary')}"
                    if derived_profile.get("wuxing", {}).get("secondary")
                    else ""
                )
            )

        scored_directions.append(
            {
                "direction": spec["name"],
                "score": max(0, round(score, 1)),
                "reasons": reasons,
                "subjectMatch": subject_note,
                "subjectRisk": subject_risk,
                "parentMatch": parent_note,
                "parentLabel": parent_label,
                "hardEvidence": list(dict.fromkeys(hard_evidence)),
                "auxiliaryEvidence": list(dict.fromkeys(auxiliary_evidence)),
            }
        )

    scored_directions.sort(key=lambda item: item["score"], reverse=True)
    top_reasons = scored_directions[:5]
    recommended = [item["direction"] for item in top_reasons]
    avoid = [item["direction"] for item in scored_directions if item["subjectRisk"]][:3]
    preferred = recommended[0] if recommended else "待补充画像信息"
    top_parent = top_reasons[0] if top_reasons else None

    subject_match_summary = top_reasons[0]["subjectMatch"] if top_reasons else "待补充选科匹配说明。"
    auxiliary_explanations = list(dict.fromkeys((profile.get("explanations") or []) + [PORTRAIT_EXPLANATION_NOTE]))

    return {
        "hasPortraitData": True,
        "preferredDirection": preferred,
        "recommendedMajorDirections": recommended,
        "avoidMajorDirections": avoid,
        "majorFitReasons": top_reasons,
        "personalityMatchTags": personality_tags,
        "parentConcernMatch": {
            "status": "matched" if top_parent and top_parent["parentLabel"] == "基本符合家长诉求" else "partial",
            "label": top_parent["parentLabel"] if top_parent else "待补充家长诉求",
            "details": top_parent["parentMatch"] if top_parent else "待补充家长诉求说明。",
        },
        "subjectMatchSummary": subject_match_summary,
        "auxiliaryExplanation": auxiliary_explanations,
        "hardEvidence": list(PORTRAIT_HARD_EVIDENCE),
        "disclaimer": PORTRAIT_DISCLAIMER,
    }


def _apply_portrait_summary(rule_summary: dict[str, Any], portrait_recommendation: dict[str, Any]) -> dict[str, Any]:
    updated = dict(rule_summary)
    top_reason = (portrait_recommendation.get("majorFitReasons") or [{}])[0]
    updated["preferredDirection"] = portrait_recommendation.get("preferredDirection") or "待补充画像信息"
    updated["preferredDirectionReason"] = "；".join((top_reason.get("reasons") or [])[:2]) or "待补充画像辅助解释。"
    updated["preferredDirectionStatus"] = "ready" if portrait_recommendation.get("hasPortraitData") else "needs_profile"
    if not updated.get("topMajors") and portrait_recommendation.get("recommendedMajorDirections"):
        updated["topMajors"] = [
            {
                "name": item["direction"],
                "subject_label": item["subjectMatch"],
                "score_label": item["parentLabel"],
                "match_score": item["score"],
                "probability_label": "画像辅助推荐",
                "plan_risk_label": "需结合真实录取规则复核",
            }
            for item in (portrait_recommendation.get("majorFitReasons") or [])[:3]
        ]
    return updated


def _keyword_match_score(row: dict[str, Any], keywords: list[str]) -> tuple[int, list[str]]:
    haystack = " ".join(
        str(row.get(field) or "")
        for field in (
            "category_name",
            "representative_majors",
            "suitable_traits",
            "subject_requirement_reference",
            "matching_cities_industries",
            "career_paths",
        )
    )
    hits = [keyword for keyword in keywords if keyword and keyword in haystack]
    base_score = min(100, 50 + len(hits) * 10 + safe_int(row.get("recommendation_index")) * 2)
    return base_score, list(dict.fromkeys(hits))


def _get_real_admissions_bundle(student: dict[str, Any]) -> dict[str, Any]:
    return match_admissions_candidates(student, evaluate_subject_requirement)


def _real_context_notice(context: dict[str, Any]) -> str | None:
    if context.get("candidate_strategy") == "score_relaxed_real_data":
        return "当前候选仍来自真实招生表，但由于本届分数/位次口径与已入库历史年份不完全同口径，系统已临时放宽位次硬门槛，优先按真实分数线与真实招生记录筛选。"
    return None


def _fallback_reason_text(student: dict[str, Any], context: dict[str, Any]) -> str:
    if not student.get("province"):
        return "缺少省份信息，当前无法命中真实招生数据。"
    if safe_number(context.get("score")) <= 0:
        return "缺少有效分数，当前无法命中真实招生数据。"
    if not context.get("track_labels"):
        return "当前选科/科类信息无法映射到已入库真实招生轨道。"
    if not context.get("latest_year"):
        return "当前省份或选科轨道尚未补齐可用于推荐的真实历史招生数据。"
    return "当前分数、位次、选科或批次条件未命中已入库真实招生候选，系统已退回画像/规则结果。"


def _build_result_source(
    student: dict[str, Any],
    admissions_bundle: dict[str, Any] | None,
    *,
    used_real_candidates: bool,
) -> dict[str, Any]:
    bundle = admissions_bundle or {}
    context = bundle.get("context") or build_admissions_context(student)
    candidate_count = len(bundle.get("candidates") or [])
    candidate_strategy = context.get("candidate_strategy") or None
    notice = _real_context_notice(context)

    if used_real_candidates and candidate_count > 0:
        mode = "real_relaxed" if candidate_strategy == "score_relaxed_real_data" else "real"
        label = "真实招生结果（放宽位次）" if mode == "real_relaxed" else "真实招生结果"
        return {
            "mode": mode,
            "label": label,
            "isRealData": True,
            "matchedCandidateCount": candidate_count,
            "candidateStrategy": candidate_strategy,
            "rankSource": context.get("rank_source"),
            "latestAdmissionYear": context.get("latest_year"),
            "fallbackReason": None,
            "notice": notice,
        }

    return {
        "mode": "fallback",
        "label": "画像/规则兜底结果",
        "isRealData": False,
        "matchedCandidateCount": candidate_count,
        "candidateStrategy": candidate_strategy,
        "rankSource": context.get("rank_source"),
        "latestAdmissionYear": context.get("latest_year"),
        "fallbackReason": _fallback_reason_text(student, context),
        "notice": notice,
    }


def _build_real_major_cards(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    return group_major_recommendations(bundle.get("candidates") or [])


def _build_real_rule_summary(
    student: dict[str, Any],
    bundle: dict[str, Any],
    strategy: dict[str, Any],
    major_cards: list[dict[str, Any]],
    portrait_recommendation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    score_profile = evaluate_score_profile(student)
    context = bundle.get("context") or build_admissions_context(student)
    candidates = bundle.get("candidates") or []
    structured_recommendations = _build_structured_recommendations(student, bundle)
    recommendation_table = structured_recommendations["recommendationTable"]
    first_choice = structured_recommendations["firstChoice"]

    top_majors = []
    for item in recommendation_table[:3]:
        top_majors.append(
            {
                "name": item.get("majorName") or "专业方向",
                "subject_label": item.get("subjectLabel") or "待复核",
                "score_label": item.get("riskLabel") or "待补充",
                "match_score": item.get("compositeScore") or 0,
                "probability_label": item.get("probabilityLabel") or "待补充概率",
                "plan_risk_label": item.get("planRiskLabel") or "待补充风险",
            }
        )

    risk_items = list(score_profile["risk_items"])
    if context.get("rank_source") == "score_segments_estimate":
        risk_items.append("当前位次来自一分一段表估算，正式填报前需换成官方位次。")
    context_notice = _real_context_notice(context)
    if context_notice:
        risk_items.append(context_notice)
    if not candidates:
        risk_items.append("当前未命中真实招生候选，请检查分数、位次、选科或批次信息。")
    else:
        highlighted_risks = []
        for candidate in candidates[:5]:
            for risk in candidate.get("risks") or []:
                message = f"{candidate.get('institution_name') or '目标院校'}-{candidate.get('major_name') or '目标专业'}：{risk['label']}"
                if message not in highlighted_risks:
                    highlighted_risks.append(message)
        risk_items.extend(highlighted_risks[:4])

    summary = {
        "scoreLevel": score_profile["level"]["label"],
        "scoreComment": (
            f"{score_profile['comment']} 当前已命中 {len(candidates)} 条真实招生候选，"
            f"采用 {context.get('latest_year') or '最近'} 年数据作为主要参考。"
        ),
        "riskLevel": "high" if not candidates else score_profile["risk_level"],
        "riskItems": risk_items,
        "studentSubjects": sorted(infer_student_subjects(student)),
        "strategy": strategy,
        "topMajors": top_majors or [
            {
                "name": item.get("title") or "待定方向",
                "subject_label": item.get("tagLabel") or "待复核",
                "score_label": item.get("reason") or "待补充",
                "match_score": item.get("score") or 0,
                "probability_label": "待补充概率",
                "plan_risk_label": "待补充风险",
            }
            for item in major_cards[:3]
        ],
        "matchedCount": len(candidates),
        "latestAdmissionYear": context.get("latest_year"),
        "rankSource": context.get("rank_source"),
        "topRisks": risk_items[:6],
        "recommendationTable": recommendation_table,
        "firstChoice": first_choice,
        "alternatives": structured_recommendations["alternatives"],
        "notRecommended": structured_recommendations["notRecommended"],
    }
    return _apply_portrait_summary(summary, portrait_recommendation or _build_portrait_major_recommendation(student, bundle))


def _build_real_analysis_buckets(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bucket_defs = {
        "rush": ("冲一冲", "风险较高", "warning"),
        "steady": ("稳一稳", "建议主力", "primary"),
        "safe": ("保一保", "相对安全", "success"),
    }
    grouped: dict[str, list[dict[str, Any]]] = {"rush": [], "steady": [], "safe": []}
    for item in candidates:
        bucket = item.get("bucket")
        if bucket in grouped:
            grouped[bucket].append(item)

    buckets = []
    for bucket_key, (title, tag_label, tag_variant) in bucket_defs.items():
        items = grouped[bucket_key][:2]
        lines = []
        for item in items:
            lines.append(
                f"{item.get('institution_name') or '目标院校'} - {item.get('major_name') or '目标专业'}"
            )
            lines.append(
                f"近年门槛：最低分 {safe_number(item.get('min_score')) or '待补充'} / 最低位次 {safe_int(item.get('min_rank')) or '待补充'}"
            )
            lines.append(
                f"录取概率：{item['probability']['label']}；计划风险：{item['plan_risk']['label']}"
            )
        if not lines:
            lines = ["当前暂无该分层候选，建议继续补充分数、位次或批次信息。"]

        buckets.append(
            {
                "key": bucket_key,
                "title": title,
                "note": f"当前真实招生候选 {len(grouped[bucket_key])} 条，正式填报前仍需复核计划波动和调剂规则。",
                "tagLabel": tag_label,
                "tagVariant": tag_variant,
                "items": lines,
            }
        )
    return buckets


POLICY_SIGNAL_MAP = {
    "general_regulation": ("招生章程", "体检", "报名", "录取规则"),
    "military": ("军队", "军校", "飞行", "政治考核", "面试", "体检", "英语语种"),
    "sergeant": ("军士", "定向培养", "政治考核", "面试", "体检"),
    "special_plan": ("专项计划", "国家专项", "高校专项", "地方专项", "资格审核"),
    "high_level_sports": ("高水平运动队", "专项"),
    "police": ("公安", "警察", "政治考察", "体能测评", "体检"),
    "tibet": ("西藏", "定向就业"),
    "sports": ("体育", "专业考试", "提前批"),
    "arts": ("艺术", "设计", "音乐", "美术", "舞蹈", "专业考试"),
}


STRICT_POLICY_SIGNAL_MAP = {
    "general_regulation": ("招生章程", "体检", "报名", "录取规则"),
    "military": ("军队", "军校", "飞行", "飞行学员", "政治考核", "军检", "只招英语"),
    "sergeant": ("军士", "定向培养军士", "政治考核", "军检"),
    "special_plan": ("专项计划", "国家专项", "高校专项", "地方专项", "资格审核"),
    "high_level_sports": ("高水平运动队", "体育教育", "运动训练"),
    "police": ("公安", "警察", "政治考察", "体能测评"),
    "tibet": ("西藏就业", "定向西藏", "西藏生源"),
    "sports": ("体育类", "体育教育", "社会体育", "运动训练"),
    "arts": ("艺术类", "美术", "音乐", "舞蹈", "播音", "表演", "设计学"),
}

POLICY_TOPIC_DISPLAY_MAP = {
    "physical_requirement": ("体检复核", "体检与身体条件复核"),
    "adjustment_policy": ("调剂规则", "专业调剂与退档规则"),
    "cooperative_education": ("中外合作成本", "中外合作办学与培养成本"),
    "language_requirement": ("语种限制", "外语语种与单科要求"),
    "subject_selection_reference": ("选科复核", "选考科目要求复核"),
    "special_plan": ("专项计划资格", "专项计划资格审核"),
    "military": ("军校资格要求", "军校政审面试体检要求"),
    "sergeant": ("军士培养要求", "定向培养军士资格要求"),
    "police": ("公安类审核", "公安类政审体检体测要求"),
    "high_level_sports": ("高水平运动队要求", "高水平运动队资格要求"),
}

POLICY_TOPIC_PRIORITY = {
    "physical_requirement": 100,
    "adjustment_policy": 95,
    "cooperative_education": 90,
    "language_requirement": 85,
    "subject_selection_reference": 80,
    "special_plan": 75,
    "military": 70,
    "sergeant": 65,
    "police": 60,
    "high_level_sports": 55,
}


def _policy_signal_text(student: dict[str, Any], bundle: dict[str, Any]) -> str:
    parts = [
        str(student.get("target_direction") or ""),
        str(student.get("interest_preferences") or ""),
        str(student.get("development_goal") or ""),
        str(student.get("subject_group") or ""),
    ]
    for item in (bundle.get("candidates") or [])[:10]:
        parts.extend(
            [
                str(item.get("institution_name") or ""),
                str(item.get("major_name") or ""),
                str(item.get("batch_code") or ""),
                str(item.get("plan_notes") or ""),
            ]
        )
        for risk in item.get("risks") or []:
            if risk.get("policy_key"):
                parts.append(str(risk.get("policy_key")))
            if risk.get("policy_topic"):
                parts.append(str(risk.get("policy_topic")))
    return " ".join(parts).lower()


def _policy_matches_signal_text(policy_key: str, signal_text: str) -> bool:
    normalized_key = str(policy_key or "")
    normalized_signal = str(signal_text or "").lower()
    if "general_regulation" in normalized_key:
        return True

    for key, tokens in STRICT_POLICY_SIGNAL_MAP.items():
        if key not in normalized_key:
            continue
        return any(token.lower() in normalized_signal for token in tokens)
    return False


def _candidate_policy_keys(bundle: dict[str, Any], limit: int = 10) -> set[str]:
    keys: set[str] = set()
    for candidate in (bundle.get("candidates") or [])[:limit]:
        for risk in candidate.get("risks") or []:
            policy_key = str(risk.get("policy_key") or "").strip()
            if policy_key:
                keys.add(policy_key)
    return keys


def _candidate_policy_topics(bundle: dict[str, Any], limit: int = 10) -> dict[str, str]:
    topic_counters: dict[str, Counter[str]] = {}
    for candidate in (bundle.get("candidates") or [])[:limit]:
        for risk in candidate.get("risks") or []:
            policy_key = str(risk.get("policy_key") or "").strip()
            policy_topic = str(risk.get("policy_topic") or "").strip()
            if not policy_key or not policy_topic:
                continue
            topic_counters.setdefault(policy_key, Counter())[policy_topic] += 1

    selected: dict[str, str] = {}
    for policy_key, counter in topic_counters.items():
        selected[policy_key] = max(
            counter,
            key=lambda topic: (counter[topic], POLICY_TOPIC_PRIORITY.get(topic, 0), topic),
        )
    return selected


def _format_policy_highlight(item: dict[str, Any], policy_topic: str | None = None) -> dict[str, Any]:
    topic_key = str(policy_topic or "").strip()
    original_title = str(item.get("policy_title") or "政策依据").strip() or "政策依据"
    summary = str(item.get("trend_summary") or "").strip()
    display_title = original_title
    if topic_key:
        display_title = POLICY_TOPIC_DISPLAY_MAP.get(topic_key, (original_title, ""))[0] or original_title
    if topic_key and summary:
        summary = f"依据《{original_title}》提炼：{summary}"
    return {
        "year": item.get("exam_year"),
        "key": item.get("policy_key"),
        "title": display_title,
        "type": item.get("trend_type") or "policy",
        "summary": summary,
        "source": str(item.get("source_url") or "").replace("/", "\\").split("\\")[-1],
        "documentTitle": original_title,
        "policyTopic": topic_key or None,
    }


def _fetch_policy_highlights(student: dict[str, Any], bundle: dict[str, Any], limit: int = 3) -> list[dict[str, Any]]:
    province = student.get("province")
    if not province:
        return []

    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT exam_year, policy_key, policy_title, trend_type, trend_summary, impact_scope, source_url
            FROM policy_trends
            WHERE province = ?
            ORDER BY exam_year DESC, id DESC
            """,
            [province],
        ).fetchall()

    signal_text = _policy_signal_text(student, bundle)
    direct_policy_keys = _candidate_policy_keys(bundle)
    scored: list[tuple[int, dict[str, Any]]] = []
    seen_keys: set[str] = set()
    for row in rows:
        item = dict(row)
        policy_key = str(item.get("policy_key") or "")
        score = 0
        if "general_regulation" in policy_key:
            score += 1
        if policy_key in direct_policy_keys:
            score += 20
        if _policy_matches_signal_text(policy_key, signal_text):
            score += 6
        if any(
            policy_key == str(risk.get("policy_key") or "")
            for candidate in (bundle.get("candidates") or [])[:10]
            for risk in (candidate.get("risks") or [])
        ):
            score += 10
        if score <= 0 and "general_regulation" not in policy_key:
            continue
        if policy_key in seen_keys:
            continue
        seen_keys.add(policy_key)
        scored.append((score, item))

    scored.sort(key=lambda pair: (pair[0], pair[1].get("exam_year") or 0), reverse=True)
    highlights: list[dict[str, Any]] = []
    for _, item in scored[:limit]:
        source_name = str(item.get("source_url") or "").replace("/", "\\").split("\\")[-1]
        highlights.append(
            {
                "year": item.get("exam_year"),
                "key": item.get("policy_key"),
                "title": item.get("policy_title") or "政策依据",
                "type": item.get("trend_type") or "policy",
                "summary": item.get("trend_summary") or "",
                "source": source_name,
            }
        )
    return highlights


def _format_policy_highlight(item: dict[str, Any], policy_topic: str | None = None) -> dict[str, Any]:
    topic_key = str(policy_topic or "").strip()
    original_title = str(item.get("policy_title") or "政策依据").strip() or "政策依据"
    summary = str(item.get("trend_summary") or "").strip()
    display_title = original_title
    if topic_key:
        display_title = POLICY_TOPIC_DISPLAY_MAP.get(topic_key, (original_title, ""))[0] or original_title
    if topic_key and summary:
        summary = f"依据《{original_title}》提炼：{summary}"
    return {
        "year": item.get("exam_year"),
        "key": item.get("policy_key"),
        "title": display_title,
        "type": item.get("trend_type") or "policy",
        "summary": summary,
        "source": str(item.get("source_url") or "").replace("/", "\\").split("\\")[-1],
        "documentTitle": original_title,
        "policyTopic": topic_key or None,
    }


def _fetch_policy_highlights(student: dict[str, Any], bundle: dict[str, Any], limit: int = 3) -> list[dict[str, Any]]:
    province = student.get("province")
    if not province:
        return []

    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT exam_year, policy_key, policy_title, trend_type, trend_summary, impact_scope, source_url
            FROM policy_trends
            WHERE province = ?
            ORDER BY exam_year DESC, id DESC
            """,
            [province],
        ).fetchall()

    signal_text = _policy_signal_text(student, bundle)
    direct_policy_keys = _candidate_policy_keys(bundle)
    direct_policy_topics = _candidate_policy_topics(bundle)
    scored: list[tuple[int, dict[str, Any]]] = []
    seen_keys: set[str] = set()
    for row in rows:
        item = dict(row)
        policy_key = str(item.get("policy_key") or "")
        score = 0
        if "general_regulation" in policy_key:
            score += 1
        if policy_key in direct_policy_keys:
            score += 20
        if _policy_matches_signal_text(policy_key, signal_text):
            score += 6
        if any(
            policy_key == str(risk.get("policy_key") or "")
            for candidate in (bundle.get("candidates") or [])[:10]
            for risk in (candidate.get("risks") or [])
        ):
            score += 10
        if score <= 0 and "general_regulation" not in policy_key:
            continue
        if policy_key in seen_keys:
            continue
        seen_keys.add(policy_key)
        scored.append((score, item))

    scored.sort(key=lambda pair: (pair[0], pair[1].get("exam_year") or 0), reverse=True)
    highlights: list[dict[str, Any]] = []
    for _, item in scored[:limit]:
        policy_key = str(item.get("policy_key") or "").strip()
        highlights.append(_format_policy_highlight(item, direct_policy_topics.get(policy_key)))
    return highlights


def _build_real_report_sections(
    student: dict[str, Any],
    bundle: dict[str, Any],
    strategy: dict[str, Any],
    major_cards: list[dict[str, Any]],
    policy_highlights: list[dict[str, Any]] | None = None,
    portrait_recommendation: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    score_profile = evaluate_score_profile(student)
    policy_highlights = policy_highlights or []
    derived_profile = _build_derived_profile_summary(student)
    pillars = derived_profile["pillars"]
    four_pillars = " / ".join(
        [value for value in (pillars["year"], pillars["month"], pillars["day"], pillars["hour"]) if value]
    ) or "待补充"
    candidates = bundle.get("candidates") or []
    structured_recommendations = _build_structured_recommendations(student, bundle)
    first_choice = structured_recommendations["firstChoice"]
    alternatives = structured_recommendations["alternatives"]
    not_recommended = structured_recommendations["notRecommended"]
    context = bundle.get("context") or {}
    top_candidates = candidates[:3]
    top_major_names = [item.get("major_name") or "目标专业" for item in top_candidates]
    top_school_names = [item.get("institution_name") or "目标院校" for item in top_candidates]
    top_cities = list(dict.fromkeys([item.get("city_text") or "目标地区" for item in top_candidates]))
    city_industry_notes = _suggest_industries_by_city(top_cities)
    portrait_recommendation = portrait_recommendation or _build_portrait_major_recommendation(student, bundle)
    estimated_rank_note = ""
    first_choice_text = (
        f" 当前第一志愿建议可优先关注 {first_choice.get('institutionName')} - {first_choice.get('majorName')}。"
        if first_choice
        else ""
    )
    alternatives_text = (
        " 备选志愿可继续围绕 "
        + " / ".join(f"{item.get('institutionName')}-{item.get('majorName')}" for item in alternatives[:3])
        + " 做顺序优化。"
        if alternatives
        else ""
    )
    not_recommended_text = (
        " 当前不建议优先报考的方向包括 "
        + " / ".join(f"{item.get('institutionName')}-{item.get('majorName')}" for item in not_recommended[:3])
        + "。"
        if not_recommended
        else ""
    )
    if context.get("rank_source") == "score_segments_estimate":
        estimated_rank_note = "当前位次来自一分一段表估算，正式填报前必须换成官方位次。"
    context_notice = _real_context_notice(context)
    if context_notice:
        estimated_rank_note = f"{estimated_rank_note}{context_notice}"

    return [
        {
            "title": "学生基本信息",
            "body": (
                f"{student.get('name') or '该学生'}，"
                f"{student.get('province') or '待补充省份'}，"
                f"{student.get('exam_year') or datetime.now().year} 届"
                f"{EXAM_TYPE_LABELS.get(student.get('exam_type') or 'gaokao', '高考')}考生，"
                f"当前选科/方向为 {student.get('subject_group') or '待补充'}。"
            ),
        },
        {
            "title": "八字四柱与星座辅助分析",
            "body": (
                f"阳历生日 {derived_profile.get('birthday') or '待补充'}，"
                f"出生时辰 {derived_profile.get('birthTime') or '待补充'}，"
                f"四柱为 {four_pillars}，星座为 {derived_profile.get('constellation') or '待补充'}。"
                "本层只用于解释学生的沟通方式、学习倾向和环境适应，不替代真实录取数据。"
            ),
        },
        {
            "title": "分数与位次分析",
            "body": (
                f"当前有效总分约为 {score_profile['total_score']}，位次 {context.get('rank') or '待补充'}，"
                f"采用 {context.get('latest_year') or '最近'} 年河南真实招生数据做第一轮匹配。"
                f"{estimated_rank_note}"
            ),
        },
        {
            "title": "专业方向建议",
            "body": (
                f"画像辅助推荐的优先方向为 {' / '.join(portrait_recommendation.get('recommendedMajorDirections')[:3]) or '待补充画像信息'}。"
                f"其中真实数据层面会继续核对选科组合、正式高考成绩、全省位次、批次和历年录取门槛；"
                f"辅助解释层面则结合 {derived_profile.get('constellation') or '星座待补充'}、"
                f"{'、'.join(derived_profile.get('personalityTraits')[:3]) or '性格标签待补充'}"
                " 来说明学生为什么更适合这些方向。"
            ),
        },
        {
            "title": "专业与学校建议",
            "body": (
                f"当前优先命中的真实专业方向为 {' / '.join(top_major_names) if top_major_names else '待补充'}，"
                f"对应重点院校样本包括 {' / '.join(top_school_names) if top_school_names else '待补充'}。"
                "这些结果已经过分数、位次和选科要求联合筛选，并叠加了历史门槛区间与计划波动判断。"
                + first_choice_text
            ),
        },
        {
            "title": "城市与区域建议",
            "body": (
                f"当前真实候选主要分布在 {' / '.join(top_cities) if top_cities else '待补充地区'}。"
                "后续还需要继续结合城市产业、生活节奏和家庭距离偏好进一步优化。"
            ),
        },
        {
            "title": "城市产业匹配建议",
            "body": (
                "当前建议把城市选择和未来实习就业机会一起看。"
                + (
                    f"结合已接入城市产业库，可优先关注 {'；'.join(city_industry_notes)}。"
                    if city_industry_notes
                    else "当前候选城市的产业说明仍在持续补充，正式交付前建议结合城市主导产业再复核一次。"
                )
            ),
        },
        {
            "title": "冲稳保策略建议",
            "body": (
                f"当前建议采用“冲 {strategy['rush_ratio']}% / 稳 {strategy['steady_ratio']}% / 保 {strategy['safe_ratio']}%”结构，"
                f"优先专业方向可参考 {' / '.join(item['title'] for item in major_cards[:3]) if major_cards else '待补充方向'}。"
                f"其中首位候选的录取概率提示为 {top_candidates[0]['probability']['label'] if top_candidates else '待补充'}，"
                f"计划风险提示为 {top_candidates[0]['plan_risk']['label'] if top_candidates else '待补充'}。"
                + alternatives_text
            ),
        },
        {
            "title": "录取规则与特殊风险提示",
            "body": (
                "当前真实候选中已识别出的重点规则包括："
                + (
                    "；".join(
                        f"{item.get('institution_name') or '目标院校'}-{item.get('major_name') or '目标专业'}："
                        + "、".join(risk["label"] for risk in (item.get("risks") or [])[:2])
                        for item in top_candidates
                        if item.get("risks")
                    )
                    if any(item.get("risks") for item in top_candidates)
                    else "暂未识别出显性特殊限制，但正式填报前仍要逐校复核招生章程、调剂和退档规则。"
                )
                + not_recommended_text
            ),
        },
        {
            "title": "名校策略建议",
            "body": (
                f"如果家庭有明显的名校诉求，建议先确认是否接受 {' / '.join(top_school_names[:2]) if top_school_names else '目标院校'}"
                " 这类院校可能出现的专业冷热差异、调剂空间与培养成本。真正的名校策略不是只冲学校名气，而是看孩子能否在该专业路径上持续成长。"
            ),
        },
        {
            "title": "家长沟通建议",
            "body": (
                _build_parent_guidance(student, top_major_names, top_cities)
                + f" 当前画像辅助推荐判断：{portrait_recommendation.get('parentConcernMatch', {}).get('details') or '待补充家长诉求说明。'}"
            ),
        },
        {
            "title": "未来发展路径建议",
            "body": _build_future_path_text(top_major_names, top_cities),
        },
        {
            "title": "风险提示与免责说明",
            "body": COMPLIANCE_DISCLAIMER,
            "warning": True,
        },
    ]


def _major_rule_results(student: dict[str, Any]) -> list[dict[str, Any]]:
    keywords = _student_keywords(student)
    student_subjects = infer_student_subjects(student)
    total_score = safe_number(student.get("total_score"))
    rows = _fetch_all_major_rows()
    results: list[dict[str, Any]] = []

    for row in rows:
        keyword_score, keyword_hits = _keyword_match_score(row, keywords)
        subject_fit = evaluate_subject_requirement(row.get("subject_requirement_reference"), student_subjects)
        score_fit = evaluate_major_score_fit(str(row.get("category_name") or ""), total_score)
        recommendation_index = safe_int(row.get("recommendation_index"))

        composite_score = round(
            keyword_score * 0.35 + subject_fit["score"] * 0.35 + score_fit["score"] * 0.2 + recommendation_index * 2,
            1,
        )

        results.append(
            {
                "row": row,
                "keyword_hits": keyword_hits,
                "keyword_score": keyword_score,
                "subject_fit": subject_fit,
                "score_fit": score_fit,
                "composite_score": composite_score,
            }
        )

    results.sort(key=lambda item: item["composite_score"], reverse=True)
    return results


def _city_rule_results(student: dict[str, Any], major_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keywords = _student_keywords(student)
    score_profile = evaluate_score_profile(student)
    top_major_names = [item["row"].get("category_name") or "专业方向" for item in major_results[:3]]
    rows = _fetch_all_city_rows()
    results: list[dict[str, Any]] = []

    for row in rows:
        major_text = " ".join(
            [
                str(row.get("suitable_major_directions") or ""),
                str(row.get("leading_industries") or ""),
                " ".join(top_major_names),
            ]
        )
        fit_result = evaluate_city_fit(str(row.get("city_name") or ""), major_text, keywords, score_profile)
        results.append(
            {
                "row": row,
                "fit_score": fit_result["score"],
                "fit_note": fit_result["note"],
            }
        )

    results.sort(key=lambda item: item["fit_score"], reverse=True)
    return results


def _subject_bars(student: dict[str, Any]) -> list[dict[str, Any]]:
    values = []
    for key, label in SCORE_BAR_FIELDS:
        score = student.get(key)
        if score in (None, ""):
            continue
        numeric_score = safe_number(score)
        percent = max(0, min(100, round(numeric_score / 150 * 100)))
        values.append({"label": label, "value": round(numeric_score, 1), "percent": percent})
    return values


def _build_major_cards(major_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cards = []
    for item in major_results[:4]:
        row = item["row"]
        subject_fit = item["subject_fit"]
        score_fit = item["score_fit"]
        keyword_hits = item["keyword_hits"]
        composite_score = item["composite_score"]

        meta = [
            f"选科判断：{subject_fit['label']}，{subject_fit['note']}",
            f"分数判断：{score_fit['label']}，{score_fit['note']}",
            f"发展路径：{row.get('career_paths') or '建议继续结合考研、就业与城市机会综合判断'}",
        ]
        if row.get("risk_notes"):
            meta.append(f"风险提醒：{row['risk_notes']}")

        cards.append(
            {
                "title": row.get("category_name") or "专业方向",
                "type": row.get("representative_majors") or "专业大类",
                "score": int(round(composite_score)),
                "reason": (
                    f"关键词命中：{'、'.join(keyword_hits[:4]) if keyword_hits else '当前以基础适配规则判定'}。"
                ),
                "meta": meta,
                "tagLabel": "优先考虑" if composite_score >= 85 else "建议复核",
                "tagVariant": "success" if composite_score >= 85 else "primary",
                "footer": row.get("matching_cities_industries") or "建议继续结合城市产业机会判断。",
            }
        )
    return cards


def _build_plan_columns(
    student: dict[str, Any],
    major_results: list[dict[str, Any]],
    city_results: list[dict[str, Any]],
    portrait_recommendation: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    score_profile = evaluate_score_profile(student)
    strategy = evaluate_strategy(score_profile, major_results)
    top_major_names = [item["row"].get("category_name") or "专业方向" for item in major_results[:4]]
    if not top_major_names and portrait_recommendation:
        top_major_names = portrait_recommendation.get("recommendedMajorDirections") or []
    top_city_names = [item["row"].get("city_name") or "目标城市" for item in city_results[:4]]
    shared_metrics = [
        f"当前总分：{score_profile['total_score']}",
        f"当前位次：{score_profile['rank'] or '待补充'}",
    ]

    columns = [
        {
            "title": "冲一冲",
            "note": f"建议占比约 {strategy['rush_ratio']}%，适合少量上探，但不能影响整体安全性。",
            "tagLabel": "风险较高",
            "tagVariant": "warning",
            "cards": [
                {
                    "school": f"{top_city_names[0] if top_city_names else '目标城市'}冲刺院校池",
                    "detail": "优先冲平台，但要接受结果波动。",
                    "metrics": [*shared_metrics, f"策略占比：{strategy['rush_ratio']}%"],
                    "major": f"建议方向：{top_major_names[0] if top_major_names else '待定'}",
                    "reason": "适合作为上限尝试，正式填报前必须复核位次和招生规则。",
                }
            ],
        },
        {
            "title": "稳一稳",
            "note": f"建议占比约 {strategy['steady_ratio']}%，应作为主力区间，优先保证专业接受度。",
            "tagLabel": "建议主力",
            "tagVariant": "primary",
            "cards": [
                {
                    "school": f"{top_city_names[1] if len(top_city_names) > 1 else top_city_names[0] if top_city_names else '目标城市'}稳妥院校池",
                    "detail": "优先兼顾专业匹配与城市机会。",
                    "metrics": [*shared_metrics, f"策略占比：{strategy['steady_ratio']}%"],
                    "major": f"建议方向：{' / '.join(top_major_names[:2]) if top_major_names else '待定'}",
                    "reason": "更适合做正式志愿主体，后续按官方位次和专业组微调。",
                }
            ],
        },
        {
            "title": "保一保",
            "note": f"建议占比约 {strategy['safe_ratio']}%，重点防止滑档，同时兼顾专业可接受性。",
            "tagLabel": "相对安全",
            "tagVariant": "success",
            "cards": [
                {
                    "school": f"{student.get('province') or '本省'}保底院校池",
                    "detail": "优先控制滑档与调剂风险。",
                    "metrics": [*shared_metrics, f"策略占比：{strategy['safe_ratio']}%"],
                    "major": f"建议保底方向：{top_major_names[-1] if top_major_names else '待定'}",
                    "reason": "保底不只是看能否录取，更要看后续学习体验和就业去向是否可接受。",
                }
            ],
        },
    ]
    return columns, strategy


def _build_rule_summary(student: dict[str, Any], major_results: list[dict[str, Any]], strategy: dict[str, Any]) -> dict[str, Any]:
    score_profile = evaluate_score_profile(student)
    student_subjects = sorted(infer_student_subjects(student))
    top_majors = []
    for item in major_results[:3]:
        top_majors.append(
            {
                "name": item["row"].get("category_name") or "专业方向",
                "subject_label": item["subject_fit"]["label"],
                "score_label": item["score_fit"]["label"],
                "match_score": item["composite_score"],
            }
        )

    return {
        "scoreLevel": score_profile["level"]["label"],
        "scoreComment": score_profile["comment"],
        "riskLevel": score_profile["risk_level"],
        "riskItems": score_profile["risk_items"],
        "studentSubjects": student_subjects,
        "strategy": strategy,
        "topMajors": top_majors,
    }


def _build_derived_profile_summary(student: dict[str, Any]) -> dict[str, Any]:
    derived_profile = student.get("derived_profile") or {}
    pillars = derived_profile.get("pillars") or {}
    wuxing = derived_profile.get("wuxing") or {}
    profile = derived_profile.get("profile") or {}

    personality_traits = [item for item in profile.get("personalityTraits") or [] if item]
    interest_directions = [item for item in profile.get("interestDirections") or [] if item]
    region_preferences = [item for item in profile.get("regionPreferences") or [] if item]
    development_goals = [item for item in profile.get("developmentGoals") or [] if item]
    learning_style = " / ".join(item for item in profile.get("learningStyle") or [] if item)

    return {
        "constellation": derived_profile.get("constellation"),
        "birthday": derived_profile.get("birthday"),
        "birthTime": derived_profile.get("birthTime"),
        "pillars": {
            "year": pillars.get("year") or student.get("bazi_year_pillar"),
            "month": pillars.get("month") or student.get("bazi_month_pillar"),
            "day": pillars.get("day") or student.get("bazi_day_pillar"),
            "hour": pillars.get("hour") or student.get("bazi_hour_pillar"),
        },
        "hourBranchLabel": derived_profile.get("hourBranchLabel"),
        "wuxing": {
            "dominant": wuxing.get("dominant"),
            "secondary": wuxing.get("secondary"),
            "counts": wuxing.get("counts") or {},
        },
        "personalityTraits": personality_traits,
        "learningStyle": learning_style,
        "decisionStyle": "更适合把兴趣方向和正式规则一起拆解后再做选择。" if personality_traits else "",
        "stressStyle": "更适合把正式位次、选科要求和家长诉求拆开逐项确认。" if personality_traits else "",
        "socialStyle": "建议通过老师和家长协同沟通，确认学生对专业与城市的真实接受度。" if personality_traits else "",
        "interestDirections": interest_directions,
        "regionPreferences": region_preferences,
        "developmentGoals": development_goals,
        "explanations": profile.get("explanations") or derived_profile.get("explanations") or [],
        "disclaimer": derived_profile.get("disclaimer") or COMPLIANCE_DISCLAIMER,
    }


def _build_report_sections(
    student: dict[str, Any],
    major_results: list[dict[str, Any]],
    city_results: list[dict[str, Any]],
    strategy: dict[str, Any],
    portrait_recommendation: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    score_profile = evaluate_score_profile(student)
    top_major_names = [item["row"].get("category_name") or "专业方向" for item in major_results[:3]]
    portrait_recommendation = portrait_recommendation or _build_portrait_major_recommendation(student)
    if not top_major_names:
        top_major_names = portrait_recommendation.get("recommendedMajorDirections") or []
    top_city_names = [item["row"].get("city_name") or "目标城市" for item in city_results[:3]]
    derived_profile = _build_derived_profile_summary(student)
    pillars = derived_profile["pillars"]
    four_pillars = " / ".join(
        [value for value in (pillars["year"], pillars["month"], pillars["day"], pillars["hour"]) if value]
    ) or "待补充"
    trait_text = "、".join(derived_profile["personalityTraits"][:4]) or "待结合更多信息补充"
    interest_text = "、".join(derived_profile["interestDirections"][:3]) or "待结合成绩与兴趣完善"
    region_text = "、".join(derived_profile["regionPreferences"][:3]) or "待结合家庭偏好完善"
    development_text = "、".join(derived_profile["developmentGoals"][:3]) or "待结合目标路径完善"
    city_industry_notes = [
        f"{item['row'].get('city_name') or '目标城市'}：{item['row'].get('leading_industries') or '待补充产业信息'}"
        for item in city_results[:3]
    ]

    return [
        {
            "title": "学生基本信息",
            "body": (
                f"{student.get('name') or '该学生'}，"
                f"{student.get('province') or '待补充省份'}，"
                f"{student.get('exam_year') or datetime.now().year} 届"
                f"{EXAM_TYPE_LABELS.get(student.get('exam_type') or 'gaokao', '高考')}考生，"
                f"当前选科/方向为 {student.get('subject_group') or '待补充'}。"
            ),
        },
        {
            "title": "八字四柱与星座辅助分析",
            "body": (
                f"阳历生日 {derived_profile.get('birthday') or '待补充'}，"
                f"出生时辰 {derived_profile.get('birthTime') or '待补充'}，"
                f"四柱为 {four_pillars}，星座为 {derived_profile.get('constellation') or '待补充'}。"
                f"当前辅助倾向显示，核心特质更偏向 {trait_text}；"
                f"五行主导为 {derived_profile['wuxing'].get('dominant') or '待识别'}，"
                f"次要倾向为 {derived_profile['wuxing'].get('secondary') or '待识别'}。"
                "这一层只用于解释学生天赋风格、环境适配与沟通方式，不替代真实志愿数据判断。"
            ),
        },
        {
            "title": "分数与位次分析",
            "body": (
                f"当前总分约为 {score_profile['total_score']}，位次 {score_profile['rank'] or '待补充'}，"
                f"处于“{score_profile['level']['label']}”。{score_profile['comment']}"
            ),
        },
        {
            "title": "专业方向建议",
            "body": (
                f"当前更建议优先关注 {', '.join(portrait_recommendation.get('recommendedMajorDirections')[:3]) if portrait_recommendation.get('recommendedMajorDirections') else ', '.join(top_major_names) if top_major_names else '目标专业方向'}。"
                f"硬条件层面，系统会先核对选科组合、正式高考成绩、全省位次和批次信息；"
                f"辅助解释层面，当前兴趣与画像更偏向 {interest_text}。"
                "正式筛选时仍需逐校逐专业核对选科要求、录取分数和调剂规则。"
            ),
        },
        {
            "title": "城市与区域建议",
            "body": (
                f"优先关注 {', '.join(top_city_names) if top_city_names else '目标城市'} 等资源更匹配的区域。"
                f"辅助区域倾向更偏向 {region_text}，发展路径偏向 {development_text}，"
                "建议继续结合产业机会、生活节奏、家庭距离与消费水平综合决策。"
            ),
        },
        {
            "title": "城市产业匹配建议",
            "body": (
                f"当前城市产业样本更偏向 {'；'.join(city_industry_notes) if city_industry_notes else '待补充城市产业库'}。"
                "正式生成可售卖报告时，建议把目标专业、目标城市和当地实习就业机会一起解释给家长。"
            ),
        },
        {
            "title": "冲稳保策略建议",
            "body": (
                f"当前建议采用“冲 {strategy['rush_ratio']}% / 稳 {strategy['steady_ratio']}% / 保 {strategy['safe_ratio']}%”的结构，"
                "正式提交前建议进行一次人工复核，并补上当年最新招生计划与位次校准。"
            ),
        },
        {
            "title": "名校策略建议",
            "body": (
                "如果家庭更看重名校平台，建议提前讲清楚学校层次、专业热度、培养成本和调剂接受度之间的取舍。"
                "名校优先不等于盲目追热门，重点是确认孩子是否愿意在该专业路径上持续投入。"
            ),
        },
        {
            "title": "家长沟通建议",
            "body": (
                _build_parent_guidance(student, top_major_names, top_city_names)
                + f" 当前画像辅助推荐判断：{portrait_recommendation.get('parentConcernMatch', {}).get('details') or '待补充家长诉求说明。'}"
            ),
        },
        {
            "title": "未来发展路径建议",
            "body": _build_future_path_text(top_major_names, top_city_names),
        },
        {
            "title": "风险提示与免责说明",
            "body": COMPLIANCE_DISCLAIMER,
            "warning": True,
        },
    ]


def get_dashboard_data() -> dict[str, Any]:
    today_text = datetime.now().strftime("%Y-%m-%d")
    with db_session() as connection:
        total_students = connection.execute("SELECT COUNT(*) AS total FROM students").fetchone()["total"]
        today_students = connection.execute(
            "SELECT COUNT(*) AS total FROM students WHERE substr(created_at, 1, 10) = ?",
            (today_text,),
        ).fetchone()["total"]
        pending_review = connection.execute(
            "SELECT COUNT(*) AS total FROM students WHERE status = 'review_pending'"
        ).fetchone()["total"]
        reviewed = connection.execute(
            "SELECT COUNT(*) AS total FROM students WHERE status = 'reviewed'"
        ).fetchone()["total"]
        high_risk = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM students
            LEFT JOIN scores ON scores.student_id = students.id
            WHERE scores.total_score IS NULL OR scores.total_score <= 0 OR scores.rank IS NULL
            """
        ).fetchone()["total"]
        recent_rows = connection.execute(
            """
            SELECT
                students.*,
                scores.total_score,
                scores.rank
            FROM students
            LEFT JOIN scores ON scores.student_id = students.id
            ORDER BY students.updated_at DESC, students.id DESC
            LIMIT 5
            """
        ).fetchall()

    recent_students = []
    for row in recent_rows:
        student = dict(row)
        tag = _status_tag(student)
        score_text = "待补充分数"
        if student.get("total_score") not in (None, ""):
            score_text = f"当前总分 {round(safe_number(student['total_score']), 1)}"
        recent_students.append(
            {
                "name": student.get("name") or "未命名学生",
                "detail": f"{student.get('province') or '待补充省份'} / {student.get('subject_group') or '待补充方向'} / {score_text}",
                "tag": tag["variant"],
                "tagLabel": tag["label"],
            }
        )

    return {
        "metrics": [
            {
                "title": "今日新增学生",
                "value": str(today_students).zfill(2),
                "note": f"当前累计学生档案 {total_students} 份。",
                "variant": "default",
            },
            {
                "title": "待人工复核",
                "value": str(pending_review).zfill(2),
                "note": "建议优先处理待复核与信息未完善学生。",
                "variant": "default",
            },
            {
                "title": "已复核学生",
                "value": str(reviewed).zfill(2),
                "note": "可作为正式报告和后续交付的优先对象。",
                "variant": "default",
            },
            {
                "title": "高风险档案",
                "value": str(high_risk).zfill(2),
                "note": "分数、位次或核心信息不完整，需要尽快补齐。",
                "variant": "risk",
            },
        ],
        "quickActions": [
            {"title": "学生管理", "description": "查看档案、更新状态、安排复核", "target": "students"},
            {"title": "录入新学生", "description": "新增学生档案并录入基础成绩", "target": "intake"},
            {"title": "查看分析页", "description": "按真实学生档案查看分析结果", "target": "analysis"},
            {"title": "进入报告页", "description": "查看真实学生的报告预览与风险提示", "target": "reports"},
        ],
        "recentStudents": recent_students,
    }


def get_settings_data() -> dict[str, Any]:
    return {
        "copyRules": list(COMPLIANCE_COPY_RULES),
        "boundaryNote": INTERFACE_BOUNDARY_NOTE,
    }


def get_student_analysis(student_id: int) -> dict[str, Any]:
    student = fetch_student_or_404(student_id)
    admissions_bundle = _get_real_admissions_bundle(student)
    portrait_recommendation = _build_portrait_major_recommendation(student, admissions_bundle)
    if admissions_bundle.get("candidates"):
        major_cards = _build_real_major_cards(admissions_bundle)
        _, strategy = build_plan_columns_from_candidates(admissions_bundle["candidates"], admissions_bundle["context"])
        policy_highlights = _fetch_policy_highlights(student, admissions_bundle, limit=3)
        score_profile = evaluate_score_profile(student)
        tag = _status_tag(student)
        context = admissions_bundle["context"]
        result_source = _build_result_source(student, admissions_bundle, used_real_candidates=True)

        warnings = [
            *score_profile["risk_items"],
            "当前结果已切换为真实招生表驱动，但正式填报前仍需复核院校章程、计划变化和调剂规则。",
            COMPLIANCE_DISCLAIMER,
        ]
        if context.get("rank_source") == "score_segments_estimate":
            warnings.insert(0, "当前位次来自一分一段表估算，正式填报前请换成官方位次。")
        context_notice = _real_context_notice(context)
        if context_notice:
            warnings.insert(0, context_notice)
        for item in admissions_bundle["candidates"][:4]:
            for risk in item.get("risks") or []:
                risk_message = f"{item.get('institution_name') or '目标院校'}-{item.get('major_name') or '目标专业'}：{risk['label']}，{risk['note']}"
                if risk_message not in warnings:
                    warnings.append(risk_message)
        warnings = warnings[:10]

        return {
            "hasStudent": True,
            "studentId": student_id,
            "summary": {
                "name": student.get("name") or "未命名学生",
                "meta": (
                    f"{student.get('province') or '待补充省份'} / "
                    f"{student.get('exam_year') or '待补充年份'} 届 / "
                    f"{student.get('subject_group') or '待补充方向'} / "
                    f"当前状态：{tag['label']}"
                ),
                "tags": [
                    {"label": tag["label"], "variant": tag["variant"]},
                    {"label": EXAM_TYPE_LABELS.get(student.get("exam_type") or "gaokao", "高考"), "variant": "primary"},
                ],
            },
            "metrics": [
                {"title": "当前总分", "value": f"{score_profile['total_score']}", "note": "来自学生档案中的当前有效分数。"},
                {"title": "当前位次", "value": str(context.get("rank") or "待补充"), "note": "已优先使用正式位次，其次才使用一分一段估算。"},
                {"title": "真实候选数", "value": str(len(admissions_bundle["candidates"])), "note": f"基于 {context.get('latest_year') or '最近'} 年真实招生数据筛出。"},
                {"title": "冲稳保比例", "value": f"{strategy['rush_ratio']}/{strategy['steady_ratio']}/{strategy['safe_ratio']}", "note": "来自真实候选分布的分层建议。"},
            ],
            "buckets": _build_real_analysis_buckets(admissions_bundle["candidates"]),
            "subjectBars": _subject_bars(student),
            "warnings": warnings,
            "ruleSummary": _build_real_rule_summary(student, admissions_bundle, strategy, major_cards, portrait_recommendation),
            "derivedProfile": _build_derived_profile_summary(student),
            "portraitRecommendation": portrait_recommendation,
            "policyHighlights": policy_highlights,
            "resultSource": result_source,
        }

    major_results = _major_rule_results(student)
    strategy = evaluate_strategy(evaluate_score_profile(student), major_results)
    score_profile = evaluate_score_profile(student)
    tag = _status_tag(student)

    warnings = [
        *score_profile["risk_items"],
        "当前分析仍需结合当年正式位次、一分一段表和招生计划复核。",
        "若院校专业组、选科要求或调剂规则发生变化，方案需要同步调整。",
        COMPLIANCE_DISCLAIMER,
    ]
    result_source = _build_result_source(student, admissions_bundle, used_real_candidates=False)

    return {
        "hasStudent": True,
        "studentId": student_id,
        "summary": {
            "name": student.get("name") or "未命名学生",
            "meta": (
                f"{student.get('province') or '待补充省份'} / "
                f"{student.get('exam_year') or '待补充年份'} 届 / "
                f"{student.get('subject_group') or '待补充方向'} / "
                f"当前状态：{tag['label']}"
            ),
            "tags": [
                {"label": tag["label"], "variant": tag["variant"]},
                {"label": EXAM_TYPE_LABELS.get(student.get("exam_type") or "gaokao", "高考"), "variant": "primary"},
            ],
        },
        "metrics": [
            {"title": "当前总分", "value": f"{score_profile['total_score']}", "note": "来自当前学生档案中的最新成绩快照。"},
            {"title": "当前位次", "value": str(score_profile["rank"] or "待补充"), "note": "正式方案应以当年官方位次为准。"},
            {
                "title": "冲稳保比例",
                "value": f"{strategy['rush_ratio']}/{strategy['steady_ratio']}/{strategy['safe_ratio']}",
                "note": "分别对应冲刺、稳妥、保底建议占比。",
            },
        ],
        "buckets": [
            {
                "key": "rush",
                "title": "冲一冲",
                "note": f"建议占比约 {strategy['rush_ratio']}%，适合少量上探。",
                "tagLabel": "风险较高",
                "tagVariant": "warning",
                "items": [
                    f"优先方向：{major_results[0]['row'].get('category_name') if major_results else portrait_recommendation.get('preferredDirection') or '待补充画像信息'}",
                    f"规则说明：{major_results[0]['score_fit']['label'] if major_results else '待补充'}",
                ],
            },
            {
                "key": "steady",
                "title": "稳一稳",
                "note": f"建议占比约 {strategy['steady_ratio']}%，应作为方案主体。",
                "tagLabel": "建议主力",
                "tagVariant": "primary",
                "items": [
                    f"主力方向：{major_results[1]['row'].get('category_name') if len(major_results) > 1 else major_results[0]['row'].get('category_name') if major_results else portrait_recommendation.get('preferredDirection') or '待补充画像信息'}",
                    "重点结合位次、选科要求和正式招生规则复核。",
                ],
            },
            {
                "key": "safe",
                "title": "保一保",
                "note": f"建议占比约 {strategy['safe_ratio']}%，重点防止滑档。",
                "tagLabel": "相对安全",
                "tagVariant": "success",
                "items": [
                    f"保底方向：{major_results[-1]['row'].get('category_name') if major_results else portrait_recommendation.get('preferredDirection') or '待补充画像信息'}",
                    "正式提交前需核对服从调剂与退档规则。",
                ],
            },
        ],
        "subjectBars": _subject_bars(student),
        "warnings": warnings,
        "ruleSummary": _apply_portrait_summary(_build_rule_summary(student, major_results, strategy), portrait_recommendation),
        "derivedProfile": _build_derived_profile_summary(student),
        "portraitRecommendation": portrait_recommendation,
        "resultSource": result_source,
    }


def get_student_majors(student_id: int) -> dict[str, Any]:
    student = fetch_student_or_404(student_id)
    admissions_bundle = _get_real_admissions_bundle(student)
    portrait_recommendation = _build_portrait_major_recommendation(student, admissions_bundle)
    if admissions_bundle.get("candidates"):
        rows = _build_real_major_cards(admissions_bundle)
        _, strategy = build_plan_columns_from_candidates(admissions_bundle["candidates"], admissions_bundle["context"])
        return {
            "hasStudent": True,
            "studentId": student_id,
            "rows": rows,
            "ruleSummary": _build_real_rule_summary(student, admissions_bundle, strategy, rows, portrait_recommendation),
            "portraitRecommendation": portrait_recommendation,
            "derivedProfile": _build_derived_profile_summary(student),
            "disclaimer": COMPLIANCE_DISCLAIMER,
            "resultSource": _build_result_source(student, admissions_bundle, used_real_candidates=True),
        }

    major_results = _major_rule_results(student)
    return {
        "hasStudent": True,
        "studentId": student_id,
        "rows": _build_major_cards(major_results),
        "ruleSummary": _apply_portrait_summary(
            _build_rule_summary(student, major_results, evaluate_strategy(evaluate_score_profile(student), major_results)),
            portrait_recommendation,
        ),
        "portraitRecommendation": portrait_recommendation,
        "derivedProfile": _build_derived_profile_summary(student),
        "disclaimer": COMPLIANCE_DISCLAIMER,
        "resultSource": _build_result_source(student, admissions_bundle, used_real_candidates=False),
    }


def get_student_plan(student_id: int) -> dict[str, Any]:
    student = fetch_student_or_404(student_id)
    admissions_bundle = _get_real_admissions_bundle(student)
    portrait_recommendation = _build_portrait_major_recommendation(student, admissions_bundle)
    if admissions_bundle.get("candidates"):
        columns, strategy = build_plan_columns_from_candidates(admissions_bundle["candidates"], admissions_bundle["context"])
        major_cards = _build_real_major_cards(admissions_bundle)
        structured_recommendations = _build_structured_recommendations(student, admissions_bundle)
        return {
            "hasStudent": True,
            "studentId": student_id,
            "columns": columns,
            "ruleSummary": _build_real_rule_summary(student, admissions_bundle, strategy, major_cards, portrait_recommendation),
            "recommendationTable": structured_recommendations["recommendationTable"],
            "firstChoice": structured_recommendations["firstChoice"],
            "alternatives": structured_recommendations["alternatives"],
            "notRecommended": structured_recommendations["notRecommended"],
            "portraitRecommendation": portrait_recommendation,
            "disclaimer": COMPLIANCE_DISCLAIMER,
            "resultSource": _build_result_source(student, admissions_bundle, used_real_candidates=True),
        }

    major_results = _major_rule_results(student)
    city_results = _city_rule_results(student, major_results)
    columns, strategy = _build_plan_columns(student, major_results, city_results, portrait_recommendation)
    return {
        "hasStudent": True,
        "studentId": student_id,
        "columns": columns,
        "ruleSummary": _apply_portrait_summary(_build_rule_summary(student, major_results, strategy), portrait_recommendation),
        "portraitRecommendation": portrait_recommendation,
        "disclaimer": COMPLIANCE_DISCLAIMER,
        "resultSource": _build_result_source(student, admissions_bundle, used_real_candidates=False),
    }


def get_student_report(
    student_id: int,
    product_code: str | None = None,
    generated_by: str | None = None,
    generation_mode: str = "preview",
) -> dict[str, Any]:
    student = fetch_student_or_404(student_id)
    selected_product_code = _normalize_report_product_code(product_code)
    report_products = _build_report_product_catalog(selected_product_code)
    admissions_bundle = _get_real_admissions_bundle(student)
    portrait_recommendation = _build_portrait_major_recommendation(student, admissions_bundle)
    if admissions_bundle.get("candidates"):
        _, strategy = build_plan_columns_from_candidates(admissions_bundle["candidates"], admissions_bundle["context"])
        major_cards = _build_real_major_cards(admissions_bundle)
        structured_recommendations = _build_structured_recommendations(student, admissions_bundle)
        policy_highlights = _fetch_policy_highlights(student, admissions_bundle, limit=3)
        result_source = _build_result_source(student, admissions_bundle, used_real_candidates=True)
        sections = _inject_policy_section(
            _build_real_report_sections(student, admissions_bundle, strategy, major_cards, policy_highlights, portrait_recommendation),
            policy_highlights,
        )
        matched_majors = [item.get("title") or "专业方向" for item in major_cards[:4]]
        matched_cities = list(dict.fromkeys([item.get("city_text") or "目标地区" for item in admissions_bundle["candidates"][:4]]))
        rule_summary = _build_real_rule_summary(student, admissions_bundle, strategy, major_cards, portrait_recommendation)
        derived_profile = _build_derived_profile_summary(student)
        report_title = f"{student.get('name') or '学生'} 志愿规划报告预览"
        _create_report_generation_record(
            student_id=student_id,
            product_code=selected_product_code,
            report_title=report_title,
            rule_summary=rule_summary,
            matched_majors=matched_majors,
            matched_cities=matched_cities,
            generated_by=generated_by,
            generation_mode=generation_mode,
        )
        advisor_notes = _list_report_advisor_notes(student_id, selected_product_code)
        generation_records = _list_report_generation_records(student_id, selected_product_code)
        delivery_records = _list_report_delivery_records(student_id, selected_product_code)
        sections = _build_manual_consultation_sections(
            student=student,
            selected_product_code=selected_product_code,
            sections=sections,
            advisor_notes=advisor_notes,
            generation_records=generation_records,
            delivery_records=delivery_records,
            matched_majors=matched_majors,
            matched_cities=matched_cities,
        )
        sections = _polish_sections_for_export(sections)
        return {
            "hasStudent": True,
            "studentId": student_id,
            "activeProductCode": selected_product_code,
            "activeProductLabel": REPORT_PRODUCT_CONFIG[selected_product_code]["label"],
            "reportProducts": report_products,
            "reportTitle": report_title,
            "reportSubtitle": (
                f"{student.get('province') or '待补充省份'} / "
                f"{student.get('exam_year') or datetime.now().year} 届 / "
                f"{student.get('subject_group') or '待补充方向'}"
            ),
            "outline": [f"{index}. {section['title']}" for index, section in enumerate(sections, start=1)],
            "sections": sections,
            "matchedMajors": matched_majors,
            "matchedCities": matched_cities,
            "ruleSummary": rule_summary,
            "recommendationTable": structured_recommendations["recommendationTable"],
            "firstChoice": structured_recommendations["firstChoice"],
            "alternatives": structured_recommendations["alternatives"],
            "notRecommended": structured_recommendations["notRecommended"],
            "derivedProfile": derived_profile,
            "portraitRecommendation": portrait_recommendation,
            "policyHighlights": policy_highlights,
            "advisorNotes": advisor_notes,
            "generationRecords": generation_records,
            "deliveryRecords": delivery_records,
            "resultSource": result_source,
            "reportJson": _build_formal_report_json(
                student=student,
                product_code=selected_product_code,
                sections=sections,
                rule_summary=rule_summary,
                derived_profile=derived_profile,
                matched_majors=matched_majors,
                matched_cities=matched_cities,
                policy_highlights=policy_highlights,
                advisor_notes=advisor_notes,
                delivery_records=delivery_records,
                portrait_recommendation=portrait_recommendation,
                structured_recommendations=structured_recommendations,
                result_source=result_source,
            ),
            "disclaimer": COMPLIANCE_DISCLAIMER,
            "boundaryNote": INTERFACE_BOUNDARY_NOTE,
            "copyRules": list(COMPLIANCE_COPY_RULES),
        }

    major_results = _major_rule_results(student)
    city_results = _city_rule_results(student, major_results)
    _, strategy = _build_plan_columns(student, major_results, city_results, portrait_recommendation)
    sections = _build_report_sections(student, major_results, city_results, strategy, portrait_recommendation)
    matched_majors = [item["row"].get("category_name") or "专业方向" for item in major_results[:4]]
    matched_cities = [item["row"].get("city_name") or "目标城市" for item in city_results[:4]]
    rule_summary = _apply_portrait_summary(_build_rule_summary(student, major_results, strategy), portrait_recommendation)
    derived_profile = _build_derived_profile_summary(student)
    result_source = _build_result_source(student, admissions_bundle, used_real_candidates=False)
    report_title = f"{student.get('name') or '学生'} 志愿规划报告预览"
    _create_report_generation_record(
        student_id=student_id,
        product_code=selected_product_code,
        report_title=report_title,
        rule_summary=rule_summary,
        matched_majors=matched_majors,
        matched_cities=matched_cities,
        generated_by=generated_by,
        generation_mode=generation_mode,
    )
    advisor_notes = _list_report_advisor_notes(student_id, selected_product_code)
    generation_records = _list_report_generation_records(student_id, selected_product_code)
    delivery_records = _list_report_delivery_records(student_id, selected_product_code)
    sections = _build_manual_consultation_sections(
        student=student,
        selected_product_code=selected_product_code,
        sections=sections,
        advisor_notes=advisor_notes,
        generation_records=generation_records,
        delivery_records=delivery_records,
        matched_majors=matched_majors,
        matched_cities=matched_cities,
    )
    sections = _polish_sections_for_export(sections)
    return {
        "hasStudent": True,
        "studentId": student_id,
        "activeProductCode": selected_product_code,
        "activeProductLabel": REPORT_PRODUCT_CONFIG[selected_product_code]["label"],
        "reportProducts": report_products,
        "reportTitle": report_title,
        "reportSubtitle": (
            f"{student.get('province') or '待补充省份'} / "
            f"{student.get('exam_year') or datetime.now().year} 届 / "
            f"{student.get('subject_group') or '待补充方向'}"
        ),
        "outline": [f"{index}. {section['title']}" for index, section in enumerate(sections, start=1)],
        "sections": sections,
        "matchedMajors": matched_majors,
        "matchedCities": matched_cities,
        "ruleSummary": rule_summary,
        "derivedProfile": derived_profile,
        "portraitRecommendation": portrait_recommendation,
        "advisorNotes": advisor_notes,
        "generationRecords": generation_records,
        "deliveryRecords": delivery_records,
        "resultSource": result_source,
        "reportJson": _build_formal_report_json(
            student=student,
            product_code=selected_product_code,
            sections=sections,
            rule_summary=rule_summary,
            derived_profile=derived_profile,
            matched_majors=matched_majors,
            matched_cities=matched_cities,
            advisor_notes=advisor_notes,
            delivery_records=delivery_records,
            portrait_recommendation=portrait_recommendation,
            structured_recommendations=None,
            result_source=result_source,
        ),
        "disclaimer": COMPLIANCE_DISCLAIMER,
        "boundaryNote": INTERFACE_BOUNDARY_NOTE,
        "copyRules": list(COMPLIANCE_COPY_RULES),
    }


def get_default_student_id() -> int | None:
    return _fetch_latest_student_id()
