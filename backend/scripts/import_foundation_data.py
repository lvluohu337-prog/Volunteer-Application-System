from __future__ import annotations

import argparse
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from backend.database import db_session, init_db
from backend.excel_importer import (
    FOCUS_SHEETS,
    build_sheet_overview,
    extract_focus_datasets,
    load_workbook,
    write_csv,
    write_json,
)
from backend.foundation_repository import (
    upsert_city_industries,
    upsert_major_categories,
    upsert_report_template_fields,
    upsert_sample_students,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data_assets" / "raw"
IMPORTED_DIR = PROJECT_ROOT / "data_assets" / "imported"
TEMPLATES_DIR = PROJECT_ROOT / "data_assets" / "templates"
ACTIVE_WORKBOOK_POINTER = RAW_DIR / "active_foundation_workbook.txt"
LEGACY_DEFAULT_WORKBOOK = RAW_DIR / "歪歪志愿馆_高考志愿系统_基础数据包.xlsx"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import the active foundation workbook into intermediate files and database tables."
    )
    parser.add_argument(
        "--workbook",
        type=str,
        default=None,
        help="Optional workbook path. If omitted, the script reads data_assets/raw/active_foundation_workbook.txt.",
    )
    return parser.parse_args()


def _resolve_workbook_from_pointer() -> Path:
    if not ACTIVE_WORKBOOK_POINTER.exists():
        if LEGACY_DEFAULT_WORKBOOK.exists():
            return LEGACY_DEFAULT_WORKBOOK.resolve()
        raise FileNotFoundError(
            "未找到当前基础导入文件指针。请创建 data_assets/raw/active_foundation_workbook.txt，"
            "或使用 --workbook 显式指定导入文件。"
        )

    pointer_text = ACTIVE_WORKBOOK_POINTER.read_text(encoding="utf-8").strip()
    if not pointer_text:
        raise ValueError("data_assets/raw/active_foundation_workbook.txt 不能为空。")

    workbook_path = Path(pointer_text)
    if not workbook_path.is_absolute():
        workbook_path = PROJECT_ROOT / workbook_path
    return workbook_path.resolve()


def _locate_workbook(workbook_arg: str | None = None) -> Path:
    workbook_path = Path(workbook_arg).expanduser() if workbook_arg else _resolve_workbook_from_pointer()
    if not workbook_path.is_absolute():
        workbook_path = (PROJECT_ROOT / workbook_path).resolve()
    if workbook_path.suffix.lower() != ".xlsx":
        raise ValueError(f"基础导入文件必须是 .xlsx：{workbook_path}")
    if not workbook_path.exists():
        raise FileNotFoundError(f"未找到基础导入文件：{workbook_path}")
    return workbook_path


def _print_sheet_summary(overview: dict[str, object]) -> None:
    print(f"Workbook: {overview['workbook_name']}")
    for sheet in overview["sheets"]:
        print(f"=== SHEET: {sheet['sheet_name']} ===")
        print(f"Fields: {', '.join(sheet['headers'])}")
        print(f"Data rows: {sheet['data_row_count']}")
        for index, sample in enumerate(sheet["sample_rows"], start=1):
            print(f"Sample {index}: {sample}")
        print()


def _save_intermediate_files(datasets: dict[str, list[dict[str, str]]]) -> None:
    for sheet_name, slug in FOCUS_SHEETS.items():
        rows = datasets.get(slug, [])
        write_json(IMPORTED_DIR / f"{slug}.json", rows)
        write_csv(IMPORTED_DIR / f"{slug}.csv", rows)
        if slug == "report_template_fields":
            write_json(TEMPLATES_DIR / "report_template_fields.json", rows)


def _count_table(table_name: str) -> int:
    with db_session() as connection:
        return connection.execute(f"SELECT COUNT(*) AS total FROM {table_name}").fetchone()["total"]


def main() -> None:
    args = parse_args()
    workbook_path = _locate_workbook(args.workbook)
    workbook_data = load_workbook(workbook_path)
    overview = build_sheet_overview(workbook_data)
    datasets = extract_focus_datasets(workbook_data)

    IMPORTED_DIR.mkdir(parents=True, exist_ok=True)
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

    write_json(IMPORTED_DIR / "excel_sheet_overview.json", overview)
    _save_intermediate_files(datasets)

    init_db()

    imported_counts = {
        "major_categories": upsert_major_categories(datasets.get("major_categories", [])),
        "city_industries": upsert_city_industries(datasets.get("city_industries", [])),
        "sample_students": upsert_sample_students(datasets.get("sample_students", [])),
        "report_template_fields": upsert_report_template_fields(datasets.get("report_template_fields", [])),
    }
    table_counts = {table_name: _count_table(table_name) for table_name in imported_counts}

    summary = {
        "workbook_name": workbook_path.name,
        "workbook_path": str(workbook_path),
        "imported_counts": imported_counts,
        "table_counts": table_counts,
    }
    write_json(IMPORTED_DIR / "import_summary.json", summary)

    _print_sheet_summary(overview)
    print("=== IMPORT COUNTS ===")
    for table_name, count in imported_counts.items():
        print(f"{table_name}: processed={count}, table_total={table_counts[table_name]}")


if __name__ == "__main__":
    main()
