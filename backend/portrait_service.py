from __future__ import annotations

from typing import Any

from backend.compliance import (
    PORTRAIT_DISCLAIMER,
    PORTRAIT_EXPLANATION_NOTE,
    PORTRAIT_HARD_EVIDENCE,
)
from backend.foundation_constants import COMPLIANCE_DISCLAIMER
from backend.repository import normalize_text
from backend.rules_engine import infer_student_subjects, split_keywords


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


def student_keywords(student: dict[str, Any]) -> list[str]:
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


def portrait_text_tokens(student: dict[str, Any]) -> list[str]:
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


def subject_track_flags(student: dict[str, Any]) -> tuple[bool, bool]:
    subject_group = str(student.get("subject_group") or "")
    subjects = infer_student_subjects(student)
    is_physics = "物理" in subject_group or "物" in subject_group or "physics" in subject_group.lower() or "物理" in subjects
    is_history = "历史" in subject_group or "史" in subject_group or "history" in subject_group.lower() or "历史" in subjects
    return is_physics, is_history


def candidate_direction_counts(bundle: dict[str, Any] | None) -> dict[str, int]:
    counts = {spec["name"]: 0 for spec in DIRECTION_CATALOG}
    candidates = (bundle or {}).get("candidates") or []
    for item in candidates[:30]:
        major_name = str(item.get("major_name") or "")
        for spec in DIRECTION_CATALOG:
            if any(keyword and keyword in major_name for keyword in spec["keywords"]):
                counts[spec["name"]] += 1
    return counts


def subject_match_for_direction(student: dict[str, Any], spec: dict[str, Any]) -> tuple[int, str, bool]:
    is_physics, is_history = subject_track_flags(student)
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


def parent_match_for_direction(student: dict[str, Any], spec: dict[str, Any]) -> tuple[int, str, str]:
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


def has_portrait_inputs(student: dict[str, Any], derived_profile: dict[str, Any]) -> bool:
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


def build_portrait_major_recommendation(
    student: dict[str, Any],
    bundle: dict[str, Any] | None = None,
) -> dict[str, Any]:
    derived_profile = student.get("derived_profile") or {}
    profile = derived_profile.get("profile") or {}
    portrait_tokens = portrait_text_tokens(student)
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
    candidate_counts = candidate_direction_counts(bundle)
    has_portrait_data = has_portrait_inputs(student, derived_profile)

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
        subject_score, subject_note, subject_risk = subject_match_for_direction(student, spec)
        parent_score, parent_label, parent_note = parent_match_for_direction(student, spec)
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


def apply_portrait_summary(rule_summary: dict[str, Any], portrait_recommendation: dict[str, Any]) -> dict[str, Any]:
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


def build_derived_profile_summary(student: dict[str, Any]) -> dict[str, Any]:
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


