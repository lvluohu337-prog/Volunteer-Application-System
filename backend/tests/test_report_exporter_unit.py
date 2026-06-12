from __future__ import annotations

from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import zipfile


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "data_assets" / "vendor"))

from pypdf import PdfReader

from backend.report_exporters import export_report_docx, export_report_pdf
from backend.tests.report_export_fixtures import build_minimal_report_data


class ReportExporterUnitTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="report-export-unit-"))

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_export_report_pdf_generates_real_pdf(self):
        artifact_path = self.temp_dir / "sample.pdf"

        export_report_pdf(
            build_minimal_report_data(),
            artifact_path,
            reviewed_by="测试老师",
            include_signature=True,
        )

        self.assertTrue(artifact_path.exists())
        self.assertTrue(artifact_path.read_bytes().startswith(b"%PDF-"))

        reader = PdfReader(str(artifact_path))
        self.assertGreaterEqual(len(reader.pages), 1)
        extracted_text = "\n".join(page.extract_text() or "" for page in reader.pages)
        self.assertIn("正式院校专业推荐表", extracted_text)
        self.assertIn("专业组 / 代码", extracted_text)
        self.assertIn("第一志愿建议", extracted_text)
        self.assertIn("备选志愿建议", extracted_text)
        self.assertIn("不建议报考项", extracted_text)
        self.assertIn("调剂风险", extracted_text)
        self.assertIn("合规提示", extracted_text)
        self.assertIn("保录", extracted_text)
        self.assertIn("咨询师签字", extracted_text)

    def test_export_report_docx_generates_real_docx(self):
        artifact_path = self.temp_dir / "sample.docx"

        export_report_docx(
            build_minimal_report_data(),
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
        self.assertIn("<w:tbl>", document_xml)
        self.assertIn("正式院校专业推荐表", document_xml)
        self.assertIn("第一志愿建议", document_xml)
        self.assertIn("备选志愿建议", document_xml)
        self.assertIn("不建议报考项", document_xml)
        self.assertIn("调剂风险", document_xml)
        self.assertIn("合规提示", document_xml)
        self.assertIn("保录", document_xml)
        self.assertIn("咨询师签字", document_xml)


if __name__ == "__main__":
    unittest.main()
