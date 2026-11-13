"""RAG Manager - wraps RAGService with assistant-specific collections."""

from __future__ import annotations

from typing import Any

from shared.rag import RAGService


class RAGManager:
    """Manages RAG for multiple assistants with tenant isolation."""

    def __init__(self, rag_service: RAGService):
        self.rag = rag_service

    async def ingest(
        self,
        content: str,
        assistant_id: str,
        tenant_id: str,
        source: str,
        metadata: dict | None = None,
    ) -> dict:
        """Ingest content into RAG for a specific assistant."""
        collection = f"{tenant_id}_{assistant_id}"
        meta = {"source": source, "assistant_id": assistant_id, "tenant_id": tenant_id}
        if metadata:
            meta.update(metadata)

        result = await self.rag.ingest(
            content=content,
            metadata=meta,
            collection=collection,
        )
        return {"document_id": result["id"], "chunks": result["chunks"], "collection": collection}

    async def search(
        self,
        query: str,
        assistant_id: str,
        tenant_id: str,
        top_k: int = 5,
        collections: list[str] | None = None,
    ) -> list[dict]:
        """Search RAG for relevant content."""
        if collections is None:
            collections = [f"{tenant_id}_{assistant_id}", f"{tenant_id}_shared", f"global_{assistant_id.split('-')[0]}"]

        all_results = []
        for collection in collections:
            try:
                results = await self.rag.search(query=query, collection=collection, top_k=top_k)
                for r in results:
                    r["collection"] = collection
                all_results.extend(results)
            except Exception:
                continue

        # Sort by score and return top_k
        all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return all_results[:top_k]

    async def ingest_connector_data(
        self,
        assistant_id: str,
        tenant_id: str,
        connector: str,
        items: list[dict],
    ) -> int:
        """Ingest data from a connector (Gmail, Calendar, etc.)."""
        count = 0
        for item in items:
            content = str(item)
            meta = {"source": connector, **item}
            await self.ingest(content, assistant_id, tenant_id, connector, meta)
            count += 1
        return count


def create_rag_manager(rag_service: RAGService) -> RAGManager:
    return RAGManager(rag_service)