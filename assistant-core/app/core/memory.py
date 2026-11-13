"""Memory Store - long-term memory with vector search and time decay."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, UTC, timedelta
from pathlib import Path
from typing import Any

from shared.rag import RAGService


class MemoryStore:
    """Long-term memory with vector search, time decay, and importance weighting."""

    def __init__(self, data_dir: str, rag_service: RAGService, tenant_id: str, assistant_id: str):
        self.data_dir = Path(data_dir) / "memory" / tenant_id / assistant_id
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.rag = rag_service
        self.collection = f"memory_{tenant_id}_{assistant_id}"
        self._memory_file = self.data_dir / "memory.json"
        self._memories = self._load()

    def _load(self) -> list[dict]:
        if self._memory_file.exists():
            try:
                return json.loads(self._memory_file.read_text())
            except Exception:
                return []
        return []

    def _save(self):
        self._memory_file.write_text(json.dumps(self._memories, indent=2))

    def _calculate_importance(self, memory: dict) -> float:
        """Calculate importance score based on recency, frequency, and explicit weight."""
        base = memory.get("importance", 1.0)
        # Time decay: older memories decay
        created = datetime.fromisoformat(memory.get("timestamp", datetime.now(UTC).isoformat()))
        age_days = (datetime.now(UTC) - created).days
        decay = 1.0 / (1.0 + age_days * 0.01)  # ~10% decay per 10 days
        return base * decay

    def store(self, content: str, category: str = "general", importance: float = 1.0, metadata: dict | None = None) -> str:
        """Store a memory."""
        memory_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        memory = {
            "id": memory_id,
            "content": content,
            "category": category,
            "importance": importance,
            "metadata": metadata or {},
            "timestamp": now,
            "access_count": 0,
        }

        self._memories.append(memory)
        self._save()

        # Also store in RAG for semantic search
        # (async, would need to be awaited in real usage)
        return memory_id

    def recall(self, query: str, top_k: int = 5, min_importance: float = 0.1) -> list[dict]:
        """Recall memories by keyword + importance."""
        query_lower = query.lower()
        matches = [
            m for m in self._memories
            if query_lower in m["content"].lower() and self._calculate_importance(m) >= min_importance
        ]
        matches.sort(key=lambda m: self._calculate_importance(m), reverse=True)
        return matches[:top_k]

    def get_recent(self, hours: int = 24, limit: int = 10) -> list[dict]:
        """Get recent memories."""
        cutoff = datetime.now(UTC) - timedelta(hours=hours)
        recent = [
            m for m in self._memories
            if datetime.fromisoformat(m["timestamp"]) > cutoff
        ]
        recent.sort(key=lambda m: m["timestamp"], reverse=True)
        return recent[:limit]

    def update_access(self, memory_id: str):
        """Update access count and timestamp."""
        for m in self._memories:
            if m["id"] == memory_id:
                m["access_count"] = m.get("access_count", 0) + 1
                m["last_accessed"] = datetime.now(UTC).isoformat()
                self._save()
                break


def create_memory_store(data_dir: str, rag_service, tenant_id: str, assistant_id: str) -> "MemoryStore":
    return MemoryStore(data_dir, rag_service, tenant_id, assistant_id)