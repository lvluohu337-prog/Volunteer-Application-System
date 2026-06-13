from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROVINCE_SUPPORT_DEFINITION_PATH = Path(__file__).resolve().parent.parent / "shared" / "province_support.json"


def _load_province_support_definition() -> dict[str, Any]:
    raw = json.loads(PROVINCE_SUPPORT_DEFINITION_PATH.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


PROVINCE_SUPPORT_DEFINITION = _load_province_support_definition()
LAST_VERIFIED_DATE = str(PROVINCE_SUPPORT_DEFINITION.get("lastVerifiedDate") or "")
FORMAL_SUPPORTED_PROVINCES = tuple(str(item) for item in (PROVINCE_SUPPORT_DEFINITION.get("formalSupportedProvinces") or []))
PROVINCE_SUPPORT_CATALOG = {
    str(name): {
        "status": str(config.get("status") or ""),
        "statusLabel": str(config.get("statusLabel") or ""),
        "description": str(config.get("description") or ""),
    }
    for name, config in (PROVINCE_SUPPORT_DEFINITION.get("provinceCatalog") or {}).items()
}


def is_formally_supported_province(province: str | None) -> bool:
    normalized = str(province or "").strip()
    return normalized in FORMAL_SUPPORTED_PROVINCES


def build_province_support_options() -> list[dict[str, Any]]:
    options: list[dict[str, Any]] = []
    for province, config in PROVINCE_SUPPORT_CATALOG.items():
        is_formal = province in FORMAL_SUPPORTED_PROVINCES
        options.append(
            {
                "value": province,
                "label": province,
                "status": config["status"],
                "statusLabel": config["statusLabel"],
                "description": config["description"],
                "disabled": not is_formal,
            }
        )
    options.sort(key=lambda item: (item["disabled"], item["value"]))
    return options


def build_province_support_summary() -> dict[str, Any]:
    options = build_province_support_options()
    return {
        "lastVerifiedDate": LAST_VERIFIED_DATE,
        "formalSupportedProvinces": list(FORMAL_SUPPORTED_PROVINCES),
        "formalSupportedLabel": " / ".join(FORMAL_SUPPORTED_PROVINCES) if FORMAL_SUPPORTED_PROVINCES else "待补充",
        "pendingProvinces": [item["value"] for item in options if item["disabled"]],
        "options": options,
        "notice": (
            f"当前正式支持省份仅限 {' / '.join(FORMAL_SUPPORTED_PROVINCES)}。"
            if FORMAL_SUPPORTED_PROVINCES
            else "当前尚未明确正式支持省份。"
        ),
    }
