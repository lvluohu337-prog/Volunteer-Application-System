from __future__ import annotations

import re
from typing import Any


SUBJECT_LABELS = {
    "physics": "物理",
    "chemistry": "化学",
    "biology": "生物",
    "politics": "思想政治",
    "history": "历史",
    "geography": "地理",
}

SUBJECT_ALIASES = {
    "政治": "思想政治",
    "物": "物理",
    "化": "化学",
    "生": "生物",
    "史": "历史",
    "地": "地理",
    "政": "思想政治",
}

SUBJECT_NAME_SET = tuple(dict.fromkeys([*SUBJECT_LABELS.values(), *SUBJECT_ALIASES.keys()]))

MAJOR_SCORE_THRESHOLDS = {
    "计算机": 580,
    "人工智能": 595,
    "数据": 590,
    "电子信息": 575,
    "通信": 575,
    "电气": 560,
    "机械": 550,
    "自动化": 560,
    "医学": 605,
    "口腔": 620,
    "法学": 570,
    "财经": 565,
    "金融": 575,
    "师范": 545,
    "设计": 540,
    "传媒": 550,
}

CITY_COMPETITIVENESS_THRESHOLDS = {
    "北京": 610,
    "上海": 610,
    "深圳": 600,
    "杭州": 585,
    "南京": 575,
    "武汉": 565,
    "成都": 560,
    "西安": 555,
    "广州": 575,
}


def safe_number(value: Any, default: float = 0) -> float:
    if value in (None, ""):
        return float(default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def safe_int(value: Any, default: int = 0) -> int:
    if value in (None, ""):
        return int(default)
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return int(default)


def split_keywords(*values: Any) -> list[str]:
    keywords: list[str] = []
    for value in values:
        if not value:
            continue
        text = str(value).strip()
        if not text:
            continue
        for item in re.split(r"[\s,，、；;|/]+", text):
            token = item.strip()
            if token:
                keywords.append(token)
    return keywords


def infer_student_subjects(student: dict[str, Any]) -> set[str]:
    subjects = set()
    for field_key, label in SUBJECT_LABELS.items():
        if student.get(field_key) not in (None, ""):
            subjects.add(label)

    subject_group = str(student.get("subject_group") or "")
    for label in SUBJECT_LABELS.values():
        if label in subject_group:
            subjects.add(label)
    for alias, canonical in SUBJECT_ALIASES.items():
        if alias in subject_group:
            subjects.add(canonical)
    return subjects


def evaluate_score_profile(student: dict[str, Any]) -> dict[str, Any]:
    total_score = safe_number(student.get("final_score")) or safe_number(student.get("total_score"))
    rank = student.get("final_rank") or student.get("rank")

    if total_score >= 630:
        level = {"code": "elite", "label": "高分冲刺段", "rush_ratio": 25, "steady_ratio": 50, "safe_ratio": 25}
        comment = "可以在平台和专业之间做组合比较，但冲刺位次仍要严格控制。"
    elif total_score >= 600:
        level = {"code": "high", "label": "高分稳进段", "rush_ratio": 20, "steady_ratio": 55, "safe_ratio": 25}
        comment = "更适合平衡城市、专业和学校层次，保持稳中带冲。"
    elif total_score >= 560:
        level = {"code": "upper_mid", "label": "中上稳妥段", "rush_ratio": 15, "steady_ratio": 55, "safe_ratio": 30}
        comment = "建议优先保障专业适配度，再争取学校平台和城市资源。"
    elif total_score >= 520:
        level = {"code": "mid", "label": "中段优化段", "rush_ratio": 10, "steady_ratio": 50, "safe_ratio": 40}
        comment = "更要重视保底和专业接受度，避免只追学校名气。"
    else:
        level = {"code": "basic", "label": "基础保稳段", "rush_ratio": 5, "steady_ratio": 45, "safe_ratio": 50}
        comment = "建议把滑档风险控制放在前面，优先确保结果可接受。"

    risk_items: list[str] = []
    risk_level = "low"
    if total_score <= 0:
        risk_level = "high"
        risk_items.append("当前学生档案缺少有效总分，无法做可靠的分数层级判断。")
    if rank in (None, ""):
        risk_level = "medium" if risk_level == "low" else risk_level
        risk_items.append("当前缺少正式位次，冲稳保比例应按保守策略处理。")

    return {
        "total_score": round(total_score, 1),
        "rank": rank,
        "level": level,
        "comment": comment,
        "risk_level": risk_level,
        "risk_items": risk_items,
    }


def evaluate_subject_requirement(
    requirement_text: str | None,
    student_subjects: set[str],
    track_code: str | None = None,
) -> dict[str, Any]:
    requirement = str(requirement_text or "").strip()
    if not requirement:
        return {
            "status": "review",
            "score": 72,
            "label": "待复核",
            "note": "当前要求文本不完整，需要结合院校专业组规则再复核。",
        }

    if "首选物理" in requirement and track_code and track_code != "physics":
        return {
            "status": "mismatch",
            "score": 12,
            "label": "首选科目不匹配",
            "note": "该专业组首选科目要求为物理，当前学生不满足。",
        }

    if "首选历史" in requirement and track_code and track_code != "history":
        return {
            "status": "mismatch",
            "score": 12,
            "label": "首选科目不匹配",
            "note": "该专业组首选科目要求为历史，当前学生不满足。",
        }

    if "再选不限" in requirement or "不限" == requirement:
        return {
            "status": "match",
            "score": 92,
            "label": "选科匹配",
            "note": "首选科目满足要求，再选科目限制较弱。",
        }

    extra_text = requirement.split("再选", 1)[1] if "再选" in requirement else requirement
    mentioned_subjects = []
    for subject in SUBJECT_NAME_SET:
        canonical = SUBJECT_ALIASES.get(subject, subject)
        if subject in extra_text and canonical not in mentioned_subjects:
            mentioned_subjects.append(canonical)

    if not mentioned_subjects:
        return {
            "status": "review",
            "score": 76,
            "label": "待复核",
            "note": "当前要求文本未能完全结构化识别，需结合院校专业组说明复核。",
        }

    if "2科必选" in extra_text or "均须选考" in extra_text or "均必须选考" in extra_text:
        missing = [subject for subject in mentioned_subjects if subject not in student_subjects]
        if missing:
            return {
                "status": "mismatch",
                "score": 20,
                "label": "必选科目缺失",
                "note": f"该专业组要求同时具备 {'、'.join(mentioned_subjects)}，当前缺少 {'、'.join(missing)}。",
            }
        return {
            "status": "match",
            "score": 96,
            "label": "选科强匹配",
            "note": f"当前学生已具备该专业组要求的 {'、'.join(mentioned_subjects)} 组合。",
        }

    if len(mentioned_subjects) == 1:
        required_subject = mentioned_subjects[0]
        if required_subject in student_subjects:
            return {
                "status": "match",
                "score": 91,
                "label": "选科匹配",
                "note": f"当前学生包含 {required_subject}，满足该专业组常见要求。",
            }
        return {
            "status": "mismatch",
            "score": 24,
            "label": "选科不匹配",
            "note": f"该专业组要求 {required_subject}，当前学生未覆盖该科目。",
        }

    overlap = [subject for subject in mentioned_subjects if subject in student_subjects]
    if overlap:
        return {
            "status": "match",
            "score": 85,
            "label": "选科基本匹配",
            "note": f"当前学生覆盖 {'、'.join(overlap)}，但仍需复核院校对多科要求的具体解释。",
        }

    return {
        "status": "mismatch",
        "score": 28,
        "label": "选科风险",
        "note": f"该专业组常涉及 {'、'.join(mentioned_subjects)}，当前学生组合未明显覆盖。",
    }


def evaluate_major_score_fit(category_name: str, total_score: float) -> dict[str, Any]:
    threshold = 550
    for keyword, keyword_threshold in MAJOR_SCORE_THRESHOLDS.items():
        if keyword in category_name:
            threshold = keyword_threshold
            break

    diff = round(total_score - threshold, 1)
    if diff >= 25:
        return {"score": 95, "label": "分数支持较强", "note": "按经验阈值看，当前总分对该方向有较强支撑。"}
    if diff >= 5:
        return {"score": 82, "label": "分数基本支持", "note": "按经验阈值看，当前总分对该方向基本够用。"}
    if diff >= -15:
        return {"score": 68, "label": "分数边缘匹配", "note": "当前总分接近该方向经验阈值，正式填报时应保守判断。"}
    return {"score": 45, "label": "分数压力较大", "note": "当前总分对该方向存在一定压力，建议更多放在冲刺或谨慎观察区。"}


def evaluate_city_fit(city_name: str, major_text: str, student_keywords: list[str], score_profile: dict[str, Any]) -> dict[str, Any]:
    threshold = CITY_COMPETITIVENESS_THRESHOLDS.get(city_name, 550)
    total_score = score_profile["total_score"]
    score_diff = total_score - threshold
    keyword_hits = sum(1 for keyword in student_keywords if keyword and keyword in major_text)

    fit_score = 55 + min(20, keyword_hits * 6)
    fit_note = "城市产业方向与当前学生关注方向存在一定交集。"
    if score_diff >= 20:
        fit_score += 15
        fit_note = "城市资源和当前学生分数层级相对匹配，可重点关注。"
    elif score_diff >= 0:
        fit_score += 8
        fit_note = "城市层级与当前学生分数基本匹配，适合作为稳中带冲的选择。"
    else:
        fit_score -= min(18, abs(int(score_diff)) // 2)
        fit_note = "城市资源较强，但以当前分数层级看要注意竞争压力。"

    return {
        "score": max(35, min(95, fit_score)),
        "note": fit_note,
    }


def evaluate_strategy(score_profile: dict[str, Any], top_major_results: list[dict[str, Any]]) -> dict[str, Any]:
    rush_ratio = score_profile["level"]["rush_ratio"]
    steady_ratio = score_profile["level"]["steady_ratio"]
    safe_ratio = score_profile["level"]["safe_ratio"]

    if score_profile["risk_level"] == "medium":
        rush_ratio = max(5, rush_ratio - 5)
        safe_ratio = min(50, safe_ratio + 5)
    if score_profile["risk_level"] == "high":
        rush_ratio = 0
        steady_ratio = min(50, steady_ratio - 5)
        safe_ratio = max(50, safe_ratio + 10)

    average_major_score = 0
    if top_major_results:
        average_major_score = round(
            sum(item["composite_score"] for item in top_major_results[:3]) / min(3, len(top_major_results)),
            1,
        )
        if average_major_score < 70:
            rush_ratio = max(5, rush_ratio - 5)
            safe_ratio = min(55, safe_ratio + 5)

    return {
        "rush_ratio": rush_ratio,
        "steady_ratio": steady_ratio,
        "safe_ratio": safe_ratio,
        "average_major_score": average_major_score,
        "note": "该比例仅作为第一阶段规则建议，正式填报仍需结合位次、一分一段表和招生计划复核。",
    }
