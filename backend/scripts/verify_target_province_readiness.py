from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from backend.province_readiness import build_province_readiness_summary


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_JSON_OUTPUT = PROJECT_ROOT / "data_assets" / "imported" / "province_readiness_summary.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify whether target provinces already have the same admissions-data readiness level as Henan."
    )
    parser.add_argument("--as-of-date", required=True, help="Verification date in YYYY-MM-DD format.")
    parser.add_argument("--write-json", type=str, default=str(DEFAULT_JSON_OUTPUT), help="Optional JSON output path.")
    parser.add_argument("--write-markdown", type=str, default=None, help="Optional Markdown report output path.")
    return parser.parse_args()


def _render_markdown(summary: dict[str, object]) -> str:
    provinces = summary["provinces"]
    formal_provinces = summary["formalProvinces"]
    lines = [
        "# 目标省份真实招生数据覆盖核验",
        "",
        f"核验日期：`{summary['asOfDate']}`",
        "",
        "## 核验口径",
        "",
        "- 本次核验依据仓库内的 `data_assets/imported` 导入产物、`backend/scripts/import_*.py` 导入脚本、`data_assets/data-needed-standardized` 标准化源目录，以及项目根目录原始资料包目录。",
        "- 本次结论用于判断“是否达到与河南同等级别的真实招生数据链路”，不是当前运行时 PostgreSQL 分省行数的直接替代。",
        "- 当前判定一省达到河南同等级别的最低条件：已具备招生计划、院校录取线、院校规则、专业录取线、政策规则、批次线、一分一段、选科要求这 8 类导入产物，并且仓库中存在对应省份的专项导入脚本痕迹。",
        "",
        "## 结论",
        "",
        f"- 当前达到河南同等级别正式链路的省份：{(' / '.join(formal_provinces)) if formal_provinces else '无'}。",
        "- 浙江、河北、山东、江苏、安徽、广东、四川虽然在标准化目录中已有不同程度的原始/整理素材，但当前都还没有形成与河南对等的导入产物闭环，也没有完成同等级别的推荐/报告链路验收。",
        "",
        "## 核验矩阵",
        "",
        "| 省份 | 状态 | 导入产物 | 专项导入脚本 | 标准化目录命中 | 原始资料根目录 |",
        "| --- | --- | ---: | ---: | --- | --- |",
    ]

    for item in provinces:
        status_label = {
            "formal": "正式同级",
            "raw_only": "仅素材待接入",
            "not_ready": "未形成链路",
        }.get(str(item["status"]), str(item["status"]))
        standardized_domains = (
            " / ".join(item["standardizedDomainLabels"]) if item["standardizedDomainLabels"] else "-"
        )
        raw_roots = " / ".join(item["rawRoots"]) if item["rawRoots"] else "-"
        lines.append(
            f"| {item['province']} | {status_label} | {len(item['importedScopes'])} | {len(item['explicitImportScripts'])} | {standardized_domains} | {raw_roots} |"
        )

    lines.extend(
        [
            "",
            "## 分省说明",
            "",
        ]
    )

    for item in provinces:
        lines.append(f"### {item['province']}")
        lines.append("")
        lines.append(f"- 状态：`{item['status']}`")
        lines.append(f"- 说明：{item['description']}")
        lines.append(
            f"- 导入产物：{', '.join(item['importedScopes']) if item['importedScopes'] else '无'}"
        )
        lines.append(
            f"- 专项导入脚本：{', '.join(item['explicitImportScripts']) if item['explicitImportScripts'] else '无'}"
        )
        lines.append(
            f"- 标准化目录命中：{', '.join(item['standardizedDomainLabels']) if item['standardizedDomainLabels'] else '无'}"
        )
        lines.append(
            f"- 缺失的正式导入范围：{', '.join(item['missingRequiredImportedScopeLabels']) if item['missingRequiredImportedScopeLabels'] else '无'}"
        )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _write_json(path: Path, summary: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_markdown(path: Path, summary: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_markdown(summary), encoding="utf-8")


def main() -> None:
    args = parse_args()
    summary = build_province_readiness_summary(as_of_date=args.as_of_date)
    json_output = Path(args.write_json).expanduser()
    if not json_output.is_absolute():
        json_output = (PROJECT_ROOT / json_output).resolve()
    _write_json(json_output, summary)

    if args.write_markdown:
        markdown_output = Path(args.write_markdown).expanduser()
        if not markdown_output.is_absolute():
            markdown_output = (PROJECT_ROOT / markdown_output).resolve()
        _write_markdown(markdown_output, summary)

    print("=== TARGET PROVINCE READINESS SUMMARY ===")
    print(f"as_of_date: {summary['asOfDate']}")
    print(f"formal_provinces: {', '.join(summary['formalProvinces']) if summary['formalProvinces'] else 'none'}")
    for item in summary["provinces"]:
        print(
            f"{item['province']}: status={item['status']}, "
            f"imported_scopes={len(item['importedScopes'])}, "
            f"explicit_import_scripts={len(item['explicitImportScripts'])}, "
            f"standardized_domains={len(item['standardizedDomains'])}"
        )


if __name__ == "__main__":
    main()
