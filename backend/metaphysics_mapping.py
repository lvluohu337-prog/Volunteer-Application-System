from __future__ import annotations

from typing import Any

from backend.compliance import PORTRAIT_DISCLAIMER
from backend.intake_inference import (
    _build_autofill,
    _build_profile_sections,
    _collect_elements,
    _dominant_elements,
    _hour_branch_text,
    infer_constellation,
    parse_birth_time,
)

ELEMENT_ALIASES = {
    "wood": "木",
    "fire": "火",
    "earth": "土",
    "metal": "金",
    "water": "水",
}


def _normalize_element_name(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    return ELEMENT_ALIASES.get(text.lower(), text)


def _normalize_wuxing_counts(raw_counts: dict[str, Any]) -> dict[str, int]:
    counts = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
    for key, value in (raw_counts or {}).items():
        normalized_key = _normalize_element_name(key)
        if normalized_key not in counts:
            continue
        try:
            counts[normalized_key] += int(value)
        except (TypeError, ValueError):
            continue
    return counts


def map_bridge_payload_to_profile(
    *,
    birthday: str,
    birth_time: str | None,
    bridge_payload: dict[str, Any],
) -> dict[str, Any]:
    pillars = bridge_payload["pillars"]
    wuxing = bridge_payload.get("wuxing") or {}
    counts = _normalize_wuxing_counts(wuxing.get("counts") or {})
    if not sum(counts.values()):
        counts = _collect_elements(pillars)
    ranked_elements = _dominant_elements(counts)
    dominant = _normalize_element_name(wuxing.get("dominant")) or (ranked_elements[0] if ranked_elements else None)
    secondary = _normalize_element_name(wuxing.get("secondary")) or (ranked_elements[1] if len(ranked_elements) > 1 else None)
    constellation = infer_constellation(birthday)
    resolved_birth_time = bridge_payload.get("normalizedBirthTime") or birth_time
    profile, interest_directions, region_preferences, development_goals = _build_profile_sections(
        constellation=constellation,
        dominant=dominant,
        secondary=secondary,
        parsed_time=parse_birth_time(resolved_birth_time),
        pillars=pillars,
    )
    return {
        "birthday": birthday,
        "birthTime": birth_time,
        "birthdayType": "公历",
        "constellation": constellation,
        "pillars": pillars,
        "hourBranchLabel": _hour_branch_text(resolved_birth_time),
        "wuxing": {
            "counts": counts,
            "dominant": dominant,
            "secondary": secondary,
        },
        "profile": profile,
        "autofill": _build_autofill(
            constellation=constellation,
            pillars=pillars,
            interest_directions=interest_directions,
            region_preferences=region_preferences,
            development_goals=development_goals,
        ),
        "disclaimer": PORTRAIT_DISCLAIMER,
        "engineVersion": bridge_payload.get("engineVersion"),
        "normalizedBirthDate": bridge_payload.get("normalizedBirthDate"),
        "normalizedBirthTime": bridge_payload.get("normalizedBirthTime"),
        "trueSolarTime": bridge_payload.get("trueSolarTime"),
        "longitude": bridge_payload.get("longitude"),
        "normalizationNotes": bridge_payload.get("normalizationNotes") or [],
    }
