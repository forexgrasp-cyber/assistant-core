"""CRM Connector."""

from __future__ import annotations

import os
from typing import Any


class CRMConnector:
    name = "crm"
    required_env = ["CRM_API_KEY"]

    async def authenticate(self) -> bool:
        return bool(os.getenv(self.required_env[0]))

    async def fetch_recent(self, limit: int = 10) -> list[dict]:
        return [{"id": "mock", "name": "Contact", "email": "contact@example.com"}]

    async def search(self, query: str, limit: int = 10) -> list[dict]:
        return [{"id": "mock", "name": f"Search: {query}"}]

    async def perform_action(self, action: str, params: dict) -> dict:
        return {"status": "not_implemented", "action": action}