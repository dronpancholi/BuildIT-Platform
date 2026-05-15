"""
SEO Platform — Aggressive Operational Caching
===============================================
Ensures zero-cost data extraction is efficient by caching SERPs,
contact info, and scraped data in Redis + Local Filesystem.
"""

import functools
import hashlib
import json

from redis import Redis

from seo_platform.config import get_settings
from seo_platform.core.logging import get_logger

logger = get_logger(__name__)

def operational_cache(ttl: int = 86400):
    """
    Decorator to cache scraping results for 24 hours by default.
    Uses Redis as the primary store.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            settings = get_settings()
            redis = Redis(host=settings.redis.host, port=settings.redis.port, db=settings.redis.db)

            # Generate cache key from function name + args
            key_data = f"{func.__name__}:{args}:{kwargs}"
            cache_key = f"cache:{hashlib.sha256(key_data.encode()).hexdigest()}"

            # Try to fetch from cache
            cached_val = redis.get(cache_key)
            if cached_val:
                logger.info("cache_hit", key=cache_key)
                return json.loads(cached_val)

            # Execute and store
            result = await func(*args, **kwargs)

            try:
                # Basic serialization for Pydantic/Lists/Dicts
                serialized = json.dumps(result, default=lambda x: x.dict() if hasattr(x, 'dict') else str(x))
                redis.setex(cache_key, ttl, serialized)
                logger.info("cache_stored", key=cache_key)
            except Exception as e:
                logger.warning("cache_storage_failed", error=str(e))

            return result
        return wrapper
    return decorator
