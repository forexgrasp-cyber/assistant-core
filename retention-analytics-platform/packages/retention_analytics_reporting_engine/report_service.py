"""Report service.

Builds reports from the persisted metric, cohort and workflow-run data of the
calling tenant and writes the rendered artifact to disk so the download
endpoint serves real content.

Supported formats: ``json``, ``html`` and ``csv``. PDF rendering requires a
PDF engine; when none is installed the request is rejected instead of
silently returning an HTML file with a PDF content type.
"""

from __future__ import annotations

import csv
import html
import io
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog
from retention_analytics_core.repository import data_root, new_id, repository_for
from retention_analytics_core.service_base import CanonicalService

logger = structlog.get_logger(__name__)

CONTENT_TYPES = {
    "json": "application/json",
    "html": "text/html; charset=utf-8",
    "csv": "text/csv",
    "pdf": "application/pdf",
}


class ReportService(CanonicalService):
    SERVICE_NAME = "reporting.engine"

    def __init__(self, registry: Any) -> None:
        super().__init__("reporting.engine", registry)
        self.register_action("generate_report", self._generate_report)
        self.register_action("download_report", self._download_report)

    def register(
        self,
        subscribes_to: list | None = None,
        metadata: dict[str, Any] | None = None,
        service_type: str = "platform",
    ) -> None:
        super().register(
            subscribes_to=subscribes_to,
            metadata={**(metadata or {}), "domain": "reporting"},
            service_type=service_type,
        )

    def _tenant(self, payload: dict[str, Any]) -> str:
        return str(payload.get("tenant_id") or "default")

    async def _collect_data(self, tenant_id: str) -> dict[str, Any]:
        metrics = [record for _id, record in await repository_for("metrics", tenant_id).list_all()]
        cohorts = [record for _id, record in await repository_for("cohorts", tenant_id).list_all()]
        runs = [record for _id, record in await repository_for("workflow_runs", tenant_id).list_all()]
        return {
            "metrics": [m for m in metrics if isinstance(m, dict)],
            "cohorts": [c for c in cohorts if isinstance(c, dict)],
            "workflow_runs": [r for r in runs if isinstance(r, dict)],
        }

    def _render(self, name: str, fmt: str, data: dict[str, Any]) -> bytes:
        if fmt == "json":
            return json.dumps(data, indent=2, default=str).encode("utf-8")
        if fmt == "csv":
            return self._render_csv(data)
        if fmt == "html":
            return self._render_html(name, data).encode("utf-8")
        if fmt == "pdf":
            return self._render_pdf(name, data)
        raise ValueError(f"unsupported report format '{fmt}'")

    def _render_csv(self, data: dict[str, Any]) -> bytes:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["metric", "tenant_id", "computed_at", "payload"])
        for metric in data["metrics"]:
            writer.writerow(
                [
                    metric.get("metric", ""),
                    metric.get("tenant_id", ""),
                    metric.get("computed_at", ""),
                    json.dumps(metric, default=str),
                ]
            )
        return buffer.getvalue().encode("utf-8")

    def _render_html(self, name: str, data: dict[str, Any]) -> str:
        rows = []
        for metric in data["metrics"]:
            rows.append(
                "<tr>"
                f"<td>{_escape(metric.get('metric', ''))}</td>"
                f"<td>{_escape(metric.get('computed_at', ''))}</td>"
                f"<td><code>{_escape(json.dumps(metric, default=str))}</code></td>"
                "</tr>"
            )
        run_rows = []
        for run in data["workflow_runs"]:
            run_rows.append(
                "<tr>"
                f"<td>{_escape(run.get('workflow_id', ''))}</td>"
                f"<td>{_escape(run.get('status', ''))}</td>"
                f"<td>{_escape(run.get('id', ''))}</td>"
                "</tr>"
            )
        return (
            "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            f"<title>{_escape(name)}</title></head><body>"
            f"<h1>{_escape(name)}</h1>"
            f"<p>Generated {_escape(datetime.now(UTC).isoformat())}</p>"
            "<h2>Metrics</h2><table border=\"1\" cellspacing=\"0\" cellpadding=\"4\">"
            "<tr><th>Metric</th><th>Computed at</th><th>Payload</th></tr>"
            + "".join(rows)
            + "</table>"
            "<h2>Workflow runs</h2><table border=\"1\" cellspacing=\"0\" cellpadding=\"4\">"
            "<tr><th>Workflow</th><th>Status</th><th>Run id</th></tr>"
            + "".join(run_rows)
            + "</table></body></html>"
        )

    def _render_pdf(self, name: str, data: dict[str, Any]) -> bytes:
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
        except ImportError as exc:
            raise RuntimeError("PDF rendering is not available in this deployment") from exc

        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        y = height - 50
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(50, y, name)
        y -= 30
        pdf.setFont("Helvetica", 9)
        for metric in data["metrics"]:
            line = f"{metric.get('metric', '')} @ {metric.get('computed_at', '')}"
            pdf.drawString(50, y, line[:110])
            y -= 14
            if y < 60:
                pdf.showPage()
                pdf.setFont("Helvetica", 9)
                y = height - 50
        pdf.save()
        return buffer.getvalue()

    async def _generate_report(self, payload: dict[str, Any]) -> dict[str, Any]:
        tenant_id = self._tenant(payload)
        name = str(payload.get("name") or "Retention Report")
        fmt = str(payload.get("format") or "html").lower()

        if fmt not in CONTENT_TYPES:
            return self.fail(f"unsupported report format '{fmt}'")

        data = await self._collect_data(tenant_id)
        try:
            content = self._render(name, fmt, data)
        except RuntimeError as exc:
            return self.fail(str(exc))
        except ValueError as exc:
            return self.fail(str(exc))

        report_id = new_id("rep")
        artifact_dir = data_root() / "reports" / tenant_id
        artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = artifact_dir / f"{report_id}.{fmt}"
        artifact_path.write_bytes(content)

        record = {
            "report_id": report_id,
            "name": name,
            "format": fmt,
            "tenant_id": tenant_id,
            "path": str(artifact_path),
            "content_type": CONTENT_TYPES[fmt],
            "size_bytes": len(content),
            "generated_at": datetime.now(UTC).isoformat(),
        }
        await repository_for("reports", tenant_id).save(report_id, record)

        logger.info(
            "report.generate",
            report_id=report_id,
            name=name,
            format=fmt,
            size_bytes=len(content),
            tenant_id=tenant_id,
        )
        return {
            "status": "generated",
            "report_id": report_id,
            "name": name,
            "format": fmt,
            "download_url": f"/api/v1/reports/{report_id}/download",
            "generated_at": record["generated_at"],
            "size_bytes": len(content),
        }

    async def _download_report(self, payload: dict[str, Any]) -> dict[str, Any]:
        tenant_id = self._tenant(payload)
        report_id = payload.get("report_id")
        if not report_id:
            return self.fail("report_id is required")
        record = await repository_for("reports", tenant_id).load(str(report_id))
        if record is None:
            return self.fail("unknown report_id")
        path = Path(str(record.get("path", "")))
        if not path.is_file():
            return self.fail("report artifact is missing")
        return {
            "status": "ready",
            "report_id": report_id,
            "content_type": record.get("content_type", "application/octet-stream"),
            "path": str(path),
        }


def _escape(value: Any) -> str:
    """Escape a value for safe inclusion in an HTML document."""
    return html.escape(str(value), quote=True)


__all__ = ["CONTENT_TYPES", "ReportService"]
