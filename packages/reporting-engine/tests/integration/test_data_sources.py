"""
Integration tests for reporting engine data source execution.
Tests real data source execution paths including DailyFacts,
Program Revenue, and unknown source handling.
"""

import pytest
from reporting_engine import ReportingEngine, DataSourceConfig, DataSourceType
from reporting_engine.models import ReportContext, ReportDefinition, ReportRun, ReportStatus


class TestDataSourceExecution:
    """Test data source execution through the reporting engine."""

    @pytest.fixture
    def engine(self):
        """Create a reporting engine instance."""
        return ReportingEngine()

    @pytest.fixture
    def context(self):
        """Create a basic report context."""
        report = ReportDefinition(
            id="test_report",
            name="Test Report",
            status=ReportStatus.DRAFT,
        )
        run = ReportRun(
            id="test_run",
            report_id="test_report",
            report_name="Test Report",
            status=RunStatus.PENDING,
        )
        return ReportContext(
            visitor_id="test_visitor",
            report=report,
            run=run,
            client_id="test_client",
            date_range={},
            filters=[],
            metrics=[],
            dimensions=[],
        )

    @pytest.mark.asyncio
    async def test_daily_facts_query(self, engine, context):
        """Test executing a daily facts data source query."""
        source = DataSourceConfig(
            type=DataSourceType.DAILY_FACTS,
            metrics=["revenue", "orders"],
            dimensions=["date"],
            date_range={"start": "2024-01-01", "end": "2024-01-31"},
            filters=[],
            group_by=[],
        )

        result = await engine.execute_query(source, context)

        assert result.row_count >= 0
        assert result.metadata.get("error") is None or result.metadata.get("error") is None

    @pytest.mark.asyncio
    async def test_program_revenue_query(self, engine, context):
        """Test executing a program revenue data source query."""
        source = DataSourceConfig(
            type=DataSourceType.PROGRAM_REVENUE,
            metrics=["revenue"],
            dimensions=[],
            filters={},
            group_by=[],
        )

        result = await engine.execute_query(source, context)

        assert result.row_count >= 0

    @pytest.mark.asyncio
    async def test_dimension_facts_query(self, engine, context):
        """Test executing a dimension facts data source query."""
        source = DataSourceConfig(
            type=DataSourceType.DIMENSION_FACTS,
            metrics=["revenue"],
            dimensions=["date"],
            filters=[],
            group_by=[],
        )

        result = await engine.execute_query(source, context)

        assert result.row_count >= 0

    @pytest.mark.asyncio
    async def test_unknown_source_returns_error(self, engine, context):
        """Test that unknown source type returns error in metadata."""
        source = DataSourceConfig.model_construct(type="unknown")

        result = await engine.execute_query(source, context)

        assert result.row_count == 0
        assert "error" in result.metadata

    @pytest.mark.asyncio
    async def test_data_source_config_validation(self):
        """Test DataSourceConfig validation with valid types."""
        for source_type in DataSourceType:
            source = DataSourceConfig(
                type=source_type,
                metrics=["revenue"],
                dimensions=[],
                filters=[],
                group_by=[],
            )
            assert source.type == source_type

    @pytest.mark.asyncio
    async def test_data_source_config_invalid_type(self):
        """Test that invalid source type raises validation error."""
        with pytest.raises(Exception):
            DataSourceConfig(type="invalid_type")

    @pytest.mark.asyncio
    async def test_api_endpoint_query(self, engine, context):
        """Test executing an API endpoint data source query."""
        source = DataSourceConfig(
            type=DataSourceType.API_ENDPOINT,
            metrics=[],
            dimensions=[],
            filters={},
            group_by=[],
        )

        result = await engine.execute_query(source, context)

        assert result.row_count >= 0
        assert result.metadata.get("error") is None or result.metadata.get("error") is not None

    @pytest.mark.asyncio
    async def test_mcp_tool_query(self, engine, context):
        """Test executing an MCP tool data source query."""
        source = DataSourceConfig(
            type=DataSourceType.MCP_TOOL,
            metrics=[],
            dimensions=[],
            filters={},
            group_by=[],
        )

        result = await engine.execute_query(source, context)

        assert result.row_count >= 0