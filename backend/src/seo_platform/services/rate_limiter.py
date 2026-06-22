"""
SEO Platform — Rate Limiter Service
====================================
Token bucket rate limiting using in-memory tracking (Redis-ready).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)

# In-memory rate tracking
_rate_buckets: dict[str, dict] = {}


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""

    allowed: bool
    wait_seconds: float = 0
    remaining: dict = field(default_factory=dict)


class RateLimiter:
    """
    Token bucket rate limiting.

    Limits:
    - Per-site (e.g., max 10 req/min to truelocal.com.au)
    - Per-credential (e.g., max 5 req/min per Yelp account)
    - Per-proxy (e.g., max 60 req/min per proxy IP)
    - Global (e.g., max 1000 req/hour overall)
    """

    def _get_bucket(self, key: str) -> dict:
        """Get or create rate bucket for key."""
        if key not in _rate_buckets:
            _rate_buckets[key] = {
                "minute": [],
                "hour": [],
                "day": [],
            }
        return _rate_buckets[key]

    async def check_rate_limit(
        self,
        key: str,
        requests_per_minute: int = 10,
        requests_per_hour: int = 100,
        requests_per_day: int = 500,
    ) -> RateLimitResult:
        """
        Check if request is allowed under rate limits.
        """
        now = time.time()
        bucket = self._get_bucket(key)

        # Clean old timestamps
        bucket["minute"] = [t for t in bucket["minute"] if now - t < 60]
        bucket["hour"] = [t for t in bucket["hour"] if now - t < 3600]
        bucket["day"] = [t for t in bucket["day"] if now - t < 86400]

        remaining = {
            "minute": max(0, requests_per_minute - len(bucket["minute"])),
            "hour": max(0, requests_per_hour - len(bucket["hour"])),
            "day": max(0, requests_per_day - len(bucket["day"])),
        }

        # Check limits
        if len(bucket["minute"]) >= requests_per_minute:
            wait = 60 - (now - bucket["minute"][0]) if bucket["minute"] else 0
            return RateLimitResult(allowed=False, wait_seconds=wait, remaining=remaining)

        if len(bucket["hour"]) >= requests_per_hour:
            wait = 3600 - (now - bucket["hour"][0]) if bucket["hour"] else 0
            return RateLimitResult(allowed=False, wait_seconds=wait, remaining=remaining)

        if len(bucket["day"]) >= requests_per_day:
            wait = 86400 - (now - bucket["day"][0]) if bucket["day"] else 0
            return RateLimitResult(allowed=False, wait_seconds=wait, remaining=remaining)

        return RateLimitResult(allowed=True, remaining=remaining)

    async def record_request(self, key: str) -> None:
        """Record successful request for rate tracking."""
        now = time.time()
        bucket = self._get_bucket(key)
        bucket["minute"].append(now)
        bucket["hour"].append(now)
        bucket["day"].append(now)

    async def acquire(
        self,
        key: str,
        requests_per_minute: int = 10,
        requests_per_hour: int = 100,
        requests_per_day: int = 500,
        timeout_seconds: int = 30,
    ) -> Optional[float]:
        """
        Acquire rate limit slot. Wait if necessary up to timeout.
        Returns wait_time_seconds if acquired, None if timed out.
        """
        start = time.time()
        while time.time() - start < timeout_seconds:
            result = await self.check_rate_limit(
                key, requests_per_minute, requests_per_hour, requests_per_day
            )
            if result.allowed:
                await self.record_request(key)
                return 0
            if result.wait_seconds > 0:
                import asyncio
                await asyncio.sleep(min(result.wait_seconds, 1))
        return None

    async def get_stats(self, key: str) -> dict:
        """Get rate limit stats for a key."""
        now = time.time()
        bucket = self._get_bucket(key)

        bucket["minute"] = [t for t in bucket["minute"] if now - t < 60]
        bucket["hour"] = [t for t in bucket["hour"] if now - t < 3600]
        bucket["day"] = [t for t in bucket["day"] if now - t < 86400]

        return {
            "minute_requests": len(bucket["minute"]),
            "hour_requests": len(bucket["hour"]),
            "day_requests": len(bucket["day"]),
        }


rate_limiter = RateLimiter()
