from __future__ import annotations

import json
from typing import Any


def _matches_condition_value(value: str, condition: dict[str, Any]) -> bool:
    contains_any = condition.get("contains_any") or []
    if contains_any and not any(token and token in value for token in contains_any):
        return False

    equals_any = condition.get("equals_any") or []
    if equals_any and value not in equals_any:
        return False

    not_contains_any = condition.get("not_contains_any") or []
    if not_contains_any and any(token in value for token in not_contains_any):
        return False

    return True


def _explicit_rule_applies(rule: dict[str, Any], row: dict[str, Any]) -> bool:
    trigger_text = str(rule.get("trigger_condition") or "").strip()
    if not trigger_text:
        return True

    try:
        trigger = json.loads(trigger_text)
    except json.JSONDecodeError:
        return True

    match_any = trigger.get("match_any") or []
    if match_any and not any(
        _matches_condition_value(str(row.get(item.get("field")) or ""), item)
        for item in match_any
    ):
        return False

    match_all = trigger.get("match_all") or []
    if match_all and not all(
        _matches_condition_value(str(row.get(item.get("field")) or ""), item)
        for item in match_all
    ):
        return False

    return True


def _heuristic_risks(row: dict[str, Any]) -> list[dict[str, Any]]:
    risks: list[dict[str, Any]] = []
    batch_code = str(row.get("batch_code") or "")
    notes = str(row.get("plan_notes") or "")
    public_private = str(row.get("public_private") or "")

    def add_risk(risk_type: str, level: str, label: str, note: str, source: str = "heuristic") -> None:
        risks.append(
            {
                "type": risk_type,
                "level": level,
                "label": label,
                "note": note,
                "source": source,
            }
        )

    if "提前批" in batch_code:
        add_risk("batch", "medium", "提前批规则", "该专业处于提前批或提前批相关层次，填报和录取节奏与普通批不同。")
    if "专项" in batch_code or "专项" in notes:
        add_risk("eligibility", "high", "专项资格要求", "该候选涉及国家专项、高校专项或地方专项，需先确认是否具备专项报考资格。")
    if "中外合作办学" in notes or "中外合作办学" in public_private or "港澳台地区合作办学" in public_private:
        add_risk("tuition", "high", "合作办学成本", "该候选涉及合作办学，学费和培养模式通常明显不同，需重点确认费用与培养方案。")
    if "只招英语" in notes or "只招英语语种考生" in notes or "只招英语,俄语语种的考生" in notes:
        add_risk("language", "high", "语种限制", "该候选对外语语种有限制，需确认考生语种是否满足院校要求。")
    if any(token in notes for token in ["不招色盲", "不招色弱", "单色识别不全", "无复视", "裸视力", "矫正视力", "身高", "不宜女生报考", "不适宜女生报考"]):
        add_risk("physical", "high", "身体条件限制", "该候选包含视力、色觉、身高或性别相关限制，必须逐条核对招生章程。")
    if "招生章程" in notes or "详见院校招生章程" in notes or "其它见招生章程" in notes:
        add_risk("charter", "medium", "需复核招生章程", "该候选明确要求以院校招生章程为准，正式填报前必须人工复核。")
    if "单列专业" in notes:
        add_risk("special_track", "medium", "单列专业规则", "该候选为单列专业，培养方式或录取规则可能与普通专业不同。")
    if "定向培养军士" in notes or "军队院校" in batch_code or "飞行学员" in batch_code:
        add_risk("special_review", "high", "特殊审核要求", "该候选涉及军事或特殊培养方向，通常还会叠加政审、体检或面试要求。")
    if "5+3" in notes or "本硕" in notes:
        add_risk("study_years", "medium", "学制特殊", "该候选学制或培养路径较特殊，需确认培养周期、分流和后续要求。")

    return risks


def normalize_explicit_rule(rule: dict[str, Any]) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    raw_json = str(rule.get("raw_json") or "").strip()
    if raw_json:
        try:
            meta = json.loads(raw_json)
        except json.JSONDecodeError:
            meta = {}

    source_url = str(meta.get("source_url") or rule.get("source_url") or "").strip()
    source_name = source_url.replace("/", "\\").split("\\")[-1] if source_url else ""

    if "risk_type" in rule:
        label = meta.get("display_label") or rule.get("risk_type") or "规则风险"
        note = rule.get("risk_message") or rule.get("mitigation_suggestion") or "需结合院校规则人工复核。"
        if source_name:
            note = f"{note} 来源：{source_name}"
        return {
            "type": rule.get("risk_type") or "explicit_rule",
            "level": str(rule.get("risk_level") or "medium").lower(),
            "label": label,
            "note": note,
            "source": "risk_table",
            "policy_key": meta.get("policy_key"),
            "policy_topic": meta.get("policy_topic"),
        }

    note = rule.get("rule_content") or rule.get("notes") or "需结合院校招生章程人工复核。"
    if source_name:
        note = f"{note} 来源：{source_name}"
    return {
        "type": rule.get("rule_type") or "institution_rule",
        "level": "medium",
        "label": rule.get("rule_title") or rule.get("rule_type") or "院校规则",
        "note": note,
        "source": "institution_rule",
        "policy_key": meta.get("policy_key"),
        "policy_topic": meta.get("policy_topic"),
    }


def _normalize_explicit_rule_v2(rule: dict[str, Any]) -> dict[str, Any]:
    return normalize_explicit_rule(rule)


def _collect_risks(row: dict[str, Any], explicit_rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items = [normalize_explicit_rule(rule) for rule in explicit_rules]
    items.extend(_heuristic_risks(row))
    deduped: list[dict[str, Any]] = []
    seen = set()
    for item in items:
        key = (item["type"], item["label"], item["note"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped
