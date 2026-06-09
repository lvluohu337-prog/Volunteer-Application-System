from __future__ import annotations

import hashlib
import re
from pathlib import Path, PurePosixPath
from zipfile import ZipFile
from xml.etree import ElementTree as ET


XML_NAMESPACES = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "pkgrel": "http://schemas.openxmlformats.org/package/2006/relationships",
}

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HENAN_DATA_ROOT = PROJECT_ROOT / "河南-2026志愿填报资料"

HENAN_DATASET_PATTERNS = {
    "master_admission_plans": ["22-25年全国高校在河南的招生计划.xlsx"],
    "master_institution_scores": ["22-25年全国高校在河南的院校录取分数.xlsx"],
    "master_major_scores": ["22-25年全国高校在河南的专业录取分数.xlsx"],
    "master_score_segments_2025": ["河南2025年的一分一段表.xlsx"],
    "history_admission_plans_2024": ["河南_招生计划_2024.xlsx"],
    "history_institution_scores_2024": ["河南_投档线_2024.xlsx"],
    "history_major_scores_2024": ["河南_专业分数线_2024.xlsx"],
}

HENAN_IMPORT_TARGETS = {
    "institutions": "institutions",
    "majors": "majors",
    "subject_requirements": "subject_requirements",
    "admission_plans": "admission_plans",
    "institution_admission_scores": "institution_admission_scores",
    "major_admission_scores": "major_admission_scores",
    "score_segments": "score_segments",
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


def _normalize_text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_int(value) -> int | None:
    text = _normalize_text(value)
    if not text:
        return None
    match = re.search(r"-?\d+", text.replace(",", ""))
    if not match:
        return None
    return int(match.group(0))


def _parse_float(value) -> float | None:
    text = _normalize_text(value)
    if not text:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", text.replace(",", ""))
    if not match:
        return None
    return float(match.group(0))


def _clean_province(value) -> str | None:
    text = _normalize_text(value)
    if not text:
        return None
    return text.replace("H", "").strip()


def _normalize_subject_track(value) -> str | None:
    text = _normalize_text(value)
    if not text:
        return None
    return text.replace("文理科", "").replace("科目", "").strip()


def _normalize_batch(value) -> str | None:
    return _normalize_text(value)


def _shared_strings(zip_file: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zip_file.namelist():
        return []
    shared_root = ET.fromstring(zip_file.read("xl/sharedStrings.xml"))
    values = []
    for node in shared_root.findall("main:si", XML_NAMESPACES):
        values.append("".join(part.text or "" for part in node.iterfind(".//main:t", XML_NAMESPACES)))
    return values


def _sheet_targets(zip_file: ZipFile) -> list[tuple[str, str]]:
    workbook_root = ET.fromstring(zip_file.read("xl/workbook.xml"))
    relation_root = ET.fromstring(zip_file.read("xl/_rels/workbook.xml.rels"))
    relation_map = {
        node.attrib["Id"]: node.attrib["Target"]
        for node in relation_root.findall("pkgrel:Relationship", XML_NAMESPACES)
    }

    result = []
    for sheet in workbook_root.findall("main:sheets/main:sheet", XML_NAMESPACES):
        relation_id = sheet.attrib[
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        ]
        target = relation_map[relation_id].lstrip("/")
        if not target.startswith("xl/"):
            target = str(PurePosixPath("xl") / PurePosixPath(target))
        result.append((sheet.attrib["name"], target))
    return result


def iter_sheet_records(path: Path, sheet_name: str | None = None, limit: int | None = None):
    with ZipFile(path) as zip_file:
        shared_strings = _shared_strings(zip_file)
        sheet_map = _sheet_targets(zip_file)
        if not sheet_map:
            return
        target_name, target_path = sheet_map[0]
        if sheet_name:
            for name, path_value in sheet_map:
                if name == sheet_name:
                    target_name, target_path = name, path_value
                    break

        rows = []
        root = ET.fromstring(zip_file.read(target_path))
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
                values[cell_index] = value.strip()

            if values:
                max_index = max(values)
                rows.append([values.get(idx, "") for idx in range(max_index + 1)])
                if limit and len(rows) >= limit + 1:
                    break

        headers = _normalize_headers(rows[0] if rows else [])
        for row in rows[1:]:
            padded = row + [""] * max(0, len(headers) - len(row))
            yield target_name, dict(zip(headers, padded[: len(headers)]))


def build_sheet_sample(path: Path, sample_rows: int = 3) -> dict[str, object]:
    rows = list(iter_sheet_records(path, limit=sample_rows))
    sheet_name = rows[0][0] if rows else "Sheet1"
    sample = [row for _, row in rows[:sample_rows]]
    headers = list(sample[0].keys()) if sample else []
    return {
        "file_name": path.name,
        "sheet_name": sheet_name,
        "headers": headers,
        "sample_rows": sample,
        "sample_count": len(sample),
    }


def locate_henan_dataset_files() -> dict[str, Path]:
    located: dict[str, Path] = {}
    if not HENAN_DATA_ROOT.exists():
        return located

    for dataset_key, candidates in HENAN_DATASET_PATTERNS.items():
        for candidate_name in candidates:
            match = next(HENAN_DATA_ROOT.rglob(candidate_name), None)
            if match:
                located[dataset_key] = match
                break

    return located


def _institution_row(code: str | None, name: str | None, province: str | None = None, city: str | None = None, public_private: str | None = None, level: str | None = None) -> dict[str, object]:
    return {
        "institution_code": code,
        "institution_name": name,
        "province": province,
        "city": city,
        "public_private": public_private,
        "institution_level": level,
    }


def _major_row(code: str | None, name: str | None, study_years: str | None = None, degree_level: str | None = None) -> dict[str, object]:
    return {
        "major_code": code,
        "major_name": name,
        "study_years": study_years,
        "degree_level": degree_level,
    }


def _degree_level_from_batch(batch_code: str | None) -> str | None:
    text = batch_code or ""
    if "本科" in text or "本一" in text or "本二" in text:
        return "本科"
    if "专科" in text:
        return "专科"
    return None


def _requirement_code(institution_code: str | None, major_code: str | None, group_code: str | None, requirement_text: str | None) -> str:
    if group_code:
        return group_code
    if major_code:
        return f"major-{major_code}"
    text = requirement_text or "unknown"
    digest = hashlib.md5(f"{institution_code or 'na'}|{group_code or ''}|{text}".encode("utf-8")).hexdigest()[:12]
    return f"req-{institution_code or 'na'}-{digest}"


def load_henan_normalized_datasets(limit_per_file: int | None = None) -> dict[str, list[dict[str, object]]]:
    files = locate_henan_dataset_files()
    institutions: dict[tuple[str | None, str | None], dict[str, object]] = {}
    majors: dict[tuple[str | None, str | None], dict[str, object]] = {}
    subject_requirements: dict[tuple[object, ...], dict[str, object]] = {}
    admission_plans: list[dict[str, object]] = []
    institution_scores: list[dict[str, object]] = []
    major_scores: list[dict[str, object]] = []
    score_segments: list[dict[str, object]] = []

    master_plans = files.get("master_admission_plans")
    if master_plans:
        for _, row in iter_sheet_records(master_plans, limit=limit_per_file):
            year = _parse_int(row.get("年份"))
            code = _normalize_text(row.get("院校代码"))
            name = _normalize_text(row.get("院校名称"))
            major_code = _normalize_text(row.get("专业代码"))
            major_name = _normalize_text(row.get("专业名称"))
            province = "河南"
            subject_track = _normalize_subject_track(row.get("科类"))
            batch_code = _normalize_batch(row.get("批次"))
            group_code = _normalize_text(row.get("所属专业组"))
            requirement_text = _normalize_text(row.get("选科要求"))
            requirement_code = _requirement_code(code, major_code, group_code, requirement_text)

            institutions[(code, name)] = _institution_row(code, name)
            majors[(major_code, major_name)] = _major_row(
                major_code,
                major_name,
                study_years=_normalize_text(row.get("学制(年)")),
                degree_level=_degree_level_from_batch(batch_code),
            )

            if requirement_text:
                subject_requirements[(year, province, code, major_code, requirement_code)] = {
                    "exam_year": year,
                    "province": province,
                    "subject_track": subject_track,
                    "institution_code": code,
                    "institution_name": name,
                    "major_code": major_code,
                    "major_name": major_name,
                    "requirement_code": requirement_code,
                    "requirement_text": requirement_text,
                    "required_subjects": requirement_text,
                    "match_mode": "text_rule",
                    "notes": _normalize_text(row.get("专业备注")),
                }

            admission_plans.append(
                {
                    "exam_year": year,
                    "province": province,
                    "exam_type": "gaokao",
                    "subject_track": subject_track,
                    "batch_code": batch_code,
                    "institution_code": code,
                    "institution_name": name,
                    "major_code": major_code,
                    "major_name": major_name,
                    "plan_group_code": group_code,
                    "plan_group_name": group_code,
                    "requirement_code": requirement_code,
                    "planned_count": _parse_int(row.get("招生人数")),
                    "tuition_yearly": _parse_float(row.get("学费(元)")),
                    "study_years": _normalize_text(row.get("学制(年)")),
                    "campus_city": None,
                    "plan_notes": _normalize_text(row.get("专业备注")) or _normalize_text(row.get("招生类型")),
                }
            )

    master_institution_scores = files.get("master_institution_scores")
    if master_institution_scores:
        for _, row in iter_sheet_records(master_institution_scores, limit=limit_per_file):
            year = _parse_int(row.get("年份"))
            code = _normalize_text(row.get("院校代码"))
            name = _normalize_text(row.get("院校名称"))
            province = "河南"
            subject_track = _normalize_subject_track(row.get("科类"))
            batch_code = _normalize_batch(row.get("批次"))
            requirement_text = _normalize_text(row.get("选科要求"))
            group_code = _normalize_text(row.get("专业组"))

            institutions[(code, name)] = _institution_row(
                code,
                name,
                province=_clean_province(row.get("学校所在")),
                public_private=_normalize_text(row.get("学校性质")),
            )
            if requirement_text:
                subject_requirements[(year, province, code, None, _requirement_code(code, None, group_code, requirement_text))] = {
                    "exam_year": year,
                    "province": province,
                    "subject_track": subject_track,
                    "institution_code": code,
                    "institution_name": name,
                    "major_code": None,
                    "major_name": None,
                    "requirement_code": _requirement_code(code, None, group_code, requirement_text),
                    "requirement_text": requirement_text,
                    "required_subjects": requirement_text,
                    "match_mode": "text_rule",
                    "notes": _normalize_text(row.get("招生类型")),
                }

            institution_scores.append(
                {
                    "exam_year": year,
                    "province": province,
                    "exam_type": "gaokao",
                    "subject_track": subject_track,
                    "batch_code": batch_code,
                    "institution_code": code,
                    "institution_name": name,
                    "min_score": _parse_float(row.get("最低分数")),
                    "min_rank": _parse_int(row.get("最低分位")),
                    "avg_score": None,
                    "avg_rank": None,
                    "max_score": None,
                    "max_rank": None,
                    "planned_count": None,
                    "admitted_count": _parse_int(row.get("录取人数")),
                    "score_line": None,
                    "notes": _normalize_text(row.get("招生类型")) or _normalize_text(row.get("专业组")),
                }
            )

    master_major_scores = files.get("master_major_scores")
    if master_major_scores:
        for _, row in iter_sheet_records(master_major_scores, limit=limit_per_file):
            year = _parse_int(row.get("年份"))
            code = _normalize_text(row.get("院校代码"))
            name = _normalize_text(row.get("院校名称"))
            major_code = _normalize_text(row.get("专业代码"))
            major_name = _normalize_text(row.get("专业"))
            province = "河南"
            subject_track = _normalize_subject_track(row.get("科类"))
            batch_code = _normalize_batch(row.get("批次"))
            group_code = _normalize_text(row.get("所属专业组"))
            requirement_text = _normalize_text(row.get("选科要求"))
            requirement_code = _requirement_code(code, major_code, group_code, requirement_text)

            institutions[(code, name)] = _institution_row(code, name, province=_clean_province(row.get("学校所在")))
            majors[(major_code, major_name)] = _major_row(major_code, major_name, degree_level=_degree_level_from_batch(batch_code))

            if requirement_text:
                subject_requirements[(year, province, code, major_code, requirement_code)] = {
                    "exam_year": year,
                    "province": province,
                    "subject_track": subject_track,
                    "institution_code": code,
                    "institution_name": name,
                    "major_code": major_code,
                    "major_name": major_name,
                    "requirement_code": requirement_code,
                    "requirement_text": requirement_text,
                    "required_subjects": requirement_text,
                    "match_mode": "text_rule",
                    "notes": _normalize_text(row.get("专业备注")),
                }

            major_scores.append(
                {
                    "exam_year": year,
                    "province": province,
                    "exam_type": "gaokao",
                    "subject_track": subject_track,
                    "batch_code": batch_code,
                    "institution_code": code,
                    "institution_name": name,
                    "major_code": major_code,
                    "major_name": major_name,
                    "plan_group_code": group_code,
                    "min_score": _parse_float(row.get("最低分数")),
                    "min_rank": _parse_int(row.get("最低位次")),
                    "avg_score": None,
                    "avg_rank": None,
                    "max_score": None,
                    "max_rank": None,
                    "planned_count": None,
                    "admitted_count": _parse_int(row.get("录取人数")),
                    "notes": _normalize_text(row.get("专业备注")),
                }
            )

    score_segments_path = files.get("master_score_segments_2025")
    if score_segments_path:
        for _, row in iter_sheet_records(score_segments_path, limit=limit_per_file):
            score_text = _normalize_text(row.get("分数(分)"))
            if not score_text:
                continue
            score_segments.append(
                {
                    "exam_year": _parse_int(row.get("年份")),
                    "province": "河南",
                    "exam_type": "gaokao",
                    "subject_track": _normalize_subject_track(row.get("科类")),
                    "batch_code": _normalize_batch(row.get("批次")),
                    "control_line": _parse_float(row.get("控制线(分)")),
                    "score_text": score_text,
                    "score_value": _parse_float(score_text),
                    "segment_count": _parse_int(row.get("本段人数(人)")),
                    "cumulative_count": _parse_int(row.get("累计人数(人)")),
                    "rank_range": _normalize_text(row.get("排名区间")),
                    "historical_same_rank_score": _normalize_text(row.get("历史同位次考生得分")),
                }
            )

    history_plan_path = files.get("history_admission_plans_2024")
    if history_plan_path:
        for _, row in iter_sheet_records(history_plan_path, limit=limit_per_file):
            code = _normalize_text(row.get("招生代码"))
            name = _normalize_text(row.get("学校"))
            major_code = _normalize_text(row.get("专业代码"))
            major_name = _normalize_text(row.get("专业"))
            province = _clean_province(row.get("省份")) or "河南"
            batch_code = _normalize_batch(row.get("批次"))
            institutions[(code, name)] = _institution_row(code, name, province=province)
            majors[(major_code, major_name)] = _major_row(
                major_code,
                major_name,
                study_years=_normalize_text(row.get("学制")),
                degree_level=_degree_level_from_batch(batch_code),
            )

    history_institution_path = files.get("history_institution_scores_2024")
    if history_institution_path:
        for sheet_name, row in iter_sheet_records(history_institution_path, sheet_name="Sheet1", limit=limit_per_file):
            year = _parse_int(row.get("年份"))
            if not year:
                continue
            name = _normalize_text(row.get("学校"))
            code = None
            institutions[(code, name)] = _institution_row(
                code,
                name,
                province=_clean_province(row.get("省")),
                city=_normalize_text(row.get("城市")),
                public_private=_normalize_text(row.get("办学性质")),
                level=_normalize_text(row.get("是否双一流")),
            )

    history_major_path = files.get("history_major_scores_2024")
    if history_major_path:
        for _, row in iter_sheet_records(history_major_path, sheet_name="Sheet2", limit=limit_per_file):
            code = _normalize_text(row.get("院校代码"))
            name = _normalize_text(row.get("院校名称"))
            major_code = _normalize_text(row.get("专业代码"))
            major_name = _normalize_text(row.get("专业名称"))
            institutions[(code, name)] = _institution_row(code, name)
            majors[(major_code, major_name)] = _major_row(major_code, major_name)

    return {
        "institutions": list(institutions.values()),
        "majors": list(majors.values()),
        "subject_requirements": list(subject_requirements.values()),
        "admission_plans": admission_plans,
        "institution_admission_scores": institution_scores,
        "major_admission_scores": major_scores,
        "score_segments": score_segments,
    }


def build_henan_dataset_overview() -> dict[str, object]:
    files = locate_henan_dataset_files()
    return {
        "root": str(HENAN_DATA_ROOT),
        "found_files": {key: str(path) for key, path in files.items()},
        "samples": {
            key: build_sheet_sample(path)
            for key, path in files.items()
        },
    }
