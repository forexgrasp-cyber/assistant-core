"""Gmail Connector."""

from __future__ import annotations

import os
from typing import Any


class GmailConnector:
    name = "gmail"
    required_env = ["GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN"]

    async def authenticate(self) -> bool:
        return all(os.getenv(k) for k in self.required_env)

    async def fetch_recent(self, limit: int = 10) -> list[dict]:
        # TODO: Implement Gmail API
        return [{"id": "mock", "subject": "Mock email", "snippet": "This is a mock email"}]

    async def search(self, query: str, limit: int = 10) -> list[dict]:
        return [{"id": "mock", "subject": f"Search: {query}", "snippet": "Mock result"}]

    async def perform_action(self, action: str, params: dict) -> dict:
        return {"status": "not_implemented", "action": action}