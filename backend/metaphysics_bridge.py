from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


BRIDGE_DIR = Path(__file__).resolve().parents[1] / "tools" / "metaphysics_bridge"
BRIDGE_ENTRY = BRIDGE_DIR / "bridge.mjs"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _candidate_node_paths() -> list[str]:
    env_node = os.environ.get("METAPHYSICS_NODE_BIN")
    bundled = Path.home() / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "node" / "bin" / "node.exe"
    discovered = shutil.which("node")

    candidates = [
        env_node,
        str(bundled),
        discovered,
    ]
    return [candidate for candidate in candidates if candidate]


def _resolve_node_executable() -> str:
    for candidate in _candidate_node_paths():
        path = Path(candidate)
        if not path.exists():
            continue
        normalized = str(path)
        if "AppData\\Local\\mise\\shims" in normalized:
            continue
        if normalized.startswith("C:\\Program Files\\WindowsApps\\"):
            continue
        return normalized
    raise RuntimeError("Node.js executable not found for metaphysics bridge")


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
    node_executable = _resolve_node_executable()
    completed = subprocess.run(
        [node_executable, str(BRIDGE_ENTRY), json.dumps(payload, ensure_ascii=False)],
        cwd=str(BRIDGE_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "metaphysics bridge failed")
    return json.loads(completed.stdout)
