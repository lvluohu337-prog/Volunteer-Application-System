from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


COMPLIANCE_DEFINITION_PATH = Path(__file__).resolve().parent.parent / "shared" / "compliance.json"


def _load_compliance_definition() -> dict[str, Any]:
    raw = json.loads(COMPLIANCE_DEFINITION_PATH.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


COMPLIANCE_DEFINITION = _load_compliance_definition()
COMPLIANCE_DISCLAIMER = str(COMPLIANCE_DEFINITION.get("disclaimer") or "")
INTERFACE_BOUNDARY_NOTE = str(COMPLIANCE_DEFINITION.get("interfaceBoundaryNote") or "")
INTAKE_DISCLAIMER = str(COMPLIANCE_DEFINITION.get("intakeDisclaimer") or COMPLIANCE_DISCLAIMER)
PORTRAIT_DISCLAIMER = str(COMPLIANCE_DEFINITION.get("portraitDisclaimer") or "")
PORTRAIT_EXPLANATION_NOTE = str(COMPLIANCE_DEFINITION.get("portraitExplanationNote") or "")
PORTRAIT_HARD_EVIDENCE = tuple(str(item) for item in (COMPLIANCE_DEFINITION.get("portraitHardEvidence") or []))
COMPLIANCE_COPY_RULES = tuple(str(item) for item in (COMPLIANCE_DEFINITION.get("copyRules") or []))
PROHIBITED_PROMISE_PHRASES = tuple(str(item) for item in (COMPLIANCE_DEFINITION.get("prohibitedPromisePhrases") or []))


def _normalize_for_phrase_match(value: str | None) -> str:
    return re.sub(r"\s+", "", str(value or "")).lower()


def find_prohibited_promise_phrases(*values: object) -> list[str]:
    haystack = _normalize_for_phrase_match(" ".join(str(value or "") for value in values))
    hits: list[str] = []
    for phrase in PROHIBITED_PROMISE_PHRASES:
        normalized_phrase = _normalize_for_phrase_match(phrase)
        if normalized_phrase and normalized_phrase in haystack and phrase not in hits:
            hits.append(phrase)
    return hits
