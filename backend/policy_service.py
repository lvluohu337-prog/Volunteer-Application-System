from __future__ import annotations

from collections import Counter
from typing import Any, Callable


DbSessionFactory = Callable[[], Any]


STRICT_POLICY_SIGNAL_MAP = {
    "general_regulation": ("招生章程", "体检", "报名", "录取规则"),
    "registration": ("报名", "资格审核", "现场确认", "单招", "运动训练", "保送"),
    "military": ("军队", "军校", "飞行", "飞行学员", "政治考核", "军检", "只招英语"),
    "sergeant": ("军士", "定向培养军士", "政治考核", "军检"),
    "single_exam": ("单招", "高职单招", "职业技能测试", "职业适应性测试"),
    "special_plan": ("专项计划", "国家专项", "高校专项", "地方专项", "资格审核"),
    "high_level_sports": ("高水平运动队", "体育教育", "运动训练"),
    "counterpart": ("对口", "中职", "中等职业学校", "专业对照", "美术与设计类", "音乐与舞蹈类"),
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


def policy_signal_text(student: dict[str, Any], bundle: dict[str, Any]) -> str:
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


def policy_matches_signal_text(policy_key: str, signal_text: str) -> bool:
    normalized_key = str(policy_key or "")
    normalized_signal = str(signal_text or "").lower()
    if "general_regulation" in normalized_key:
        return True

    for key, tokens in STRICT_POLICY_SIGNAL_MAP.items():
        if key not in normalized_key:
            continue
        return any(token.lower() in normalized_signal for token in tokens)
    return False


def candidate_policy_keys(bundle: dict[str, Any], limit: int = 10) -> set[str]:
    keys: set[str] = set()
    for candidate in (bundle.get("candidates") or [])[:limit]:
        for risk in candidate.get("risks") or []:
            policy_key = str(risk.get("policy_key") or "").strip()
            if policy_key:
                keys.add(policy_key)
    return keys


def candidate_policy_topics(bundle: dict[str, Any], limit: int = 10) -> dict[str, str]:
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


def format_policy_highlight(item: dict[str, Any], policy_topic: str | None = None) -> dict[str, Any]:
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


def fetch_policy_highlights(
    student: dict[str, Any],
    bundle: dict[str, Any],
    *,
    db_session_factory: DbSessionFactory,
    limit: int = 3,
) -> list[dict[str, Any]]:
    province = student.get("province")
    if not province:
        return []

    with db_session_factory() as connection:
        rows = connection.execute(
            """
            SELECT exam_year, policy_key, policy_title, trend_type, trend_summary, impact_scope, source_url
            FROM policy_trends
            WHERE province = ?
            ORDER BY exam_year DESC, id DESC
            """,
            [province],
        ).fetchall()

    signal_text = policy_signal_text(student, bundle)
    direct_policy_keys = candidate_policy_keys(bundle)
    direct_policy_topics = candidate_policy_topics(bundle)
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
        if policy_matches_signal_text(policy_key, signal_text):
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
        highlights.append(format_policy_highlight(item, direct_policy_topics.get(policy_key)))
    return highlights
