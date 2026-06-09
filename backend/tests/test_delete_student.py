from __future__ import annotations

import unittest
from contextlib import contextmanager
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend import repository
from backend.main import app


class DeleteStudentApiTest(unittest.TestCase):
    def setUp(self):
        self.init_db_patcher = patch("backend.main.init_db", return_value=None)
        self.init_db_patcher.start()
        self.client_context = TestClient(app)
        self.client = self.client_context.__enter__()

    def tearDown(self):
        self.client_context.__exit__(None, None, None)
        self.init_db_patcher.stop()

    def test_delete_student_success_returns_ok(self):
        with patch("backend.main.delete_student", return_value={"id": 42}):
            response = self.client.delete("/api/students/42")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "student deleted")
        self.assertEqual(response.json()["data"]["id"], 42)

    def test_delete_missing_student_returns_not_found(self):
        with patch("backend.main.delete_student", side_effect=HTTPException(status_code=404, detail="Student not found")):
            response = self.client.delete("/api/students/999999")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Student not found")


class DeleteStudentCompatibilityTest(unittest.TestCase):
    def test_delete_student_does_not_depend_on_rowcount(self):
        class ResultWithoutRowcount:
            def __init__(self, row=None):
                self._row = row

            def fetchone(self):
                return self._row

        class FakeConnection:
            def __init__(self):
                self.delete_calls = 0

            def execute(self, sql, params=None):
                normalized_sql = " ".join(sql.split())
                if normalized_sql.startswith("SELECT id FROM students"):
                    return ResultWithoutRowcount({"id": params[0]})
                if normalized_sql.startswith("DELETE FROM students"):
                    self.delete_calls += 1
                    return ResultWithoutRowcount()
                raise AssertionError(f"Unexpected SQL: {normalized_sql}")

        fake_connection = FakeConnection()

        @contextmanager
        def fake_db_session():
            yield fake_connection

        with patch.object(repository, "db_session", fake_db_session):
            repository.delete_student(42)

        self.assertEqual(fake_connection.delete_calls, 1)

    def test_delete_student_missing_record_still_returns_not_found(self):
        class ResultWithoutRowcount:
            def fetchone(self):
                return None

        class FakeConnection:
            def execute(self, sql, params=None):
                normalized_sql = " ".join(sql.split())
                if normalized_sql.startswith("SELECT id FROM students"):
                    return ResultWithoutRowcount()
                raise AssertionError(f"Unexpected SQL: {normalized_sql}")

        @contextmanager
        def fake_db_session():
            yield FakeConnection()

        with patch.object(repository, "db_session", fake_db_session):
            with self.assertRaises(HTTPException) as context:
                repository.delete_student(404)

        self.assertEqual(context.exception.status_code, 404)
        self.assertEqual(context.exception.detail, "Student not found")
