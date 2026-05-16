"""
SEO Platform — Aggressive Operational Caching
===============================================
Ensures zero-cost data extraction is efficient by caching SERPs,
contact info, and scraped data in Redis via the shared async pool.
"""

import functools
import hashlib
import json

from seo_platform.core.logging import get_logger
from seo_platform.core.redis import get_redis

logger = get_logger(__name__)


def operational_cache(ttl: int = 86400):
    """
    Decorator to cache async function results in Redis.

    Uses the platform's shared async Redis pool (``get_redis()``) instead of
    creating a new synchronous connection per call.  Cache keys are
    deterministic SHA-256 hashes of ``{function_name}:{args}:{kwargs}``.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            key_data = f"{func.__name__}:{args}:{kwargs}"
            cache_key = f"cache:{hashlib.sha256(key_data.encode()).hexdigest()}"

            redis = await get_redis()
            cached_val = await redis.get(cache_key)
            if cached_val:
                logger.info("cache_hit", key=cache_key)
                return json.loads(cached_val)

            result = await func(*args, **kwargs)

            try:
                serialized = json.dumps(
                    result,
                    default=lambda x: x.model_dump() if hasattr(x, "model_dump") else str(x),
                )
                await redis.setex(cache_key, ttl, serialized)
                logger.info("cache_stored", key=cache_key)
            except Exception as e:
                logger.warning("cache_storage_failed", error=str(e))

            return result
        return wrapper
    return decorator
