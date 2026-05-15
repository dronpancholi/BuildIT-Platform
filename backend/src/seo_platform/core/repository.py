"""
SEO Platform — Repository Pattern Base
=========================================
Generic async repository providing typed CRUD operations.

Design principles:
- Type-safe: generic over model and schema types
- Async-first: all operations are async
- Tenant-aware: all queries include tenant_id filtering
- Audit-integrated: mutations emit structured audit events
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from seo_platform.core.database import Base
from seo_platform.core.logging import get_logger

logger = get_logger(__name__)

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """
    Generic async repository for typed database operations.

    All domain repositories inherit from this base, inheriting:
    - get_by_id, get_all, create, update, delete
    - Pagination support
    - Tenant filtering
    - Query builder helpers

    Usage:
        class ClientRepository(BaseRepository[Client]):
            model = Client

            async def get_by_domain(self, session: AsyncSession, tenant_id: UUID, domain: str) -> Client | None:
                stmt = select(self.model).where(
                    self.model.tenant_id == tenant_id,
                    self.model.domain == domain,
                )
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
    """

    model: type[ModelT]

    async def get_by_id(
        self,
        session: AsyncSession,
        entity_id: UUID,
        *,
        tenant_id: UUID | None = None,
    ) -> ModelT | None:
        """
        Fetch a single entity by primary key.

        If tenant_id is provided, additionally filters by tenant_id
        as a defense-in-depth measure (RLS is primary enforcement).
        """
        stmt = select(self.model).where(self.model.id == entity_id)
        if tenant_id and hasattr(self.model, "tenant_id"):
            stmt = stmt.where(self.model.tenant_id == tenant_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        session: AsyncSession,
        *,
        tenant_id: UUID | None = None,
        offset: int = 0,
        limit: int = 50,
        order_by: str | None = None,
    ) -> Sequence[ModelT]:
        """
        Fetch all entities with pagination.

        Default limit: 50 (prevents accidental full-table scans).
        Maximum limit enforced at API layer.
        """
        stmt = select(self.model)
        if tenant_id and hasattr(self.model, "tenant_id"):
            stmt = stmt.where(self.model.tenant_id == tenant_id)
        if order_by and hasattr(self.model, order_by):
            stmt = stmt.order_by(getattr(self.model, order_by).desc())
        elif hasattr(self.model, "created_at"):
            stmt = stmt.order_by(self.model.created_at.desc())
        stmt = stmt.offset(offset).limit(min(limit, 200))
        result = await session.execute(stmt)
        return result.scalars().all()

    async def count(
        self,
        session: AsyncSession,
        *,
        tenant_id: UUID | None = None,
    ) -> int:
        """Count entities, optionally filtered by tenant."""
        stmt = select(func.count()).select_from(self.model)
        if tenant_id and hasattr(self.model, "tenant_id"):
            stmt = stmt.where(self.model.tenant_id == tenant_id)
        result = await session.execute(stmt)
        return result.scalar_one()

    async def create(self, session: AsyncSession, **kwargs: Any) -> ModelT:
        """
        Create a new entity.

        Fields are passed as keyword arguments matching model columns.
        Returns the created entity with database-generated fields populated.
        """
        entity = self.model(**kwargs)
        session.add(entity)
        await session.flush()
        await session.refresh(entity)
        logger.info(
            "entity_created",
            entity_type=self.model.__tablename__,
            entity_id=str(entity.id) if hasattr(entity, "id") else "N/A",
        )
        return entity

    async def update_by_id(
        self,
        session: AsyncSession,
        entity_id: UUID,
        *,
        tenant_id: UUID | None = None,
        **kwargs: Any,
    ) -> ModelT | None:
        """
        Update an entity by primary key.

        Returns the updated entity, or None if not found.
        Only provided fields are updated (partial update).
        """
        entity = await self.get_by_id(session, entity_id, tenant_id=tenant_id)
        if entity is None:
            return None
        for key, value in kwargs.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        await session.flush()
        await session.refresh(entity)
        logger.info(
            "entity_updated",
            entity_type=self.model.__tablename__,
            entity_id=str(entity_id),
            updated_fields=list(kwargs.keys()),
        )
        return entity

    async def delete_by_id(
        self,
        session: AsyncSession,
        entity_id: UUID,
        *,
        tenant_id: UUID | None = None,
    ) -> bool:
        """
        Delete an entity by primary key. Returns True if deleted.

        Note: For audit-critical tables (AuditLog, WorkflowEvent),
        deletion is prevented at the database level via triggers.
        """
        stmt = delete(self.model).where(self.model.id == entity_id)
        if tenant_id and hasattr(self.model, "tenant_id"):
            stmt = stmt.where(self.model.tenant_id == tenant_id)
        result = await session.execute(stmt)
        deleted = result.rowcount > 0
        if deleted:
            logger.info(
                "entity_deleted",
                entity_type=self.model.__tablename__,
                entity_id=str(entity_id),
            )
        return deleted

    async def exists(
        self,
        session: AsyncSession,
        entity_id: UUID,
        *,
        tenant_id: UUID | None = None,
    ) -> bool:
        """Check if an entity exists by ID."""
        stmt = select(func.count()).select_from(self.model).where(self.model.id == entity_id)
        if tenant_id and hasattr(self.model, "tenant_id"):
            stmt = stmt.where(self.model.tenant_id == tenant_id)
        result = await session.execute(stmt)
        return result.scalar_one() > 0
