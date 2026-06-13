from __future__ import annotations

from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
IMPORTED_ROOT = PROJECT_ROOT / "data_assets" / "imported"
SCRIPTS_ROOT = PROJECT_ROOT / "backend" / "scripts"
STANDARDIZED_ROOT = PROJECT_ROOT / "data_assets" / "data-needed-standardized"

TARGET_PROVINCE_ORDER = ("河南", "浙江", "河北", "山东", "江苏", "安徽", "广东", "四川")
PROVINCE_SLUGS = {
    "河南": "henan",
    "浙江": "zhejiang",
    "河北": "hebei",
    "山东": "shandong",
    "江苏": "jiangsu",
    "安徽": "anhui",
    "广东": "guangdong",
    "四川": "sichuan",
}

REQUIRED_IMPORTED_SCOPE_SUFFIXES = (
    "admission_plans",
    "institution_admission_scores",
    "institution_rules",
    "major_admission_scores",
    "policy_rules",
    "province_batches",
    "score_segments",
    "subject_requirements",
)
IMPORTED_SCOPE_LABELS = {
    "admission_plans": "招生计划",
    "institution_admission_scores": "院校录取线",
    "institution_rules": "院校规则",
    "major_admission_scores": "专业录取线",
    "policy_rules": "政策规则",
    "province_batches": "批次线",
    "score_segments": "一分一段",
    "subject_requirements": "选科要求",
}

STANDARDIZED_DOMAIN_ROOTS = {
    "batches_policies": STANDARDIZED_ROOT / "02_batches_policies",
    "score_segments": STANDARDIZED_ROOT / "03_score_segments",
    "admissions_scores": STANDARDIZED_ROOT / "04_admissions_scores",
    "admission_plans": STANDARDIZED_ROOT / "05_admission_plans",
    "policy_rules": STANDARDIZED_ROOT / "06_policy_rules",
}
DOMAIN_LABELS = {
    "batches_policies": "批次线/批次政策",
    "score_segments": "一分一段",
    "admissions_scores": "院校/专业录取线",
    "admission_plans": "招生计划",
    "policy_rules": "章程/政策规则",
}


def _sorted_unique(values: list[str]) -> list[str]:
    return sorted({value for value in values if value})


def _collect_imported_scopes_by_province() -> dict[str, list[str]]:
    scopes = {province: [] for province in TARGET_PROVINCE_ORDER}
    if not IMPORTED_ROOT.exists():
        return scopes

    for path in IMPORTED_ROOT.iterdir():
        if not path.is_dir():
            continue
        name = path.name.lower()
        for province, slug in PROVINCE_SLUGS.items():
            if name.startswith(f"{slug}_"):
                scopes[province].append(path.name)
                break
    return {province: sorted(values) for province, values in scopes.items()}


def _collect_explicit_import_scripts_by_province() -> dict[str, list[str]]:
    scripts = {province: [] for province in TARGET_PROVINCE_ORDER}
    if not SCRIPTS_ROOT.exists():
        return scripts

    for path in sorted(SCRIPTS_ROOT.glob("import_*.py")):
        text = path.read_text(encoding="utf-8")
        stem = path.stem.lower()
        for province, slug in PROVINCE_SLUGS.items():
            if province in text or slug in stem or slug in text.lower():
                scripts[province].append(path.name)
    return {province: _sorted_unique(values) for province, values in scripts.items()}


def _path_contains_province_segment(path: Path, province: str) -> bool:
    return province in path.parts


def _collect_standardized_domains_by_province() -> dict[str, list[str]]:
    hits = {province: [] for province in TARGET_PROVINCE_ORDER}
    for domain_name, root in STANDARDIZED_DOMAIN_ROOTS.items():
        if not root.exists():
            continue
        for province in TARGET_PROVINCE_ORDER:
            if any(_path_contains_province_segment(path, province) for path in root.rglob("*")):
                hits[province].append(domain_name)
    return {province: sorted(values) for province, values in hits.items()}


def _collect_raw_roots_by_province() -> dict[str, list[str]]:
    raw_roots = {province: [] for province in TARGET_PROVINCE_ORDER}
    for path in PROJECT_ROOT.iterdir():
        if not path.is_dir():
            continue
        for province in TARGET_PROVINCE_ORDER:
            if province in path.name:
                raw_roots[province].append(path.name)
    return {province: sorted(values) for province, values in raw_roots.items()}


def _build_readiness_description(
    province: str,
    imported_scopes: list[str],
    explicit_import_scripts: list[str],
    standardized_domains: list[str],
    raw_roots: list[str],
    missing_required_scopes: list[str],
) -> str:
    domain_labels = [DOMAIN_LABELS.get(name, name) for name in standardized_domains]
    if not missing_required_scopes and imported_scopes and explicit_import_scripts:
        return (
            f"{province}已经具备完整导入产物、专项导入脚本和标准化源目录痕迹，"
            "可以视为当前仓库内与河南同等级别的正式招生数据链路。"
        )
    if standardized_domains:
        return (
            f"{province}已发现标准化素材覆盖 {', '.join(domain_labels)}，"
            "但当前没有同省导入产物闭环，也没有对应专项导入脚本与推荐/报告链路验收，"
            "仍不能按河南同等级别正式交付。"
        )
    if raw_roots:
        return (
            f"{province}在仓库根目录存在原始资料目录 {', '.join(raw_roots)}，"
            "但当前尚未形成标准化导入和正式链路验证。"
        )
    return f"{province}当前既未发现同省导入产物，也未发现足以支撑正式链路的标准化素材目录。"


def build_province_readiness_summary(as_of_date: str) -> dict[str, Any]:
    imported_scopes_by_province = _collect_imported_scopes_by_province()
    explicit_scripts_by_province = _collect_explicit_import_scripts_by_province()
    standardized_domains_by_province = _collect_standardized_domains_by_province()
    raw_roots_by_province = _collect_raw_roots_by_province()

    provinces: list[dict[str, Any]] = []
    formal_provinces: list[str] = []

    for province in TARGET_PROVINCE_ORDER:
        slug = PROVINCE_SLUGS[province]
        imported_scopes = imported_scopes_by_province[province]
        imported_scope_suffixes = sorted(
            scope[len(f"{slug}_") :] for scope in imported_scopes if scope.lower().startswith(f"{slug}_")
        )
        missing_required_scopes = [
            suffix for suffix in REQUIRED_IMPORTED_SCOPE_SUFFIXES if suffix not in imported_scope_suffixes
        ]
        explicit_import_scripts = explicit_scripts_by_province[province]
        standardized_domains = standardized_domains_by_province[province]
        raw_roots = raw_roots_by_province[province]
        same_level_as_henan = not missing_required_scopes and bool(imported_scopes) and bool(explicit_import_scripts)
        readiness_status = "formal" if same_level_as_henan else ("raw_only" if standardized_domains or raw_roots else "not_ready")

        if same_level_as_henan:
            formal_provinces.append(province)

        provinces.append(
            {
                "province": province,
                "status": readiness_status,
                "sameLevelAsHenan": same_level_as_henan,
                "importedScopes": imported_scopes,
                "importedScopeSuffixes": imported_scope_suffixes,
                "missingRequiredImportedScopes": missing_required_scopes,
                "missingRequiredImportedScopeLabels": [IMPORTED_SCOPE_LABELS.get(name, name) for name in missing_required_scopes],
                "explicitImportScripts": explicit_import_scripts,
                "standardizedDomains": standardized_domains,
                "standardizedDomainLabels": [DOMAIN_LABELS.get(name, name) for name in standardized_domains],
                "rawRoots": raw_roots,
                "description": _build_readiness_description(
                    province=province,
                    imported_scopes=imported_scopes,
                    explicit_import_scripts=explicit_import_scripts,
                    standardized_domains=standardized_domains,
                    raw_roots=raw_roots,
                    missing_required_scopes=missing_required_scopes,
                ),
            }
        )

    return {
        "asOfDate": as_of_date,
        "verificationBasis": "filesystem_import_chain",
        "requiredImportedScopes": list(REQUIRED_IMPORTED_SCOPE_SUFFIXES),
        "formalProvinces": formal_provinces,
        "provinces": provinces,
    }
