from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def normalize_target(value: str) -> str:
    target = value.strip()
    if target.endswith(".py") or "\\" in target or "/" in target:
        path = Path(target.replace("\\", "/"))
        if not path.is_absolute():
            path = (PROJECT_ROOT / path).resolve()
        else:
            path = path.resolve()
        try:
            relative = path.relative_to(PROJECT_ROOT)
        except ValueError:
            raise SystemExit(f"Test target must be inside project root: {value}") from None
        target = ".".join(relative.with_suffix("").parts)
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a single unittest module with a timeout.")
    parser.add_argument("target", help="Unittest module name or test file path inside the repo")
    parser.add_argument("--timeout-seconds", type=int, default=30, help="Timeout for the test command")
    args = parser.parse_args()

    module_name = normalize_target(args.target)
    command = [sys.executable, "-m", "unittest", module_name]

    try:
        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            timeout=args.timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        print(
            f"Timed out after {args.timeout_seconds} seconds while running {module_name}.",
            file=sys.stderr,
        )
        return 124

    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
