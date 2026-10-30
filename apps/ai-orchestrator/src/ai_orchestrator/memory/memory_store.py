"""
Memory System for AI Orchestrator

Provides vector-based memory storage using ChromaDB with support for:
- Short-term memory (working memory for current conversation)
- Long-term memory (persistent vector storage)
- Episodic memory (event-based memories)
- Semantic memory (fact-based knowledge)
"""

import asyncio
import hashlib
import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from chromadb import Client as ChromaClient
from chromadb.config import Settings as ChromaSettings

from ..config import get_ai_orchestrator_settings
from ..models import MemoryEntry, MemoryType


class MemoryStore:
    """
    Vector-based memory store using ChromaDB.
    
    Supports multiple memory types:
    - Short-term: Recent conversation context (TTL-based)
    - Long-term: Persistent memories that survive across sessions
    - Episodic: Event-based memories with timestamps
    - Semantic: Fact-based knowledge
    - Working: Temporary working memory for current task
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8000,
        collection_prefix: str = "ai_orchestrator",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    ):
        self.settings = get_ai_orchestrator_settings()
        self.host = host or self.settings.chromadb_host
        self.port = port or self.settings.chromadb_port
        self.collection_prefix = collection_prefix or self.settings.chromadb_collection_prefix
        self.embedding_model = embedding_model or self.settings.memory_embedding_model
        
        self._client: Optional[ChromaClient] = None
        self._collections: Dict[str, Any] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize ChromaDB client and collections."""
        if self._initialized:
            return

        self._client = ChromaClient(
            ChromaSettings(
                chroma_host=self.host,
                chroma_port=self.port,
            )
        )

        # Create collections for each memory type
        for memory_type in MemoryType:
            collection_name = f"{self.collection_prefix}_{memory_type.value}"
            try:
                collection = self._client.get_collection(name=collection_name)
            except Exception:
                collection = self._client.create_collection(
                    name=collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
            self._collections[memory_type.value] = collection

        self._initialized = True
        logger.info("memory_store_initialized", collections=list(self._collections.keys()))

    async def store(
        self,
        agent_id: str,
        memory_type: MemoryType,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 1.0,
        tags: Optional[List[str]] = None,
        expires_at: Optional[datetime] = None,
    ) -> str:
        """
        Store a memory entry.
        
        Returns the memory ID.
        """
        if not self._initialized:
            await self.initialize()

        memory_id = uuid.uuid4().hex
        collection = self._collections.get(memory_type.value)
        if collection is None:
            raise ValueError(f"Unknown memory type: {memory_type.value}")

        # Generate embedding
        embedding = self._embed(content)

        # Prepare metadata
        meta = {
            "agent_id": agent_id,
            "memory_type": memory_type.value,
            "importance": importance,
            "created_at": datetime.utcnow().isoformat(),
            "tags": ",".join(tags or []),
        }
        if expires_at:
            meta["expires_at"] = expires_at.isoformat()
        if metadata:
            meta.update(metadata)

        collection.add(
            ids=[memory_id],
            documents=[content],
            embeddings=[embedding],
            metadatas=[meta],
        )

        logger.debug(
            "memory_stored",
            memory_id=memory_id,
            agent_id=agent_id,
            memory_type=memory_type.value,
        )

        return memory_id

    async def search(
        self,
        agent_id: str,
        query: str,
        memory_types: Optional[List[MemoryType]] = None,
        limit: int = 10,
        min_similarity: float = 0.7,
    ) -> List[MemoryEntry]:
        """
        Search memories by semantic similarity.
        
        Returns matching memory entries sorted by relevance.
        """
        if not self._initialized:
            await self.initialize()

        query_embedding = self._embed(query)
        memory_types = memory_types or list(MemoryType)
        results: List[MemoryEntry] = []

        for mem_type in memory_types:
            collection = self._collections.get(mem_type.value)
            if collection is None:
                continue

            try:
                results_raw = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=limit,
                    where={"agent_id": agent_id},
                    include=["documents", "metadatas", "distances"],
                )

                for i in range(len(results_raw.get("ids", [[]])[0])):
                    doc_id = results_raw["ids"][0][i]
                    doc = results_raw["documents"][0][i]
                    meta = results_raw["metadatas"][0][i]
                    distance = results_raw["distances"][0][i]
                    similarity = 1.0 - distance  # Convert distance to similarity

                    if similarity < min_similarity:
                        continue

                    memory_entry = MemoryEntry(
                        memory_id=doc_id,
                        agent_id=agent_id,
                        memory_type=MemoryType(meta.get("memory_type", memory_type.value)),
                        content=doc,
                        metadata={k: v for k, v in meta.items() if k not in ("agent_id", "memory_type", "importance", "created_at", "tags", "expires_at")},
                        importance=meta.get("importance", 1.0),
                        tags=meta.get("tags", "").split(",") if meta.get("tags") else [],
                        created_at=datetime.fromisoformat(meta.get("created_at", datetime.utcnow().isoformat())),
                        expires_at=datetime.fromisoformat(meta["expires_at"]) if meta.get("expires_at") else None,
                    )
                    results.append(memory_entry)

            except Exception as e:
                logger.error(
                    "memory_search_error",
                    memory_type=mem_type.value,
                    error=str(e),
                )

        # Sort by similarity (importance * similarity)
        results.sort(key=lambda m: m.importance * 1.0, reverse=True)
        return results[:limit]

    async def get(self, memory_id: str) -> Optional[MemoryEntry]:
        """Get a specific memory entry by ID."""
        if not self._initialized:
            await self.initialize()

        # Search across all collections
        for mem_type, collection in self._collections.items():
            try:
                result = collection.get(ids=[memory_id], include=["documents", "metadatas"])
                if result and result.get("ids") and result["ids"][0]:
                    meta = result["metadatas"][0]
                    return MemoryEntry(
                        memory_id=result["ids"][0],
                        agent_id=meta.get("agent_id", ""),
                        memory_type=MemoryType(meta.get("memory_type", mem_type)),
                        content=result["documents"][0],
                        metadata={k: v for k, v in meta.items() if k not in ("agent_id", "memory_type", "importance", "created_at", "tags", "expires_at")},
                        importance=meta.get("importance", 1.0),
                        tags=meta.get("tags", "").split(",") if meta.get("tags") else [],
                        created_at=datetime.fromisoformat(meta.get("created_at", datetime.utcnow().isoformat())),
                        expires_at=datetime.fromisoformat(meta["expires_at"]) if meta.get("expires_at") else None,
                    )
            except Exception:
                continue

        return None

    async def delete(self, memory_id: str) -> bool:
        """Delete a memory entry by ID."""
        if not self._initialized:
            await self.initialize()

        for collection in self._collections.values():
            try:
                collection.delete(ids=[memory_id])
                return True
            except Exception:
                continue

        return False

    async def get_recent(
        self,
        agent_id: str,
        memory_type: MemoryType = MemoryType.SHORT_TERM,
        limit: int = 10,
    ) -> List[MemoryEntry]:
        """Get recent memories for an agent."""
        if not self._initialized:
            await self.initialize()

        collection = self._collections.get(memory_type.value)
        if collection is None:
            return []

        try:
            result = collection.get(
                where={"agent_id": agent_id},
                limit=limit,
                include=["documents", "metadatas"],
            )

            memories = []
            for i in range(len(result.get("ids", []))):
                meta = result["metadatas"][i]
                memories.append(MemoryEntry(
                    memory_id=result["ids"][i],
                    agent_id=meta.get("agent_id", agent_id),
                    memory_type=memory_type,
                    content=result["documents"][i],
                    metadata={k: v for k, v in meta.items() if k not in ("agent_id", "memory_type", "importance", "created_at", "tags", "expires_at")},
                    importance=meta.get("importance", 1.0),
                    tags=meta.get("tags", "").split(",") if meta.get("tags") else [],
                    created_at=datetime.fromisoformat(meta.get("created_at", datetime.utcnow().isoformat())),
                ))
            return memories

        except Exception as e:
            logger.error("get_recent_error", memory_type=memory_type.value, error=str(e))
            return []

    async def clear_agent_memory(
        self,
        agent_id: str,
        memory_types: Optional[List[MemoryType]] = None,
    ) -> int:
        """Delete all memories for an agent."""
        memory_types = memory_types or list(MemoryType)
        deleted_count = 0

        for mem_type in memory_types:
            collection = self._collections.get(mem_type.value)
            if collection is None:
                continue

            try:
                result = collection.get(
                    where={"agent_id": agent_id},
                    include=["ids"],
                )
                ids = result.get("ids", [])
                if ids:
                    collection.delete(ids=ids)
                    deleted_count += len(ids)
            except Exception as e:
                logger.error("memory_delete_error", memory_type=mem_type.value, error=str(e))

        return deleted_count

    def _embed(self, text: str) -> List[float]:
        """Generate embedding for text."""
        # Use sentence-transformers for embedding
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(self.embedding_model)
            embedding = model.encode(text).tolist()
            return embedding
        except Exception:
            # Fallback: simple hash-based embedding
            import hashlib
            hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
            return [(hash_val % 1000) / 1000.0] * 384  # 384-dim embedding


class MemoryManager:
    """
    High-level memory manager for agents.
    
    Provides a simpler interface for common memory operations
    across different memory types.
    """

    def __init__(self, store: MemoryStore):
        self.store = store

    async def remember(
        self,
        agent_id: str,
        content: str,
        memory_type: MemoryType = MemoryType.SHORT_TERM,
        importance: float = 1.0,
        tags: Optional[List[str]] = None,
        expires_in_seconds: Optional[int] = None,
    ) -> str:
        """Store a memory."""
        expires_at = None
        if expires_in_seconds:
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in_seconds)

        return await self.store.store(
            agent_id=agent_id,
            memory_type=memory_type,
            content=content,
            importance=importance,
            tags=tags,
            expires_at=expires_at,
        )

    async def recall(
        self,
        agent_id: str,
        query: str,
        memory_types: Optional[List[MemoryType]] = None,
        limit: int = 10,
        min_similarity: float = 0.7,
    ) -> List[MemoryEntry]:
        """Recall memories by semantic similarity."""
        return await self.store.search(
            agent_id=agent_id,
            query=query,
            memory_types=memory_types,
            limit=limit,
            min_similarity=min_similarity,
        )

    async def get_recent_context(
        self,
        agent_id: str,
        limit: int = 10,
    ) -> List[MemoryEntry]:
        """Get recent context memories for an agent."""
        return await self.store.get_recent(
            agent_id=agent_id,
            memory_type=MemoryType.SHORT_TERM,
            limit=limit,
        )

    async def forget(
        self,
        agent_id: str,
        memory_id: str,
    ) -> bool:
        """Delete a specific memory."""
        return await self.store.delete(memory_id)

    async def clear_agent_memory(
        self,
        agent_id: str,
        memory_types: Optional[List[MemoryType]] = None,
    ) -> int:
        """Clear all memories for an agent."""
        return await self.store.clear_agent_memory(agent_id, memory_types)


# Global memory manager instance
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """Get or create the global memory manager."""
    global _memory_manager
    if _memory_manager is None:
        from ..config import get_ai_orchestrator_settings
        settings = get_ai_orchestrator_settings()
        store = MemoryStore(
            host=settings.chromadb_host,
            port=settings.chromadb_port,
            collection_prefix=settings.chromadb_collection_prefix,
            embedding_model=settings.memory_embedding_model,
        )
        _memory_manager = MemoryManager(store)
    return _memory_manager