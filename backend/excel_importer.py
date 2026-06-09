from __future__ import annotations

import csv
import json
import re
from pathlib import Path, PurePosixPath
from zipfile import ZipFile
from xml.etree import ElementTree as ET


XML_NAMESPACES = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "pkgrel": "http://schemas.openxmlformats.org/package/2006/relationships",
}

FOCUS_SHEETS = {
    "专业大类库": "major_categories",
    "城市产业库": "city_industries",
    "样例学生数据": "sample_students",
    "报告模板字段": "report_template_fields",
}


def _column_to_index(column_name: str) -> int:
    value = 0
    for char in column_name:
        if char.isalpha():
            value = value * 26 + (ord(char.upper()) - 64)
    return value - 1


def _normalize_headers(headers: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: dict[str, int] = {}
    for index, header in enumerate(headers):
        base = (header or "").strip() or f"column_{index + 1}"
        count = seen.get(base, 0)
        seen[base] = count + 1
        normalized.append(base if count == 0 else f"{base}_{count + 1}")
    return normalized


def _read_sheet_rows(zip_file: ZipFile, target: str, shared_strings: list[str]) -> list[list[str]]:
    root = ET.fromstring(zip_file.read(target))
    rows: list[list[str]] = []

    for row in root.findall(".//main:sheetData/main:row", XML_NAMESPACES):
        values: dict[int, str] = {}
        for cell in row.findall("main:c", XML_NAMESPACES):
            reference = cell.attrib.get("r", "")
            match = re.match(r"([A-Z]+)", reference)
            cell_index = _column_to_index(match.group(1)) if match else len(values)
            cell_type = cell.attrib.get("t")
            value = ""

            if cell_type == "s":
                raw_value = cell.find("main:v", XML_NAMESPACES)
                if raw_value is not None and raw_value.text is not None:
                    value = shared_strings[int(raw_value.text)]
            elif cell_type == "inlineStr":
                inline_string = cell.find("main:is", XML_NAMESPACES)
                if inline_string is not None:
                    value = "".join(
                        node.text or ""
                        for node in inline_string.iterfind(".//main:t", XML_NAMESPACES)
                    )
            else:
                raw_value = cell.find("main:v", XML_NAMESPACES)
                if raw_value is not None and raw_value.text is not None:
                    value = raw_value.text

            values[cell_index] = value.strip() if isinstance(value, str) else value

        if values:
            max_index = max(values)
            rows.append([values.get(idx, "") for idx in range(max_index + 1)])

    return rows


def load_workbook(path: Path) -> dict[str, object]:
    with ZipFile(path) as zip_file:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in zip_file.namelist():
            shared_root = ET.fromstring(zip_file.read("xl/sharedStrings.xml"))
            for node in shared_root.findall("main:si", XML_NAMESPACES):
                shared_strings.append(
                    "".join(
                        part.text or ""
                        for part in node.iterfind(".//main:t", XML_NAMESPACES)
                    )
                )

        workbook_root = ET.fromstring(zip_file.read("xl/workbook.xml"))
        relation_root = ET.fromstring(zip_file.read("xl/_rels/workbook.xml.rels"))
        relation_map = {
            node.attrib["Id"]: node.attrib["Target"]
            for node in relation_root.findall("pkgrel:Relationship", XML_NAMESPACES)
        }

        sheets: list[dict[str, object]] = []
        for sheet in workbook_root.findall("main:sheets/main:sheet", XML_NAMESPACES):
            relation_id = sheet.attrib[
                "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
            ]
            target = relation_map[relation_id].lstrip("/")
            if not target.startswith("xl/"):
                target = str(PurePosixPath("xl") / PurePosixPath(target))

            raw_rows = _read_sheet_rows(zip_file, target, shared_strings)
            raw_headers = raw_rows[0] if raw_rows else []
            headers = _normalize_headers(raw_headers)
            records: list[dict[str, str]] = []

            for row in raw_rows[1:]:
                padded_row = row + [""] * max(0, len(headers) - len(row))
                records.append(dict(zip(headers, padded_row[: len(headers)])))

            sheets.append(
                {
                    "sheet_name": sheet.attrib["name"],
                    "headers": headers,
                    "data_row_count": len(records),
                    "sample_rows": records[:3],
                    "records": records,
                }
            )

    return {
        "workbook_name": path.name,
        "sheets": sheets,
    }


def extract_focus_datasets(workbook_data: dict[str, object]) -> dict[str, list[dict[str, str]]]:
    datasets: dict[str, list[dict[str, str]]] = {}
    for sheet in workbook_data["sheets"]:
        sheet_name = sheet["sheet_name"]
        if sheet_name in FOCUS_SHEETS:
            datasets[FOCUS_SHEETS[sheet_name]] = sheet["records"]
    return datasets


def build_sheet_overview(workbook_data: dict[str, object]) -> dict[str, object]:
    return {
        "workbook_name": workbook_data["workbook_name"],
        "sheets": [
            {
                "sheet_name": sheet["sheet_name"],
                "headers": sheet["headers"],
                "data_row_count": sheet["data_row_count"],
                "sample_rows": sheet["sample_rows"],
            }
            for sheet in workbook_data["sheets"]
        ],
    }


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        if headers:
            writer.writeheader()
            writer.writerows(rows)

