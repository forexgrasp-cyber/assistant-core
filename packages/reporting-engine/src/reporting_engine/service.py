"""
Reporting Engine Service

Main service that orchestrates report generation by:
1. Integrating with shared analytics services (DailyFactsService, AnalyticsService, AnalyticsCollector)
2. Executing data queries against multiple sources
3. Rendering widgets using template registry and component renderers
4. Exporting to multiple formats (PDF, HTML, CSV, JSON)
5. Scheduling and delivery via email, Slack, webhooks
"""

from __future__ import annotations

import asyncio
import io
import json
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

import structlog
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .models import (
    ReportDefinition,
    ReportTemplate,
    ReportRun,
    ReportSchedule,
    ReportSection,
    WidgetDefinition,
    WidgetConfig,
    DataSourceConfig,
    DataSourceType,
    WidgetType,
    ExportFormat,
    ReportStatus,
    RunStatus,
    ExportOptions,
    ReportContext,
    QueryResult,
    RenderedWidget,
    RenderedSection,
    RenderedReport,
    AIReportSummary,
    ALL_TEMPLATES,
)
from .templates import TemplateRegistry
from .components import WidgetRenderer, ChartRenderer, TableRenderer
from .exporters import PDFExporter, HTMLExporter, CSVExporter, JSONExporter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .scheduler import ReportScheduler

log = structlog.get_logger()

# Add shared-canonical-services to path
import sys
SHARED_PATH = Path(__file__).parent.parent.parent.parent.parent / "shared-canonical-services"
if str(SHARED_PATH) not in sys.path:
    sys.path.insert(0, str(SHARED_PATH))

try:
    from shared.analytics.daily_facts import DailyFactsService
    from shared.analytics.analytics_service import AnalyticsService
    from shared.analytics.collectors import AnalyticsCollector
    from shared.analytics.alerting import evaluate_alerts
    from shared.metrics import MetricsCollector, AnalyticsRouter
    from shared.reporting import ReportingService as SharedReportingService
    SHARED_ANALYTICS_AVAILABLE = True
except ImportError as e:
    log.warning("shared_analytics_unavailable", error=str(e))
    SHARED_ANALYTICS_AVAILABLE = False
    DailyFactsService = None
    AnalyticsService = None
    AnalyticsCollector = None
    evaluate_alerts = None
    MetricsCollector = None
    AnalyticsRouter = None
    SharedReportingService = None


class ReportingEngine:
    """
    Main reporting engine that generates reports from dynamic definitions.
    
    Integrates with shared analytics services for data, uses Jinja2 for templates,
    WeasyPrint/Playwright for PDF, and supports multiple export formats.
    """

    def __init__(
        self,
        # Shared services (injected for testing)
        daily_facts_service: Optional[DailyFactsService] = None,
        analytics_service: Optional[AnalyticsService] = None,
        analytics_collector: Optional[AnalyticsCollector] = None,
        metrics_collector: Optional[MetricsCollector] = None,
        analytics_router: Optional[AnalyticsRouter] = None,
        shared_reporting: Optional[SharedReportingService] = None,
        # Configuration
        template_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        static_dir: Optional[Path] = None,
        # Exporters
        pdf_exporter: Optional[PDFExporter] = None,
        html_exporter: Optional[HTMLExporter] = None,
        csv_exporter: Optional[CSVExporter] = None,
        json_exporter: Optional[JSONExporter] = None,
        # Scheduler
        scheduler: Optional[ReportScheduler] = None,
        # AI
        ai_service: Any = None,
        # Cache
        query_cache_ttl: int = 300,  # 5 minutes
    ):
        # Shared services
        self.daily_facts = daily_facts_service or (DailyFactsService() if SHARED_ANALYTICS_AVAILABLE else None)
        self.analytics_service = analytics_service or (AnalyticsService() if SHARED_ANALYTICS_AVAILABLE else None)
        self.collector = analytics_collector or (AnalyticsCollector() if SHARED_ANALYTICS_AVAILABLE else None)
        self.metrics = metrics_collector or (MetricsCollector() if SHARED_ANALYTICS_AVAILABLE else None)
        self.router = analytics_router or (AnalyticsRouter() if SHARED_ANALYTICS_AVAILABLE else None)
        self.shared_reporting = shared_reporting or (SharedReportingService() if SHARED_ANALYTICS_AVAILABLE else None)
        
        # Directories
        self.template_dir = template_dir or Path(__file__).parent / "templates"
        self.output_dir = output_dir or Path("output/reports")
        self.static_dir = static_dir or Path(__file__).parent.parent / "static"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Exporters
        self.pdf_exporter = pdf_exporter or PDFExporter(self.output_dir)
        self.html_exporter = html_exporter or HTMLExporter(self.output_dir)
        self.csv_exporter = csv_exporter or CSVExporter(self.output_dir)
        self.json_exporter = json_exporter or JSONExporter(self.output_dir)

        # Scheduler (lazy import avoids circular dependency)
        if scheduler is None:
            from .scheduler import ReportScheduler
            scheduler = ReportScheduler(engine=self)
        self.scheduler = scheduler
        
        # AI service
        self.ai_service = ai_service
        
        # Template registry
        self.template_registry = TemplateRegistry(self.template_dir)
        self._register_builtin_templates()
        
        # Renderers
        self.widget_renderer = WidgetRenderer(self)
        self.chart_renderer = ChartRenderer()
        self.table_renderer = TableRenderer()
        
        # Cache
        self._query_cache: Dict[str, tuple[QueryResult, datetime]] = {}
        self.query_cache_ttl = query_cache_ttl
        
        # In-memory stores (would be DB in production)
        self._reports: Dict[str, ReportDefinition] = {}
        self._templates: Dict[str, ReportTemplate] = {**ALL_TEMPLATES}
        self._runs: Dict[str, ReportRun] = {}
        self._schedules: Dict[str, ReportSchedule] = {}
        
        log.info("reporting_engine_initialized",
            has_daily_facts=self.daily_facts is not None,
            has_analytics=self.analytics_service is not None,
            has_collector=self.collector is not None,
        templates_loaded=len(self._templates))

    def _register_builtin_templates(self):
        """Register built-in templates with the registry."""
        for tmpl in ALL_TEMPLATES.values():
            self.template_registry.register(tmpl)

    # ========================================================================
    # Report Definition Management
    # ========================================================================

    def create_report(self, report: ReportDefinition) -> ReportDefinition:
        """Create a new report definition."""
        if not report.id:
            report.id = f"rpt_{uuid.uuid4().hex[:8]}"
        report.created_at = datetime.utcnow()
        report.updated_at = datetime.utcnow()
        self._reports[report.id] = report
        
        # Create schedule if defined
        if report.schedule:
            self.create_schedule(ReportSchedule(
                report_id=report.id,
                cron_expression=report.schedule,
                timezone=report.timezone,
            ))
        
        log.info("report_created", report_id=report.id, name=report.name)
        return report

    def create_report_from_template(
        self,
        template_id: str,
        name: str,
        overrides: Optional[Dict[str, Any]] = None,
        client_ids: Optional[List[UUID]] = None,
    ) -> ReportDefinition:
        """Create a report from a template with optional overrides."""
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        report = ReportDefinition(
            name=name,
            description=template.description,
        template_id=template.id,
            sections=template.sections.copy(),
            filters=template.default_filters.copy(),
            schedule=template.default_schedule,
            formats=template.default_formats,
            tags=template.tags.copy(),
            vertical=template.vertical,
        client_ids=client_ids or [],
        )
        
        if overrides:
            for key, value in overrides.items():
                if hasattr(report, key):
                    setattr(report, key, value)
        
        return self.create_report(report)

    def get_report(self, report_id: str) -> Optional[ReportDefinition]:
        return self._reports.get(report_id)

    def list_reports(
        self,
        status: Optional[ReportStatus] = None,
        vertical: Optional[str] = None,
        client_id: Optional[UUID] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ReportDefinition]:
        reports = list(self._reports.values())
        
        if status:
            reports = [r for r in reports if r.status == status]
        if vertical:
            reports = [r for r in reports if r.vertical == vertical]
        if client_id:
            reports = [r for r in reports if not r.client_ids or client_id in r.client_ids]
        
        reports.sort(key=lambda r: r.updated_at, reverse=True)
        return reports[offset:offset + limit]

    def update_report(self, report_id: str, updates: Dict[str, Any]) -> Optional[ReportDefinition]:
        report = self._reports.get(report_id)
        if not report:
            return None
        
        for key, value in updates.items():
            if hasattr(report, key):
                setattr(report, key, value)
        
        report.updated_at = datetime.utcnow()
        
        # Update schedule if changed
        if "schedule" in updates:
            self._update_schedule(report)
        
        log.info("report_updated", report_id=report_id)
        return report

    def delete_report(self, report_id: str) -> bool:
        if report_id not in self._reports:
            return False
        
        # Delete associated schedule
        schedules_to_delete = [s for s in self._schedules.values() if s.report_id == report_id]
        for s in schedules_to_delete:
            self.delete_schedule(s.id)
        
        del self._reports[report_id]
        log.info("report_deleted", report_id=report_id)
        return True

    def _update_schedule(self, report: ReportDefinition):
        """Update or create schedule for a report."""
        existing = next((s for s in self._schedules.values() if s.report_id == report.id), None)
        if existing:
            existing.cron_expression = report.schedule or ""
            existing.timezone = report.timezone
            existing.is_active = bool(report.schedule)
            existing.updated_at = datetime.utcnow()
        elif report.schedule:
            self.create_schedule(ReportSchedule(
                report_id=report.id,
                cron_expression=report.schedule,
                timezone=report.timezone,
            ))

    # ========================================================================
    # Template Management
    # ========================================================================

    def get_template(self, template_id: str) -> Optional[ReportTemplate]:
        return self._templates.get(template_id)

    def list_templates(
        self,
        category: Optional[str] = None,
        vertical: Optional[str] = None,
        is_system: Optional[bool] = None,
    ) -> List[ReportTemplate]:
        templates = list(self._templates.values())
        
        if category:
            templates = [t for t in templates if t.category == category]
        if vertical:
            templates = [t for t in templates if t.vertical == vertical]
        if is_system is not None:
            templates = [t for t in templates if t.is_system == is_system]
        
        return templates

    def register_template(self, template: ReportTemplate) -> ReportTemplate:
        self._templates[template.id] = template
        self.template_registry.register(template)
        log.info("template_registered", template_id=template.id, name=template.name)
        return template

    # ========================================================================
    # Report Execution
    # ========================================================================

    async def run_report(
        self,
        report_id: str,
        triggered_by: str = "manual",
        triggered_by_user: Optional[UUID] = None,
        parameters: Optional[Dict[str, Any]] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        date_range: Optional[Dict[str, str]] = None,
        formats: Optional[List[ExportFormat]] = None,
    ) -> ReportRun:
        """Execute a report and generate outputs."""
        report = self.get_report(report_id)
        if not report:
            raise ValueError(f"Report not found: {report_id}")
        
        # Create run record
        run = ReportRun(
        report_id=report.id,
        report_name=report.name,
            triggered_by=triggered_by,
            triggered_by_user=triggered_by_user,
            parameters=parameters or {},
            filters_applied=filters or report.filters,
        date_range=date_range or self._resolve_date_range(report),
            status=RunStatus.RUNNING,
        started_at=datetime.utcnow(),
        )
        self._runs[run.id] = run
        
        # Update report last run
        report.last_run_at = datetime.utcnow()
        if report.schedule:
            report.next_run_at = self._calculate_next_run(report.schedule, report.timezone)
        
        log.info("report_run_started", run_id=run.id, report_id=report_id)
        
        try:
            # Build context
            context = await self._build_context(report, run)
            
            # Execute data queries for all widgets
            await self._execute_queries(context)
            
            # Render report
            rendered = await self._render_report(context)
            
            # Export to requested formats
            output_files = await self._export_report(rendered, formats or report.formats)
            
            # Update run with results
            run.status = RunStatus.COMPLETED
            run.completed_at = datetime.utcnow()
            run.output_files = output_files
            run.widgets_rendered = rendered.total_widgets
            run.widgets_failed = rendered.failed_widgets
            run.total_data_rows = rendered.total_data_rows
            run.total_time_ms = int((run.completed_at - run.started_at).total_seconds() * 1000) if run.started_at else 0
            
            # Deliver
            await self._deliver_report(report, run, output_files)
            
            log.info("report_run_completed", run_id=run.id, 
                widgets=run.widgets_rendered, failed=run.widgets_failed,
                formats=len(output_files))
            
        except Exception as e:
            log.exception("report_run_failed", run_id=run.id, error=str(e))
            run.status = RunStatus.FAILED
            run.completed_at = datetime.utcnow()
            run.error_message = str(e)
            run.error_details = {"type": type(e).__name__}
        
        return run

    async def _build_context(self, report: ReportDefinition, run: ReportRun) -> ReportContext:
        """Build runtime context for report generation."""
        # Resolve client IDs
        client_ids = report.client_ids
        if not client_ids and self.daily_facts:
            # Get all sites from daily facts
            sites = self.daily_facts.sites()
            # Filter out portfolio site
        client_ids = [UUID(s) for s in sites if s != "__all__"]
        
        return ReportContext(
        report=report,
            run=run,
        client_ids=client_ids,
        date_range=run.date_range or {},
            timezone=report.timezone,
            daily_facts_service=self.daily_facts,
            analytics_service=self.analytics_service,
            collector=self.collector,
            metrics_collector=self.metrics,
            analytics_router=self.router,
            export_options=ExportOptions(),
        )

    def _resolve_date_range(self, report: ReportDefinition) -> Dict[str, str]:
        """Resolve date range from report filters or defaults."""
        # Check filters for date range
        for f in report.filters:
            if f.get("field") in ("date", "created_at", "period"):
                return {
                    "start": f.get("value", {}).get("start", ""),
                    "end": f.get("value", {}).get("end", ""),
                }
        
        # Default to last 30 days
        end = datetime.utcnow().date()
        start = end - timedelta(days=30)
        return {"start": start.isoformat(), "end": end.isoformat()}

    def _calculate_next_run(self, cron_expression: str, timezone: str) -> datetime:
        """Calculate next run time from cron expression."""
        # Simplified - in production use croniter
        return datetime.utcnow() + timedelta(days=1)

    # ========================================================================
    # Data Query Execution
    # ========================================================================

    async def _execute_queries(self, context: ReportContext):
        """Execute data queries for all widgets in the report."""
        for section in context.report.sections:
            for widget in section.widgets:
                cache_key = self._cache_key(widget.config.data_source, context)
                
                # Check cache
                if cache_key in self._query_cache:
                    result, cached_at = self._query_cache[cache_key]
                    if (datetime.utcnow() - cached_at).total_seconds() < self.query_cache_ttl:
                        context.data_cache[widget.id] = result
                        continue
                
                # Execute query
                result = await self._execute_data_source(widget.config.data_source, context)
                context.data_cache[widget.id] = result
                self._query_cache[cache_key] = (result, datetime.utcnow())
                
                run.widgets_rendered += 1

    def _cache_key(self, source: DataSourceConfig, context: ReportContext) -> str:
        """Generate cache key for a data source."""
        key_parts = [
            getattr(source.type, 'value', source.type),
            json.dumps(source.metrics, sort_keys=True),
            json.dumps(source.dimensions, sort_keys=True),
            json.dumps(source.filters, sort_keys=True),
            json.dumps(source.date_range, sort_keys=True),
            json.dumps(source.group_by, sort_keys=True),
        ]
        return "|".join(key_parts)


    async def _execute_data_source(
        self,
        source: DataSourceConfig,
        context: ReportContext,
    ) -> QueryResult:
        try:
            start_time = datetime.utcnow()
            if source.type == DataSourceType.DAILY_FACTS:
                return await self._query_daily_facts(source, context)
            elif source.type == DataSourceType.PROGRAM_REVENUE:
                return await self._query_program_revenue(source, context)
            elif source.type == DataSourceType.DIMENSION_FACTS:
                return await self._query_dimension_facts(source, context)
            elif source.type == DataSourceType.PAYMENT_FACTS:
                return await self._query_payment_facts(source, context)
            elif source.type == DataSourceType.REVENUE_EVENTS:
                return await self._query_revenue_events(source, context)
            elif source.type == DataSourceType.USAGE_EVENTS:
                return await self._query_usage_events(source, context)
            elif source.type == DataSourceType.CUSTOM_SQL:
                return await self._query_custom_sql(source, context)
            elif source.type == DataSourceType.MCP_TOOL:
                return await self._query_mcp_tool(source, context)
            elif source.type == DataSourceType.API_ENDPOINT:
                return await self._query_api_endpoint(source, context)
            elif source.type == DataSourceType.VERTICAL_PACK:
                return await self._query_vertical_pack(source, context)
            else:
                raise ValueError(f"Unknown data source type: {source.type}")

        except Exception as e:
            log.exception("query_failed", source_type=getattr(source.type, 'value', source.type), error=str(e))
            return QueryResult(
                data=[],
                columns=[],
                row_count=0,
                execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                source=None,
                metadata={"error": str(e)},
            )
        days = date_range.get("days", 30)
        start = date_range.get("start")
        end = date_range.get("end")
        
        # For each client, get series and aggregate
        all_data = []
        for client_id in context.client_ids:
            series = self.daily_facts.get_series(
            site=str(client_id),
        days=days,
        start=start,
        end=end,
            )
        for row in series:
            row["client_id"] = str(client_id)
        all_data.append(row)
        
        # Apply filters
        filtered = self._apply_filters(all_data, source.filters)
        
        # Apply grouping
        if source.group_by:
            filtered = self._group_data(filtered, source.group_by, source.metrics)
        
        # Apply ordering
        if source.order_by:
            filtered = self._order_data(filtered, source.order_by)
        
        # Apply limit
        if source.limit:
            filtered = filtered[:source.limit]
        
            columns = list(filtered[0].keys()) if filtered else []
        
        return QueryResult(
            data=filtered,
            columns=columns,
        row_count=len(filtered),
            execution_time_ms=int((datetime.utcnow() - datetime.utcnow()).total_seconds() * 1000),
            source=DataSourceType.DAILY_FACTS,
            )

    async def _query_daily_facts(self, source: DataSourceConfig, context: ReportContext) -> QueryResult:
        """Query daily facts from shared analytics."""
        if not self.daily_facts:
            return QueryResult(data=[], columns=[], row_count=0, source=DataSourceType.DAILY_FACTS)

        date_range = source.date_range or {}
        days = date_range.get("days", 30)
        start = date_range.get("start")
        end = date_range.get("end")

        metric = source.metrics[0] if source.metrics else "sessions"

        all_data = []
        for client_id in context.client_ids:
            series = self.daily_facts.get_series(
                site=str(client_id),
                days=days,
                start=start,
                end=end,
            )
            for row in series:
                row["client_id"] = str(client_id)
                all_data.append(row)

        filtered = self._apply_filters(all_data, source.filters)

        if source.group_by:
            grouped = self._group_data(filtered, source.group_by, source.metrics)
            data = grouped
        else:
            data = filtered

        if source.order_by:
            data = self._order_data(data, source.order_by)

        if source.limit:
            data = data[:source.limit]

        columns = list(data[0].keys()) if data else []

        return QueryResult(
            data=data,
            columns=columns,
            row_count=len(data),
            execution_time_ms=0,
            source=DataSourceType.DAILY_FACTS,
        )

    async def _query_program_revenue(self, source: DataSourceConfig, context: ReportContext) -> QueryResult:
        """Query program revenue from shared analytics."""
        if not self.daily_facts:
                return QueryResult(data=[], columns=[], row_count=0, source=DataSourceType.PROGRAM_REVENUE)
        
        date_range = source.date_range or {}
        days = date_range.get("days", 30)
        start = date_range.get("start")
        
        all_data = []
        for client_id in context.client_ids:
            detail = self.daily_facts.program_detail(
                site=str(client_id),
                days=days,
                start=start,
            )
        for row in detail:
                row["client_id"] = str(client_id)
                all_data.append(row)
        
        filtered = self._apply_filters(all_data, source.filters)
        
        if source.group_by:
            filtered = self._group_data(filtered, source.group_by, source.metrics)
        
        if source.order_by:
            filtered = self._order_data(filtered, source.order_by)
        
        if source.limit:
            filtered = filtered[:source.limit]
        
        columns = list(filtered[0].keys()) if filtered else []
        
        return QueryResult(
            data=filtered,
            columns=columns,
        row_count=len(filtered),
            source=DataSourceType.PROGRAM_REVENUE,
        )

    async def _query_dimension_facts(self, source: DataSourceConfig, context: ReportContext) -> QueryResult:
        """Query dimension facts from shared analytics."""
        if not self.daily_facts:
            return QueryResult(data=[], columns=[], row_count=0, source=DataSourceType.DIMENSION_FACTS)
        
        date_range = source.date_range or {}
        days = date_range.get("days", 30)
        
        # Use pivot or breakdown based on query
        dim_type = None
        for f in source.filters:
            if f.get("field") == "dim_type":
                dim_type = f.get("value")
                break
        
        if not dim_type and source.dimensions:
            dim_type = source.dimensions[0]
        
        if not dim_type:
            return QueryResult(data=[], columns=[], row_count=0, source=DataSourceType.DIMENSION_FACTS)
        
        metric = source.metrics[0] if source.metrics else "sessions"
        
        all_data = []
        for client_id in context.client_ids:
            # Use breakdown for single metric by dimension
            breakdown = self.daily_facts.breakdown_counts(
                source="dimension",
                rows_axis="dim",
                metrics=[metric],
                site=str(client_id),
                days=days,
                dim_type=dim_type,
            )
        for row in breakdown:
                row["client_id"] = str(client_id)
                all_data.append(row)
        
        filtered = self._apply_filters(all_data, source.filters)
        
        if source.order_by:
            filtered = self._order_data(filtered, source.order_by)
        
        if source.limit:
            filtered = filtered[:source.limit]
        
        columns = list(filtered[0].keys()) if filtered else []
        
        return QueryResult(
            data=filtered,
            columns=columns,
        row_count=len(filtered),
            source=DataSourceType.DIMENSION_FACTS,
        )

    async def _query_payment_facts(self, source: DataSourceConfig, context: ReportContext) -> QueryResult:
        """Query payment facts from shared analytics."""
        if not self.daily_facts:
            return QueryResult(data=[], columns=[], row_count=0, source=DataSourceType.PAYMENT_FACTS)
        
        date_range = source.date_range or {}
        days = date_range.get("days", 30)
        start = date_range.get("start")
        end = date_range.get("end")
        
        all_data = []
        for client_id in context.client_ids:
            facts = self.daily_facts.payment_facts(
                site=str(client_id),
                days=days,
                start=start,
                end=end,
            )
        for row in facts:
                row["client_id"] = str(client_id)
                all_data.append(row)
        
        filtered = self._apply_filters(all_data, source.filters)
        
        if source.group_by:
            filtered = self._group_data(filtered, source.group_by, source.metrics)
        
        if source.order_by:
            filtered = self._order_data(filtered, source.order_by)
        
        if source.limit:
            filtered = filtered[:source.limit]
        
        columns = list(filtered[0].keys()) if filtered else []
        
        return QueryResult(
            data=filtered,
            columns=columns,
        row_count=len(filtered),
            source=DataSourceType.PAYMENT_FACTS,
        )

    async def _query_revenue_events(self, source: DataSourceConfig, context: ReportContext) -> QueryResult:
        """Query revenue events from analytics service."""
        if not self.analytics_service:
            return QueryResult(data=[], columns=[], row_count=0, source=DataSourceType.REVENUE_EVENTS)
        
        # Use analytics service to get revenue summary
        result = self.analytics_service.get_revenue_summary(
            tenant_id=str(context.client_ids[0]) if context.client_ids else None,
        days=source.date_range.get("days", 30) if source.date_range else 30,
        )
        
        if result.success and result.data:
            return QueryResult(
                data=[result.data],
                columns=list(result.data.keys()),
                row_count=1,
                source=DataSourceType.REVENUE_EVENTS,
            )
        
        return QueryResult(data=[], columns=[], row_count=0, source=DataSourceType.REVENUE_EVENTS)

    async def _query_usage_events(self, source: DataSourceConfig, context: ReportContext) -> QueryResult:
        """Query usage events from analytics service."""
        # Similar to revenue events but for usage
        return QueryResult(data=[], columns=[], row_count=0, source=DataSourceType.USAGE_EVENTS)

    async def _query_custom_sql(self, source: DataSourceConfig, context: ReportContext) -> QueryResult:
        """Execute custom SQL query."""
        # Would connect to ClickHouse or PostgreSQL
        return QueryResult(data=[], columns=[], row_count=0, source=DataSourceType.CUSTOM_SQL)

    async def _query_mcp_tool(self, source: DataSourceConfig, context: ReportContext) -> QueryResult:
        """Call MCP tool for data."""
        if not context.mcp_client or not source.tool_name:
            return QueryResult(data=[], columns=[], row_count=0, source=DataSourceType.MCP_TOOL)
        
        result = await context.mcp_client.call_tool(source.tool_name, source.tool_params)
        
        return QueryResult(
            data=result.get("data", []),
            columns=result.get("columns", []),
        row_count=len(result.get("data", [])),
            source=DataSourceType.MCP_TOOL,
        )

    async def _query_api_endpoint(self, source: DataSourceConfig, context: ReportContext) -> QueryResult:
        """Call external API endpoint."""
        # Would use httpx to call API
        return QueryResult(data=[], columns=[], row_count=0, source=DataSourceType.API_ENDPOINT)

    async def _query_vertical_pack(self, source: DataSourceConfig, context: ReportContext) -> QueryResult:
        """Query vertical pack metric."""
        # This would be implemented by vertical packs
        # For now, return empty
        return QueryResult(data=[], columns=[], row_count=0, source=DataSourceType.VERTICAL_PACK)

    # ========================================================================
    # Data Transformation Helpers
    # ========================================================================

    def _apply_filters(self, data: List[Dict[str, Any]], filters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply filters to data."""
        if not filters:
            return data
        
        result = data
        for f in filters:
            field = f.get("field")
            operator = f.get("operator", "eq")
            value = f.get("value")
            
            if not field:
                continue
            
            if operator == "eq":
                result = [r for r in result if r.get(field) == value]
            elif operator == "neq":
                result = [r for r in result if r.get(field) != value]
            elif operator == "gt":
                result = [r for r in result if (r.get(field) or 0) > value]
            elif operator == "gte":
                result = [r for r in result if (r.get(field) or 0) >= value]
            elif operator == "lt":
                result = [r for r in result if (r.get(field) or 0) < value]
            elif operator == "lte":
                result = [r for r in result if (r.get(field) or 0) <= value]
            elif operator == "in":
                result = [r for r in result if r.get(field) in value]
            elif operator == "not_in":
                result = [r for r in result if r.get(field) not in value]
            elif operator == "contains":
                result = [r for r in result if value in str(r.get(field, ""))]
            elif operator == "between":
                if isinstance(value, (list, tuple)) and len(value) == 2:
                    result = [r for r in result if value[0] <= (r.get(field) or 0) <= value[1]]
        
        return result

    def _group_data(
        self,
        data: List[Dict[str, Any]],
        group_by: List[str],
        metrics: List[str],
    ) -> List[Dict[str, Any]]:
        """Group data by fields and aggregate metrics."""
        if not group_by:
            return data
        
        groups: Dict[tuple, Dict[str, Any]] = {}
        
        for row in data:
            key = tuple(row.get(g) for g in group_by)
        if key not in groups:
                groups[key] = {g: row.get(g) for g in group_by}
                for m in metrics:
                    groups[key][m] = 0
            
        for m in metrics:
                val = row.get(m)
                if val is not None:
                    try:
                        groups[key][m] += float(val)
                    except (TypeError, ValueError):
                        pass
        
        return list(groups.values())

    def _order_data(self, data: List[Dict[str, Any]], order_by: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Order data by fields."""
        if not order_by:
            return data
        
        def sort_key(row):
            keys = []
            for o in order_by:
                field = o.get("field")
                direction = o.get("dir", "asc")
                val = row.get(field, 0)
                if direction == "desc":
                    val = -val if isinstance(val, (int, float)) else val
                keys.append(val)
            return tuple(keys)
        return sorted(data, key=sort_key)
        return sorted(data, key=sort_key)

    # ========================================================================
    # Report Rendering
    # ========================================================================

    async def _render_report(self, context: ReportContext) -> RenderedReport:
        """Render all sections and widgets."""
        rendered_sections = []
        total_widgets = 0
        failed_widgets = 0
        total_data_rows = 0
        total_render_time = 0
        
        for section in context.report.sections:
            # Check section conditions
            if not self._evaluate_conditions(section.conditions, context):
                continue
            
            rendered_widgets = []
            
            for widget in section.widgets:
                    # Check widget conditions
                    if not self._evaluate_conditions(widget.config.conditions, context):
                        continue
                
                    try:
                        rendered = await self.widget_renderer.render(widget, context)
                        rendered_widgets.append(rendered)
                        total_widgets += 1
                        total_data_rows += rendered.data_rows
                        total_render_time += rendered.render_time_ms
                    
                        if rendered.errors:
                            failed_widgets += 1
                        
                    except Exception as e:
                        log.exception("widget_render_failed", widget_id=widget.id, error=str(e))
                        failed_widgets += 1
                        rendered_widgets.append(RenderedWidget(
                            widget_id=widget.id,
                            type=widget.config.type,
                            title=widget.config.title,
                            errors=[str(e)],
                        ))
            
            rendered_sections.append(RenderedSection(
                section_id=section.id,
                title=section.title,
                widgets=rendered_widgets,
                content=section.content,
                page_break_before=section.page_break_before,
            ))
        
        # Generate AI summary if enabled
        ai_summary = None
        if self.ai_service and context.report.tags and "ai_summary" in context.report.tags:
            ai_summary = await self._generate_ai_summary(context, rendered_sections)
        
        return RenderedReport(
        report_id=context.report.id,
            run_id=context.run.id,
            name=context.report.name,
            generated_at=datetime.utcnow(),
            sections=rendered_sections,
            total_widgets=total_widgets,
            failed_widgets=failed_widgets,
            total_data_rows=total_data_rows,
            total_render_time_ms=total_render_time,
            ai_summary=ai_summary,
            export_options=context.export_options,
        )

    def _evaluate_conditions(self, conditions: List[Dict[str, Any]], context: ReportContext) -> bool:
        """Evaluate display conditions."""
        if not conditions:
            return True
        
        for cond in conditions:
            field = cond.get("field")
            operator = cond.get("operator", "eq")
            value = cond.get("value")
            
            # Get value from context
            actual = None
            if field == "client_id":
                actual = str(context.client_ids[0]) if context.client_ids else None
            elif field in context.data_cache:
                actual = context.data_cache[field]
            elif hasattr(context.report, field):
                actual = getattr(context.report, field)
            
            # Evaluate
            if operator == "eq" and actual != value:
                return False
            elif operator == "neq" and actual == value:
                return False
            elif operator == "gt" and (actual or 0) <= value:
                return False
            elif operator == "gte" and (actual or 0) < value:
                return False
            elif operator == "lt" and (actual or 0) >= value:
                return False
            elif operator == "lte" and (actual or 0) > value:
                return False
        
        return True

    async def _generate_ai_summary(
        self,
        context: ReportContext,
        sections: List[RenderedSection],
    ) -> Optional[str]:
        """Generate AI summary of the report."""
        if not self.ai_service:
            return None
        
        # Prepare data for AI
        summary_data = {
            "report_name": context.report.name,
            "date_range": context.date_range,
            "sections": [],
        }
        
        for section in sections:
            section_data = {
                "title": section.title,
                "widgets": [],
            }
        for widget in section.widgets:
            if widget.data:
                section_data["widgets"].append({
                    "title": widget.title,
                    "type": widget.type.value,
                    "row_count": widget.data_rows,
                    "sample": widget.data[:3] if widget.data else [],
                })
        summary_data["sections"].append(section_data)
        
        prompt = f"""
        Generate an executive summary for this analytics report:
        {json.dumps(summary_data, indent=2, default=str)}
        
        Focus on:
        1. Key metrics and trends
        2. Anomalies or significant changes
        3. Actionable recommendations
        Keep it concise (2-3 paragraphs).
        """
        
        try:
            response = await self.ai_service.generate(prompt)
            return response.text
        except Exception as e:
            log.warning("ai_summary_failed", error=str(e))
        return None

    # ========================================================================
    # Export
    # ========================================================================

    async def _export_report(
        self,
        rendered: RenderedReport,
        formats: List[ExportFormat],
    ) -> List[Dict[str, Any]]:
        """Export rendered report to multiple formats."""
        output_files = []
        
        for fmt in formats:
            try:
                if fmt == ExportFormat.PDF:
                    file_info = await self.pdf_exporter.export(rendered, self.output_dir)
                elif fmt == ExportFormat.HTML:
                    file_info = await self.html_exporter.export(rendered, self.output_dir)
                elif fmt == ExportFormat.CSV:
                    file_info = await self.csv_exporter.export(rendered, self.output_dir)
                elif fmt == ExportFormat.JSON:
                    file_info = await self.json_exporter.export(rendered, self.output_dir)
                else:
                    continue
                
                output_files.append(file_info)
                
            except Exception as e:
                log.exception("export_failed", format=fmt.value, error=str(e))
        
        return output_files

    async def _deliver_report(
        self,
        report: ReportDefinition,
        run: ReportRun,
        output_files: List[Dict[str, Any]],
    ):
        """Deliver report via email, Slack, webhooks."""
        # Email delivery
        if report.recipients:
            await self._send_email(report, run, output_files, report.recipients)
        
        # Slack delivery
        if report.slack_channels:
            await self._send_slack(report, run, output_files, report.slack_channels)
        
        # Webhook delivery
        if report.webhook_urls:
            await self._send_webhooks(report, run, output_files, report.webhook_urls)

    async def _send_email(
        self,
        report: ReportDefinition,
        run: ReportRun,
        output_files: List[Dict[str, Any]],
        recipients: List[str],
    ):
        """Send report via email."""
        # Would integrate with shared.email_marketing or shared.email_outbox
        pass

    async def _send_slack(
        self,
        report: ReportDefinition,
        run: ReportRun,
        output_files: List[Dict[str, Any]],
        channels: List[str],
    ):
        """Send report to Slack channels."""
        # Would integrate with shared.webhooks or Slack SDK
        pass

    async def _send_webhooks(
        self,
        report: ReportDefinition,
        run: ReportRun,
        output_files: List[Dict[str, Any]],
        urls: List[str],
    ):
        """Send report to webhook URLs."""
        # Would use shared.webhooks
        pass

    # ========================================================================
    # Schedule Management
    # ========================================================================

    def create_schedule(self, schedule: ReportSchedule) -> ReportSchedule:
        if not schedule.id:
            schedule.id = f"sched_{uuid.uuid4().hex[:8]}"
        schedule.created_at = datetime.utcnow()
        schedule.updated_at = datetime.utcnow()
        self._schedules[schedule.id] = schedule
        return schedule

    def get_schedule(self, schedule_id: str) -> Optional[ReportSchedule]:
        return self._schedules.get(schedule_id)

    def list_schedules(self, report_id: Optional[str] = None, active_only: bool = True) -> List[ReportSchedule]:
        schedules = list(self._schedules.values())
        if report_id:
            schedules = [s for s in schedules if s.report_id == report_id]
        if active_only:
            schedules = [s for s in schedules if s.is_active]
        return schedules

    def delete_schedule(self, schedule_id: str) -> bool:
        if schedule_id in self._schedules:
            del self._schedules[schedule_id]
        return True
        return False

    # ========================================================================
    # Run History
    # ========================================================================

    def get_run(self, run_id: str) -> Optional[ReportRun]:
        return self._runs.get(run_id)

    def list_runs(
        self,
        report_id: Optional[str] = None,
        status: Optional[RunStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ReportRun]:
        runs = list(self._runs.values())
        
        if report_id:
            runs = [r for r in runs if r.report_id == report_id]
        if status:
            runs = [r for r in runs if r.status == status]
        
        runs.sort(key=lambda r: r.created_at, reverse=True)
        return runs[offset:offset + limit]

    # ========================================================================
    # Ad-hoc Query (for API/exploration)
    # ========================================================================

    async def execute_query(
        self,
        source: DataSourceConfig,
        client_ids: Optional[List[UUID]] = None,
        date_range: Optional[Dict[str, Any]] = None,
    ) -> QueryResult:
        """Execute an ad-hoc query."""
        context = ReportContext(
        report=ReportDefinition(id="adhoc", name="Ad-hoc Query"),
            run=ReportRun(id="adhoc", report_id="adhoc", report_name="Ad-hoc"),
        client_ids=client_ids or [],
        date_range=date_range or {},
            daily_facts_service=self.daily_facts,
            analytics_service=self.analytics_service,
        )
        return await self._execute_data_source(source, context)