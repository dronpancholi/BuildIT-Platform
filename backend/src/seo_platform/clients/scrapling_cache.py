"""
SEO Platform — Scrapling Cache
=================================
Type-safe Redis caching manager for Scrapling queries using the shared
async Redis connection pool. Guarantees proper object reconstruction.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from typing import Any, Type, TypeVar

from pydantic import BaseModel

from seo_platform.core.logging import get_logger
from seo_platform.core.redis import get_redis

logger = get_logger(__name__)

T = TypeVar("T")


class ScraplingCache:
    @staticmethod
    def _generate_key(prefix: str, payload: Any) -> str:
        serialized = json.dumps(payload, sort_keys=True)
        h = hashlib.sha256(serialized.encode()).hexdigest()
        return f"scrapling:{prefix}:{h}"

    @classmethod
    async def get(cls, prefix: str, payload: Any, expected_type: Type[T]) -> T | list[T] | None:
        try:
            redis = await get_redis()
            key = cls._generate_key(prefix, payload)
            data = await redis.get(key)
            if not data:
                return None

            raw = json.loads(data)
            logger.info("scrapling_cache_hit", key=key)

            if isinstance(raw, list):
                return [cls._deserialize_item(item, expected_type) for item in raw]

            return cls._deserialize_item(raw, expected_type)
        except Exception as e:
            logger.warning("scrapling_cache_read_failed", error=str(e))
            return None

    @classmethod
    async def set(cls, prefix: str, payload: Any, value: Any, ttl: int) -> None:
        try:
            redis = await get_redis()
            key = cls._generate_key(prefix, payload)

            if isinstance(value, list):
                serialized = json.dumps([cls._serialize_item(item) for item in value])
            else:
                serialized = json.dumps(cls._serialize_item(value))

            await redis.setex(key, ttl, serialized)
            logger.info("scrapling_cache_stored", key=key, ttl=ttl)
        except Exception as e:
            logger.warning("scrapling_cache_write_failed", error=str(e))

    @staticmethod
    def _serialize_item(item: Any) -> Any:
        if isinstance(item, BaseModel):
            return item.model_dump()
        elif is_dataclass(item):
            return asdict(item)
        return item

    @staticmethod
    def _deserialize_item(data: Any, expected_type: Type[T]) -> T:
        if issubclass(expected_type, BaseModel):
            return expected_type.model_validate(data)
        elif is_dataclass(expected_type):
            return expected_type(**data)
        return data
