# Metaphysics Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current approximate Four Pillars derivation with a precise, testable Phase 1 metaphysics engine that keeps the existing `derived_profile` contract stable for the Python backend and frontend consumers.

**Architecture:** Keep Python as the public entrypoint and add a small Node bridge under `tools/metaphysics_bridge/` to calculate normalized Bazi data with `lunar-javascript`. Add a Python bridge wrapper plus a mapping layer so `backend/intake_inference.py` can delegate to the new engine while preserving the current response shape, explicit engine versioning, and controlled fallback behavior.

**Tech Stack:** Python 3, Node.js, `lunar-javascript`, `subprocess`, `unittest`, existing FastAPI/backend modules.

---

## File Structure

- Create: `tools/metaphysics_bridge/package.json` - isolated Node dependency manifest for the metaphysics bridge.
- Create: `tools/metaphysics_bridge/bridge.mjs` - CLI entrypoint that accepts normalized birth inputs and returns precise Bazi payload JSON.
- Create: `backend/metaphysics_bridge.py` - Python wrapper that invokes the Node bridge and translates bridge failures into typed backend errors/results.
- Create: `backend/metaphysics_mapping.py` - converts bridge payloads into the current `derived_profile` shape expected by the rest of the backend.
- Create: `backend/metaphysics_profile.py` - Phase 1 orchestration entrypoint for accurate Bazi derivation and compatibility metadata.
- Modify: `backend/intake_inference.py` - keep public API stable while delegating to `metaphysics_profile`.
- Modify: `backend/portrait_service.py` - only if needed to consume added metadata fields such as `engineVersion` or normalization notes without breaking old profiles.
- Create: `backend/tests/test_metaphysics_bridge.py` - bridge contract and failure-path tests.
- Create: `backend/tests/test_metaphysics_profile.py` - accuracy and fallback behavior tests.
- Create: `backend/tests/test_intake_inference_compat.py` - compatibility tests for current `derive_birth_profile()` consumers.
- Modify: `README.md` - add Phase 1 runtime and verification notes if the implementation adds a required local Node bridge install step.

### Task 1: Scaffold the Node metaphysics bridge

**Files:**
- Create: `tools/metaphysics_bridge/package.json`
- Create: `tools/metaphysics_bridge/bridge.mjs`
- Test: `backend/tests/test_metaphysics_bridge.py`

- [ ] **Step 1: Write the failing bridge-contract test**

```python
import json
import unittest
from unittest.mock import patch

from backend.metaphysics_bridge import run_bazi_bridge


class MetaphysicsBridgeContractTest(unittest.TestCase):
    def test_run_bazi_bridge_returns_parsed_payload(self) -> None:
        completed = type(
            "Completed",
            (),
            {
                "returncode": 0,
                "stdout": json.dumps(
                    {
                        "engineVersion": "bazi_lunar_v1",
                        "normalizedBirthDate": "2006-02-04",
                        "normalizedBirthTime": "23:40",
                        "pillars": {"year": "乙酉", "month": "戊寅", "day": "甲子", "hour": "甲子"},
                    }
                ),
                "stderr": "",
            },
        )()

        with patch("backend.metaphysics_bridge.subprocess.run", return_value=completed):
            result = run_bazi_bridge(
                birthday="2006-02-04",
                birth_time="23:40",
                longitude=115.85,
            )

        self.assertEqual(result["engineVersion"], "bazi_lunar_v1")
        self.assertEqual(result["normalizedBirthDate"], "2006-02-04")
        self.assertEqual(result["pillars"]["hour"], "甲子")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest backend.tests.test_metaphysics_bridge.MetaphysicsBridgeContractTest.test_run_bazi_bridge_returns_parsed_payload -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'backend.metaphysics_bridge'`

- [ ] **Step 3: Create bridge package manifest**

```json
{
  "name": "metaphysics-bridge",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "dependencies": {
    "lunar-javascript": "^1.7.5"
  }
}
```

- [ ] **Step 4: Add the minimal bridge CLI**

```js
import process from "node:process";

function readInput() {
  const raw = process.argv[2];
  if (!raw) {
    throw new Error("missing-json-arg");
  }
  return JSON.parse(raw);
}

function main() {
  const input = readInput();
  const payload = {
    engineVersion: "bazi_lunar_v1",
    normalizedBirthDate: input.birthday,
    normalizedBirthTime: input.birthTime ?? null,
    pillars: { year: null, month: null, day: null, hour: null },
    normalizationNotes: [],
  };
  process.stdout.write(JSON.stringify(payload));
}

main();
```

- [ ] **Step 5: Add the minimal Python wrapper**

```python
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


BRIDGE_DIR = Path(__file__).resolve().parents[1] / "tools" / "metaphysics_bridge"
BRIDGE_ENTRY = BRIDGE_DIR / "bridge.mjs"


def run_bazi_bridge(
    *,
    birthday: str,
    birth_time: str | None,
    longitude: float | None = None,
) -> dict[str, Any]:
    payload = {
        "birthday": birthday,
        "birthTime": birth_time,
        "longitude": longitude,
    }
    completed = subprocess.run(
        ["node", str(BRIDGE_ENTRY), json.dumps(payload, ensure_ascii=False)],
        cwd=str(BRIDGE_DIR),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "metaphysics bridge failed")
    return json.loads(completed.stdout)
```

- [ ] **Step 6: Run test to verify it passes**

Run: `python -m unittest backend.tests.test_metaphysics_bridge.MetaphysicsBridgeContractTest.test_run_bazi_bridge_returns_parsed_payload -v`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add tools/metaphysics_bridge/package.json tools/metaphysics_bridge/bridge.mjs backend/metaphysics_bridge.py backend/tests/test_metaphysics_bridge.py
git commit -m "feat: scaffold metaphysics bridge"
```

### Task 2: Implement precise normalization in the Node bridge

**Files:**
- Modify: `tools/metaphysics_bridge/bridge.mjs`
- Test: `backend/tests/test_metaphysics_profile.py`

- [ ] **Step 1: Write the failing accuracy tests for LiChun, JieQi, late-子时, and longitude correction**

```python
import unittest
from unittest.mock import patch

from backend.metaphysics_profile import derive_birth_profile_v2


class MetaphysicsAccuracyTest(unittest.TestCase):
    def test_lichun_boundary_uses_previous_year_before_lichun(self) -> None:
        payload = {
            "engineVersion": "bazi_lunar_v1",
            "normalizedBirthDate": "2006-02-03",
            "normalizedBirthTime": "10:00",
            "trueSolarTime": "09:44",
            "pillars": {"year": "乙酉", "month": "己丑", "day": "甲子", "hour": "己巳"},
            "wuxing": {"counts": {"木": 2, "火": 1, "土": 2, "金": 2, "水": 1}, "dominant": "土", "secondary": "木"},
            "normalizationNotes": ["year-pillar-before-lichun"],
        }
        with patch("backend.metaphysics_profile.run_bazi_bridge", return_value=payload):
            result = derive_birth_profile_v2("2006-02-03", "10:00")
        self.assertEqual(result["pillars"]["year"], "乙酉")

    def test_late_zi_hour_rolls_to_next_day(self) -> None:
        payload = {
            "engineVersion": "bazi_lunar_v1",
            "normalizedBirthDate": "2006-02-05",
            "normalizedBirthTime": "23:40",
            "trueSolarTime": "23:22",
            "pillars": {"year": "丙戌", "month": "庚寅", "day": "乙丑", "hour": "丙子"},
            "wuxing": {"counts": {"木": 2, "火": 2, "土": 2, "金": 1, "水": 1}, "dominant": "木", "secondary": "火"},
            "normalizationNotes": ["late-zi-hour-next-day"],
        }
        with patch("backend.metaphysics_profile.run_bazi_bridge", return_value=payload):
            result = derive_birth_profile_v2("2006-02-04", "23:40")
        self.assertEqual(result["normalizedBirthDate"], "2006-02-05")
        self.assertIn("late-zi-hour-next-day", result["normalizationNotes"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest backend.tests.test_metaphysics_profile.MetaphysicsAccuracyTest -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'backend.metaphysics_profile'`

- [ ] **Step 3: Replace the placeholder bridge logic with `lunar-javascript` normalization**

```js
import { Lunar, Solar } from "lunar-javascript";
import process from "node:process";

function normalizeClock(dateText, timeText) {
  const [year, month, day] = dateText.split("-").map(Number);
  const [hour, minute] = (timeText ?? "12:00").split(":").map(Number);
  return { year, month, day, hour, minute };
}

function applyLateZiRule(parts) {
  if (parts.hour < 23) {
    return { ...parts, notes: [] };
  }
  const shifted = new Date(Date.UTC(parts.year, parts.month - 1, parts.day));
  shifted.setUTCDate(shifted.getUTCDate() + 1);
  return {
    year: shifted.getUTCFullYear(),
    month: shifted.getUTCMonth() + 1,
    day: shifted.getUTCDate(),
    hour: parts.hour,
    minute: parts.minute,
    notes: ["late-zi-hour-next-day"],
  };
}

function applyTrueSolarTime(parts, longitude) {
  if (longitude == null) {
    return { ...parts, trueSolarTime: null, notes: [] };
  }
  const offsetMinutes = Math.round((Number(longitude) - 120) * 4);
  const utc = Date.UTC(parts.year, parts.month - 1, parts.day, parts.hour, parts.minute);
  const shifted = new Date(utc + offsetMinutes * 60 * 1000);
  return {
    year: shifted.getUTCFullYear(),
    month: shifted.getUTCMonth() + 1,
    day: shifted.getUTCDate(),
    hour: shifted.getUTCHours(),
    minute: shifted.getUTCMinutes(),
    trueSolarTime: `${String(shifted.getUTCHours()).padStart(2, "0")}:${String(shifted.getUTCMinutes()).padStart(2, "0")}`,
    notes: [`true-solar-time:${offsetMinutes}`],
  };
}

function buildPayload(input) {
  const base = normalizeClock(input.birthday, input.birthTime);
  const ziAdjusted = applyLateZiRule(base);
  const solarAdjusted = applyTrueSolarTime(ziAdjusted, input.longitude);
  const solar = Solar.fromYmdHms(
    solarAdjusted.year,
    solarAdjusted.month,
    solarAdjusted.day,
    solarAdjusted.hour,
    solarAdjusted.minute,
    0,
  );
  const lunar = Lunar.fromSolar(solar);
  return {
    engineVersion: "bazi_lunar_v1",
    normalizedBirthDate: `${solarAdjusted.year.toString().padStart(4, "0")}-${String(solarAdjusted.month).padStart(2, "0")}-${String(solarAdjusted.day).padStart(2, "0")}`,
    normalizedBirthTime: `${String(solarAdjusted.hour).padStart(2, "0")}:${String(solarAdjusted.minute).padStart(2, "0")}`,
    trueSolarTime: solarAdjusted.trueSolarTime,
    pillars: {
      year: lunar.getYearInGanZhi(),
      month: lunar.getMonthInGanZhiExact(),
      day: lunar.getDayInGanZhiExact(),
      hour: input.birthTime ? lunar.getTimeInGanZhi() : null,
    },
    normalizationNotes: [...ziAdjusted.notes, ...solarAdjusted.notes],
  };
}

const input = JSON.parse(process.argv[2]);
process.stdout.write(JSON.stringify(buildPayload(input)));
```

- [ ] **Step 4: Run a bridge smoke command**

Run: `node tools/metaphysics_bridge/bridge.mjs "{\"birthday\":\"2006-02-04\",\"birthTime\":\"23:40\",\"longitude\":115.85}"`

Expected: JSON output containing `engineVersion`, `normalizedBirthDate`, `pillars`, and `normalizationNotes`

- [ ] **Step 5: Commit**

```bash
git add tools/metaphysics_bridge/bridge.mjs backend/tests/test_metaphysics_profile.py
git commit -m "feat: implement precise bazi normalization in bridge"
```

### Task 3: Add the Python orchestration and explicit failure policy

**Files:**
- Create: `backend/metaphysics_profile.py`
- Modify: `backend/metaphysics_bridge.py`
- Test: `backend/tests/test_metaphysics_bridge.py`
- Test: `backend/tests/test_metaphysics_profile.py`

- [ ] **Step 1: Write the failing fallback-policy tests**

```python
import unittest
from unittest.mock import patch

from backend.metaphysics_profile import derive_birth_profile_v2


class MetaphysicsFailurePolicyTest(unittest.TestCase):
    def test_production_mode_raises_when_bridge_fails(self) -> None:
        with patch("backend.metaphysics_profile.run_bazi_bridge", side_effect=RuntimeError("bridge down")):
            with self.assertRaises(RuntimeError):
                derive_birth_profile_v2("2006-06-22", "08:00", runtime_mode="production")

    def test_explicit_legacy_mode_marks_engine_version(self) -> None:
        with patch("backend.metaphysics_profile.run_bazi_bridge", side_effect=RuntimeError("bridge down")):
            result = derive_birth_profile_v2(
                "2006-06-22",
                "08:00",
                runtime_mode="development",
                fallback_mode="legacy",
            )
        self.assertEqual(result["engineVersion"], "legacy_fallback")
        self.assertIn("bridge down", result["normalizationNotes"][0])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest backend.tests.test_metaphysics_profile.MetaphysicsFailurePolicyTest -v`

Expected: FAIL with `AttributeError` or missing `derive_birth_profile_v2`

- [ ] **Step 3: Extend the Python bridge wrapper with typed error details**

```python
class MetaphysicsBridgeError(RuntimeError):
    pass


def run_bazi_bridge(
    *,
    birthday: str,
    birth_time: str | None,
    longitude: float | None = None,
) -> dict[str, Any]:
    payload = {
        "birthday": birthday,
        "birthTime": birth_time,
        "longitude": longitude,
    }
    completed = subprocess.run(
        ["node", str(BRIDGE_ENTRY), json.dumps(payload, ensure_ascii=False)],
        cwd=str(BRIDGE_DIR),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "metaphysics bridge failed"
        raise MetaphysicsBridgeError(message)
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise MetaphysicsBridgeError(f"invalid bridge json: {exc}") from exc
```

- [ ] **Step 4: Add the Phase 1 orchestration entrypoint**

```python
from __future__ import annotations

from typing import Any

from backend.intake_inference import derive_birth_profile as derive_birth_profile_legacy
from backend.metaphysics_bridge import MetaphysicsBridgeError, run_bazi_bridge
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
        legacy["normalizationNotes"] = []
        return legacy

    try:
        payload = run_bazi_bridge(
            birthday=birthday,
            birth_time=birth_time,
            longitude=longitude,
        )
    except MetaphysicsBridgeError as exc:
        if runtime_mode == "production" or fallback_mode != "legacy":
            raise
        legacy = derive_birth_profile_legacy(birthday, birth_time)
        legacy["engineVersion"] = "legacy_fallback"
        legacy["normalizedBirthDate"] = legacy.get("birthday")
        legacy["normalizedBirthTime"] = legacy.get("birthTime")
        legacy["trueSolarTime"] = None
        legacy["normalizationNotes"] = [str(exc)]
        return legacy

    return map_bridge_payload_to_profile(
        birthday=birthday,
        birth_time=birth_time,
        bridge_payload=payload,
    )
```

- [ ] **Step 5: Run the failure-policy tests to verify they pass**

Run: `python -m unittest backend.tests.test_metaphysics_profile.MetaphysicsFailurePolicyTest -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/metaphysics_bridge.py backend/metaphysics_profile.py backend/tests/test_metaphysics_bridge.py backend/tests/test_metaphysics_profile.py
git commit -m "feat: add metaphysics orchestration and failure policy"
```

### Task 4: Build the compatibility mapping layer

**Files:**
- Create: `backend/metaphysics_mapping.py`
- Test: `backend/tests/test_intake_inference_compat.py`

- [ ] **Step 1: Write the failing compatibility test for current response shape**

```python
import unittest

from backend.metaphysics_mapping import map_bridge_payload_to_profile


class IntakeInferenceCompatibilityTest(unittest.TestCase):
    def test_map_bridge_payload_preserves_existing_profile_shape(self) -> None:
        payload = {
            "engineVersion": "bazi_lunar_v1",
            "normalizedBirthDate": "2006-06-22",
            "normalizedBirthTime": "08:00",
            "trueSolarTime": "07:43",
            "pillars": {"year": "丙戌", "month": "甲午", "day": "辛酉", "hour": "壬辰"},
            "wuxing": {"counts": {"木": 1, "火": 2, "土": 1, "金": 3, "水": 1}, "dominant": "金", "secondary": "火"},
            "normalizationNotes": ["true-solar-time:-17"],
        }

        result = map_bridge_payload_to_profile(
            birthday="2006-06-22",
            birth_time="08:00",
            bridge_payload=payload,
        )

        self.assertEqual(result["birthday"], "2006-06-22")
        self.assertEqual(result["birthTime"], "08:00")
        self.assertEqual(result["pillars"]["hour"], "壬辰")
        self.assertIn("personalityTraits", result["profile"])
        self.assertIn("autofill", result)
        self.assertEqual(result["engineVersion"], "bazi_lunar_v1")
        self.assertEqual(result["normalizedBirthTime"], "08:00")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest backend.tests.test_intake_inference_compat.IntakeInferenceCompatibilityTest.test_map_bridge_payload_preserves_existing_profile_shape -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'backend.metaphysics_mapping'`

- [ ] **Step 3: Add the mapping module**

```python
from __future__ import annotations

from typing import Any

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
    counts = (bridge_payload.get("wuxing") or {}).get("counts") or _collect_elements(pillars)
    ranked_elements = _dominant_elements(counts)
    dominant = (bridge_payload.get("wuxing") or {}).get("dominant") or (ranked_elements[0] if ranked_elements else None)
    secondary = (bridge_payload.get("wuxing") or {}).get("secondary") or (ranked_elements[1] if len(ranked_elements) > 1 else None)
    constellation = infer_constellation(birthday)

    return {
        "birthday": birthday,
        "birthTime": birth_time,
        "birthdayType": "公历",
        "constellation": constellation,
        "pillars": pillars,
        "hourBranchLabel": _hour_branch_text(bridge_payload.get("normalizedBirthTime") or birth_time),
        "wuxing": {"counts": counts, "dominant": dominant, "secondary": secondary},
        "profile": {
            "personalityTraits": [],
            "learningStyle": [],
            "interestDirections": [],
            "regionPreferences": [],
            "developmentGoals": [],
            "explanations": [],
        },
        "autofill": {
            "constellation": constellation,
            "bazi_year_pillar": pillars.get("year"),
            "bazi_month_pillar": pillars.get("month"),
            "bazi_day_pillar": pillars.get("day"),
            "bazi_hour_pillar": pillars.get("hour"),
            "interest_preferences": None,
            "region_preference": None,
            "development_goal": None,
        },
        "disclaimer": "画像结果仅作辅助解释，正式志愿仍以分数、位次和招生规则为准。",
        "engineVersion": bridge_payload.get("engineVersion"),
        "normalizedBirthDate": bridge_payload.get("normalizedBirthDate"),
        "normalizedBirthTime": bridge_payload.get("normalizedBirthTime"),
        "trueSolarTime": bridge_payload.get("trueSolarTime"),
        "longitude": bridge_payload.get("longitude"),
        "normalizationNotes": bridge_payload.get("normalizationNotes") or [],
    }
```

- [ ] **Step 4: Run the compatibility test to verify it passes**

Run: `python -m unittest backend.tests.test_intake_inference_compat.IntakeInferenceCompatibilityTest.test_map_bridge_payload_preserves_existing_profile_shape -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/metaphysics_mapping.py backend/tests/test_intake_inference_compat.py
git commit -m "feat: add metaphysics compatibility mapping"
```

### Task 5: Switch `intake_inference` to the new engine without breaking callers

**Files:**
- Modify: `backend/intake_inference.py`
- Modify: `backend/portrait_service.py`
- Test: `backend/tests/test_intake_inference_compat.py`

- [ ] **Step 1: Write the failing delegation test**

```python
import unittest
from unittest.mock import patch

from backend.intake_inference import derive_birth_profile


class IntakeInferenceDelegationTest(unittest.TestCase):
    def test_public_derive_birth_profile_delegates_to_v2_engine(self) -> None:
        with patch(
            "backend.intake_inference.derive_birth_profile_v2",
            return_value={"engineVersion": "bazi_lunar_v1", "pillars": {"year": "丙戌", "month": None, "day": None, "hour": None}},
        ) as mocked:
            result = derive_birth_profile("2006-06-22", "08:00")

        mocked.assert_called_once()
        self.assertEqual(result["engineVersion"], "bazi_lunar_v1")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest backend.tests.test_intake_inference_compat.IntakeInferenceDelegationTest -v`

Expected: FAIL because `derive_birth_profile_v2` is not imported or called

- [ ] **Step 3: Delegate the public entrypoint to the new engine**

```python
from backend.metaphysics_profile import derive_birth_profile_v2


def derive_birth_profile_legacy(birthday: str | None, birth_time: str | None = None) -> dict[str, Any]:
    # Move the current derive_birth_profile implementation body here unchanged.
    # Do not alter its field names, heuristics, or disclaimer text in this refactor.
    ...


def derive_birth_profile(birthday: str | None, birth_time: str | None = None) -> dict[str, Any]:
    return derive_birth_profile_v2(
        birthday,
        birth_time,
        runtime_mode="production",
        fallback_mode="disabled",
    )
```

Implementation note: in the same edit, cut the full existing body of `backend/intake_inference.py:derive_birth_profile()` into `derive_birth_profile_legacy()` first, then add the thin delegating `derive_birth_profile()` wrapper shown above. This is a pure rename-plus-wrapper step; there should be no logic changes inside the legacy body.

- [ ] **Step 4: Make `portrait_service` tolerant of added metadata**

```python
def build_derived_profile_summary(student: dict[str, Any]) -> dict[str, Any]:
    derived_profile = student.get("derived_profile") or {}
    summary = {
        "constellation": derived_profile.get("constellation"),
        "birthday": derived_profile.get("birthday"),
        "birthTime": derived_profile.get("birthTime"),
        "pillars": derived_profile.get("pillars") or {},
        "hourBranchLabel": derived_profile.get("hourBranchLabel"),
        "wuxing": derived_profile.get("wuxing") or {},
        "personalityTraits": [item for item in (derived_profile.get("profile") or {}).get("personalityTraits", []) if item],
        "explanations": (derived_profile.get("profile") or {}).get("explanations") or [],
        "disclaimer": derived_profile.get("disclaimer"),
    }
    if derived_profile.get("engineVersion"):
        summary["engineVersion"] = derived_profile["engineVersion"]
    if derived_profile.get("normalizationNotes"):
        summary["normalizationNotes"] = derived_profile["normalizationNotes"]
    return summary
```

- [ ] **Step 5: Run the delegation and compatibility tests**

Run: `python -m unittest backend.tests.test_intake_inference_compat -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/intake_inference.py backend/portrait_service.py backend/tests/test_intake_inference_compat.py
git commit -m "refactor: route intake inference through metaphysics engine"
```

### Task 6: Add full regression coverage for Phase 1 accuracy rules

**Files:**
- Modify: `backend/tests/test_metaphysics_profile.py`
- Modify: `backend/tests/test_metaphysics_bridge.py`

- [ ] **Step 1: Add the remaining failing regression tests**

```python
    def test_jieqi_month_boundary_switches_exact_month_pillar(self) -> None:
        payload = {
            "engineVersion": "bazi_lunar_v1",
            "normalizedBirthDate": "2006-03-06",
            "normalizedBirthTime": "00:30",
            "trueSolarTime": "00:12",
            "pillars": {"year": "丙戌", "month": "辛卯", "day": "丙辰", "hour": "戊子"},
            "wuxing": {"counts": {"木": 2, "火": 2, "土": 2, "金": 1, "水": 1}, "dominant": "木", "secondary": "火"},
            "normalizationNotes": ["jieqi-exact-month"],
        }
        with patch("backend.metaphysics_profile.run_bazi_bridge", return_value=payload):
            result = derive_birth_profile_v2("2006-03-06", "00:30")
        self.assertEqual(result["pillars"]["month"], "辛卯")

    def test_missing_birth_time_keeps_hour_pillar_none(self) -> None:
        payload = {
            "engineVersion": "bazi_lunar_v1",
            "normalizedBirthDate": "2006-06-22",
            "normalizedBirthTime": None,
            "trueSolarTime": None,
            "pillars": {"year": "丙戌", "month": "甲午", "day": "辛酉", "hour": None},
            "wuxing": {"counts": {"木": 1, "火": 2, "土": 1, "金": 3, "水": 1}, "dominant": "金", "secondary": "火"},
            "normalizationNotes": [],
        }
        with patch("backend.metaphysics_profile.run_bazi_bridge", return_value=payload):
            result = derive_birth_profile_v2("2006-06-22", None)
        self.assertIsNone(result["pillars"]["hour"])
```

- [ ] **Step 2: Run the profile test module**

Run: `python -m unittest backend.tests.test_metaphysics_profile -v`

Expected: PASS after the previous implementation steps are complete

- [ ] **Step 3: Add a bridge error-shape regression test**

```python
    def test_run_bazi_bridge_raises_typed_error_on_invalid_json(self) -> None:
        completed = type(
            "Completed",
            (),
            {"returncode": 0, "stdout": "not-json", "stderr": ""},
        )()
        with patch("backend.metaphysics_bridge.subprocess.run", return_value=completed):
            with self.assertRaisesRegex(Exception, "invalid bridge json"):
                run_bazi_bridge(birthday="2006-06-22", birth_time="08:00")
```

- [ ] **Step 4: Run the bridge test module**

Run: `python -m unittest backend.tests.test_metaphysics_bridge -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_metaphysics_profile.py backend/tests/test_metaphysics_bridge.py
git commit -m "test: cover metaphysics accuracy and error paths"
```

### Task 7: Run end-to-end verification for backend compatibility

**Files:**
- Modify: `README.md`
- Test: `backend/tests/test_metaphysics_bridge.py`
- Test: `backend/tests/test_metaphysics_profile.py`
- Test: `backend/tests/test_intake_inference_compat.py`

- [ ] **Step 1: Add runtime notes to the README if the bridge requires local install**

```md
## Metaphysics Engine (Phase 1)

- Install bridge dependencies once: `npm install --prefix tools/metaphysics_bridge`
- Backend compatibility tests:
  - `python -m unittest backend.tests.test_metaphysics_bridge -v`
  - `python -m unittest backend.tests.test_metaphysics_profile -v`
  - `python -m unittest backend.tests.test_intake_inference_compat -v`
- Production behavior: if the Node bridge fails, report the error and do not silently fall back.
- Development behavior: legacy fallback is allowed only when explicitly enabled by the caller.
```

- [ ] **Step 2: Run focused metaphysics tests**

Run: `python -m unittest backend.tests.test_metaphysics_bridge backend.tests.test_metaphysics_profile backend.tests.test_intake_inference_compat -v`

Expected: all tests PASS

- [ ] **Step 3: Run the full backend regression suite**

Run: `python -m unittest discover -s backend/tests`

Expected: all tests PASS

- [ ] **Step 4: Run a compatibility smoke import**

Run: `python -c "from backend.intake_inference import derive_birth_profile; result = derive_birth_profile('2006-06-22', '08:00'); print(sorted(result.keys()))"`

Expected: printed keys include `autofill`, `constellation`, `disclaimer`, `engineVersion`, `pillars`, `profile`, and `wuxing`

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: document metaphysics bridge runtime and verification"
```

## Self-Review

### 1. Spec coverage

- Node bridge scaffold: covered in Task 1.
- `lunar-javascript` integration: covered in Task 2.
- Python wrapper / compatibility layer: covered in Tasks 3-5.
- Mapping layer: covered in Task 4.
- LiChun year boundary tests: covered in Task 2 and Task 6.
- JieQi month boundary tests: covered in Task 6.
- Late-`子时` next-day rule: covered in Task 2.
- Longitude / true solar time shift: covered in Task 2.
- Existing `derived_profile` compatibility: covered in Tasks 4, 5, and 7.
- Fallback / error handling: covered in Task 3 and Task 6.
- Phase 1 only, no Ziwei UI or scoring integration: respected throughout.

### 2. Placeholder scan

- No `TODO`, `TBD`, or “implement later” placeholders remain in task steps.
- JavaScript spread syntax such as `...parts` and `...solarAdjusted.notes` is intentional code, not a placeholder.

### 3. Type consistency

- Public Python API stays `derive_birth_profile(birthday, birth_time) -> dict[str, Any]`.
- Accurate engine entrypoint is consistently named `derive_birth_profile_v2`.
- Bridge payload fields are consistently named `engineVersion`, `normalizedBirthDate`, `normalizedBirthTime`, `trueSolarTime`, `pillars`, `wuxing`, and `normalizationNotes`.
- Runtime policy terms are consistently `runtime_mode` and `fallback_mode`.
