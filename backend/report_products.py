from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PRODUCT_DEFINITION_PATH = Path(__file__).resolve().parent.parent / "shared" / "report_products.json"


def _load_product_definition() -> dict[str, Any]:
    raw = json.loads(PRODUCT_DEFINITION_PATH.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


PRODUCT_DEFINITION = _load_product_definition()
DEFAULT_REPORT_PRODUCT_CODE = str(PRODUCT_DEFINITION.get("defaultProductCode") or "399")

REPORT_PRODUCT_CONFIG = {
    str(code): {
        "label": str(config.get("label") or ""),
        "short_label": str(config.get("shortLabel") or config.get("label") or ""),
        "description": str(config.get("description") or ""),
        "target_user": str(config.get("targetUser") or ""),
        "delivery_channels": list(config.get("deliveryChannels") or []),
    }
    for code, config in (PRODUCT_DEFINITION.get("formalProducts") or {}).items()
}

SUPPORTED_REPORT_PRODUCT_CODES = tuple(REPORT_PRODUCT_CONFIG.keys())

PLANNED_REPORT_PRODUCTS = {
    str(code): dict(config)
    for code, config in (PRODUCT_DEFINITION.get("plannedProducts") or {}).items()
}

REPORT_PRODUCT_LABELS = {
    code: config["label"]
    for code, config in REPORT_PRODUCT_CONFIG.items()
}


def normalize_report_product_code(product_code: str | None) -> str:
    normalized = str(product_code or DEFAULT_REPORT_PRODUCT_CODE).strip()
    return normalized if normalized in REPORT_PRODUCT_CONFIG else DEFAULT_REPORT_PRODUCT_CODE


def get_report_product_label(product_code: str | None) -> str:
    normalized = normalize_report_product_code(product_code)
    return REPORT_PRODUCT_LABELS[normalized]
