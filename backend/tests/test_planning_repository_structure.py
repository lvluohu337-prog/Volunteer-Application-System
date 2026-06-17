from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path
import unittest


REPOSITORY_PATH = Path(__file__).resolve().parents[1] / "planning_repository.py"


class PlanningRepositoryStructureTest(unittest.TestCase):
    def test_planning_repository_does_not_define_duplicate_functions(self):
        module = ast.parse(REPOSITORY_PATH.read_text(encoding="utf-8"))
        function_names = [
            node.name
            for node in module.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        duplicates = sorted(name for name, count in Counter(function_names).items() if count > 1)

        self.assertEqual([], duplicates)


if __name__ == "__main__":
    unittest.main()
