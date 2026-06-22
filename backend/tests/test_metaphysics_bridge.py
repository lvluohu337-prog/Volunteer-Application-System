import json
import unittest
from unittest.mock import patch

from backend.metaphysics_bridge import (
    MetaphysicsBridgeError,
    _resolve_node_executable,
    run_bazi_bridge,
)


class MetaphysicsBridgeContractTest(unittest.TestCase):
    def test_resolve_node_executable_prefers_bundled_runtime_over_broken_shim(self) -> None:
        bundled = r"C:\Users\lenovo\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
        shim = r"C:\Users\lenovo\AppData\Local\mise\shims\node.exe"

        with patch("backend.metaphysics_bridge.os.environ", {}, create=True):
            with patch("backend.metaphysics_bridge.shutil.which", return_value=shim):
                with patch("backend.metaphysics_bridge._candidate_node_paths", return_value=[bundled, shim]):
                    with patch.object(
                        __import__("pathlib").Path,
                        "exists",
                        lambda path_obj: str(path_obj) in {bundled, shim},
                    ):
                        self.assertEqual(_resolve_node_executable(), bundled)

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
                        "pillars": {
                            "year": "year-pillar",
                            "month": "month-pillar",
                            "day": "day-pillar",
                            "hour": "hour-pillar",
                        },
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
        self.assertEqual(result["pillars"]["hour"], "hour-pillar")

    def test_run_bazi_bridge_rolls_business_normalized_date_for_late_zi_hour(self) -> None:
        result = run_bazi_bridge(
            birthday="2006-02-04",
            birth_time="23:40",
            longitude=115.85,
        )

        self.assertEqual(result["normalizedBirthDate"], "2006-02-05")
        self.assertEqual(result["normalizedBirthTime"], "23:23")
        self.assertTrue(result["pillars"]["day"])
        self.assertIn("late-zi-hour-next-day", result["normalizationNotes"])

    def test_run_bazi_bridge_raises_typed_error_for_invalid_json(self) -> None:
        completed = type(
            "Completed",
            (),
            {
                "returncode": 0,
                "stdout": "{invalid-json",
                "stderr": "",
            },
        )()

        with patch("backend.metaphysics_bridge.subprocess.run", return_value=completed):
            with self.assertRaises(MetaphysicsBridgeError) as context:
                run_bazi_bridge(
                    birthday="2006-02-04",
                    birth_time="23:40",
                    longitude=115.85,
                )

        self.assertIn("invalid bridge json", str(context.exception))

    def test_run_bazi_bridge_raises_typed_error_for_nonzero_exit(self) -> None:
        completed = type(
            "Completed",
            (),
            {
                "returncode": 1,
                "stdout": "",
                "stderr": "bridge failed on exact-jieqi lookup",
            },
        )()

        with patch("backend.metaphysics_bridge.subprocess.run", return_value=completed):
            with self.assertRaises(MetaphysicsBridgeError) as context:
                run_bazi_bridge(
                    birthday="2006-06-22",
                    birth_time="08:00",
                    longitude=115.85,
                )

        self.assertIn("bridge failed on exact-jieqi lookup", str(context.exception))
