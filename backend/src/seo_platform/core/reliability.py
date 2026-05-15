"""
SEO Platform — Reliability Infrastructure
============================================
Circuit breaker, rate limiter, and idempotency store.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Coroutine
from enum import Enum
from typing import Any, TypeVar
from uuid import UUID

from seo_platform.core.errors import CircuitOpenError
from seo_platform.core.logging import get_logger

logger = get_logger(__name__)
T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker for external service calls. CLOSED→OPEN→HALF_OPEN→CLOSED."""

    def __init__(self, service_name: str, failure_threshold: int = 5,
                 recovery_timeout: int = 30, success_threshold: int = 2) -> None:
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    async def call(self, func: Callable[..., Coroutine[Any, Any, T]], *args: Any, **kwargs: Any) -> T:
        async with self._lock:
            if self._state == CircuitState.OPEN:
                if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._success_count = 0
                else:
                    raise CircuitOpenError(self.service_name, f"Circuit OPEN for {self.service_name}")
        try:
            result = await func(*args, **kwargs)
            async with self._lock:
                if self._state == CircuitState.HALF_OPEN:
                    self._success_count += 1
                    if self._success_count >= self.success_threshold:
                        self._state = CircuitState.CLOSED
                        logger.info("circuit_closed", service=self.service_name)
                self._failure_count = 0
            return result
        except Exception:
            async with self._lock:
                self._failure_count += 1
                self._last_failure_time = time.monotonic()
                if self._state == CircuitState.HALF_OPEN or self._failure_count >= self.failure_threshold:
                    self._state = CircuitState.OPEN
                    logger.warning("circuit_opened", service=self.service_name, failures=self._failure_count)
            raise


class RateLimitResult:
    def __init__(self, allowed: bool, retry_after_seconds: float = 0.0) -> None:
        self.allowed = allowed
        self.retry_after_seconds = retry_after_seconds


class TokenBucketRateLimiter:
    """Redis Lua token bucket rate limiter for per-tenant, per-operation limits."""

    LUA_SCRIPT = """
    local key = KEYS[1]
    local tokens_req = tonumber(ARGV[1])
    local max_t = tonumber(ARGV[2])
    local refill = tonumber(ARGV[3])
    local now = tonumber(ARGV[4])
    local b = redis.call('HMGET', key, 'tokens', 'last_refill')
    local cur = tonumber(b[1]) or max_t
    local last = tonumber(b[2]) or now
    local refilled = math.min(max_t, cur + ((now - last) * refill))
    if refilled < tokens_req then
        return {0, tostring((tokens_req - refilled) / refill)}
    end
    redis.call('HMSET', key, 'tokens', refilled - tokens_req, 'last_refill', now)
    redis.call('EXPIRE', key, 3600)
    return {1, "0"}
    """

    async def consume(self, tenant_id: UUID, resource: str, tokens: int = 1,
                      max_tokens: int = 1000, refill_rate: float = 10.0) -> RateLimitResult:
        from seo_platform.core.redis import get_redis
        redis = await get_redis()
        result = await redis.eval(self.LUA_SCRIPT, 1, f"rate_limit:{tenant_id}:{resource}",
                                  str(tokens), str(max_tokens), str(refill_rate), str(time.time()))
        return RateLimitResult(allowed=bool(int(result[0])), retry_after_seconds=float(result[1]))


class IdempotencyStore:
    """Redis-backed idempotency store for retry-safe execution."""

    async def get(self, operation_id: str) -> str | None:
        from seo_platform.core.redis import get_redis
        redis = await get_redis()
        return await redis.get(f"idempotency:{operation_id}")

    async def store(self, operation_id: str, result: str, ttl: int = 86400) -> None:
        from seo_platform.core.redis import get_redis
        redis = await get_redis()
        await redis.setex(f"idempotency:{operation_id}", ttl, result)

    async def exists(self, operation_id: str) -> bool:
        from seo_platform.core.redis import get_redis
        redis = await get_redis()
        return bool(await redis.exists(f"idempotency:{operation_id}"))


rate_limiter = TokenBucketRateLimiter()
idempotency_store = IdempotencyStore()
