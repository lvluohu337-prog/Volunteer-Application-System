from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "data_assets" / "vendor"))

from pypdf import PdfReader

from backend import planning_repository
from backend.report_exporters import export_report_docx, export_report_pdf


SAMPLE_REPORT = {
    "reportTitle": "胡祥荟 志愿规划报告",
    "reportSubtitle": "河南 2026 届高考考生 / 399 报告预览",
    "activeProductLabel": "399 咨询版",
    "sections": [
        {"title": "学生基本信息", "body": "胡祥荟，河南，2026 届高考考生，当前选科/方向为物理类。"},
        {"title": "专业与学校建议", "body": "当前优先命中的真实专业方向为计算机类 / 地理科学类 / 计算机科学与技术。"},
    ],
    "advisorNotes": [
        {
            "note_title": "联调备注",
            "note_content": "导出测试应生成真实 PDF 与 DOCX 文件，而不是中间 HTML 或 Markdown。",
        }
    ],
    "disclaimer": "本报告为高考志愿规划辅助建议，不承诺任何录取结果。",
}


class ReportExporterTest(unittest.TestCase):
    def setUp(self):
        Path("C:\\tmp").mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="report-export-", dir="C:\\tmp"))

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_export_report_pdf_generates_real_pdf(self):
        artifact_path = self.temp_dir / "sample.pdf"

        export_report_pdf(
            SAMPLE_REPORT,
            artifact_path,
            reviewed_by="测试老师",
            include_signature=True,
        )

        self.assertTrue(artifact_path.exists())
        self.assertTrue(artifact_path.read_bytes().startswith(b"%PDF-"))

        reader = PdfReader(str(artifact_path))
        self.assertGreaterEqual(len(reader.pages), 1)

    def test_export_report_docx_generates_real_docx(self):
        artifact_path = self.temp_dir / "sample.docx"

        export_report_docx(
            SAMPLE_REPORT,
            artifact_path,
            reviewed_by="测试老师",
            include_signature=True,
        )

        self.assertTrue(artifact_path.exists())

        with zipfile.ZipFile(artifact_path) as archive:
            names = set(archive.namelist())
            self.assertIn("[Content_Types].xml", names)
            self.assertIn("word/document.xml", names)
            document_xml = archive.read("word/document.xml").decode("utf-8")

        self.assertIn("胡祥荟 志愿规划报告", document_xml)
        self.assertIn("咨询师签字", document_xml)

    def test_export_report_package_returns_final_document_metadata(self):
        payload = SimpleNamespace(
            reportVersion="399",
            reviewedBy="测试老师",
            includeSignature=True,
        )
        created_records: list[dict[str, object]] = []

        def fake_create_report_delivery_record(**kwargs):
            created_records.append(kwargs)
            return {
                "id": 1,
                "artifact_name": kwargs["artifact_name"],
                "artifact_path": kwargs["artifact_path"],
                "payload": kwargs["payload_summary"],
            }

        with (
            patch.object(planning_repository, "PROJECT_ROOT", self.temp_dir),
            patch.object(planning_repository, "get_student_report", return_value=SAMPLE_REPORT),
            patch.object(planning_repository, "_create_report_delivery_record", side_effect=fake_create_report_delivery_record),
        ):
            result = planning_repository.export_report_package(123, payload, export_format="pdf")

        self.assertEqual(result["studentId"], 123)
        self.assertEqual(result["productCode"], "399")
        self.assertEqual(result["artifactType"], "final_document")
        self.assertTrue(result["artifactName"].endswith(".pdf"))
        self.assertTrue(Path(result["downloadUrl"]).exists())
        self.assertEqual(created_records[0]["payload_summary"]["artifactType"], "final_document")


if __name__ == "__main__":
    unittest.main()
