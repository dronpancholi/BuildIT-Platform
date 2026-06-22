"""Memory Service – CRUD, semantic retrieval, and optional Qdrant vector integration.

Provides deterministic, auditable operations on `MemoryEntry` records. All operations are
tenant‑isolated, emit Prometheus metrics, and are wrapped in OpenTelemetry spans.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import select
from typing import List, Optional

from opentelemetry import trace

from seo_platform.core.database import get_tenant_session
from seo_platform.core.logging import get_logger
from seo_platform.core.planning_metrics import (
    seo_memory_queries_total,
    seo_memory_query_duration_seconds,
)

from seo_platform.models.operational_memory import MemoryEntry, MemoryEntryType, MemorySource
from seo_platform.models.audit_ledger import AuditLedgerEntry

# Optional Qdrant vector store for embeddings
from seo_platform.services.vector_store import qdrant_vector_store, VECTOR_SIZE
from qdrant_client import models as qdrant_models

logger = get_logger(__name__)
tracer = trace.get_tracer(__name__)


class MemoryService:
    """Stateless service handling CRUD and optional vector upserts for memory entries."""

    async def _audit(self, tenant_id: uuid.UUID, action_name: str, summary: str, entity_id: uuid.UUID) -> None:
        async with get_tenant_session(tenant_id) as session:
            entry = AuditLedgerEntry(
                tenant_id=tenant_id,
                action_name=action_name,
                actor_id=uuid.UUID(int=0),  # system actor
                actor_type="system",
                target_type="memory_entry",
                target_id=entity_id,
                summary=summary,
                input_snapshot={},
                output_snapshot={},
                immutable_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
            )
            session.add(entry)
            await session.flush()

    async def create_memory(
        self,
        tenant_id: uuid.UUID,
        entry_type: MemoryEntryType,
        source: MemorySource,
        summary: str,
        detail: dict,
        tags: Optional[List[str]] = None,
        confidence: Optional[float] = None,
        impact_score: Optional[float] = None,
        related_entry_ids: Optional[List[uuid.UUID]] = None,
        embedding: Optional[List[float]] = None,
        expires_at: Optional[datetime] = None,
        source_execution_id: Optional[uuid.UUID] = None,
    ) -> MemoryEntry:
        """Create a new `MemoryEntry` record.

        If an `embedding` is supplied, it is up‑serted into Qdrant under a
        collection named after the entry type (e.g. ``memory_<type>``).
        """
        start = datetime.utcnow()
        with tracer.start_as_current_span("memory_service.create_memory"):
            async with get_tenant_session(tenant_id) as session:
                mem = MemoryEntry(
                    tenant_id=tenant_id,
                    entry_type=entry_type,
                    source=source,
                    summary=summary,
                    detail=detail,
                    tags=tags or [],
                    confidence=confidence,
                    impact_score=impact_score,
                    related_entry_ids=related_entry_ids or [],
                    expires_at=expires_at,
                    source_execution_id=source_execution_id,
                )
                session.add(mem)
                await session.flush()

                # Optional vector upsert
                if embedding:
                    # Ensure embedding length matches VECTOR_SIZE; pad or truncate as needed
                    if len(embedding) != VECTOR_SIZE:
                        if len(embedding) > VECTOR_SIZE:
                            embedding = embedding[:VECTOR_SIZE]
                        else:
                            embedding = embedding + [0.0] * (VECTOR_SIZE - len(embedding))
                    collection_name = f"memory_{entry_type.value}" if hasattr(entry_type, "value") else f"memory_{entry_type}"
                    point_id = str(mem.id)
                    payload = {
                        "tenant_id": str(tenant_id),
                        "entry_type": str(entry_type),
                        "summary": summary,
                    }
                    try:
                        await qdrant_vector_store.initialize()
                        client = await qdrant_vector_store._get_client()
                        await client.upsert(
                            collection_name=collection_name,
                            points=[
                                qdrant_models.PointStruct(
                                    id=point_id,
                                    vector=embedding,
                                    payload=payload,
                                )
                            ],
                        )
                    except Exception as e:
                        logger.warning("memory_qdrant_upsert_failed", error=str(e))

                await session.commit()
                await self._audit(tenant_id, "memory_created", f"Memory entry {mem.id} created", mem.id)
                duration = (datetime.utcnow() - start).total_seconds()
                seo_memory_queries_total.labels(operation="create", tenant_id=str(tenant_id)).inc()
                seo_memory_query_duration_seconds.labels(operation="create").observe(duration)
                return mem

    async def get_memory(self, tenant_id: uuid.UUID, memory_id: uuid.UUID) -> MemoryEntry:
        """Retrieve a single memory entry by its UUID."""
        start = datetime.utcnow()
        with tracer.start_as_current_span("memory_service.get_memory"):
            async with get_tenant_session(tenant_id) as session:
                mem = await session.get(MemoryEntry, memory_id)
                if not mem or mem.tenant_id != tenant_id:
                    raise ValueError("Memory entry not found")
                duration = (datetime.utcnow() - start).total_seconds()
                seo_memory_queries_total.labels(operation="read", tenant_id=str(tenant_id)).inc()
                seo_memory_query_duration_seconds.labels(operation="read").observe(duration)
                return mem

    async def list_memory(
        self,
        tenant_id: uuid.UUID,
        entry_type: Optional[MemoryEntryType] = None,
        source: Optional[MemorySource] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[MemoryEntry]:
        """List memory entries for a tenant, optionally filtered by type."""
        start = datetime.utcnow()
        with tracer.start_as_current_span("memory_service.list_memory"):
            async with get_tenant_session(tenant_id) as session:
                stmt = select(MemoryEntry).where(MemoryEntry.tenant_id == tenant_id)
                if entry_type:
                    stmt = stmt.where(MemoryEntry.entry_type == entry_type)
                if source:
                    stmt = stmt.where(MemoryEntry.source == source)
                stmt = stmt.offset(offset).limit(limit)
                result = await session.execute(stmt)
                entries = result.scalars().all()
                duration = (datetime.utcnow() - start).total_seconds()
                seo_memory_queries_total.labels(operation="list", tenant_id=str(tenant_id)).inc()
                seo_memory_query_duration_seconds.labels(operation="list").observe(duration)
                return entries

    async def delete_memory(self, tenant_id: uuid.UUID, memory_id: uuid.UUID) -> None:
        """Delete a memory entry (soft‑delete not supported – permanent removal)."""
        start = datetime.utcnow()
        with tracer.start_as_current_span("memory_service.delete_memory"):
            async with get_tenant_session(tenant_id) as session:
                mem = await session.get(MemoryEntry, memory_id)
                if not mem or mem.tenant_id != tenant_id:
                    raise ValueError("Memory entry not found")
                await session.delete(mem)
                await session.commit()
                await self._audit(tenant_id, "memory_deleted", f"Memory entry {memory_id} deleted", memory_id)
                duration = (datetime.utcnow() - start).total_seconds()
                seo_memory_queries_total.labels(operation="delete", tenant_id=str(tenant_id)).inc()
                seo_memory_query_duration_seconds.labels(operation="delete").observe(duration)

# Export singleton instance
memory_service = MemoryService()
