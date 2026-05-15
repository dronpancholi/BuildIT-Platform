"""
SEO Platform — Redis Client
==============================
Async Redis client with connection pooling, key namespacing, and health checks.

Design principles:
- Tenant-aware key namespacing: {tenant_id}:{key} (no cross-tenant access)
- Connection pooling with health monitoring
- Lua script support for atomic operations (rate limiting, token buckets)
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import redis.asyncio as aioredis

from seo_platform.config import get_settings
from seo_platform.core.logging import get_logger

logger = get_logger(__name__)

_redis_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Get or create the async Redis client (singleton with pool)."""
    global _redis_pool
    if _redis_pool is None:
        settings = get_settings()
        _redis_pool = aioredis.from_url(
            settings.redis.url,
            max_connections=settings.redis.max_connections,
            socket_timeout=settings.redis.socket_timeout,
            socket_connect_timeout=settings.redis.socket_connect_timeout,
            decode_responses=settings.redis.decode_responses,
            health_check_interval=30,
        )
        logger.info("redis_pool_created", host=settings.redis.host, port=settings.redis.port)
    return _redis_pool


async def close_redis() -> None:
    """Close the Redis connection pool."""
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.close()
        _redis_pool = None
        logger.info("redis_pool_closed")


class TenantRedis:
    """
    Tenant-namespaced Redis client wrapper.

    All keys are automatically prefixed with {tenant_id}: to enforce
    data isolation at the cache layer. This prevents accidental
    cross-tenant cache reads/writes.

    Usage:
        redis = TenantRedis(tenant_id=UUID("..."))
        await redis.set("keyword_volume:seo tools", volume_data, ttl=86400)
        data = await redis.get("keyword_volume:seo tools")
    """

    def __init__(self, tenant_id: UUID) -> None:
        self.tenant_id = tenant_id
        self._prefix = f"{tenant_id}:"

    def _key(self, key: str) -> str:
        """Namespace key with tenant prefix."""
        return f"{self._prefix}{key}"

    async def _client(self) -> aioredis.Redis:
        return await get_redis()

    async def get(self, key: str) -> str | None:
        """Get a value by tenant-namespaced key."""
        client = await self._client()
        return await client.get(self._key(key))

    async def set(self, key: str, value: str | bytes, ttl: int | None = None) -> None:
        """Set a value with optional TTL (seconds)."""
        client = await self._client()
        if ttl:
            await client.setex(self._key(key), ttl, value)
        else:
            await client.set(self._key(key), value)

    async def delete(self, key: str) -> int:
        """Delete a key."""
        client = await self._client()
        return await client.delete(self._key(key))

    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        client = await self._client()
        return bool(await client.exists(self._key(key)))

    async def incr(self, key: str, amount: int = 1) -> int:
        """Atomically increment a key."""
        client = await self._client()
        return await client.incrby(self._key(key), amount)

    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL on an existing key."""
        client = await self._client()
        return await client.expire(self._key(key), ttl)

    async def hset(self, key: str, mapping: dict[str, Any]) -> int:
        """Set hash fields."""
        client = await self._client()
        return await client.hset(self._key(key), mapping=mapping)

    async def hget(self, key: str, field: str) -> str | None:
        """Get a hash field."""
        client = await self._client()
        return await client.hget(self._key(key), field)

    async def hgetall(self, key: str) -> dict[str, str]:
        """Get all hash fields."""
        client = await self._client()
        return await client.hgetall(self._key(key))

    async def eval_lua(
        self,
        script: str,
        keys: list[str],
        args: list[Any],
    ) -> Any:
        """Execute a Lua script with tenant-namespaced keys."""
        client = await self._client()
        namespaced_keys = [self._key(k) for k in keys]
        return await client.eval(script, len(namespaced_keys), *namespaced_keys, *args)
