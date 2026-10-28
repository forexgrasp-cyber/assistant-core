"""
Reporting Engine Models

Dynamic, configuration-driven report definitions that integrate with
shared analytics services.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Literal, Union
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing_extensions import Annotated


class ExportFormat(str, Enum):
    PDF = "pdf"
    HTML = "html"
    CSV = "csv"
    JSON = "json"
    XLSX = "xlsx"
    MARKDOWN = "md"


class ReportStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class RunStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WidgetType(str, Enum):
    # Charts
    LINE_CHART = "line_chart"
    BAR_CHART = "bar_chart"
    AREA_CHART = "area_chart"
    PIE_CHART = "pie_chart"
    DONUT_CHART = "donut_chart"
    SCATTER_PLOT = "scatter_plot"
    HEATMAP = "heatmap"
    FUNNEL_CHART = "funnel_chart"
    COHORT_HEATMAP = "cohort_heatmap"
    # Tables
    DATA_TABLE = "data_table"
    PIVOT_TABLE = "pivot_table"
    SUMMARY_TABLE = "summary_table"
    # Metrics
    KPI_CARD = "kpi_card"
    METRIC_CARD = "metric_card"
    GAUGE = "gauge"
    PROGRESS_BAR = "progress_bar"
    # Text
    MARKDOWN = "markdown"
    TEXT_BLOCK = "text_block"
    AI_SUMMARY = "ai_summary"
    # Special
    IMAGE = "image"
    IFRAME = "iframe"
    CUSTOM = "custom"


class DataSourceType(str, Enum):
    DAILY_FACTS = "daily_facts"           # shared.analytics.daily_facts
    PROGRAM_REVENUE = "program_revenue"   # shared.analytics.daily_facts
    DIMENSION_FACTS = "dimension_facts"   # shared.analytics.daily_facts
    PAYMENT_FACTS = "payment_facts"       # shared.analytics.daily_facts
    REVENUE_EVENTS = "revenue_events"     # shared.analytics.analytics_service
    USAGE_EVENTS = "usage_events"         # shared.analytics.analytics_service
    CUSTOM_SQL = "custom_sql"
    MCP_TOOL = "mcp_tool"
    API_ENDPOINT = "api_endpoint"
    VERTICAL_PACK = "vertical_pack"


class AggregationType(str, Enum):
    SUM = "sum"
    AVG = "avg"
    COUNT = "count"
    MIN = "min"
    MAX = "max"
    MEDIAN = "median"
    PERCENTILE_90 = "p90"
    PERCENTILE_95 = "p95"
    RATE = "rate"
    DELTA = "delta"
    PCT_CHANGE = "pct_change"
    RUNNING_TOTAL = "running_total"
    MOVING_AVG = "moving_avg"


class TimeGrain(str, Enum):
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


class FilterOperator(str, Enum):
    EQ = "eq"
    NEQ = "neq"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    REGEX = "regex"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    BETWEEN = "between"


class FilterConfig(BaseModel):
    """Filter configuration for data queries."""
    field: str
    operator: FilterOperator
    value: Any


class DateRangeConfig(BaseModel):
    """Date range configuration for queries."""
    start: Optional[str] = None
    end: Optional[str] = None
    days: Optional[int] = None
    grain: Optional[str] = None  # hour, day, week, month, quarter, year


class OrderByConfig(BaseModel):
    """Order by configuration for queries."""
    field: str
    dir: Literal["asc", "desc"] = "asc"


class DataSourceConfig(BaseModel):
    """Configuration for a data source."""
    type: DataSourceType
    # For daily_facts / program_revenue / dimension_facts / payment_facts
    metrics: List[str] = Field(default_factory=list)
    dimensions: List[str] = Field(default_factory=list)
    filters: List[Dict[str, Any]] = Field(default_factory=list)
    date_range: Optional[Dict[str, Any]] = None  # {start, end, days, grain}
    group_by: List[str] = Field(default_factory=list)
    order_by: List[Dict[str, str]] = Field(default_factory=list)  # [{field, dir}]
    limit: Optional[int] = None
    # For custom_sql
    query: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)
    # For mcp_tool
    tool_name: Optional[str] = None
    tool_params: Dict[str, Any] = Field(default_factory=dict)
    # For api_endpoint
    endpoint: Optional[str] = None
    method: str = "GET"
    headers: Dict[str, str] = Field(default_factory=dict)
    # For vertical_pack
    vertical: Optional[str] = None
    pack_metric: Optional[str] = None


class WidgetConfig(BaseModel):
    """Widget visualization configuration."""
    type: WidgetType
    title: str
    subtitle: Optional[str] = None
    # Data
    data_source: DataSourceConfig
    # Transformations
    transformations: List[Dict[str, Any]] = Field(default_factory=list)
    # Visual
    width: int = 12  # 1-12 grid columns
    height: Optional[int] = None
    options: Dict[str, Any] = Field(default_factory=dict)
    # Conditional display
    conditions: List[Dict[str, Any]] = Field(default_factory=list)
    # Drill-down
    drill_down: Optional[Dict[str, Any]] = None
    # AI enhancement
    ai_summary: bool = False
    ai_prompt: Optional[str] = None


class KPICardProps(BaseModel):
    """KPI Card widget properties."""
    title: str
    value: Union[str, float, int]
    format: Literal["currency", "number", "percent", "ratio"] = "number"
    trend: Optional[float] = None
    trend_direction: Optional[Literal["up", "down", "flat"]] = None
    subtitle: Optional[str] = None
    icon: Optional[str] = None


class WidgetDefinition(BaseModel):
    """Complete widget definition."""
    id: str = Field(default_factory=lambda: f"widget_{uuid.uuid4().hex[:8]}")
    config: WidgetConfig
    # Layout
    x: int = 0
    y: int = 0
    w: int = 12
    h: int = 6
    # Metadata
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class DashboardDefinition(BaseModel):
    """Dashboard layout and widgets."""
    id: str = Field(default_factory=lambda: f"dash_{uuid.uuid4().hex[:8]}")
    name: str
    description: Optional[str] = None
    # Layout
    layout: Literal["grid", "freeform", "tabs"] = "grid"
    columns: int = 12
    row_height: int = 50
    # Widgets
    widgets: List[WidgetDefinition] = Field(default_factory=list)
    # Global filters (applied to all widgets)
    global_filters: List[Dict[str, Any]] = Field(default_factory=list)
    # Refresh
    auto_refresh_seconds: Optional[int] = None
    # Metadata
    tags: List[str] = Field(default_factory=list)
    is_template: bool = False
    created_by: Optional[UUID] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ReportSection(BaseModel):
    """A section within a report."""
    id: str = Field(default_factory=lambda: f"section_{uuid.uuid4().hex[:8]}")
    title: str
    description: Optional[str] = None
    # Widgets in this section
    widgets: List[WidgetDefinition] = Field(default_factory=list)
    # Or inline content
    content: Optional[str] = None  # Markdown/HTML
    # Page break before
    page_break_before: bool = False
    # Conditions
    conditions: List[Dict[str, Any]] = Field(default_factory=list)


class ReportTemplate(BaseModel):
    """Reusable report template."""
    id: str = Field(default_factory=lambda: f"tmpl_{uuid.uuid4().hex[:8]}")
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    # Structure
    sections: List[ReportSection] = Field(default_factory=list)
    # Default filters
    default_filters: List[Dict[str, Any]] = Field(default_factory=list)
    # Default schedule
    default_schedule: Optional[str] = None  # cron
    # Export defaults
    default_formats: List[ExportFormat] = Field(default_factory=lambda: [ExportFormat.PDF])
    # Metadata
    tags: List[str] = Field(default_factory=list)
    vertical: Optional[str] = None
    is_system: bool = False
    created_by: Optional[UUID] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ReportDefinition(BaseModel):
    """Complete report definition (instance of a template with overrides)."""
    id: str = Field(default_factory=lambda: f"rpt_{uuid.uuid4().hex[:8]}")
    name: str
    description: Optional[str] = None
    # Template reference
    template_id: Optional[str] = None
    # Structure (overrides template)
    sections: List[ReportSection] = Field(default_factory=list)
    # Filters (merged with template defaults)
    filters: List[Dict[str, Any]] = Field(default_factory=list)
    # Schedule
    schedule: Optional[str] = None  # cron expression
    timezone: str = "UTC"
    # Export
    formats: List[ExportFormat] = Field(default_factory=lambda: [ExportFormat.PDF])
    export_options: Dict[str, Any] = Field(default_factory=dict)
    # Recipients
    recipients: List[str] = Field(default_factory=list)  # emails
    slack_channels: List[str] = Field(default_factory=list)
    webhook_urls: List[str] = Field(default_factory=list)
    # Access
    client_ids: List[UUID] = Field(default_factory=list)  # empty = all clients
    is_public: bool = False
    # Status
    status: ReportStatus = ReportStatus.DRAFT
    # Metadata
    tags: List[str] = Field(default_factory=list)
    vertical: Optional[str] = None
    created_by: Optional[UUID] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None


class ReportRun(BaseModel):
    """A single execution of a report."""
    id: str = Field(default_factory=lambda: f"run_{uuid.uuid4().hex[:8]}")
    report_id: str
    report_name: str
    # Trigger
    triggered_by: Literal["schedule", "manual", "api", "webhook"] = "manual"
    triggered_by_user: Optional[UUID] = None
    # Parameters
    parameters: Dict[str, Any] = Field(default_factory=dict)
    filters_applied: List[Dict[str, Any]] = Field(default_factory=list)
    date_range: Optional[Dict[str, str]] = None
    # Status
    status: RunStatus = RunStatus.PENDING
    progress: float = 0.0
    current_step: Optional[str] = None
    # Output
    output_files: List[Dict[str, Any]] = Field(default_factory=list)  # [{format, url, size, path}]
    # Stats
    widgets_rendered: int = 0
    widgets_failed: int = 0
    data_rows_processed: int = 0
    render_time_ms: int = 0
    total_time_ms: int = 0
    # Errors
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ReportSchedule(BaseModel):
    """Scheduled report configuration."""
    id: str = Field(default_factory=lambda: f"sched_{uuid.uuid4().hex[:8]}")
    report_id: str
    cron_expression: str
    timezone: str = "UTC"
    # Window
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    # Parameters
    default_parameters: Dict[str, Any] = Field(default_factory=dict)
    # Recipients (override report)
    recipients: List[str] = Field(default_factory=list)
    slack_channels: List[str] = Field(default_factory=list)
    webhook_urls: List[str] = Field(default_factory=list)
    # Status
    is_active: bool = True
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    run_count: int = 0
    failure_count: int = 0
    # Metadata
    created_by: Optional[UUID] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ExportOptions(BaseModel):
    """Export format specific options."""
    # PDF
    pdf_page_size: str = "A4"
    pdf_orientation: Literal["portrait", "landscape"] = "portrait"
    pdf_margins: Dict[str, str] = Field(default_factory=lambda: {"top": "20mm", "bottom": "20mm", "left": "15mm", "right": "15mm"})
    pdf_header: Optional[str] = None
    pdf_footer: Optional[str] = None
    pdf_toc: bool = True
    pdf_page_numbers: bool = True
    # HTML
    html_embed_assets: bool = True
    html_standalone: bool = True
    html_theme: Optional[str] = None
    # CSV
    csv_delimiter: str = ","
    csv_encoding: str = "utf-8"
    csv_include_header: bool = True
    # General
    timezone: str = "UTC"
    locale: str = "en_US"
    currency: str = "USD"
    number_format: Dict[str, Any] = Field(default_factory=dict)
    date_format: str = "%Y-%m-%d"
    datetime_format: str = "%Y-%m-%d %H:%M:%S"


class ReportContext(BaseModel):
    """Runtime context for report generation."""
    report: ReportDefinition
    run: ReportRun
    # Resolved data
    client_ids: List[UUID] = Field(default_factory=list)
    agency_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    # Time
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    date_range: Dict[str, str] = Field(default_factory=dict)
    timezone: str = "UTC"
    # Services (injected at runtime)
    daily_facts_service: Any = None
    analytics_service: Any = None
    collector: Any = None
    mcp_client: Any = None
    ai_service: Any = None
    # Cache
    data_cache: Dict[str, Any] = Field(default_factory=dict)
    # Export
    export_options: ExportOptions = Field(default_factory=ExportOptions)


class QueryResult(BaseModel):
    """Result of a data query."""
    data: List[Dict[str, Any]] = Field(default_factory=list)
    columns: List[str] = Field(default_factory=list)
    row_count: int = 0
    execution_time_ms: int = 0
    query: Optional[str] = None
    source: Optional[DataSourceType] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RenderedWidget(BaseModel):
    """A widget after rendering."""
    widget_id: str
    type: WidgetType
    title: str
    # Rendered output
    html: Optional[str] = None
    markdown: Optional[str] = None
    data: Optional[List[Dict[str, Any]]] = None
    chart_config: Optional[Dict[str, Any]] = None
    # Metadata
    render_time_ms: int = 0
    data_rows: int = 0
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class RenderedSection(BaseModel):
    """A section after rendering."""
    section_id: str
    title: str
    widgets: List[RenderedWidget] = Field(default_factory=list)
    content: Optional[str] = None
    page_break_before: bool = False


class RenderedReport(BaseModel):
    """Fully rendered report ready for export."""
    report_id: str
    run_id: str
    name: str
    generated_at: datetime
    sections: List[RenderedSection] = Field(default_factory=list)
    # Global metadata
    total_widgets: int = 0
    failed_widgets: int = 0
    total_data_rows: int = 0
    total_render_time_ms: int = 0
    # AI summary
    ai_summary: Optional[str] = None
    # Export options
    export_options: ExportOptions = Field(default_factory=ExportOptions)


class AIReportSummary(BaseModel):
    """AI-generated report summary."""
    report_id: str
    run_id: str
    # Summary sections
    executive_summary: str
    key_findings: List[str] = Field(default_factory=list)
    anomalies: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    # Metadata
    model_used: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Pre-built Report Templates (Marketing Vertical)
# ============================================================================

MARKETING_TEMPLATES = {
    "monthly_client_report": ReportTemplate(
        id="tmpl_monthly_client",
        name="Monthly Client Report",
        description="Comprehensive monthly performance report for a client",
        category="marketing",
        vertical="marketing",
        sections=[
            ReportSection(
                title="Executive Summary",
                widgets=[
                    WidgetDefinition(config=WidgetConfig(
                        type=WidgetType.KPI_CARD,
                        title="Attributed Revenue",
                        data_source=DataSourceConfig(
                            type=DataSourceType.DAILY_FACTS,
                            metrics=["aff_revenue", "adsense_revenue", "lead_value"],
                            date_range={"days": 30, "grain": "day"},
                        ),
                        options={"format": "currency", "trend": True},
                    )),
                    WidgetDefinition(config=WidgetConfig(
                        type=WidgetType.KPI_CARD,
                        title="Total Sessions",
                        data_source=DataSourceConfig(
                            type=DataSourceType.DAILY_FACTS,
                            metrics=["sessions"],
                            date_range={"days": 30, "grain": "day"},
                        ),
                        options={"format": "number", "trend": True},
                    )),
                    WidgetDefinition(config=WidgetConfig(
                        type=WidgetType.KPI_CARD,
                        title="Conversions",
                        data_source=DataSourceConfig(
                            type=DataSourceType.DAILY_FACTS,
                            metrics=["conversions", "aff_conversions"],
                            date_range={"days": 30, "grain": "day"},
                        ),
                        options={"format": "number", "trend": True},
                    )),
                    WidgetDefinition(config=WidgetConfig(
                        type=WidgetType.KPI_CARD,
                        title="ROAS",
                        data_source=DataSourceConfig(
                            type=DataSourceType.DAILY_FACTS,
                            metrics=["aff_revenue"],
                            date_range={"days": 30, "grain": "day"},
                        ),
                        options={"format": "ratio", "trend": True},
                    )),
                ],
            ),
            ReportSection(
                title="Traffic & Acquisition",
                widgets=[
                    WidgetDefinition(config=WidgetConfig(
                        type=WidgetType.LINE_CHART,
                        title="Daily Sessions Trend",
                        data_source=DataSourceConfig(
                            type=DataSourceType.DAILY_FACTS,
                            metrics=["sessions", "users", "new_users"],
                            dimensions=["date"],
                            date_range={"days": 30, "grain": "day"},
                            group_by=["date"],
                        ),
                        options={"x_axis": "date", "y_axis": "sessions", "series": ["sessions", "users", "new_users"]},
                    )),
                    WidgetDefinition(config=WidgetConfig(
                        type=WidgetType.PIVOT_TABLE,
                        title="Traffic by Channel",
                        data_source=DataSourceConfig(
                            type=DataSourceType.DIMENSION_FACTS,
                            metrics=["sessions", "users", "conversions"],
                            dimensions=["dim_value"],
                            filters=[{"field": "dim_type", "operator": "eq", "value": "channel"}],
                            date_range={"days": 30},
                            group_by=["dim_value"],
                        ),
                        options={"rows": ["dim_value"], "values": ["sessions", "users", "conversions"]},
                    )),
                ],
            ),
            ReportSection(
                title="Revenue Attribution",
                widgets=[
                    WidgetDefinition(config=WidgetConfig(
                        type=WidgetType.BAR_CHART,
                        title="Revenue by Source",
                        data_source=DataSourceConfig(
                            type=DataSourceType.DAILY_FACTS,
                            metrics=["aff_revenue", "adsense_revenue", "lead_value"],
                            date_range={"days": 30, "grain": "day"},
                        ),
                        options={"stacked": True, "format": "currency"},
                    )),
                    WidgetDefinition(config=WidgetConfig(
                        type=WidgetType.DATA_TABLE,
                        title="Top Affiliate Programs",
                        data_source=DataSourceConfig(
                            type=DataSourceType.PROGRAM_REVENUE,
                            metrics=["revenue", "conversions"],
                            dimensions=["program"],
                            filters=[{"field": "channel", "operator": "eq", "value": "affiliate"}],
                            date_range={"days": 30},
                            group_by=["program"],
                            order_by=[{"field": "revenue", "dir": "desc"}],
                            limit=10,
                        ),
                        options={"columns": ["program", "revenue", "conversions", "avg_order_value"]},
                    )),
                ],
            ),
            ReportSection(
                title="Campaign Performance",
                widgets=[
                    WidgetDefinition(config=WidgetConfig(
                        type=WidgetType.DATA_TABLE,
                        title="Top Campaigns by Revenue",
                        data_source=DataSourceConfig(
                            type=DataSourceType.VERTICAL_PACK,
                            vertical="marketing",
                            pack_metric="campaign_performance",
                            metrics=["attributed_revenue", "attributed_orders", "open_rate", "click_rate"],
                            dimensions=["campaign_id", "name", "type"],
                            date_range={"days": 30},
                            order_by=[{"field": "attributed_revenue", "dir": "desc"}],
                            limit=20,
                        ),
                        options={"columns": ["name", "type", "sent", "opened", "clicked", "attributed_revenue", "roas"]},
                    )),
                ],
            ),
            ReportSection(
                title="Retention & LTV",
                widgets=[
                    WidgetDefinition(config=WidgetConfig(
                        type=WidgetType.COHORT_HEATMAP,
                        title="Retention Cohorts",
                        data_source=DataSourceConfig(
                            type=DataSourceType.VERTICAL_PACK,
                            vertical="marketing",
                            pack_metric="cohort_retention",
                            metrics=["repeat_rate", "revenue_per_customer"],
                            dimensions=["cohort_month", "period"],
                            date_range={"days": 365},
                        ),
                        options={"cohort_axis": "cohort_month", "period_axis": "period", "value": "repeat_rate"},
                    )),
                    WidgetDefinition(config=WidgetConfig(
                        type=WidgetType.DATA_TABLE,
                        title="RFM Segments",
                        data_source=DataSourceConfig(
                            type=DataSourceType.VERTICAL_PACK,
                            vertical="marketing",
                            pack_metric="rfm_segments",
                            metrics=["customer_count", "total_revenue", "avg_order_value"],
                            dimensions=["segment"],
                            date_range={"days": 30},
                        ),
                        options={"columns": ["segment", "customer_count", "total_revenue", "avg_order_value", "pct_of_revenue"]},
                    )),
                ],
            ),
        ],
        default_formats=[ExportFormat.PDF, ExportFormat.HTML],
        tags=["monthly", "client-facing", "comprehensive"],
    ),

    "weekly_performance_snapshot": ReportTemplate(
        id="tmpl_weekly_snapshot",
        name="Weekly Performance Snapshot",
        description="Quick weekly overview for agency leadership",
        category="marketing",
        vertical="marketing",
        sections=[
            ReportSection(
                title="Week at a Glance",
                widgets=[
                    WidgetDefinition(config=WidgetConfig(
                        type=WidgetType.KPI_CARD,
                        title="Revenue (WoW)",
                        data_source=DataSourceConfig(
                            type=DataSourceType.DAILY_FACTS,
                            metrics=["aff_revenue", "adsense_revenue", "lead_value"],
                            date_range={"days": 7, "grain": "day"},
                        ),
                        options={"format": "currency", "compare": "previous_period", "trend": True},
                    )),
                    WidgetDefinition(config=WidgetConfig(
                        type=WidgetType.KPI_CARD,
                        title="New Conversions",
                        data_source=DataSourceConfig(
                            type=DataSourceType.DAILY_FACTS,
                            metrics=["aff_conversions", "conversions"],
                            date_range={"days": 7, "grain": "day"},
                        ),
                        options={"format": "number", "compare": "previous_period"},
                    )),
                ],
            ),
            ReportSection(
                title="Top Movers",
                widgets=[
                    WidgetDefinition(config=WidgetConfig(
                        type=WidgetType.DATA_TABLE,
                        title="Biggest Revenue Changes",
                        data_source=DataSourceConfig(
                            type=DataSourceType.DAILY_FACTS,
                            metrics=["aff_revenue"],
                            dimensions=["site"],
                            date_range={"days": 14, "grain": "day"},
                            group_by=["site"],
                            transformations=[{"type": "period_over_period", "period_days": 7}],
                        ),
                        options={"sort_by": "pct_change", "limit": 10},
                    )),
                ],
            ),
        ],
        default_formats=[ExportFormat.PDF, ExportFormat.HTML],
        default_schedule="0 6 * * 1",  # Monday 6 AM
        tags=["weekly", "leadership", "snapshot"],
    ),

    "campaign_deep_dive": ReportTemplate(
        id="tmpl_campaign_deep_dive",
        name="Campaign Deep Dive",
        description="Detailed analysis of a single campaign",
        category="marketing",
        vertical="marketing",
        sections=[
            ReportSection(
                title="Campaign Overview",
                widgets=[
                    WidgetDefinition(config=WidgetConfig(
                        type=WidgetType.KPI_CARD,
                        title="Attributed Revenue",
                        data_source=DataSourceConfig(
                            type=DataSourceType.VERTICAL_PACK,
                            vertical="marketing",
                            pack_metric="campaign_performance",
                            filters=[{"field": "campaign_id", "operator": "eq", "value": "{{campaign_id}}"}],
                        ),
                        options={"format": "currency", "prominent": True},
                    )),
                ],
            ),
            ReportSection(
                title="Engagement Funnel",
                widgets=[
                    WidgetDefinition(config=WidgetConfig(
                        type=WidgetType.FUNNEL_CHART,
                        title="Email Funnel",
                        data_source=DataSourceConfig(
                            type=DataSourceType.VERTICAL_PACK,
                            vertical="marketing",
                            pack_metric="campaign_performance",
                            filters=[{"field": "campaign_id", "operator": "eq", "value": "{{campaign_id}}"}],
                        ),
                        options={"stages": ["sent", "delivered", "opened", "clicked", "converted"]},
                    )),
                ],
            ),
            ReportSection(
                title="Creative Performance",
                widgets=[
                    WidgetDefinition(config=WidgetConfig(
                        type=WidgetType.DATA_TABLE,
                        title="A/B Variants",
                        data_source=DataSourceConfig(
                            type=DataSourceType.VERTICAL_PACK,
                            vertical="marketing",
                            pack_metric="campaign_variants",
                            filters=[{"field": "campaign_id", "operator": "eq", "value": "{{campaign_id}}"}],
                        ),
                        options={"columns": ["variant", "subject", "sent", "open_rate", "click_rate", "revenue"]},
                    )),
                ],
            ),
        ],
        default_formats=[ExportFormat.PDF, ExportFormat.HTML],
        tags=["campaign", "deep-dive", "creative"],
    ),
}

ECOMMERCE_TEMPLATES = {
    "monthly_store_report": ReportTemplate(
        id="tmpl_monthly_store",
        name="Monthly Store Report",
        description="Ecommerce store performance report",
        category="ecommerce",
        vertical="ecommerce",
        sections=[
            ReportSection(
                title="Revenue Overview",
                widgets=[
                    WidgetDefinition(config=WidgetConfig(
                        type=WidgetType.KPI_CARD,
                        title="Total Revenue",
                        data_source=DataSourceConfig(
                            type=DataSourceType.VERTICAL_PACK,
                            vertical="ecommerce",
                            pack_metric="ecommerce_revenue",
                            date_range={"days": 30},
                        ),
                        options={"format": "currency", "trend": True},
                    )),
                    WidgetDefinition(config=WidgetConfig(
                        type=WidgetType.KPI_CARD,
                        title="Orders",
                        data_source=DataSourceConfig(
                            type=DataSourceType.VERTICAL_PACK,
                            vertical="ecommerce",
                            pack_metric="orders",
                            date_range={"days": 30},
                        ),
                        options={"format": "number", "trend": True},
                    )),
                    WidgetDefinition(config=WidgetConfig(
                        type=WidgetType.KPI_CARD,
                        title="AOV",
                        data_source=DataSourceConfig(
                            type=DataSourceType.VERTICAL_PACK,
                            vertical="ecommerce",
                            pack_metric="aov",
                            date_range={"days": 30},
                        ),
                        options={"format": "currency", "trend": True},
                    )),
                    WidgetDefinition(config=WidgetConfig(
                        type=WidgetType.KPI_CARD,
                        title="Conversion Rate",
                        data_source=DataSourceConfig(
                            type=DataSourceType.VERTICAL_PACK,
                            vertical="ecommerce",
                            pack_metric="conversion_rate",
                            date_range={"days": 30},
                        ),
                        options={"format": "percent", "trend": True},
                    )),
                ],
            ),
            ReportSection(
                title="Product Performance",
                widgets=[
                    WidgetDefinition(config=WidgetConfig(
                        type=WidgetType.DATA_TABLE,
                        title="Top Products by Revenue",
                        data_source=DataSourceConfig(
                            type=DataSourceType.VERTICAL_PACK,
                            vertical="ecommerce",
                            pack_metric="product_performance",
                            metrics=["revenue", "units_sold", "orders", "conversion_rate"],
                            dimensions=["product_id", "name", "category"],
                            date_range={"days": 30},
                            order_by=[{"field": "revenue", "dir": "desc"}],
                            limit=20,
                        ),
                        options={"columns": ["name", "category", "revenue", "units_sold", "orders", "conversion_rate"]},
                    )),
                ],
            ),
        ],
        default_formats=[ExportFormat.PDF, ExportFormat.HTML],
        tags=["monthly", "ecommerce", "store"],
    ),
}

SAAS_TEMPLATES = {
    "monthly_saas_report": ReportTemplate(
        id="tmpl_monthly_saas",
        name="Monthly SaaS Report",
        description="SaaS metrics: MRR, churn, LTV, expansion",
        category="saas",
        vertical="saas",
        sections=[
            ReportSection(
                title="MRR Overview",
                widgets=[
                    WidgetDefinition(config=WidgetConfig(
                        type=WidgetType.KPI_CARD,
                        title="MRR",
                        data_source=DataSourceConfig(
                            type=DataSourceType.VERTICAL_PACK,
                            vertical="saas",
                            pack_metric="mrr",
                            date_range={"days": 30},
                        ),
                        options={"format": "currency", "trend": True, "prominent": True},
                    )),
                    WidgetDefinition(config=WidgetConfig(
                        type=WidgetType.KPI_CARD,
                        title="Churn Rate",
                        data_source=DataSourceConfig(
                            type=DataSourceType.VERTICAL_PACK,
                            vertical="saas",
                            pack_metric="churn_rate",
                            date_range={"days": 30},
                        ),
                        options={"format": "percent", "trend": True, "inverse": True},
                    )),
                    WidgetDefinition(config=WidgetConfig(
                        type=WidgetType.KPI_CARD,
                        title="LTV:CAC",
                        data_source=DataSourceConfig(
                            type=DataSourceType.VERTICAL_PACK,
                            vertical="saas",
                            pack_metric="ltv_cac_ratio",
                            date_range={"days": 90},
                        ),
                        options={"format": "ratio", "trend": True},
                    )),
                    WidgetDefinition(config=WidgetConfig(
                        type=WidgetType.KPI_CARD,
                        title="Net Revenue Retention",
                        data_source=DataSourceConfig(
                            type=DataSourceType.VERTICAL_PACK,
                            vertical="saas",
                            pack_metric="nrr",
                            date_range={"days": 90},
                        ),
                        options={"format": "percent", "trend": True},
                    )),
                ],
            ),
            ReportSection(
                title="MRR Components",
                widgets=[
                    WidgetDefinition(config=WidgetConfig(
                        type=WidgetType.BAR_CHART,
                        title="MRR Movement",
                        data_source=DataSourceConfig(
                            type=DataSourceType.VERTICAL_PACK,
                            vertical="saas",
                            pack_metric="mrr_movement",
                            metrics=["new_mrr", "expansion_mrr", "contraction_mrr", "churned_mrr", "reactivation_mrr"],
                            dimensions=["date"],
                            date_range={"days": 90, "grain": "month"},
                            group_by=["date"],
                        ),
                        options={"stacked": True, "format": "currency", "waterfall": True},
                    )),
                ],
            ),
            ReportSection(
                title="Churn Analysis",
                widgets=[
                    WidgetDefinition(config=WidgetConfig(
                        type=WidgetType.COHORT_HEATMAP,
                        title="Churn by Cohort",
                        data_source=DataSourceConfig(
                            type=DataSourceType.VERTICAL_PACK,
                            vertical="saas",
                            pack_metric="churn_cohorts",
                            metrics=["churn_rate", "logo_churn", "revenue_churn"],
                            dimensions=["cohort_month", "period"],
                            date_range={"days": 365},
                        ),
                        options={"value": "churn_rate", "format": "percent"},
                    )),
                ],
            ),
        ],
        default_formats=[ExportFormat.PDF, ExportFormat.HTML],
        tags=["monthly", "saas", "board-ready"],
    ),
}

ALL_TEMPLATES = {
    **MARKETING_TEMPLATES,
    **ECOMMERCE_TEMPLATES,
    **SAAS_TEMPLATES,
}