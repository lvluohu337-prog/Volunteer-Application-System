from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import shutil
import tempfile
import unittest
from unittest.mock import patch

from backend import planning_repository
from backend.tests.report_export_fixtures import build_minimal_report_data


class ReportExportIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="report-export-integration-"))

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_export_report_package_minimal_regression_for_pdf_and_word(self):
        created_records: list[dict[str, object]] = []

        def fake_create_report_delivery_record(**kwargs):
            created_records.append(kwargs)
            return {
                "id": len(created_records),
                "artifact_name": kwargs["artifact_name"],
                "artifact_path": kwargs["artifact_path"],
                "payload": kwargs["payload_summary"],
            }

        with (
            patch.object(planning_repository, "PROJECT_ROOT", self.temp_dir),
            patch.object(planning_repository, "get_student_report", side_effect=lambda *args, **kwargs: build_minimal_report_data()),
            patch.object(planning_repository, "_create_report_delivery_record", side_effect=fake_create_report_delivery_record),
        ):
            for export_format, expected_suffix in (("pdf", ".pdf"), ("word", ".docx")):
                with self.subTest(export_format=export_format):
                    payload = SimpleNamespace(
                        reportVersion="399",
                        reviewedBy="测试老师",
                        includeSignature=True,
                    )
                    result = planning_repository.export_report_package(123, payload, export_format=export_format)

                    delivery_kwargs = created_records[-1]
                    artifact_path = Path(str(delivery_kwargs["artifact_path"]))

                    self.assertEqual(result["studentId"], 123)
                    self.assertEqual(result["productCode"], "399")
                    self.assertEqual(result["artifactType"], "final_document")
                    self.assertTrue(result["artifactName"].endswith(expected_suffix))
                    self.assertEqual(
                        result["downloadUrl"],
                        f"/api/reports/student/123/deliveries/{len(created_records)}/download",
                    )
                    self.assertTrue(artifact_path.exists())
                    self.assertEqual(artifact_path.name, result["artifactName"])
                    self.assertEqual(delivery_kwargs["payload_summary"]["artifactType"], "final_document")
                    self.assertIn("renderEngine", delivery_kwargs["payload_summary"])


if __name__ == "__main__":
    unittest.main()
