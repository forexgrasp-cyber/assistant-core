"""Reporting engine package.

Generates reports (PDF/HTML/CSV/JSON) from metrics and workflow outputs.
Actions can be scheduled by pipelines and downloaded via the frontend.
"""

from __future__ import annotations

from retention_analytics_reporting_engine.report_service import ReportService

__all__ = ["ReportService"]
