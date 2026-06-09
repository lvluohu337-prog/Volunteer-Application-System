from __future__ import annotations

from datetime import date, datetime
from typing import Any


HEAVENLY_STEMS = "甲乙丙丁戊己庚辛壬癸"
EARTHLY_BRANCHES = "子丑寅卯辰巳午未申酉戌亥"

CONSTELLATION_BOUNDARIES = (
    ((1, 20), "摩羯座", "水瓶座"),
    ((2, 19), "水瓶座", "双鱼座"),
    ((3, 21), "双鱼座", "白羊座"),
    ((4, 20), "白羊座", "金牛座"),
    ((5, 21), "金牛座", "双子座"),
    ((6, 22), "双子座", "巨蟹座"),
    ((7, 23), "巨蟹座", "狮子座"),
    ((8, 23), "狮子座", "处女座"),
    ((9, 23), "处女座", "天秤座"),
    ((10, 24), "天秤座", "天蝎座"),
    ((11, 23), "天蝎座", "射手座"),
    ((12, 22), "射手座", "摩羯座"),
)

MONTH_BRANCH_BOUNDARIES = (
    ((1, 6), 11),
    ((2, 4), 0),
    ((3, 6), 1),
    ((4, 5), 2),
    ((5, 6), 3),
    ((6, 6), 4),
    ((7, 7), 5),
    ((8, 8), 6),
    ((9, 8), 7),
    ((10, 8), 8),
    ((11, 7), 9),
    ((12, 7), 10),
)

YEAR_STEM_TO_MONTH_START = {
    0: 2,
    5: 2,
    1: 4,
    6: 4,
    2: 6,
    7: 6,
    3: 8,
    8: 8,
    4: 0,
    9: 0,
}

DAY_STEM_TO_HOUR_START = {
    0: 0,  # 甲己日起甲子
    5: 0,
    1: 2,  # 乙庚日起丙子
    6: 2,
    2: 4,  # 丙辛日起戊子
    7: 4,
    3: 6,  # 丁壬日起庚子
    8: 6,
    4: 8,  # 戊癸日起壬子
    9: 8,
}

STEM_ELEMENT_MAP = {
    "甲": "木",
    "乙": "木",
    "丙": "火",
    "丁": "火",
    "戊": "土",
    "己": "土",
    "庚": "金",
    "辛": "金",
    "壬": "水",
    "癸": "水",
}

BRANCH_ELEMENT_MAP = {
    "子": "水",
    "丑": "土",
    "寅": "木",
    "卯": "木",
    "辰": "土",
    "巳": "火",
    "午": "火",
    "未": "土",
    "申": "金",
    "酉": "金",
    "戌": "土",
    "亥": "水",
}

ELEMENT_INTEREST_MAP = {
    "木": ["教育", "设计", "文化传播", "策划", "成长服务"],
    "火": ["传媒", "电子信息", "能源", "表演表达", "市场传播"],
    "土": ["管理", "金融", "公共事务", "稳定型服务", "地产规划"],
    "金": ["机械工程", "制造", "法律", "质量规范", "工程管理"],
    "水": ["计算机", "信息科学", "科研分析", "数据方向", "贸易流通"],
}

ELEMENT_REGION_MAP = {
    "木": ["南方", "开放型城市", "文化教育资源较强区域"],
    "火": ["南方", "节奏较快城市", "新一线或产业活跃城市"],
    "土": ["本省优先", "省会城市", "区域中心城市"],
    "金": ["北方", "制造业基础强城市", "规则体系成熟城市"],
    "水": ["沿海城市", "创新资源密集区域", "信息流动快的城市"],
}

ELEMENT_DEVELOPMENT_MAP = {
    "木": ["持续成长", "长期深耕", "教育与内容表达"],
    "火": ["快速成长", "机会导向", "技术传播或市场拓展"],
    "土": ["稳定就业", "考公考编", "组织管理路径"],
    "金": ["工程进阶", "规则型职业", "制造与法务路径"],
    "水": ["技术研发", "数据分析", "跨领域创新"],
}

ELEMENT_TRAIT_MAP = {
    "木": ["成长驱动", "重视空间", "长期积累"],
    "火": ["行动力强", "表达欲强", "反馈敏感"],
    "土": ["稳定务实", "责任感强", "重视秩序"],
    "金": ["规则感强", "执行力强", "偏理性判断"],
    "水": ["适应力强", "理解力强", "信息处理快"],
}

CONSTELLATION_TRAIT_MAP = {
    "白羊座": ["主动", "行动快", "敢尝试"],
    "金牛座": ["稳健", "耐性强", "重体验"],
    "双子座": ["好奇", "沟通强", "学习快"],
    "巨蟹座": ["敏感", "重归属", "照顾型"],
    "狮子座": ["自驱", "表现力强", "需要成就感"],
    "处女座": ["细致", "重方法", "偏完备"],
    "天秤座": ["平衡感强", "善协调", "重关系"],
    "天蝎座": ["专注", "投入深", "抗压潜力高"],
    "射手座": ["探索欲强", "开放", "视野导向"],
    "摩羯座": ["目标感强", "耐力强", "重结果"],
    "水瓶座": ["独立", "创新", "偏系统思维"],
    "双鱼座": ["感受力强", "想象力强", "偏共情"],
}

HOUR_BRANCH_LABELS = [
    "子时(23:00-00:59)",
    "丑时(01:00-02:59)",
    "寅时(03:00-04:59)",
    "卯时(05:00-06:59)",
    "辰时(07:00-08:59)",
    "巳时(09:00-10:59)",
    "午时(11:00-12:59)",
    "未时(13:00-14:59)",
    "申时(15:00-16:59)",
    "酉时(17:00-18:59)",
    "戌时(19:00-20:59)",
    "亥时(21:00-22:59)",
]


def parse_birthday(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_birth_time(value: str | None) -> tuple[int, int] | None:
    if not value:
        return None
    try:
        hour_text, minute_text = value.strip().split(":")
        hour = int(hour_text)
        minute = int(minute_text)
    except (ValueError, AttributeError):
        return None
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return hour, minute


def infer_constellation(birthday: str | None) -> str | None:
    parsed = parse_birthday(birthday)
    if parsed is None:
        return None

    for (month, boundary_day), before_label, after_label in CONSTELLATION_BOUNDARIES:
        if parsed.month == month:
            return before_label if parsed.day < boundary_day else after_label
    return None


def _ganzhi(index: int) -> str:
    return f"{HEAVENLY_STEMS[index % 10]}{EARTHLY_BRANCHES[index % 12]}"


def _adjusted_year_for_pillar(parsed: date) -> int:
    lichun = date(parsed.year, 2, 4)
    return parsed.year if parsed >= lichun else parsed.year - 1


def infer_year_pillar(parsed: date) -> str:
    adjusted_year = _adjusted_year_for_pillar(parsed)
    return _ganzhi(adjusted_year - 1984)


def _infer_month_index(parsed: date) -> int:
    current = (parsed.month, parsed.day)
    month_index = 10
    for boundary, index in MONTH_BRANCH_BOUNDARIES:
        if current >= boundary:
            month_index = index
    return month_index


def infer_month_pillar(parsed: date) -> str:
    adjusted_year = _adjusted_year_for_pillar(parsed)
    year_stem_index = (adjusted_year - 1984) % 10
    month_index = _infer_month_index(parsed)
    month_branch = EARTHLY_BRANCHES[(2 + month_index) % 12]
    month_stem_start = YEAR_STEM_TO_MONTH_START[year_stem_index]
    month_stem = HEAVENLY_STEMS[(month_stem_start + month_index) % 10]
    return f"{month_stem}{month_branch}"


def infer_day_pillar(parsed: date) -> str:
    base_date = date(1984, 2, 2)
    offset = (parsed - base_date).days
    return _ganzhi(offset)


def infer_hour_branch_index(birth_time: str | None) -> int | None:
    parsed = parse_birth_time(birth_time)
    if parsed is None:
        return None
    hour, _minute = parsed
    if hour == 23 or hour == 0:
        return 0
    return (hour + 1) // 2


def infer_hour_pillar(parsed_date: date, birth_time: str | None) -> str | None:
    hour_branch_index = infer_hour_branch_index(birth_time)
    if hour_branch_index is None:
        return None
    day_stem_index = (parsed_date - date(1984, 2, 2)).days % 10
    hour_stem_start = DAY_STEM_TO_HOUR_START[day_stem_index]
    hour_stem = HEAVENLY_STEMS[(hour_stem_start + hour_branch_index) % 10]
    hour_branch = EARTHLY_BRANCHES[hour_branch_index]
    return f"{hour_stem}{hour_branch}"


def infer_four_pillars(birthday: str | None, birth_time: str | None = None) -> dict[str, str | None]:
    parsed = parse_birthday(birthday)
    if parsed is None:
        return {"year": None, "month": None, "day": None, "hour": None}

    return {
        "year": infer_year_pillar(parsed),
        "month": infer_month_pillar(parsed),
        "day": infer_day_pillar(parsed),
        "hour": infer_hour_pillar(parsed, birth_time),
    }


def _collect_elements(pillars: dict[str, str | None]) -> dict[str, int]:
    counts = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
    for pillar in pillars.values():
        if not pillar or len(pillar) != 2:
            continue
        stem, branch = pillar[0], pillar[1]
        counts[STEM_ELEMENT_MAP[stem]] += 1
        counts[BRANCH_ELEMENT_MAP[branch]] += 1
    return counts


def _dominant_elements(counts: dict[str, int]) -> list[str]:
    return [item[0] for item in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0])) if item[1] > 0]


def _merge_unique(*groups: list[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for group in groups:
        for item in group:
            if item in seen:
                continue
            seen.add(item)
            merged.append(item)
    return merged


def _hour_branch_text(birth_time: str | None) -> str | None:
    index = infer_hour_branch_index(birth_time)
    if index is None:
        return None
    return HOUR_BRANCH_LABELS[index]


def derive_birth_profile(birthday: str | None, birth_time: str | None = None) -> dict[str, Any]:
    parsed = parse_birthday(birthday)
    parsed_time = parse_birth_time(birth_time)
    if parsed is None:
        return {
            "birthday": birthday,
            "birthTime": birth_time,
            "birthdayType": "公历",
            "constellation": None,
            "pillars": {"year": None, "month": None, "day": None, "hour": None},
            "wuxing": {"counts": {}, "dominant": None, "secondary": None},
            "profile": {
                "personalityTraits": [],
                "learningStyle": [],
                "interestDirections": [],
                "regionPreferences": [],
                "developmentGoals": [],
                "explanations": [],
            },
            "autofill": {
                "constellation": None,
                "bazi_year_pillar": None,
                "bazi_month_pillar": None,
                "bazi_day_pillar": None,
                "bazi_hour_pillar": None,
                "interest_preferences": None,
                "region_preference": None,
                "development_goal": None,
            },
            "disclaimer": "请输入阳历生日后再进行辅助推算。",
        }

    constellation = infer_constellation(birthday)
    pillars = infer_four_pillars(birthday, birth_time)
    counts = _collect_elements(pillars)
    ranked_elements = _dominant_elements(counts)
    dominant = ranked_elements[0] if ranked_elements else None
    secondary = ranked_elements[1] if len(ranked_elements) > 1 else None

    constellation_traits = CONSTELLATION_TRAIT_MAP.get(constellation or "", [])
    dominant_traits = ELEMENT_TRAIT_MAP.get(dominant or "", [])
    secondary_traits = ELEMENT_TRAIT_MAP.get(secondary or "", [])

    interest_directions = _merge_unique(
        ELEMENT_INTEREST_MAP.get(dominant or "", []),
        ELEMENT_INTEREST_MAP.get(secondary or "", []),
    )[:6]
    region_preferences = _merge_unique(
        ELEMENT_REGION_MAP.get(dominant or "", []),
        ELEMENT_REGION_MAP.get(secondary or "", []),
    )[:4]
    development_goals = _merge_unique(
        ELEMENT_DEVELOPMENT_MAP.get(dominant or "", []),
        ELEMENT_DEVELOPMENT_MAP.get(secondary or "", []),
    )[:4]

    learning_style = []
    if dominant in {"木", "水"}:
        learning_style.append("更适合启发式、项目式学习")
    if dominant in {"土", "金"}:
        learning_style.append("更适合结构化、阶段性复盘")
    if dominant == "火":
        learning_style.append("更适合目标清晰、反馈频繁的训练")
    if parsed_time is None:
        learning_style.append("当前未录入出生时辰，时柱与细分节奏判断仍可继续补充")
    if not learning_style:
        learning_style.append("建议结合真实学习表现做人工校准")

    explanation_prefix = (
        f"系统按阳历生日和出生时辰自动推算四柱：{pillars['year']}年柱、{pillars['month']}月柱、"
        f"{pillars['day']}日柱、{pillars['hour'] or '待补充'}时柱。"
    )
    if parsed_time is None:
        explanation_prefix = (
            f"系统按阳历生日先推算前三柱：{pillars['year']}年柱、{pillars['month']}月柱、{pillars['day']}日柱；"
            "录入出生时辰后可自动补齐时柱。"
        )

    explanations = [
        explanation_prefix,
        f"当前五行倾向以“{dominant or '待识别'}”为主，{('辅以' + secondary) if secondary else '辅助元素待补充'}。",
        "兴趣、地域和发展建议仅作辅助解释，正式志愿仍需以分数、位次、招生规则和院校章程为核心依据。",
    ]

    return {
        "birthday": parsed.isoformat(),
        "birthTime": f"{parsed_time[0]:02d}:{parsed_time[1]:02d}" if parsed_time else None,
        "birthdayType": "公历",
        "constellation": constellation,
        "pillars": pillars,
        "hourBranchLabel": _hour_branch_text(birth_time),
        "wuxing": {
            "counts": counts,
            "dominant": dominant,
            "secondary": secondary,
        },
        "profile": {
            "personalityTraits": _merge_unique(dominant_traits, secondary_traits, constellation_traits)[:6],
            "learningStyle": learning_style,
            "interestDirections": interest_directions,
            "regionPreferences": region_preferences,
            "developmentGoals": development_goals,
            "explanations": explanations,
        },
        "autofill": {
            "constellation": constellation,
            "bazi_year_pillar": pillars["year"],
            "bazi_month_pillar": pillars["month"],
            "bazi_day_pillar": pillars["day"],
            "bazi_hour_pillar": pillars["hour"],
            "interest_preferences": "、".join(interest_directions[:4]) if interest_directions else None,
            "region_preference": "、".join(region_preferences[:3]) if region_preferences else None,
            "development_goal": "、".join(development_goals[:3]) if development_goals else None,
        },
        "disclaimer": "前六字、八字四柱、星座和五行倾向仅作为辅助分析，不替代真实招生数据和正式填报规则。",
    }
