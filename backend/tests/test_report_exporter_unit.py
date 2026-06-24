from __future__ import annotations

from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest
import zipfile


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "data_assets" / "vendor"))

from pypdf import PdfReader

from backend.report_exporters import (
    PDF_MARGIN_LEFT,
    PDF_MARGIN_RIGHT,
    PDF_PAGE_WIDTH,
    ReportBlock,
    _build_first_choice_table_block,
    _build_pdf_page_streams,
    _build_recommendation_table_block,
    _build_report_blocks,
    _pdf_text_command,
    export_report_docx,
    export_report_pdf,
)
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
        metadata = reader.metadata or {}
        self.assertIn("ReportLab", metadata.get("/Producer", ""))
        extracted_text = "\n".join(page.extract_text() or "" for page in reader.pages)
        self.assertIn("正式院校专业推荐表", extracted_text)
        self.assertIn("院校", extracted_text)
        self.assertIn("专业", extracted_text)
        self.assertIn("专业组 / 代码", extracted_text)
        self.assertIn("城市", extracted_text)
        self.assertIn("最低分 / 位次", extracted_text)
        self.assertIn("录取概率", extracted_text)
        self.assertIn("风险提示", extracted_text)
        self.assertIn("第一志愿建议", extracted_text)
        self.assertIn("备选志愿建议", extracted_text)
        self.assertIn("不建议报考项", extracted_text)
        self.assertIn("调剂风险", extracted_text)
        self.assertIn("合规提示", extracted_text)
        self.assertIn("保录", extracted_text)
        self.assertIn("咨询师签字", extracted_text)

    def test_report_blocks_split_export_meta_into_multiple_lines(self):
        blocks = _build_report_blocks(
            build_minimal_report_data(),
            reviewed_by="测试老师",
            include_signature=False,
        )

        meta_texts = [block.text for block in blocks[:5] if block.style == "meta"]
        self.assertIn("河南 2026 届高考考生 / 399 报告预览", meta_texts)
        self.assertIn("导出版本：399 元标准版报告", meta_texts)
        self.assertIn("导出人：测试老师", meta_texts)
        self.assertTrue(any(text.startswith("导出时间：") for text in meta_texts))

    def test_report_blocks_start_with_formal_cover_and_personalized_evidence(self):
        blocks = _build_report_blocks(
            build_minimal_report_data(),
            reviewed_by="测试老师",
            include_signature=False,
        )
        texts = [block.text for block in blocks if block.text]
        joined = "\n".join(texts)
        headings = [block.text for block in blocks if block.style == "heading"]

        self.assertEqual(blocks[0].text, "河南 2026 高考志愿正式规划报告")
        self.assertIn("个人决策画像摘要", headings)
        self.assertIn("本报告核心结论", headings)
        self.assertIn("为什么适合该学生", headings)
        self.assertIn("证据链与复核清单", headings)
        self.assertIn("胡祥荟", joined)
        self.assertIn("河南 / 2026 届 / 物理类", joined)
        self.assertIn("总分 612", joined)
        self.assertIn("位次 12543", joined)
        self.assertIn("稳妥型", joined)
        self.assertIn("郑州大学 - 自动化类", joined)
        self.assertIn("真实招生候选 48 条", joined)
        self.assertIn("组内 6 个专业接受度", joined)

    def test_report_blocks_put_formal_plan_after_page_break(self):
        blocks = _build_report_blocks(
            build_minimal_report_data(),
            reviewed_by="测试老师",
            include_signature=False,
        )
        plan_index = next(index for index, block in enumerate(blocks) if block.text == "正式院校专业推荐表")

        self.assertEqual(blocks[plan_index - 1].style, "page_break")

    def test_report_blocks_group_recommendations_by_six_display_tiers(self):
        report_data = build_minimal_report_data()
        base_item = report_data["recommendationTable"][0]
        tiers = [
            ("risk", "险中尝试"),
            ("sprint", "冲刺推荐"),
            ("steady", "稳妥主力"),
            ("protect", "保底承接"),
            ("cushion", "垫底缓冲"),
            ("fallback", "兜底守线"),
        ]
        report_data["recommendationTable"] = [
            {
                **base_item,
                "institutionName": f"{title}大学",
                "displayTier": key,
                "displayTierTitle": title,
            }
            for key, title in tiers
        ]

        blocks = _build_report_blocks(report_data, reviewed_by="测试老师", include_signature=False)
        headings = [block.text for block in blocks if block.style == "heading"]

        for _, title in tiers:
            self.assertIn(title, headings)

    def test_core_pdf_tables_fit_within_page_width(self):
        report_data = build_minimal_report_data()
        recommendation_block = _build_recommendation_table_block(report_data["recommendationTable"])
        first_choice_block = _build_first_choice_table_block(report_data["firstChoice"])
        usable_width = PDF_PAGE_WIDTH - PDF_MARGIN_LEFT - PDF_MARGIN_RIGHT

        self.assertLessEqual(sum(recommendation_block.table_column_widths), usable_width)
        self.assertLessEqual(sum(first_choice_block.table_column_widths), usable_width)

    def test_pdf_table_does_not_orphan_header_at_page_bottom(self):
        report_data = build_minimal_report_data()
        filler = ReportBlock("body", "\n".join(["填充内容"] * 35))
        recommendation_block = _build_recommendation_table_block(report_data["recommendationTable"])

        page_streams = _build_pdf_page_streams([filler, recommendation_block])

        self.assertGreaterEqual(len(page_streams), 2)
        self.assertNotIn("院".encode("utf-16-be").hex().upper(), page_streams[0])
        self.assertIn("院".encode("utf-16-be").hex().upper(), page_streams[1])

    def test_pdf_table_leaves_readable_gap_before_following_text(self):
        report_data = build_minimal_report_data()
        recommendation_block = _build_recommendation_table_block(report_data["recommendationTable"])
        page_stream = _build_pdf_page_streams([recommendation_block, ReportBlock("body", "表后说明")])[0]

        rectangle_matches = re.findall(r" ([0-9.]+) ([0-9.]+) ([0-9.]+) ([0-9.]+) re B Q", page_stream)
        table_bottom = min(float(match[1]) for match in rectangle_matches)
        marker_hex = "表".encode("utf-16-be").hex().upper()
        marker_match = re.search(rf"1 0 0 1 [0-9.]+ ([0-9.]+) Tm\n<{marker_hex}> Tj", page_stream)

        self.assertIsNotNone(marker_match)
        marker_y = float(marker_match.group(1))
        self.assertLessEqual(marker_y, table_bottom - 14.0)

    def test_pdf_text_command_positions_mixed_script_text_per_character(self):
        command = _pdf_text_command(
            "导出时间：2026-06-23 11:22:20",
            x=52.0,
            y=760.0,
            font_size=10.5,
            color_command="0 0 0 rg",
        )

        self.assertGreater(command.count(" Tj"), 5)
        self.assertGreater(command.count(" Tm"), 5)

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

        self.assertIn("河南 2026 高考志愿正式规划报告", document_xml)
        self.assertIn("胡祥荟：河南 / 2026 届 / 物理类", document_xml)
        self.assertIn("<w:tbl>", document_xml)
        self.assertIn("正式院校专业推荐表", document_xml)
        self.assertIn("院校", document_xml)
        self.assertIn("专业", document_xml)
        self.assertIn("专业组 / 代码", document_xml)
        self.assertIn("城市", document_xml)
        self.assertIn("最低分 / 位次", document_xml)
        self.assertIn("录取概率", document_xml)
        self.assertIn("风险提示", document_xml)
        self.assertIn("第一志愿建议", document_xml)
        self.assertIn("备选志愿建议", document_xml)
        self.assertIn("不建议报考项", document_xml)
        self.assertIn("调剂风险", document_xml)
        self.assertIn("合规提示", document_xml)
        self.assertIn("保录", document_xml)
        self.assertIn("咨询师签字", document_xml)


if __name__ == "__main__":
    unittest.main()
