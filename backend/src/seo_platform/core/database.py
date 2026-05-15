"""
SEO Platform — Database Layer
================================
Async SQLAlchemy 2.0 engine, session management, and tenant-isolated connections.

Design principles:
- Async-first: all database operations are async via asyncpg
- Tenant isolation: every session sets app.current_tenant via RLS
- Connection pooling: PgBouncer-aware pool configuration
- Observability: OpenTelemetry instrumentation on every query
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from seo_platform.config import get_settings
from seo_platform.core.auth import get_current_user
from seo_platform.core.logging import get_logger

logger = get_logger(__name__)

__all__ = [
    "Base",
    "get_current_user",
    "get_engine",
    "get_session",
    "get_session_factory",
    "get_tenant_session",
]


# ---------------------------------------------------------------------------
# Declarative Base
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    """
    SQLAlchemy declarative base for all ORM models.

    All models inherit from this base, ensuring consistent metadata
    and enabling Alembic to auto-detect schema changes.
    """

    pass


# ---------------------------------------------------------------------------
# Engine Factory
# ---------------------------------------------------------------------------
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Get or create the async SQLAlchemy engine (singleton)."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database.async_url,
            pool_size=settings.database.pool_size,
            max_overflow=settings.database.max_overflow,
            pool_timeout=settings.database.pool_timeout,
            pool_recycle=settings.database.pool_recycle,
            echo=settings.database.echo,
            # Performance: use server-side cursors for large result sets
            pool_pre_ping=True,
            # JSON serialization: use orjson for performance
            json_serializer=_orjson_serializer,
            json_deserializer=_orjson_deserializer,
        )
        logger.info(
            "database_engine_created",
            host=settings.database.host,
            database=settings.database.db,
            pool_size=settings.database.pool_size,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get or create the async session factory (singleton)."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


# ---------------------------------------------------------------------------
# Session Context Managers
# ---------------------------------------------------------------------------
@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide an async database session.

    Usage:
        async with get_session() as session:
            result = await session.execute(query)

    Sessions are automatically committed on successful exit and
    rolled back on exception.
    """
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


@asynccontextmanager
async def get_tenant_session(tenant_id: UUID) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a tenant-isolated database session.

    Sets PostgreSQL RLS context variable `app.current_tenant` to the
    provided tenant_id. All queries in this session are automatically
    filtered by RLS policies.

    This is the PRIMARY method for getting database sessions in
    application code. Direct `get_session()` should only be used
    for cross-tenant administrative operations.
    """
    factory = get_session_factory()
    session = factory()
    try:
        # SET commands don't support parameterized values in PostgreSQL.
        # The tenant_id is a validated UUID (Python type-checked), so it is
        # safe to format as a literal string. This is NOT user input.
        await session.execute(
            text(f"SET app.current_tenant = '{tenant_id!s}'")
        )
        logger.debug("tenant_session_opened", tenant_id=str(tenant_id))
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        # Reset tenant context on connection return to pool
        try:
            await session.execute(text("RESET app.current_tenant"))
        except Exception:
            pass  # Connection may already be invalidated
        await session.close()


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------
async def init_database() -> None:
    """Initialize database engine and verify connectivity."""
    engine = get_engine()
    async with engine.begin() as conn:
        # Verify connectivity
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1
    logger.info("database_initialized")


async def close_database() -> None:
    """Dispose of the database engine and connection pool."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("database_closed")


# ---------------------------------------------------------------------------
# JSON Serialization (orjson for performance)
# ---------------------------------------------------------------------------
def _orjson_serializer(obj: object) -> str:
    """Serialize Python objects to JSON string using orjson."""
    import orjson

    return orjson.dumps(obj).decode("utf-8")


def _orjson_deserializer(data: str) -> object:
    """Deserialize JSON string to Python objects using orjson."""
    import orjson

    return orjson.loads(data)
