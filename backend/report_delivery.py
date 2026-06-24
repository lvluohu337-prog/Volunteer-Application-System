from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from fastapi import HTTPException

from backend.rules_engine import safe_int


DbSessionFactory = Callable[[], Any]
PathFactory = Callable[[], Path]


def build_report_delivery_download_url(student_id: int, record_id: int | None) -> str:
    return f"/api/reports/student/{student_id}/deliveries/{record_id}/download"


def serialize_delivery_record(
    item: dict[str, Any],
    *,
    report_exports_dir: PathFactory,
    payload_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    import json

    if payload_summary is not None:
        item["payload"] = payload_summary
    else:
        try:
            item["payload"] = json.loads(item.get("payload_json") or "{}")
        except json.JSONDecodeError:
            item["payload"] = {}

    artifact_path_text = str(item.get("artifact_path") or "").strip()
    item["downloadUrl"] = build_report_delivery_download_url(
        safe_int(item.get("student_id")) or safe_int(item.get("studentId")) or 0,
        safe_int(item.get("id")) or None,
    )
    item["artifactExists"] = False
    item["artifactPathLabel"] = artifact_path_text
    item["artifactSizeBytes"] = None

    if not artifact_path_text:
        return item

    artifact_path = Path(artifact_path_text)
    export_dir = report_exports_dir().resolve()
    try:
        resolved_path = artifact_path.resolve()
    except OSError:
        return item

    try:
        relative_path = resolved_path.relative_to(export_dir)
        item["artifactPathLabel"] = str(relative_path)
    except ValueError:
        item["artifactPathLabel"] = str(resolved_path)

    if resolved_path.exists() and resolved_path.is_file():
        item["artifactExists"] = True
        try:
            item["artifactSizeBytes"] = resolved_path.stat().st_size
        except OSError:
            item["artifactSizeBytes"] = None

    return item


def get_report_delivery_download(
    student_id: int,
    record_id: int,
    *,
    db_session_factory: DbSessionFactory,
    report_exports_dir: PathFactory,
) -> dict[str, Any]:
    with db_session_factory() as connection:
        row = connection.execute(
            """
            SELECT id, student_id, product_code, export_format, report_title, artifact_name, artifact_path,
                   delivery_status, generated_by, include_signature, payload_json, created_at
            FROM report_delivery_records
            WHERE id = ? AND student_id = ?
            """,
            [record_id, student_id],
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Report delivery record not found")

    record = serialize_delivery_record(dict(row), report_exports_dir=report_exports_dir)
    artifact_path_text = str(record.get("artifact_path") or "").strip()
    if not artifact_path_text:
        raise HTTPException(status_code=404, detail="Export artifact path is missing")

    artifact_path = Path(artifact_path_text)
    try:
        resolved_path = artifact_path.resolve()
        export_dir = report_exports_dir().resolve()
    except OSError as exc:
        raise HTTPException(status_code=404, detail="Export artifact is unavailable") from exc

    try:
        resolved_path.relative_to(export_dir)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Export artifact is unavailable") from exc

    if not resolved_path.exists() or not resolved_path.is_file():
        raise HTTPException(status_code=404, detail="Export artifact file not found")

    export_format = str(record.get("export_format") or "").lower()
    media_type = (
        "application/pdf"
        if export_format == "pdf"
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

    return {
        "recordId": record_id,
        "studentId": student_id,
        "artifactPath": resolved_path,
        "artifactName": str(record.get("artifact_name") or resolved_path.name),
        "mediaType": media_type,
        "downloadUrl": record["downloadUrl"],
    }


def export_report_package(
    student_id: int,
    payload: Any,
    export_format: str,
    *,
    normalize_report_product_code: Callable[[str | None], str],
    normalize_text: Callable[[Any], str],
    get_student_report: Callable[..., dict[str, Any]],
    safe_report_filename: Callable[[str], str],
    report_exports_dir: PathFactory,
    export_report_pdf: Callable[..., Any],
    export_report_docx: Callable[..., Any],
    create_report_delivery_record: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    product_code = normalize_report_product_code(getattr(payload, "reportVersion", None))
    reviewed_by = normalize_text(getattr(payload, "reviewedBy", None)) or "system-export"
    include_signature = bool(getattr(payload, "includeSignature", False))
    report_data = get_student_report(
        student_id=student_id,
        product_code=product_code,
        generated_by=reviewed_by,
        generation_mode=f"export_{export_format}",
    )

    student_name = report_data.get("reportTitle", "志愿规划报告").replace(" 志愿规划报告预览", "")
    file_stub = safe_report_filename(
        f"{student_name}-{product_code}-{export_format}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    )
    export_dir = report_exports_dir()
    artifact_name = f"{file_stub}.pdf" if export_format == "pdf" else f"{file_stub}.docx"

    artifact_path = export_dir / artifact_name
    if export_format == "pdf":
        export_report_pdf(
            report_data,
            artifact_path,
            reviewed_by=reviewed_by,
            include_signature=include_signature,
        )
    else:
        export_report_docx(
            report_data,
            artifact_path,
            reviewed_by=reviewed_by,
            include_signature=include_signature,
        )

    payload_summary = {
        "reportVersion": product_code,
        "reviewedBy": reviewed_by,
        "includeSignature": include_signature,
        "artifactType": "final_document",
        "renderEngine": "reportlab_pdf_renderer" if export_format == "pdf" else "builtin_docx_renderer",
        "note": "当前阶段已直接生成正式交付文件，可用于归档、发送与线下讲解交付。",
    }
    delivery_record = create_report_delivery_record(
        student_id=student_id,
        product_code=product_code,
        export_format=export_format,
        report_title=report_data.get("reportTitle") or "志愿规划报告",
        artifact_name=artifact_name,
        artifact_path=str(artifact_path),
        generated_by=reviewed_by,
        include_signature=include_signature,
        payload_summary=payload_summary,
    )

    return {
        "studentId": student_id,
        "productCode": product_code,
        "exportFormat": export_format,
        "artifactType": payload_summary["artifactType"],
        "downloadUrl": build_report_delivery_download_url(student_id, safe_int(delivery_record.get("id")) or None),
        "artifactName": artifact_name,
        "deliveryRecord": delivery_record,
    }
