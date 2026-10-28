"""
Pytest configuration for retention-analytics-platform
"""

import sys
from pathlib import Path

# Add shared-canonical-services to path
SHARED_PATH = Path(__file__).parent.parent / "shared-canonical-services"
if str(SHARED_PATH) not in sys.path:
    sys.path.insert(0, str(SHARED_PATH))

# Add packages to path
PACKAGES_PATH = Path(__file__).parent / "packages"
if str(PACKAGES_PATH) not in sys.path:
    sys.path.insert(0, str(PACKAGES_PATH))

# Pytest configuration
pytest_plugins = []

# Test markers
def pytest_configure(config):
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "api: API tests")
    config.addinivalue_line("markers", "renderer: Renderer tests")
    config.addinivalue_line("markers", "exporter: Exporter tests")
    config.addinivalue_line("markers", "scheduler: Scheduler tests")


# Fixtures available to all tests
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_db():
    """Mock database connection."""
    mock = AsyncMock()
    mock.fetch_all = AsyncMock(return_value=[])
    mock.fetch_one = AsyncMock(return_value=None)
    mock.execute = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)
    mock.exists = AsyncMock(return_value=False)
    return mock


# Async test utilities
@pytest.fixture
def async_client():
    """Async HTTP client for testing."""
    from httpx import AsyncClient
    from retention_analytics_api.app.main import app
    return AsyncClient(app=app, base_url="http://test")


# Test data factories
class ReportFactory:
    """Factory for creating test reports."""
    
    @staticmethod
    def create_report(**overrides):
        from retention_analytics_reporting_engine.models import ReportDefinition, ReportStatus, ExportFormat
        from uuid import uuid4
        from datetime import datetime
        
        defaults = {
            "id": f"rpt_{uuid4().hex[:8]}",
            "name": "Test Report",
            "description": "A test report",
            "sections": [],
            "filters": [],
            "schedule": None,
            "formats": [ExportFormat.PDF],
            "status": ReportStatus.DRAFT,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        defaults.update(overrides)
        return ReportDefinition(**defaults)
    
    @staticmethod
    def create_widget(**overrides):
        from retention_analytics_reporting_engine.models import WidgetDefinition, WidgetConfig, DataSourceConfig, DataSourceType, WidgetType
        from uuid import uuid4
        
        defaults = {
            "id": f"widget_{uuid4().hex[:8]}",
            "config": WidgetConfig(
                type=WidgetType.KPI_CARD,
                title="Test Widget",
                data_source=DataSourceConfig(
                    type=DataSourceType.DAILY_FACTS,
                    metrics=["sessions"],
                ),
            ),
            "x": 0, "y": 0, "w": 12, "h": 6,
        }
        defaults.update(overrides)
        return WidgetDefinition(**defaults)


@pytest.fixture
def report_factory():
    return ReportFactory


# Test configuration
pytestmark = pytest.mark.asyncio