"""Calendar Connector."""

from __future__ import annotations

import os
from typing import Any


class CalendarConnector:
    name = "calendar"
    required_env = ["GOOGLE_CALENDAR_CREDENTIALS"]

    async def authenticate(self) -> bool:
        return bool(os.getenv(self.required_env[0]))

    async def fetch_recent(self, limit: int = 10) -> list[dict]:
        return [{"id": "mock", "title": "Team meeting", "time": "2024-01-15T10:00:00Z"}]

    async def search(self, query: str, limit: int = 10) -> list[dict]:
        return [{"id": "mock", "title": f"Search: {query}"}]

    async def perform_action(self, action: str, params: dict) -> dict:
        return {"status": "not_implemented", "action": action}