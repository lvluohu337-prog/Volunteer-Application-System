from __future__ import annotations

import re
from typing import Any


RULE_DEFINITIONS = [
    {
        "rule_type": "language_requirement",
        "rule_title": "外语语种与英语单科要求",
        "keywords": [
            "只招英语考生",
            "外语语种为英语",
            "英语语种考生",
            "英语专业只招英语考生",
            "英语单科成绩",
            "英语成绩不得低于",
            "英语口语成绩",
            "英语口试成绩",
            "公共外语为英语",
        ],
    },
    {
        "rule_type": "physical_requirement",
        "rule_title": "体检与身体条件限制",
        "keywords": [
            "体检",
            "身体健康状况",
            "色盲",
            "色弱",
            "视力",
            "身高",
            "体能测试",
        ],
    },
    {
        "rule_type": "adjustment_policy",
        "rule_title": "专业调剂与退档规则",
        "keywords": [
            "不予调剂",
            "服从专业调剂",
            "专业调剂",
            "调剂到",
            "退档",
            "征集志愿",
        ],
    },
    {
        "rule_type": "cooperative_education",
        "rule_title": "中外合作办学与国际项目要求",
        "keywords": [
            "中外合作办学",
            "合作办学",
            "国际学院",
            "双学位",
            "外培计划",
            "双培计划",
        ],
    },
    {
        "rule_type": "special_program",
        "rule_title": "专项计划与特殊类型招生要求",
        "keywords": [
            "专项计划",
            "高校专项",
            "国家专项",
            "强基计划",
            "高水平运动队",
            "高水平艺术团",
            "飞行技术",
            "飞行学员",
            "公安",
            "军队",
        ],
    },
    {
        "rule_type": "subject_selection_reference",
        "rule_title": "选考科目要求须结合省级目录复核",
        "keywords": [
            "选考科目要求",
            "选考科目范围",
            "高考综合改革",
            "符合其本科",
            "符合相应专业对选考科目的要求",
        ],
    },
]

GENERAL_POLICY_KEY = "henan_2026_general_regulation"

GENERAL_POLICY_TOPICS = {
    "language_requirement": "language_requirement",
    "physical_requirement": "physical_requirement",
    "adjustment_policy": "adjustment_policy",
    "cooperative_education": "cooperative_education",
    "subject_selection_reference": "subject_selection_reference",
    "special_program": "special_program",
}

SPECIAL_PROGRAM_POLICY_MATCHERS = [
    ("henan_2025_special_plan", "special_plan", ("专项计划", "国家专项", "高校专项", "地方专项")),
    ("henan_2025_military_colleges", "military", ("军队", "军校", "国防", "飞行学员", "飞行技术")),
    ("henan_2025_sergeant", "sergeant", ("定向培养军士", "军士")),
    ("henan_2025_police", "police", ("公安", "警察", "司法警官")),
    ("henan_2025_high_level_sports", "high_level_sports", ("高水平运动队", "高水平艺术团")),
]


def _normalize_text(value: Any) -> str:
    text = str(value or "").replace("\u3000", " ").strip()
    if not text:
        return ""
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    return text


def _split_sentences(text: str) -> list[str]:
    compact = _normalize_text(text)
    if not compact:
        return []
    parts = re.split(r"[。；;！？\n]+", compact)
    sentences: list[str] = []
    seen: set[str] = set()
    for part in parts:
        item = part.strip(" ，,")
        if item and item not in seen:
            seen.add(item)
            sentences.append(item)
    return sentences


def _pick_snippets(text: str, keywords: list[str], limit: int = 2) -> list[str]:
    sentences = _split_sentences(text)
    if not sentences:
        return []
    picked: list[str] = []
    seen: set[str] = set()
    for keyword in keywords:
        for sentence in sentences:
            if keyword in sentence and sentence not in seen:
                seen.add(sentence)
                picked.append(sentence)
                if len(picked) >= limit:
                    return picked
    return picked


def _parse_exam_year(title: str, default_year: int = 2021) -> int:
    text = title or ""
    if "20201年" in text:
        return 2021

    exact_matches = [int(item) for item in re.findall(r"(20\d{2})年", text)]
    if default_year in exact_matches:
        return default_year
    if exact_matches:
        return exact_matches[0]

    fuzzy_matches = [int(item) for item in re.findall(r"(20\d{2})", text)]
    in_range = [item for item in fuzzy_matches if 2017 <= item <= 2026]
    if default_year in in_range:
        return default_year
    if in_range:
        return in_range[0]
    return default_year


def _infer_policy_metadata(rule_type: str, snippets: list[str], notes: str) -> dict[str, str]:
    text = " ".join([rule_type, notes, *snippets])
    if rule_type == "special_program":
        for policy_key, policy_topic, keywords in SPECIAL_PROGRAM_POLICY_MATCHERS:
            if any(keyword in text for keyword in keywords):
                return {
                    "policy_key": policy_key,
                    "policy_topic": policy_topic,
                    "policy_confidence": "high",
                }

    return {
        "policy_key": GENERAL_POLICY_KEY,
        "policy_topic": GENERAL_POLICY_TOPICS.get(rule_type, rule_type),
        "policy_confidence": "high" if rule_type in GENERAL_POLICY_TOPICS else "medium",
    }


def _record_field(record: dict[str, Any], candidates: list[str], fallback_index: int) -> str:
    for candidate in candidates:
        if candidate in record:
            return str(record.get(candidate) or "")

    lowered_candidates = [candidate.lower() for candidate in candidates]
    for key, value in record.items():
        key_text = str(key)
        key_lower = key_text.lower()
        if any(candidate in key_text or candidate in key_lower for candidate in lowered_candidates):
            return str(value or "")

    values = list(record.values())
    if 0 <= fallback_index < len(values):
        return str(values[fallback_index] or "")
    return ""


def build_institution_rule_rows(
    records: list[dict[str, str]],
    source_path: str,
    province: str = "河南",
    default_year: int = 2021,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for record in records:
        institution_name = _normalize_text(
            _record_field(record, ["简章名称", "院校名称", "学校名称", "institution_name"], 0)
        )
        charter_title = _normalize_text(
            _record_field(record, ["时间", "标题", "title", "charter_title"], 1)
        )
        content = _normalize_text(
            _record_field(record, ["内容_2", "内容", "正文", "content"], 2)
        )
        if not institution_name or not content:
            continue

        source_exam_year = _parse_exam_year(charter_title or content, default_year=default_year)
        for definition in RULE_DEFINITIONS:
            snippets = _pick_snippets(content, definition["keywords"], limit=2)
            if not snippets:
                continue

            policy_meta = _infer_policy_metadata(definition["rule_type"], snippets, charter_title)
            rows.append(
                {
                    "exam_year": None,
                    "province": province,
                    "institution_name": institution_name,
                    "rule_type": definition["rule_type"],
                    "rule_title": definition["rule_title"],
                    "rule_content": "；".join(snippets),
                    "source_url": source_path,
                    "notes": charter_title or "2021 招生章程抽取",
                    "source_exam_year": source_exam_year,
                    "policy_key": policy_meta["policy_key"],
                    "policy_topic": policy_meta["policy_topic"],
                    "policy_confidence": policy_meta["policy_confidence"],
                }
            )
    return rows
