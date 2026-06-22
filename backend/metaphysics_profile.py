from __future__ import annotations

from typing import Any

from backend.compliance import PORTRAIT_DISCLAIMER
from backend.intake_inference import derive_birth_profile as derive_birth_profile_legacy
from backend.metaphysics_bridge import run_bazi_bridge
from backend.metaphysics_mapping import map_bridge_payload_to_profile


def derive_birth_profile_v2(
    birthday: str | None,
    birth_time: str | None = None,
    *,
    longitude: float | None = None,
    runtime_mode: str = "production",
    fallback_mode: str = "disabled",
) -> dict[str, Any]:
    if not birthday:
        legacy = derive_birth_profile_legacy(birthday, birth_time)
        legacy["engineVersion"] = "legacy_empty_input"
        legacy["normalizedBirthDate"] = legacy.get("birthday")
        legacy["normalizedBirthTime"] = legacy.get("birthTime")
        legacy["trueSolarTime"] = None
        legacy["longitude"] = longitude
        legacy["normalizationNotes"] = []
        legacy["disclaimer"] = legacy.get("disclaimer") or PORTRAIT_DISCLAIMER
        return legacy

    try:
        payload = run_bazi_bridge(
            birthday=birthday,
            birth_time=birth_time,
            longitude=longitude,
        )
    except RuntimeError as exc:
        if runtime_mode == "production" or fallback_mode != "legacy":
            raise
        legacy = derive_birth_profile_legacy(birthday, birth_time)
        legacy["engineVersion"] = "legacy_fallback"
        legacy["normalizedBirthDate"] = legacy.get("birthday")
        legacy["normalizedBirthTime"] = legacy.get("birthTime")
        legacy["trueSolarTime"] = None
        legacy["longitude"] = longitude
        legacy["normalizationNotes"] = [str(exc)]
        return legacy

    return map_bridge_payload_to_profile(
        birthday=birthday,
        birth_time=birth_time,
        bridge_payload=payload,
    )
