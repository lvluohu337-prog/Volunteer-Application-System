from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import io
from pathlib import Path
import zipfile
import zlib
from xml.sax.saxutils import escape

from backend.compliance import COMPLIANCE_COPY_RULES, COMPLIANCE_DISCLAIMER, INTERFACE_BOUNDARY_NOTE


PDF_PAGE_WIDTH = 595.28
PDF_PAGE_HEIGHT = 841.89
PDF_MARGIN_LEFT = 52.0
PDF_MARGIN_RIGHT = 52.0
PDF_MARGIN_TOP = 56.0
PDF_MARGIN_BOTTOM = 56.0
HOT_MAJOR_KEYWORDS = (
    "计算机",
    "人工智能",
    "软件",
    "电子信息",
    "通信",
    "自动化",
    "电气",
    "临床",
    "口腔",
    "法学",
    "师范",
)


@dataclass(frozen=True)
class ReportBlock:
    style: str
    text: str = ""
    table_headers: tuple[str, ...] = ()
    table_rows: tuple[tuple[str, ...], ...] = ()
    table_column_widths: tuple[float, ...] = ()


def export_report_docx(
    report_data: dict[str, object],
    output_path: Path,
    *,
    reviewed_by: str | None = None,
    include_signature: bool = False,
) -> None:
    blocks = _build_report_blocks(report_data, reviewed_by=reviewed_by, include_signature=include_signature)
    document_xml = _build_docx_document_xml(blocks)

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _build_docx_content_types_xml())
        archive.writestr("_rels/.rels", _build_docx_root_rels_xml())
        archive.writestr("docProps/core.xml", _build_docx_core_xml(report_data))
        archive.writestr("docProps/app.xml", _build_docx_app_xml())
        archive.writestr("word/document.xml", document_xml)
        archive.writestr("word/styles.xml", _build_docx_styles_xml())
        archive.writestr("word/_rels/document.xml.rels", _build_docx_document_rels_xml())


def export_report_pdf(
    report_data: dict[str, object],
    output_path: Path,
    *,
    reviewed_by: str | None = None,
    include_signature: bool = False,
) -> None:
    blocks = _build_report_blocks(report_data, reviewed_by=reviewed_by, include_signature=include_signature)
    page_streams = _build_pdf_page_streams(blocks)
    output_path.write_bytes(_build_pdf_bytes(page_streams))


def _build_report_blocks(
    report_data: dict[str, object],
    *,
    reviewed_by: str | None,
    include_signature: bool,
) -> list[ReportBlock]:
    title = str(report_data.get("reportTitle") or "志愿规划报告")
    subtitle = str(report_data.get("reportSubtitle") or "")
    product_label = str(report_data.get("activeProductLabel") or "报告版本")
    export_meta = f"导出版本：{product_label}    导出时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    if reviewed_by:
        export_meta += f"    导出人：{reviewed_by}"

    blocks = [
        ReportBlock("title", title),
        ReportBlock("meta", subtitle),
        ReportBlock("meta", export_meta),
    ]

    _append_structured_recommendation_blocks(blocks, report_data)

    for section in report_data.get("sections") or []:
        if not isinstance(section, dict):
            continue
        heading = str(section.get("title") or "章节")
        body = str(section.get("body") or "")
        blocks.append(ReportBlock("heading", heading))
        blocks.append(ReportBlock("body", body))

    advisor_notes = report_data.get("advisorNotes") or []
    if advisor_notes:
        blocks.append(ReportBlock("heading", "咨询师补充备注"))
        for item in advisor_notes:
            if not isinstance(item, dict):
                continue
            note_title = str(item.get("note_title") or "未命名备注")
            note_content = str(item.get("note_content") or "")
            blocks.append(ReportBlock("bullet", f"{note_title}：{note_content}"))

    blocks.append(ReportBlock("heading", "合规提示"))
    blocks.append(ReportBlock("body", str(report_data.get("disclaimer") or COMPLIANCE_DISCLAIMER)))
    blocks.append(ReportBlock("body", f"接口边界：{str(report_data.get('boundaryNote') or INTERFACE_BOUNDARY_NOTE)}"))
    for rule in COMPLIANCE_COPY_RULES:
        blocks.append(ReportBlock("bullet", rule))

    if include_signature:
        blocks.append(ReportBlock("heading", "签字确认"))
        blocks.append(ReportBlock("signature", "咨询师签字：________________    家长确认：________________"))

    return [block for block in blocks if block.text.strip() or block.table_rows]


def _append_structured_recommendation_blocks(
    blocks: list[ReportBlock],
    report_data: dict[str, object],
) -> None:
    recommendation_table = [item for item in (report_data.get("recommendationTable") or []) if isinstance(item, dict)]
    first_choice = report_data.get("firstChoice") if isinstance(report_data.get("firstChoice"), dict) else None
    alternatives = [item for item in (report_data.get("alternatives") or []) if isinstance(item, dict)]
    not_recommended = [item for item in (report_data.get("notRecommended") or []) if isinstance(item, dict)]

    if not any([recommendation_table, first_choice, alternatives, not_recommended]):
        return

    blocks.append(ReportBlock("heading", "正式院校专业推荐表"))
    blocks.append(
        ReportBlock(
            "body",
            f"本次导出共包含 {len(recommendation_table)} 条结构化推荐，以下内容用于正式交付前的院校专业复核。",
        )
    )

    grouped: dict[str, list[dict[str, object]]] = {"rush": [], "steady": [], "safe": []}
    for item in recommendation_table:
        bucket = str(item.get("bucket") or "")
        if bucket in grouped:
            grouped[bucket].append(item)
        else:
            grouped["steady"].append(item)

    for bucket_key, bucket_label in (("rush", "冲刺推荐"), ("steady", "稳妥推荐"), ("safe", "保底推荐")):
        items = grouped[bucket_key]
        if not items:
            continue
        blocks.append(ReportBlock("heading", bucket_label))
        blocks.append(_build_recommendation_table_block(items))

    if first_choice:
        blocks.append(ReportBlock("heading", "第一志愿建议"))
        blocks.append(
            ReportBlock(
                "body",
                "以下为本轮优先建议的一志愿样本，请在正式提交前结合专业组边界、调剂接受度和计划波动做最终确认。",
            )
        )
        blocks.append(_build_first_choice_table_block(first_choice))
        blocks.extend(_build_recommendation_blocks(first_choice, include_bucket=True))

    if alternatives:
        blocks.append(ReportBlock("heading", "备选志愿建议"))
        blocks.append(
            ReportBlock(
                "body",
                f"以下 {min(len(alternatives), 5)} 项可作为主方案后的备选清单，适合在正式志愿表里承担补位和风险对冲作用。",
            )
        )
        blocks.append(_build_alternatives_table_block(alternatives[:5]))
        for item in alternatives[:5]:
            blocks.extend(_build_recommendation_blocks(item, include_bucket=True, condensed=True))

    if not_recommended:
        blocks.append(ReportBlock("heading", "不建议报考项"))
        blocks.append(
            ReportBlock(
                "body",
                "以下项目当前不建议直接纳入正式志愿表；若家庭仍想保留，必须先逐项完成人工复核和院校规则确认。",
            )
        )
        blocks.append(_build_not_recommended_table_block(not_recommended[:5]))
        for item in not_recommended[:5]:
            blocks.append(ReportBlock("bullet", _build_not_recommended_text(item)))


def _build_recommendation_blocks(
    item: dict[str, object],
    *,
    include_bucket: bool,
    condensed: bool = False,
) -> list[ReportBlock]:
    blocks = [ReportBlock("bullet", _build_recommendation_summary(item, include_bucket=include_bucket))]

    detail_parts: list[str] = []
    recommendation_reason = str(item.get("recommendationReason") or "").strip()
    risk_summary = str(item.get("riskSummary") or "").strip()
    city_path_note = str(item.get("cityPathNote") or "").strip()

    if recommendation_reason:
        detail_parts.append(f"推荐理由：{recommendation_reason}")
    if risk_summary:
        detail_parts.append(f"风险摘要：{risk_summary}")
    if city_path_note and not condensed:
        detail_parts.append(f"城市路径：{city_path_note}")

    if detail_parts:
        blocks.append(ReportBlock("body", "\n".join(detail_parts)))

    risk_parts = _build_recommendation_risk_lines(item)
    if risk_parts:
        blocks.append(ReportBlock("body", "\n".join(risk_parts)))

    return blocks


def _build_recommendation_risk_lines(item: dict[str, object]) -> list[str]:
    return [
        f"调剂风险：{_build_adjustment_risk_text(item)}",
        f"选科限制：{_build_subject_requirement_text(item)}",
        f"计划变化风险：{_build_plan_change_risk_text(item)}",
        f"热门专业风险提示：{_build_hot_major_risk_text(item)}",
    ]


def _build_adjustment_risk_text(item: dict[str, object]) -> str:
    adjustment_advice = item.get("adjustmentAdvice") if isinstance(item.get("adjustmentAdvice"), dict) else None
    if not adjustment_advice:
        return "正式填报前仍需逐校核对专业调剂与退档规则。"

    label = str(adjustment_advice.get("label") or "").strip()
    detail = str(adjustment_advice.get("detail") or "").strip()
    if label and detail:
        return f"{label}，{detail}"
    return label or detail or "正式填报前仍需逐校核对专业调剂与退档规则。"


def _build_subject_requirement_text(item: dict[str, object]) -> str:
    subject_requirement = str(item.get("subjectRequirement") or "").strip()
    subject_label = str(item.get("subjectLabel") or "").strip()
    subject_status = str(item.get("subjectStatus") or "").strip().lower()

    if subject_requirement and subject_label:
        return f"{subject_label}，当前要求为 {subject_requirement}。"
    if subject_requirement:
        return f"当前要求为 {subject_requirement}，正式填报前需结合最新招生章程再次核对。"
    if subject_label:
        return f"{subject_label}，但仍建议和院校最新专业组要求逐项复核。"
    if subject_status == "mismatch":
        return "当前选科与目标专业组存在不匹配风险，不建议直接按该项正式报考。"
    return "当前未提取到明确选科要求，正式填报前需逐校逐专业复核。"


def _build_plan_change_risk_text(item: dict[str, object]) -> str:
    plan_risk_label = str(item.get("planRiskLabel") or "").strip()
    risk_summary = str(item.get("riskSummary") or "").strip()
    plan_count = item.get("planCount")
    group_code = str(item.get("planGroupCode") or item.get("batchCode") or "当前专业组").strip()

    parts: list[str] = []
    if plan_risk_label:
        parts.append(plan_risk_label)
    if plan_count not in (None, ""):
        parts.append(f"{group_code} 当前参考计划人数 {plan_count}")
    if risk_summary:
        parts.append(risk_summary)
    if not parts:
        return "当年招生计划、专业组拆分和招生章程变化都可能影响最终结果，提交前需再核一次。"
    return "；".join(parts)


def _build_hot_major_risk_text(item: dict[str, object]) -> str:
    major_name = str(item.get("majorName") or "").strip()
    risk_level = str(item.get("riskLevel") or "").strip().lower()
    probability_label = str(item.get("probabilityLabel") or "").strip()

    if any(keyword in major_name for keyword in HOT_MAJOR_KEYWORDS):
        hot_text = "该专业通常属于报考热度较高方向，同分段竞争和专业冷热变化可能放大实际门槛。"
        if probability_label:
            return f"{hot_text} 当前系统提示为“{probability_label}”，正式填报时需保守看待热度上浮。"
        return f"{hot_text} 正式填报时需保守看待热度上浮。"
    if risk_level in {"high", "review"}:
        return "虽然当前未识别为典型热门专业，但若当年院校宣传、城市热度或专业组调整带来集中报考，门槛仍可能上浮。"
    return "当前未识别到典型热门专业热度信号，但仍需关注当年专业冷热变化对最低位次的影响。"


def _build_group_and_codes_text(item: dict[str, object]) -> str:
    group_code = str(item.get("planGroupCode") or item.get("batchCode") or "-").strip() or "-"
    code_parts: list[str] = []

    institution_code = str(item.get("institutionCode") or "").strip()
    major_code = str(item.get("majorCode") or "").strip()
    if institution_code:
        code_parts.append(f"院校{institution_code}")
    if major_code:
        code_parts.append(f"专业{major_code}")

    if not code_parts:
        return group_code
    return f"{group_code} / {' '.join(code_parts)}"


def _build_first_choice_table_block(item: dict[str, object]) -> ReportBlock:
    headers = (
        "院校 / 专业 / 城市",
        "专业组 / 代码",
        "最低分",
        "最低位次",
        "位次差",
        "风险等级",
        "推荐定位",
    )
    location_text = str(item.get("cityText") or item.get("city") or item.get("province") or "-")
    reason_text = str(item.get("recommendationReason") or "当前适合作为第一志愿主力样本。").strip()
    return ReportBlock(
        "table",
        table_headers=headers,
        table_rows=(
            (
                f"{item.get('institutionName') or '目标院校'} / {item.get('majorName') or '目标专业'} / {location_text}",
                _build_group_and_codes_text(item),
                _format_number(item.get("minScore")) if item.get("minScore") not in (None, "") else "-",
                _format_number(item.get("minRank")) if item.get("minRank") not in (None, "") else "-",
                str(item.get("rankGap") or "-"),
                str(item.get("riskLabel") or "-"),
                reason_text,
            ),
        ),
        table_column_widths=(140.0, 88.0, 42.0, 54.0, 48.0, 48.0, 95.28),
    )


def _build_alternatives_table_block(items: list[dict[str, object]]) -> ReportBlock:
    headers = (
        "院校 / 专业 / 城市",
        "专业组 / 代码",
        "风险等级",
        "推荐理由",
        "调剂建议",
    )
    rows: list[tuple[str, ...]] = []
    for item in items:
        location_text = str(item.get("cityText") or item.get("city") or item.get("province") or "-")
        rows.append(
            (
                f"{item.get('institutionName') or '目标院校'} / {item.get('majorName') or '目标专业'} / {location_text}",
                _build_group_and_codes_text(item),
                str(item.get("riskLabel") or "-"),
                str(item.get("recommendationReason") or item.get("riskSummary") or "待补充备选理由").strip(),
                _build_adjustment_risk_text(item),
            )
        )
    return ReportBlock(
        "table",
        table_headers=headers,
        table_rows=tuple(rows),
        table_column_widths=(140.0, 88.0, 48.0, 105.0, 110.28),
    )


def _build_recommendation_table_block(items: list[dict[str, object]]) -> ReportBlock:
    headers = (
        "院校 / 专业 / 城市",
        "专业组 / 代码",
        "最低分",
        "最低位次",
        "位次差",
        "风险等级",
        "推荐理由",
    )
    rows: list[tuple[str, ...]] = []
    for item in items:
        location_text = str(item.get("cityText") or item.get("city") or item.get("province") or "-")
        reason_text = str(item.get("recommendationReason") or item.get("riskSummary") or "待补充推荐理由").strip()
        rows.append(
            (
                f"{item.get('institutionName') or '目标院校'} / {item.get('majorName') or '目标专业'} / {location_text}",
                _build_group_and_codes_text(item),
                _format_number(item.get("minScore")) if item.get("minScore") not in (None, "") else "-",
                _format_number(item.get("minRank")) if item.get("minRank") not in (None, "") else "-",
                str(item.get("rankGap") or "-"),
                str(item.get("riskLabel") or "-"),
                reason_text,
            )
        )
    return ReportBlock(
        "table",
        table_headers=headers,
        table_rows=tuple(rows),
        table_column_widths=(140.0, 88.0, 42.0, 54.0, 48.0, 48.0, 95.28),
    )


def _build_recommendation_summary(item: dict[str, object], *, include_bucket: bool) -> str:
    title = f"{item.get('institutionName') or '目标院校'} - {item.get('majorName') or '目标专业'}"
    parts = [title]

    if include_bucket and item.get("bucket"):
        parts.append(f"档位：{_bucket_label(str(item.get('bucket') or ''))}")
    if item.get("planGroupCode") or item.get("institutionCode") or item.get("majorCode"):
        parts.append(f"专业组/代码：{_build_group_and_codes_text(item)}")
    if item.get("cityText") or item.get("city") or item.get("province"):
        parts.append(f"城市：{item.get('cityText') or item.get('city') or item.get('province')}")
    if item.get("minScore") not in (None, ""):
        parts.append(f"最低分：{_format_number(item.get('minScore'))}")
    if item.get("minRank") not in (None, ""):
        parts.append(f"最低位次：{_format_number(item.get('minRank'))}")
    if item.get("rankGap") not in (None, ""):
        parts.append(f"位次差：{item.get('rankGap')}")
    if item.get("riskLabel"):
        parts.append(f"风险：{item.get('riskLabel')}")

    return " / ".join(str(part) for part in parts if str(part).strip())


def _build_not_recommended_text(item: dict[str, object]) -> str:
    title = f"{item.get('institutionName') or '目标院校'} - {item.get('majorName') or '目标专业'}"
    reason = str(item.get("reason") or item.get("riskSummary") or "建议暂不优先纳入正式志愿表。").strip()
    notes = _build_not_recommended_notes_text(item)
    if notes:
        return f"{title}：{reason}；复核说明：{notes}"
    return f"{title}：{reason}"


def _build_not_recommended_table_block(items: list[dict[str, object]]) -> ReportBlock:
    headers = (
        "院校 / 专业 / 城市",
        "专业组 / 代码",
        "最低分",
        "最低位次",
        "不建议原因",
        "复核说明",
    )
    rows: list[tuple[str, ...]] = []
    for item in items:
        location_text = str(item.get("cityText") or item.get("city") or item.get("province") or "-")
        rows.append(
            (
                f"{item.get('institutionName') or '目标院校'} / {item.get('majorName') or '目标专业'} / {location_text}",
                _build_group_and_codes_text(item),
                _format_number(item.get("minScore")) if item.get("minScore") not in (None, "") else "-",
                _format_number(item.get("minRank")) if item.get("minRank") not in (None, "") else "-",
                str(item.get("reason") or item.get("riskSummary") or "建议暂不优先纳入正式志愿表。").strip(),
                _build_not_recommended_notes_text(item),
            )
        )
    return ReportBlock(
        "table",
        table_headers=headers,
        table_rows=tuple(rows),
        table_column_widths=(132.0, 82.0, 42.0, 54.0, 100.0, 81.28),
    )


def _build_not_recommended_notes_text(item: dict[str, object]) -> str:
    notes = item.get("notes")
    if isinstance(notes, list):
        normalized = [str(note).strip() for note in notes if str(note).strip()]
        if normalized:
            return "；".join(normalized[:3])
    return "如需保留该项，需重新核对位次、选科要求、调剂与院校当年章程。"


def _bucket_label(bucket: str) -> str:
    return {
        "rush": "冲刺",
        "steady": "稳妥",
        "safe": "保底",
    }.get(bucket, "待复核")


def _format_number(value: object) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if numeric.is_integer():
        return str(int(numeric))
    return f"{numeric:.1f}"


def _build_docx_document_xml(blocks: list[ReportBlock]) -> str:
    elements: list[str] = []
    for block in blocks:
        if block.table_rows:
            elements.append(_build_docx_table_xml(block))
            continue
        style_id = _docx_style_id(block.style)
        for line in _split_block_lines(block.text):
            if not line:
                elements.append(_docx_paragraph_xml("", style_id="Normal"))
                continue
            elements.append(_docx_paragraph_xml(line, style_id=style_id))

    body = "".join(elements)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document '
        'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}"
        "<w:sectPr>"
        '<w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1440" w:right="1080" w:bottom="1440" w:left="1080" w:header="720" w:footer="720" w:gutter="0"/>'
        "</w:sectPr>"
        "</w:body></w:document>"
    )


def _build_docx_table_xml(block: ReportBlock) -> str:
    headers = list(block.table_headers)
    rows = [list(row) for row in block.table_rows]
    widths = list(block.table_column_widths) if block.table_column_widths else []
    if headers and not widths:
        widths = [7200 / len(headers)] * len(headers)

    header_xml = _docx_table_row_xml(headers, widths=widths, is_header=True)
    row_xml = "".join(_docx_table_row_xml(row, widths=widths, is_header=False) for row in rows)
    grid_cols = "".join(
        f'<w:gridCol w:w="{_docx_width_value(width)}"/>'
        for width in widths
    )

    return (
        "<w:tbl>"
        "<w:tblPr>"
        '<w:tblStyle w:val="TableGrid"/>'
        '<w:tblW w:w="0" w:type="auto"/>'
        '<w:tblLayout w:type="fixed"/>'
        "<w:tblBorders>"
        '<w:top w:val="single" w:sz="8" w:space="0" w:color="C9D7F0"/>'
        '<w:left w:val="single" w:sz="8" w:space="0" w:color="C9D7F0"/>'
        '<w:bottom w:val="single" w:sz="8" w:space="0" w:color="C9D7F0"/>'
        '<w:right w:val="single" w:sz="8" w:space="0" w:color="C9D7F0"/>'
        '<w:insideH w:val="single" w:sz="6" w:space="0" w:color="D9E3F3"/>'
        '<w:insideV w:val="single" w:sz="6" w:space="0" w:color="D9E3F3"/>'
        "</w:tblBorders>"
        '<w:tblCellMar><w:top w:w="70" w:type="dxa"/><w:left w:w="90" w:type="dxa"/><w:bottom w:w="70" w:type="dxa"/><w:right w:w="90" w:type="dxa"/></w:tblCellMar>'
        "</w:tblPr>"
        f"<w:tblGrid>{grid_cols}</w:tblGrid>"
        f"{header_xml}{row_xml}"
        "</w:tbl>"
    )


def _docx_table_row_xml(cells: list[str], *, widths: list[float], is_header: bool) -> str:
    row_cells = []
    for index, cell in enumerate(cells):
        width = widths[index] if index < len(widths) else 1200
        row_cells.append(_docx_table_cell_xml(str(cell or "-"), width=width, is_header=is_header))
    return f"<w:tr>{''.join(row_cells)}</w:tr>"


def _docx_table_cell_xml(text: str, *, width: float, is_header: bool) -> str:
    safe_text = escape(text)
    width_value = _docx_width_value(width)
    shading = '<w:shd w:val="clear" w:color="auto" w:fill="E8F0FE"/>' if is_header else ""
    bold = "<w:b/>" if is_header else ""
    color = "1D4ED8" if is_header else "1F2937"
    return (
        "<w:tc>"
        f'<w:tcPr><w:tcW w:w="{width_value}" w:type="dxa"/>{shading}</w:tcPr>'
        "<w:p>"
        '<w:pPr><w:spacing w:after="60" w:line="300" w:lineRule="auto"/></w:pPr>'
        "<w:r>"
        f'<w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="微软雅黑"/>{bold}<w:color w:val="{color}"/><w:sz w:val="20"/></w:rPr>'
        f'<w:t xml:space="preserve">{safe_text}</w:t>'
        "</w:r>"
        "</w:p>"
        "</w:tc>"
    )


def _docx_width_value(width: float) -> int:
    return max(720, int(round(width * 20)))


def _docx_paragraph_xml(text: str, *, style_id: str) -> str:
    safe_text = escape(text)
    return (
        "<w:p>"
        f'<w:pPr><w:pStyle w:val="{style_id}"/></w:pPr>'
        "<w:r>"
        '<w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="微软雅黑"/></w:rPr>'
        f'<w:t xml:space="preserve">{safe_text}</w:t>'
        "</w:r>"
        "</w:p>"
    )


def _docx_style_id(style: str) -> str:
    return {
        "title": "Title",
        "meta": "Subtitle",
        "heading": "Heading1",
        "bullet": "ListParagraph",
        "signature": "Normal",
    }.get(style, "Normal")


def _build_docx_content_types_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""


def _build_docx_root_rels_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""


def _build_docx_document_rels_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>"""


def _build_docx_core_xml(report_data: dict[str, object]) -> str:
    title = escape(str(report_data.get("reportTitle") or "志愿规划报告"))
    created = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties
    xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:dcterms="http://purl.org/dc/terms/"
    xmlns:dcmitype="http://purl.org/dc/dcmitype/"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>{title}</dc:title>
  <dc:creator>Gaokao Planning System</dc:creator>
  <cp:lastModifiedBy>Gaokao Planning System</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{created}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{created}</dcterms:modified>
</cp:coreProperties>"""


def _build_docx_app_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
    xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Gaokao Planning System</Application>
</Properties>"""


def _build_docx_styles_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:docDefaults>
    <w:rPrDefault>
      <w:rPr>
        <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="微软雅黑"/>
        <w:sz w:val="22"/>
        <w:szCs w:val="22"/>
      </w:rPr>
    </w:rPrDefault>
  </w:docDefaults>
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:qFormat/>
    <w:pPr><w:spacing w:after="140" w:line="360" w:lineRule="auto"/></w:pPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Title">
    <w:name w:val="Title"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:pPr><w:spacing w:after="220"/></w:pPr>
    <w:rPr>
      <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="微软雅黑"/>
      <w:b/>
      <w:sz w:val="34"/>
      <w:color w:val="123A8F"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Subtitle">
    <w:name w:val="Subtitle"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:rPr>
      <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="微软雅黑"/>
      <w:sz w:val="20"/>
      <w:color w:val="5B6475"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="Heading 1"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:pPr><w:spacing w:before="180" w:after="120"/></w:pPr>
    <w:rPr>
      <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="微软雅黑"/>
      <w:b/>
      <w:sz w:val="28"/>
      <w:color w:val="1D4ED8"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="ListParagraph">
    <w:name w:val="List Paragraph"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:pPr>
      <w:ind w:left="360" w:hanging="180"/>
      <w:spacing w:after="120" w:line="360" w:lineRule="auto"/>
    </w:pPr>
  </w:style>
</w:styles>"""


def _build_pdf_page_streams(blocks: list[ReportBlock]) -> list[str]:
    styles = {
        "title": {"size": 20.0, "line_height": 30.0, "before": 0.0, "after": 8.0, "indent": 0.0, "color": "0.07 0.23 0.56 rg"},
        "meta": {"size": 10.5, "line_height": 16.0, "before": 0.0, "after": 3.0, "indent": 0.0, "color": "0.36 0.39 0.46 rg"},
        "heading": {"size": 14.0, "line_height": 22.0, "before": 10.0, "after": 4.0, "indent": 0.0, "color": "0.11 0.31 0.85 rg"},
        "body": {"size": 11.0, "line_height": 18.5, "before": 0.0, "after": 6.0, "indent": 0.0, "color": "0 0 0 rg"},
        "bullet": {"size": 11.0, "line_height": 18.5, "before": 0.0, "after": 4.0, "indent": 12.0, "color": "0 0 0 rg"},
        "signature": {"size": 11.0, "line_height": 18.5, "before": 0.0, "after": 4.0, "indent": 0.0, "color": "0 0 0 rg"},
    }

    usable_width = PDF_PAGE_WIDTH - PDF_MARGIN_LEFT - PDF_MARGIN_RIGHT
    page_streams: list[str] = []
    current_commands: list[str] = []
    y = PDF_PAGE_HEIGHT - PDF_MARGIN_TOP

    def flush_page() -> None:
        nonlocal current_commands, y
        page_streams.append("\n".join(current_commands))
        current_commands = []
        y = PDF_PAGE_HEIGHT - PDF_MARGIN_TOP

    for block in blocks:
        if block.table_rows:
            y = _append_pdf_table(
                block,
                get_commands=lambda: current_commands,
                current_y=y,
                flush_page=flush_page,
            )
            continue
        spec = styles.get(block.style, styles["body"])
        y -= spec["before"]
        max_units = max(12.0, (usable_width - spec["indent"]) / spec["size"])
        lines = _wrap_text(block.text, max_units=max_units)
        if not lines:
            lines = [""]
        for line in lines:
            if not line:
                y -= spec["line_height"] * 0.8
                continue
            if y - spec["line_height"] < PDF_MARGIN_BOTTOM:
                flush_page()
            current_commands.append(
                _pdf_text_command(
                    text=line,
                    x=PDF_MARGIN_LEFT + spec["indent"],
                    y=y,
                    font_size=spec["size"],
                    color_command=spec["color"],
                )
            )
            y -= spec["line_height"]
        y -= spec["after"]

    if current_commands or not page_streams:
        flush_page()
    return page_streams


def _append_pdf_table(
    block: ReportBlock,
    *,
    get_commands,
    current_y: float,
    flush_page,
) -> float:
    headers = list(block.table_headers)
    rows = [list(row) for row in block.table_rows]
    widths = list(block.table_column_widths) if block.table_column_widths else []
    if not headers or not rows:
        return current_y
    if not widths:
        usable_width = PDF_PAGE_WIDTH - PDF_MARGIN_LEFT - PDF_MARGIN_RIGHT
        widths = [usable_width / len(headers)] * len(headers)

    padding_x = 5.0
    padding_y = 4.0
    header_font_size = 9.0
    row_font_size = 8.8
    line_height = 11.5
    y = current_y - 4.0

    def wrap_cells(cells: list[str], *, font_size: float) -> list[list[str]]:
        wrapped: list[list[str]] = []
        for index, cell in enumerate(cells):
            width = widths[index]
            max_units = max(4.0, (width - padding_x * 2) / max(font_size, 1.0))
            lines = _wrap_text(cell or "-", max_units=max_units)
            wrapped.append(lines or ["-"])
        return wrapped

    def draw_row(
        cells: list[str],
        *,
        top_y: float,
        font_size: float,
        fill_rgb: str,
        text_color: str,
        is_header: bool,
    ) -> float:
        wrapped_cells = wrap_cells(cells, font_size=font_size)
        max_lines = max(len(lines) for lines in wrapped_cells)
        row_height = padding_y * 2 + max_lines * line_height
        bottom_y = top_y - row_height
        x = PDF_MARGIN_LEFT
        border_rgb = "0.78 0.84 0.92 RG"

        for index, width in enumerate(widths):
            get_commands().append(
                f"q {fill_rgb} {border_rgb} {x:.2f} {bottom_y:.2f} {width:.2f} {row_height:.2f} re B Q"
            )
            text_y = top_y - padding_y - font_size
            for line in wrapped_cells[index]:
                get_commands().append(
                    _pdf_text_command(
                        text=line,
                        x=x + padding_x,
                        y=text_y,
                        font_size=font_size,
                        color_command=text_color,
                    )
                )
                text_y -= line_height
            x += width
        return bottom_y

    wrapped_headers = wrap_cells(headers, font_size=header_font_size)
    header_height = padding_y * 2 + max(len(lines) for lines in wrapped_headers) * line_height
    if y - header_height < PDF_MARGIN_BOTTOM:
        flush_page()
        y = PDF_PAGE_HEIGHT - PDF_MARGIN_TOP
    y = draw_row(
        headers,
        top_y=y,
        font_size=header_font_size,
        fill_rgb="0.91 0.95 1 rg",
        text_color="0.07 0.23 0.56 rg",
        is_header=True,
    )

    for row_index, row in enumerate(rows):
        wrapped_cells = wrap_cells(row, font_size=row_font_size)
        row_height = padding_y * 2 + max(len(lines) for lines in wrapped_cells) * line_height
        if y - row_height < PDF_MARGIN_BOTTOM:
            flush_page()
            y = PDF_PAGE_HEIGHT - PDF_MARGIN_TOP
            y = draw_row(
                headers,
                top_y=y,
                font_size=header_font_size,
                fill_rgb="0.91 0.95 1 rg",
                text_color="0.07 0.23 0.56 rg",
                is_header=True,
            )
        fill_rgb = "0.985 0.99 1 rg" if row_index % 2 == 0 else "1 1 1 rg"
        y = draw_row(
            row,
            top_y=y,
            font_size=row_font_size,
            fill_rgb=fill_rgb,
            text_color="0 0 0 rg",
            is_header=False,
        )

    return y - 8.0


def _build_pdf_bytes(page_streams: list[str]) -> bytes:
    objects: dict[int, bytes] = {}
    catalog_id = 1
    pages_id = 2
    type0_font_id = 3
    cid_font_id = 4
    font_descriptor_id = 5
    next_id = 6
    page_ids: list[int] = []

    for stream in page_streams:
        content_bytes = zlib.compress(stream.encode("ascii"))
        content_id = next_id
        next_id += 1
        page_id = next_id
        next_id += 1
        objects[content_id] = (
            f"<< /Length {len(content_bytes)} /Filter /FlateDecode >>\nstream\n".encode("ascii")
            + content_bytes
            + b"\nendstream"
        )
        objects[page_id] = (
            f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {PDF_PAGE_WIDTH:.2f} {PDF_PAGE_HEIGHT:.2f}] "
            f"/Resources << /ProcSet [/PDF /Text] /Font << /F1 {type0_font_id} 0 R >> >> /Contents {content_id} 0 R >>"
        ).encode("ascii")
        page_ids.append(page_id)

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[pages_id] = f"<< /Type /Pages /Count {len(page_ids)} /Kids [{kids}] >>".encode("ascii")
    objects[catalog_id] = f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode("ascii")
    objects[type0_font_id] = (
        f"<< /Type /Font /Subtype /Type0 /BaseFont /STSong-Light /Encoding /UniGB-UCS2-H "
        f"/DescendantFonts [{cid_font_id} 0 R] >>"
    ).encode("ascii")
    objects[cid_font_id] = (
        f"<< /Type /Font /Subtype /CIDFontType0 /BaseFont /STSong-Light /CIDSystemInfo "
        f"<< /Registry (Adobe) /Ordering (GB1) /Supplement 4 >> /FontDescriptor {font_descriptor_id} 0 R /DW 1000 >>"
    ).encode("ascii")
    objects[font_descriptor_id] = (
        b"<< /Type /FontDescriptor /FontName /STSong-Light /Flags 4 /ItalicAngle 0 "
        b"/Ascent 880 /Descent -120 /CapHeight 700 /StemV 80 >>"
    )

    max_object_id = max(objects)
    buffer = io.BytesIO()
    buffer.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0] * (max_object_id + 1)

    for object_id in range(1, max_object_id + 1):
        offsets[object_id] = buffer.tell()
        buffer.write(f"{object_id} 0 obj\n".encode("ascii"))
        buffer.write(objects[object_id])
        buffer.write(b"\nendobj\n")

    xref_offset = buffer.tell()
    buffer.write(f"xref\n0 {max_object_id + 1}\n".encode("ascii"))
    buffer.write(b"0000000000 65535 f \n")
    for object_id in range(1, max_object_id + 1):
        buffer.write(f"{offsets[object_id]:010d} 00000 n \n".encode("ascii"))

    buffer.write(
        f"trailer\n<< /Size {max_object_id + 1} /Root {catalog_id} 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode(
            "ascii"
        )
    )
    return buffer.getvalue()


def _pdf_text_command(text: str, *, x: float, y: float, font_size: float, color_command: str) -> str:
    hex_text = text.encode("utf-16-be").hex().upper()
    return (
        "BT\n"
        f"/F1 {font_size:.2f} Tf\n"
        f"{color_command}\n"
        f"1 0 0 1 {x:.2f} {y:.2f} Tm\n"
        f"<{hex_text}> Tj\n"
        "ET"
    )


def _split_block_lines(text: str) -> list[str]:
    return [line.strip() for line in str(text).replace("\r\n", "\n").split("\n")]


def _wrap_text(text: str, *, max_units: float) -> list[str]:
    wrapped: list[str] = []
    for raw_line in str(text).replace("\r\n", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            wrapped.append("")
            continue

        current = ""
        current_units = 0.0
        for char in line:
            if not current and char.isspace():
                continue
            char_units = _char_display_units(char)
            if current and current_units + char_units > max_units:
                wrapped.append(current.rstrip())
                if char.isspace():
                    current = ""
                    current_units = 0.0
                else:
                    current = char
                    current_units = char_units
                continue
            current += char
            current_units += char_units
        if current:
            wrapped.append(current.rstrip())
    return wrapped


def _char_display_units(char: str) -> float:
    if char.isspace():
        return 0.45
    if ord(char) < 128:
        if char in "MW@#%&":
            return 0.95
        if char in "il.,:;!'|":
            return 0.35
        return 0.58
    return 1.0
