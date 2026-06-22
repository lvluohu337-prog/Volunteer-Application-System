from __future__ import annotations

from typing import Any

from backend.compliance import PORTRAIT_DISCLAIMER
from backend.intake_inference import (
    _collect_elements,
    _dominant_elements,
    _hour_branch_text,
    infer_constellation,
)


def map_bridge_payload_to_profile(
    *,
    birthday: str,
    birth_time: str | None,
    bridge_payload: dict[str, Any],
) -> dict[str, Any]:
    pillars = bridge_payload["pillars"]
    wuxing = bridge_payload.get("wuxing") or {}
    counts = wuxing.get("counts") or _collect_elements(pillars)
    ranked_elements = _dominant_elements(counts)
    dominant = wuxing.get("dominant") or (ranked_elements[0] if ranked_elements else None)
    secondary = wuxing.get("secondary") or (ranked_elements[1] if len(ranked_elements) > 1 else None)
    return {
        "birthday": birthday,
        "birthTime": birth_time,
        "birthdayType": "公历",
        "constellation": infer_constellation(birthday),
        "pillars": pillars,
        "hourBranchLabel": _hour_branch_text(bridge_payload.get("normalizedBirthTime") or birth_time),
        "wuxing": {
            "counts": counts,
            "dominant": dominant,
            "secondary": secondary,
        },
        "profile": {
            "personalityTraits": [],
            "learningStyle": [],
            "interestDirections": [],
            "regionPreferences": [],
            "developmentGoals": [],
            "explanations": [],
        },
        "autofill": {
            "constellation": infer_constellation(birthday),
            "bazi_year_pillar": pillars.get("year"),
            "bazi_month_pillar": pillars.get("month"),
            "bazi_day_pillar": pillars.get("day"),
            "bazi_hour_pillar": pillars.get("hour"),
            "interest_preferences": None,
            "region_preference": None,
            "development_goal": None,
        },
        "disclaimer": PORTRAIT_DISCLAIMER,
        "engineVersion": bridge_payload.get("engineVersion"),
        "normalizedBirthDate": bridge_payload.get("normalizedBirthDate"),
        "normalizedBirthTime": bridge_payload.get("normalizedBirthTime"),
        "trueSolarTime": bridge_payload.get("trueSolarTime"),
        "longitude": bridge_payload.get("longitude"),
        "normalizationNotes": bridge_payload.get("normalizationNotes") or [],
    }
