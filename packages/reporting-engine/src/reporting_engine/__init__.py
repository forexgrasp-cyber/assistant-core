"""
Reporting Engine - Dynamic report generation built on shared analytics services.

Integrates with:
- shared.analytics.daily_facts.DailyFactsService (canonical analytics store)
- shared.analytics.analytics_service.AnalyticsService (revenue/events)
- shared.analytics.collectors.AnalyticsCollector (multi-source collection)
- shared.analytics.alerting (alert evaluation)
- shared.metrics (business metrics, analytics router)
- shared.reporting (base reporting service)
- shared.rag (vector search for AI summaries)
- shared.ai_llm (LLM integration)
"""

from __future__ import annotations

from .service import ReportingEngine
from .models import (
    ReportDefinition,
    ReportTemplate,
    ReportRun,
    ReportSchedule,
    WidgetDefinition,
    WidgetConfig,
    DataSourceConfig,
    DataSourceType,
    ExportFormat,
    ReportStatus,
    RunStatus,
    DashboardDefinition,
    QueryResult,
    RenderedReport,
    RenderedSection,
    RenderedWidget,
    KPICardProps,
    ReportSection,
    WidgetType,
    FilterConfig,
    FilterOperator,
    DateRangeConfig,
    OrderByConfig,
    ExportOptions,
)
from .templates import TemplateRegistry, BaseTemplate
from .components import WidgetRenderer, ChartRenderer, TableRenderer
from .exporters import PDFExporter, HTMLExporter, CSVExporter, JSONExporter
from .scheduler import ReportScheduler

__all__ = [
    "ReportingEngine",
    "ReportDefinition",
    "ReportTemplate",
    "ReportRun",
    "ReportSchedule",
    "WidgetDefinition",
    "WidgetConfig",
    "DataSourceConfig",
    "DataSourceType",
    "ExportFormat",
    "ReportStatus",
    "RunStatus",
    "DashboardDefinition",
    "QueryResult",
    "RenderedReport",
    "RenderedSection",
    "RenderedWidget",
    "KPICardProps",
    "ReportSection",
    "WidgetType",
    "FilterConfig",
    "FilterOperator",
    "DateRangeConfig",
    "OrderByConfig",
    "ExportOptions",
    "TemplateRegistry",
    "BaseTemplate",
    "WidgetRenderer",
    "ChartRenderer",
    "TableRenderer",
    "PDFExporter",
    "HTMLExporter",
    "CSVExporter",
    "JSONExporter",
    "ReportScheduler",
]

__version__ = "0.1.0"