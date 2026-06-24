from __future__ import annotations

from copy import deepcopy


HENAN_2026_TOTAL_CHOICE_TARGET = 48

HENAN_2026_RECOMMENDATION_TARGETS = {
    "rush": 14,
    "steady": 24,
    "safe": 10,
}

HENAN_2026_STRATEGY_PROFILES = {
    "balanced": {
        "mode": "balanced",
        "name": "均衡型",
        "bucket_targets": HENAN_2026_RECOMMENDATION_TARGETS,
        "tiers": [
            {
                "key": "rush",
                "bucket": "rush",
                "target": 14,
                "label": "冲",
                "title": "冲刺推荐",
                "tag": "风险较高",
                "variant": "warning",
                "description": "适合少量尝试，重点关注位次临界和计划波动风险。",
            },
            {
                "key": "steady",
                "bucket": "steady",
                "target": 24,
                "label": "稳",
                "title": "稳妥推荐",
                "tag": "建议主力",
                "variant": "primary",
                "description": "作为主力志愿区，兼顾院校平台、专业方向和风险平衡。",
            },
            {
                "key": "safe",
                "bucket": "safe",
                "target": 10,
                "label": "保",
                "title": "保底推荐",
                "tag": "相对安全",
                "variant": "success",
                "description": "用于守住底线，仍需关注调剂接受度与专业接受度。",
            },
        ],
    },
    "conservative": {
        "mode": "conservative",
        "name": "稳妥型",
        "bucket_targets": {"rush": 10, "steady": 16, "safe": 22},
        "tiers": [
            {
                "key": "risk",
                "bucket": "rush",
                "target": 5,
                "label": "险",
                "title": "险中尝试",
                "tag": "高风险尝试",
                "variant": "danger",
                "description": "只放极少数临界向上样本，必须复核专业组内所有专业是否能接受。",
            },
            {
                "key": "sprint",
                "bucket": "rush",
                "target": 5,
                "label": "冲",
                "title": "冲刺推荐",
                "tag": "谨慎冲刺",
                "variant": "warning",
                "description": "接近往年门槛的尝试项，不能承担保底功能。",
            },
            {
                "key": "steady",
                "bucket": "steady",
                "target": 16,
                "label": "稳",
                "title": "稳妥主力",
                "tag": "主力志愿",
                "variant": "primary",
                "description": "作为正式方案主力区，优先平衡院校、专业、城市和计划稳定性。",
            },
            {
                "key": "protect",
                "bucket": "safe",
                "target": 12,
                "label": "保",
                "title": "保底承接",
                "tag": "相对安全",
                "variant": "success",
                "description": "用于承接录取安全边界，仍需核对调剂和特殊限制。",
            },
            {
                "key": "cushion",
                "bucket": "safe",
                "target": 5,
                "label": "垫",
                "title": "垫底缓冲",
                "tag": "安全缓冲",
                "variant": "success",
                "description": "通过更大的位次余量增加缓冲，防止主力保底失效。",
            },
            {
                "key": "fallback",
                "bucket": "safe",
                "target": 5,
                "label": "兜",
                "title": "兜底守线",
                "tag": "底线守护",
                "variant": "info",
                "description": "用于守住本科批底线，不追求漂亮但要降低滑档风险。",
            },
        ],
    },
    "aggressive": {
        "mode": "aggressive",
        "name": "进取型",
        "bucket_targets": {"rush": 18, "steady": 22, "safe": 8},
        "tiers": [
            {
                "key": "risk",
                "bucket": "rush",
                "target": 6,
                "label": "险",
                "title": "险中尝试",
                "tag": "高风险尝试",
                "variant": "danger",
                "description": "进取型高风险尝试项，必须明确告知滑档和退档边界。",
            },
            {
                "key": "sprint",
                "bucket": "rush",
                "target": 12,
                "label": "冲",
                "title": "冲刺推荐",
                "tag": "积极冲刺",
                "variant": "warning",
                "description": "提高冲刺比例，但不替代稳妥和保底区。",
            },
            {
                "key": "steady",
                "bucket": "steady",
                "target": 22,
                "label": "稳",
                "title": "稳妥主力",
                "tag": "主力志愿",
                "variant": "primary",
                "description": "进取型仍保留主力稳定区，避免方案整体失衡。",
            },
            {
                "key": "protect",
                "bucket": "safe",
                "target": 8,
                "label": "保",
                "title": "保底推荐",
                "tag": "底线保障",
                "variant": "success",
                "description": "压缩但保留底线区，正式填报前需人工确认可接受。",
            },
        ],
    },
}


def resolve_strategy_mode(value: object | None = None) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return "balanced"
    if any(keyword in text for keyword in ("conservative", "safe", "保守", "稳妥", "稳健", "不滑档", "兜底")):
        return "conservative"
    if any(keyword in text for keyword in ("aggressive", "进取", "冲刺", "大胆")):
        return "aggressive"
    return "balanced"


def resolve_strategy_profile(value: object | None = None) -> dict[str, object]:
    mode = resolve_strategy_mode(value)
    return deepcopy(HENAN_2026_STRATEGY_PROFILES[mode])


def bucket_target_ratios(targets: dict[str, int] | None = None) -> dict[str, int]:
    targets = targets or HENAN_2026_RECOMMENDATION_TARGETS
    total = sum(targets.values()) or 1
    return {
        "rush_ratio": round(targets.get("rush", 0) / total * 100),
        "steady_ratio": round(targets.get("steady", 0) / total * 100),
        "safe_ratio": round(targets.get("safe", 0) / total * 100),
    }


def default_strategy_note(mode: object | None = None) -> str:
    profile = resolve_strategy_profile(mode)
    if profile["mode"] == "conservative":
        return (
            "本轮正式方案已按河南 2026 普通本科批 48 个院校专业组志愿结构，"
            "采用稳妥型六档展示：险5 / 冲5 / 稳16 / 保12 / 垫5 / 兜5；"
            "正式填报前必须复核院校专业组、组内 6 个专业、是否服从调剂与年度招生计划。"
        )
    if profile["mode"] == "aggressive":
        return (
            "本轮正式方案已按河南 2026 普通本科批 48 个院校专业组志愿结构，"
            "采用进取型策略提高冲刺比例；正式填报前必须重点复核高风险专业组和调剂边界。"
        )
    return (
        "本轮正式方案已按河南 2026 普通本科批 48 个院校专业组志愿结构，"
        "以冲约30%、稳约50%、保约20%的目标配比做去重和邻档补位；"
        "正式填报前仍需复核院校专业组、组内 6 个专业、是否服从调剂与年度招生计划。"
    )
