"""
Tests for Reporting Engine
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from reporting_engine import (
    ReportingEngine,
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
    QueryResult,
    RenderedReport,
    RenderedSection,
    RenderedWidget,
    KPICardProps,
)
from reporting_engine.models import (
    ReportSection,
    WidgetType,
    FilterConfig,
    FilterOperator,
    DateRangeConfig,
    OrderByConfig,
    ExportOptions,
)
from reporting_engine.components import WidgetRenderer, ChartRenderer, TableRenderer
from reporting_engine.exporters import HTMLExporter, PDFExporter, CSVExporter, JSONExporter


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_daily_facts():
    """Mock DailyFactsService."""
    mock = AsyncMock()
    mock.sites.return_value = ["client1", "client2", "__all__"]
    mock.get_series.return_value = [
        {"date": "2024-01-01", "aff_revenue": 1000, "sessions": 100, "conversions": 5},
        {"date": "2024-01-02", "aff_revenue": 1200, "sessions": 120, "conversions": 6},
        {"date": "2024-01-03", "aff_revenue": 1100, "sessions": 110, "conversions": 5},
    ]
    mock.program_detail.return_value = [
        {"date": "2024-01-01", "program": "prog1", "revenue": 500, "conversions": 3},
    ]
    mock.breakdown_counts.return_value = [
        {"label": "email", "values": {"sessions": 50}},
        {"label": "sms", "values": {"sessions": 30}},
    ]
    mock.payment_facts.return_value = []
    mock.upsert_facts.return_value = 1
    mock.upsert_many.return_value = 3
    mock.record_program_revenue.return_value = None
    return mock


@pytest.fixture
def mock_analytics_service():
    """Mock AnalyticsService."""
    mock = AsyncMock()
    mock.get_revenue_summary.return_value = MagicMock(
        success=True,
        data={
            "total_usd": 10000,
            "total_sales": 100,
            "by_source": {"email": {"amount": 6000, "count": 60}},
            "by_product": {},
        }
    )
    return mock


@pytest.fixture
def engine(mock_daily_facts, mock_analytics_service):
    """Create ReportingEngine with mocked dependencies."""
    with patch('reporting_engine.service.DailyFactsService', return_value=mock_daily_facts), \
         patch('reporting_engine.service.AnalyticsService', return_value=mock_analytics_service):
        engine = ReportingEngine()
        engine.daily_facts = mock_daily_facts
        engine.analytics_service = mock_analytics_service
        return engine


@pytest.fixture
def sample_report():
    """Create a sample report definition."""
    return ReportDefinition(
        id="test-report-1",
        name="Test Monthly Report",
        description="A test report",
        template_id="tmpl_monthly_client",
        sections=[
            ReportSection(
                id="section-1",
                title="KPIs",
                widgets=[
                    WidgetDefinition(
                        id="widget-1",
                        config=WidgetConfig(
                            type=WidgetType.KPI_CARD,
                            title="Revenue",
                            data_source=DataSourceConfig(
                                type=DataSourceType.DAILY_FACTS,
                                metrics=["aff_revenue"],
                                date_range={"days": 30},
                            ),
                            options={"format": "currency"},
                        ),
                    ),
                ],
            ),
        ],
        filters=[],
        schedule="0 6 1 * *",
        formats=[ExportFormat.PDF, ExportFormat.HTML],
        status=ReportStatus.ACTIVE,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_template():
    """Create a sample template."""
    return ReportTemplate(
        id="tmpl_test",
        name="Test Template",
        description="A test template",
        category="test",
        sections=[
            ReportSection(
                id="section-1",
                title="Overview",
                widgets=[
                    WidgetDefinition(
                        id="widget-1",
                        config=WidgetConfig(
                            type=WidgetType.KPI_CARD,
                            title="Test KPI",
                            data_source=DataSourceConfig(
                                type=DataSourceType.DAILY_FACTS,
                                metrics=["sessions"],
                            ),
                        ),
                    ),
                ],
            ),
        ],
        default_formats=[ExportFormat.PDF],
    )


# ============================================================================
# Model Tests
# ============================================================================

class TestModels:
    """Test data models."""

    def test_report_definition_creation(self):
        """Test ReportDefinition can be created with all fields."""
        report = ReportDefinition(
            name="Test Report",
            sections=[],
        )
        assert report.name == "Test Report"
        assert report.status == ReportStatus.DRAFT
        assert report.formats == [ExportFormat.PDF]

    def test_widget_config_validation(self):
        """Test WidgetConfig validates data source."""
        config = WidgetConfig(
            type=WidgetType.LINE_CHART,
            title="Test Chart",
            data_source=DataSourceConfig(
                type=DataSourceType.DAILY_FACTS,
                metrics=["sessions", "users"],
                date_range={"days": 30},
            ),
        )
        assert config.type == WidgetType.LINE_CHART
        assert config.data_source.metrics == ["sessions", "users"]

    def test_data_source_config_defaults(self):
        """Test DataSourceConfig defaults."""
        source = DataSourceConfig(type=DataSourceType.DAILY_FACTS)
        assert source.metrics == []
        assert source.filters == []
        assert source.group_by == []

    def test_export_options_defaults(self):
        """Test ExportOptions defaults."""
        opts = ExportOptions()
        assert opts.pdf_page_size == "A4"
        assert opts.pdf_orientation == "portrait"
        assert opts.csv_delimiter == ","

    def test_report_schedule_cron(self):
        """Test ReportSchedule cron expression."""
        schedule = ReportSchedule(
            report_id="test-report",
            cron_expression="0 6 * * 1",  # Monday 6 AM
            timezone="UTC",
        )
        assert schedule.cron_expression == "0 6 * * 1"
        assert schedule.timezone == "UTC"


# ============================================================================
# Engine Tests
# ============================================================================

class TestReportingEngine:
    """Test ReportingEngine core functionality."""

    @pytest.mark.asyncio
    async def test_create_report(self, engine, sample_template):
        """Test creating a report from template."""
        engine._templates[sample_template.id] = sample_template
        
        report = engine.create_report_from_template(
            template_id=sample_template.id,
            name="My Report",
            client_ids=[uuid4()],
        )
        
        assert report.name == "My Report"
        assert report.template_id == sample_template.id
        assert report.id in engine._reports

    @pytest.mark.asyncio
    async def test_create_report_invalid_template(self, engine):
        """Test creating report with invalid template raises error."""
        with pytest.raises(ValueError, match="Template not found"):
            engine.create_report_from_template("invalid-id", "Test")

    @pytest.mark.asyncio
    async def test_list_reports(self, engine, sample_report):
        """Test listing reports with filters."""
        engine._reports[sample_report.id] = sample_report
        
        reports = engine.list_reports(status=ReportStatus.ACTIVE)
        assert len(reports) == 1
        assert reports[0].id == sample_report.id

    @pytest.mark.asyncio
    async def test_update_report(self, engine, sample_report):
        """Test updating a report."""
        engine._reports[sample_report.id] = sample_report
        
        updated = engine.update_report(sample_report.id, {"name": "Updated Name", "status": ReportStatus.ACTIVE})
        
        assert updated.name == "Updated Name"
        assert updated.status == ReportStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_delete_report(self, engine, sample_report):
        """Test deleting a report."""
        engine._reports[sample_report.id] = sample_report
        
        result = engine.delete_report(sample_report.id)
        
        assert result is True
        assert sample_report.id not in engine._reports

    @pytest.mark.asyncio
    async def test_create_schedule(self, engine, sample_report):
        """Test creating a schedule."""
        engine._reports[sample_report.id] = sample_report
        
        schedule = engine.create_schedule(ReportSchedule(
            report_id=sample_report.id,
            cron_expression="0 6 * * *",
            timezone="UTC",
        ))
        
        assert schedule.report_id == sample_report.id
        assert schedule.id in engine._schedules


# ============================================================================
# Query Execution Tests
# ============================================================================

class TestQueryExecution:
    """Test data query execution."""

    @pytest.mark.asyncio
    async def test_execute_daily_facts_query(self, engine, mock_daily_facts):
        """Test querying daily facts."""
        source = DataSourceConfig(
            type=DataSourceType.DAILY_FACTS,
            metrics=["aff_revenue", "sessions"],
            date_range={"days": 30},
        )
        
        result = await engine.execute_query(source, client_ids=[uuid4()])
        
        assert isinstance(result, QueryResult)
        assert result.row_count >= 0
        assert "aff_revenue" in result.columns or result.row_count == 0

    @pytest.mark.asyncio
    async def test_execute_program_revenue_query(self, engine, mock_daily_facts):
        """Test querying program revenue."""
        source = DataSourceConfig(
            type=DataSourceType.PROGRAM_REVENUE,
            metrics=["revenue", "conversions"],
            date_range={"days": 30},
        )
        
        result = await engine.execute_query(source, client_ids=[uuid4()])
        
        assert isinstance(result, QueryResult)

    @pytest.mark.asyncio
    async def test_execute_unknown_source(self, engine):
        """Test querying unknown source type returns error in metadata."""
        # Bypass enum validation to test engine's error handling for unknown types
        source = DataSourceConfig.model_construct(type="unknown")

        result = await engine.execute_query(source)

        assert result.row_count == 0
        assert "error" in result.metadata


# ============================================================================
# Renderer Tests
# ============================================================================

class TestRenderers:
    """Test widget renderers."""

    @pytest.fixture
    def widget_renderer(self, engine):
        return WidgetRenderer(engine)

    @pytest.mark.asyncio
    async def test_render_kpi_card(self, widget_renderer, engine):
        """Test rendering KPI card widget."""
        widget = WidgetDefinition(
            id="kpi-1",
            config=WidgetConfig(
                type=WidgetType.KPI_CARD,
                title="Test Revenue",
                data_source=DataSourceConfig(
                    type=DataSourceType.DAILY_FACTS,
                    metrics=["aff_revenue"],
                ),
                options={"format": "currency"},
            ),
        )
        
        # Mock data in context
        context = MagicMock()
        context.data_cache = {
            "kpi-1": QueryResult(
                data=[{"aff_revenue": 1500.50}],
                columns=["aff_revenue"],
                row_count=1,
                source=DataSourceType.DAILY_FACTS,
            )
        }
        context.report = MagicMock()
        
        result = await widget_renderer.render(widget, context)
        
        assert isinstance(result, RenderedWidget)
        assert result.widget_id == "kpi-1"
        assert result.type == WidgetType.KPI_CARD
        assert result.html is not None
        assert "$1,500.50" in result.html or "1500.50" in result.html

    @pytest.mark.asyncio
    async def test_render_line_chart(self, widget_renderer, engine):
        """Test rendering line chart widget."""
        widget = WidgetDefinition(
            id="chart-1",
            config=WidgetConfig(
                type=WidgetType.LINE_CHART,
                title="Revenue Trend",
                data_source=DataSourceConfig(
                    type=DataSourceType.DAILY_FACTS,
                    metrics=["aff_revenue"],
                    date_range={"days": 7},
                ),
            ),
        )
        
        context = MagicMock()
        context.data_cache = {
            "chart-1": QueryResult(
                data=[
                    {"date": "2024-01-01", "aff_revenue": 1000},
                    {"date": "2024-01-02", "aff_revenue": 1200},
                ],
                columns=["date", "aff_revenue"],
                row_count=2,
                source=DataSourceType.DAILY_FACTS,
            )
        }
        
        result = await widget_renderer.render(widget, context)
        
        assert result.type == WidgetType.LINE_CHART
        assert result.chart_config is not None
        assert "data" in result.chart_config

    @pytest.mark.asyncio
    async def test_render_data_table(self, widget_renderer, engine):
        """Test rendering data table widget."""
        widget = WidgetDefinition(
            id="table-1",
            config=WidgetConfig(
                type=WidgetType.DATA_TABLE,
                title="Top Programs",
                data_source=DataSourceConfig(
                    type=DataSourceType.PROGRAM_REVENUE,
                    metrics=["revenue", "conversions"],
                    dimensions=["program"],
                    date_range={"days": 30},
                    group_by=["program"],
                ),
            ),
        )
        
        context = MagicMock()
        context.data_cache = {
            "table-1": QueryResult(
                data=[
                    {"program": "prog1", "revenue": 500, "conversions": 10},
                    {"program": "prog2", "revenue": 300, "conversions": 5},
                ],
                columns=["program", "revenue", "conversions"],
                row_count=2,
                source=DataSourceType.PROGRAM_REVENUE,
            )
        }
        
        result = await widget_renderer.render(widget, context)
        
        assert result.type == WidgetType.DATA_TABLE
        assert result.html is not None
        assert "prog1" in result.html
        assert "500" in result.html


# ============================================================================
# Exporter Tests
# ============================================================================

class TestExporters:
    """Test report exporters."""

    @pytest.fixture
    def sample_rendered_report(self):
        """Create a sample rendered report."""
        return RenderedReport(
            report_id="test-report",
            run_id="test-run",
            name="Test Report",
            generated_at=datetime.utcnow(),
            sections=[
                RenderedSection(
                    section_id="section-1",
                    title="Overview",
                    widgets=[
                        RenderedWidget(
                            widget_id="widget-1",
                            type=WidgetType.KPI_CARD,
                            title="Revenue",
                            html="<div class='kpi-card'>$1,000</div>",
                            data=[{"aff_revenue": 1000}],
                            render_time_ms=50,
                            data_rows=1,
                        ),
                    ],
                ),
            ],
            total_widgets=1,
            failed_widgets=0,
            total_data_rows=1,
            total_render_time_ms=50,
        )

    @pytest.mark.asyncio
    async def test_html_exporter(self, sample_rendered_report, tmp_path):
        """Test HTML export."""
        exporter = HTMLExporter(tmp_path)
        
        result = await exporter.export(sample_rendered_report, tmp_path)
        
        assert result["format"] == ExportFormat.HTML.value
        assert result["filename"].endswith(".html")
        assert (tmp_path / result["filename"]).exists()

    @pytest.mark.asyncio
    async def test_csv_exporter(self, sample_rendered_report, tmp_path):
        """Test CSV export (ZIP with CSVs)."""
        exporter = CSVExporter(tmp_path)
        
        result = await exporter.export(sample_rendered_report, tmp_path)
        
        assert result["format"] == ExportFormat.CSV.value
        assert result["filename"].endswith(".zip")

    @pytest.mark.asyncio
    async def test_json_exporter(self, sample_rendered_report, tmp_path):
        """Test JSON export."""
        exporter = JSONExporter(tmp_path)
        
        result = await exporter.export(sample_rendered_report, tmp_path)
        
        assert result["format"] == ExportFormat.JSON.value
        assert result["filename"].endswith(".json")
        assert (tmp_path / result["filename"]).exists()

    @pytest.mark.asyncio
    async def test_pdf_exporter_fallback(self, sample_rendered_report, tmp_path):
        """Test PDF export (falls back to Playwright if WeasyPrint not available)."""
        exporter = PDFExporter(tmp_path)
        
        # Should not raise even if WeasyPrint not installed
        try:
            result = await exporter.export(sample_rendered_report, tmp_path)
            # If successful, check result
            assert result["format"] == ExportFormat.PDF.value
        except ImportError:
            # Expected if neither WeasyPrint nor Playwright available
            pass


# ============================================================================
# Scheduler Tests
# ============================================================================

class TestScheduler:
    """Test report scheduler."""

    @pytest.mark.asyncio
    async def test_schedule_report(self, engine, sample_report):
        """Test scheduling a report."""
        engine._reports[sample_report.id] = sample_report
        
        scheduler = engine.scheduler
        await scheduler.add_schedule(ReportSchedule(
            report_id=sample_report.id,
            cron_expression="0 6 * * *",
            timezone="UTC",
        ))
        
        schedules = scheduler.engine.list_schedules(active_only=True)
        assert len(schedules) >= 1

    @pytest.mark.asyncio
    async def test_pause_resume_schedule(self, engine, sample_report):
        """Test pausing and resuming a schedule."""
        engine._reports[sample_report.id] = sample_report
        
        scheduler = engine.scheduler
        schedule = await scheduler.add_schedule(ReportSchedule(
            report_id=sample_report.id,
            cron_expression="0 6 * * *",
        ))
        
        # Pause
        await scheduler.pause_schedule(schedule.id)
        paused = scheduler.engine.get_schedule(schedule.id)
        assert paused.is_active is False
        
        # Resume
        await scheduler.resume_schedule(schedule.id)
        resumed = scheduler.engine.get_schedule(schedule.id)
        assert resumed.is_active is True

    @pytest.mark.asyncio
    async def test_trigger_schedule(self, engine, sample_report):
        """Test manually triggering a scheduled report."""
        engine._reports[sample_report.id] = sample_report
        
        scheduler = engine.scheduler
        schedule = await scheduler.add_schedule(ReportSchedule(
            report_id=sample_report.id,
            cron_expression="0 6 * * *",
        ))
        
        run_id = await scheduler.trigger_now(schedule.id)
        assert run_id is not None


# ============================================================================
# Utility Tests
# ============================================================================

class TestUtilities:
    """Test utility functions."""

    def test_format_number_currency(self):
        from reporting_engine.lib.utils import format_number
        assert format_number(1500.50, "currency") == "$1,500.50"
        assert format_number(1000000, "currency") == "$1,000,000.00"

    def test_format_number_percent(self):
        from reporting_engine.lib.utils import format_number
        assert format_number(12.5, "percent") == "12.5%"
        assert format_number(100, "percent") == "100.0%"

    def test_format_number_ratio(self):
        from reporting_engine.lib.utils import format_number
        assert format_number(4.2, "ratio") == "4.2x"

    def test_format_date(self):
        from reporting_engine.lib.utils import format_date
        assert "Jan" in format_date("2024-01-15")
        assert "2024" in format_date("2024-01-15")

    def test_class_names(self):
        from reporting_engine.lib.utils import class_names
        assert class_names("a", "b", False, None, "c") == "a b c"
        assert class_names("", "b", True and "c") == "b c"

    def test_truncate(self):
        from reporting_engine.lib.utils import truncate
        assert truncate("hello world", 8) == "hello..."
        assert truncate("hi", 10) == "hi"

    def test_download_file(self):
        from reporting_engine.lib.utils import download_file
        # Just test it doesn't error in test environment
        download_file("test content", "test.txt", "text/plain")


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration-style tests."""

    @pytest.mark.asyncio
    async def test_full_report_lifecycle(self, engine, sample_template):
        """Test complete report lifecycle: create -> run -> export."""
        engine._templates[sample_template.id] = sample_template
        
        # Create report
        report = engine.create_report_from_template(
            template_id=sample_template.id,
            name="Integration Test Report",
        )
        
        assert report.id in engine._reports
        
        # Schedule it
        schedule = engine.create_schedule(ReportSchedule(
            report_id=report.id,
            cron_expression="0 6 * * 1",
        ))
        
        assert schedule.id in engine._schedules
        
        # Run manually
        run = await engine.run_report(
            report_id=report.id,
            triggered_by="manual",
        )
        
        assert run.id in engine._runs
        # Note: Full run would require mocked data sources

    @pytest.mark.asyncio
    async def test_ad_hoc_query(self, engine):
        """Test ad-hoc query execution."""
        result = await engine.execute_query(DataSourceConfig(
            type=DataSourceType.DAILY_FACTS,
            metrics=["sessions", "users"],
            date_range={"days": 7},
        ))
        
        assert isinstance(result, QueryResult)
        assert result.source == DataSourceType.DAILY_FACTS


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])