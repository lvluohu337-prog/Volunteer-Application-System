from __future__ import annotations

import re
from typing import Any


SUBJECT_ALIASES = {
    "思想政治": "政治",
    "政治": "政治",
    "物理": "物理",
    "历史": "历史",
    "化学": "化学",
    "生物": "生物",
    "地理": "地理",
}

SUBJECT_ORDER = ["物理", "历史", "化学", "生物", "政治", "地理", "思想政治"]
UNRESTRICTED_TOKENS = {"不限", "选考不限", "再选不限", "不提科目要求", "无科目要求"}
ALL_OF_TOKENS = ("2科必选", "两科必选", "均须选考", "均应选考", "均必选", "必须选考")
ONE_OF_TOKENS = ("任选1门", "任选一门", "选考其中一门即可", "至少选考1门", "至少选考一门", "任意一门")


def _normalize_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = text.replace("（", "(").replace("）", ")")
    text = text.replace("，", ",").replace("；", ";").replace("、", "/")
    text = re.sub(r"\s+", "", text)
    return text


def _unique(items: list[str]) -> list[str]:
    result: list[str] = []
    seen = set()
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _extract_subjects(text: str) -> list[str]:
    subjects: list[str] = []
    for token in SUBJECT_ORDER:
        if token in text:
            subjects.append(SUBJECT_ALIASES.get(token, token))
    return _unique(subjects)


def _subject_text(items: list[str]) -> str | None:
    cleaned = _unique([item for item in items if item])
    return ";".join(cleaned) if cleaned else None


def parse_subject_requirement(requirement_text: str | None) -> dict[str, str | None]:
    raw_text = str(requirement_text or "").strip()
    text = _normalize_text(raw_text)
    if not text:
        return {
            "required_subjects": None,
            "optional_subjects": None,
            "forbidden_subjects": None,
            "match_mode": "review",
        }

    if text in UNRESTRICTED_TOKENS or "不限" == text:
        return {
            "required_subjects": None,
            "optional_subjects": None,
            "forbidden_subjects": None,
            "match_mode": "unrestricted",
        }

    required: list[str] = []
    optional: list[str] = []
    forbidden: list[str] = []
    mode = "review"

    first_subject: str | None = None
    if "首选物理" in text:
        first_subject = "物理"
    elif "首选历史" in text:
        first_subject = "历史"
    if first_subject:
        required.append(first_subject)

    if "再选" in text:
        _, tail = text.split("再选", 1)
    else:
        tail = text

    if "不得选考" in tail:
        _, forbidden_text = tail.split("不得选考", 1)
        forbidden.extend(_extract_subjects(forbidden_text))
        tail = tail.split("不得选考", 1)[0]

    tail_subjects = _extract_subjects(tail)

    if first_subject and (not tail or tail == "不限" or "不限" in tail):
        mode = "first_subject_only"
    elif any(token in tail for token in ALL_OF_TOKENS):
        required.extend(tail_subjects)
        mode = "first_plus_all_of" if first_subject else "all_of"
    elif any(token in tail for token in ONE_OF_TOKENS):
        optional.extend(tail_subjects)
        mode = "first_plus_one_of" if first_subject else "one_of"
    elif tail_subjects:
        if first_subject:
            if len(tail_subjects) == 1:
                required.extend(tail_subjects)
                mode = "first_plus_single"
            else:
                optional.extend(tail_subjects)
                mode = "first_plus_one_of"
        else:
            if len(tail_subjects) == 1:
                required.extend(tail_subjects)
                mode = "single_subject"
            else:
                optional.extend(tail_subjects)
                mode = "one_of"
    elif first_subject:
        mode = "first_subject_only"

    if mode == "review":
        mentioned = _extract_subjects(text)
        if mentioned:
            required.extend(mentioned)
            mode = "single_subject" if len(mentioned) == 1 else "one_of"

    return {
        "required_subjects": _subject_text(required),
        "optional_subjects": _subject_text(optional),
        "forbidden_subjects": _subject_text(forbidden),
        "match_mode": mode,
    }
