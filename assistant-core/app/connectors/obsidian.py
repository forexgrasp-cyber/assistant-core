"""Obsidian Connector."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


class ObsidianConnector:
    name = "obsidian"
    required_env = ["OBSIDIAN_VAULT_PATH"]

    async def authenticate(self) -> bool:
        path = os.getenv(self.required_env[0])
        return bool(path and Path(path).exists())

    async def fetch_recent(self, limit: int = 10) -> list[dict]:
        vault = Path(os.getenv(self.required_env[0], ""))
        files = list(vault.rglob("*.md"))[:limit] if vault.exists() else []
        return [{"path": str(f.relative_to(vault)), "title": f.stem} for f in files]

    async def search(self, query: str, limit: int = 10) -> list[dict]:
        return [{"id": "mock", "title": f"Search: {query}"}]

    async def perform_action(self, action: str, params: dict) -> dict:
        return {"status": "not_implemented", "action": action}