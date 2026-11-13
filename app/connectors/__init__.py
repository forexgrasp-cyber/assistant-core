"""Connectors for external services."""

from .gmail import GmailConnector
from .calendar import CalendarConnector
from .notion import NotionConnector
from .obsidian import ObsidianConnector
from .slack import SlackConnector
from .github import GitHubConnector
from .crm import CRMConnector

__all__ = [
    "GmailConnector",
    "CalendarConnector",
    "NotionConnector",
    "ObsidianConnector",
    "SlackConnector",
    "GitHubConnector",
    "CRMConnector",
    "get_connector",
    "list_connectors",
]

_CONNECTORS = {
    "gmail": GmailConnector,
    "calendar": CalendarConnector,
    "notion": NotionConnector,
    "obsidian": ObsidianConnector,
    "slack": SlackConnector,
    "github": GitHubConnector,
    "crm": CRMConnector,
}


def get_connector(name: str):
    """Get connector instance by name."""
    cls = _CONNECTORS.get(name)
    if cls:
        return cls()
    return None


def list_connectors() -> dict[str, dict]:
    """List available connectors."""
    return {name: {"class": cls.__name__} for name, cls in _CONNECTORS.items()}