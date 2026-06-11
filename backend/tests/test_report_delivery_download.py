from __future__ import annotations

import unittest
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from backend import planning_repository
from backend.main import get_report_delivery_file


class ReportDeliveryDownloadRepositoryTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir_ctx = TemporaryDirectory(prefix="report-download-")
        self.temp_dir = Path(self.temp_dir_ctx.name)

    def tearDown(self):
        self.temp_dir_ctx.cleanup()

    def test_get_report_delivery_download_returns_safe_metadata(self):
        artifact_path = self.temp_dir / "sample.pdf"
        artifact_path.write_bytes(b"%PDF-1.4\nsample")

        class Result:
            def __init__(self, row):
                self._row = row

            def fetchone(self):
                return self._row

        class FakeConnection:
            def execute(self, sql, params=None):
                normalized_sql = " ".join(sql.split())
                if normalized_sql.startswith("SELECT id, student_id, product_code, export_format"):
                    return Result(
                        {
                            "id": 7,
                            "student_id": 123,
                            "product_code": "399",
                            "export_format": "pdf",
                            "report_title": "示例报告",
                            "artifact_name": "sample.pdf",
                            "artifact_path": str(artifact_path),
                            "delivery_status": "generated",
                            "generated_by": "tester",
                            "include_signature": 1,
                            "payload_json": "{}",
                            "created_at": "2026-06-11 12:00:00",
                        }
                    )
                raise AssertionError(f"Unexpected SQL: {normalized_sql}")

        @contextmanager
        def fake_db_session():
            yield FakeConnection()

        with (
            patch.object(planning_repository, "db_session", fake_db_session),
            patch.object(planning_repository, "_report_exports_dir", return_value=self.temp_dir),
        ):
            result = planning_repository.get_report_delivery_download(123, 7)

        self.assertEqual(result["studentId"], 123)
        self.assertEqual(result["recordId"], 7)
        self.assertEqual(result["artifactName"], "sample.pdf")
        self.assertEqual(result["mediaType"], "application/pdf")
        self.assertEqual(result["downloadUrl"], "/api/reports/student/123/deliveries/7/download")
        self.assertEqual(result["artifactPath"], artifact_path.resolve())


class ReportDeliveryDownloadRouteTest(unittest.TestCase):
    def test_download_route_returns_file_response(self):
        artifact_path = Path("D:/2026workspace/Volunteer Application System/data_assets/generated_reports/sample.pdf")
        with patch(
            "backend.main.get_report_delivery_download",
            return_value={
                "recordId": 7,
                "studentId": 123,
                "artifactPath": artifact_path,
                "artifactName": "sample.pdf",
                "mediaType": "application/pdf",
                "downloadUrl": "/api/reports/student/123/deliveries/7/download",
            },
        ):
            response = get_report_delivery_file(123, 7)

        self.assertEqual(response.path, artifact_path)
        self.assertEqual(response.media_type, "application/pdf")
        self.assertIn('filename="sample.pdf"', response.headers["content-disposition"])


if __name__ == "__main__":
    unittest.main()
