"""
SEO Platform — Retry Handler Service
======================================
Exponential backoff with jitter for resilient operations.
"""

from __future__ import annotations

import asyncio
import random
from typing import Any, Callable, Optional

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


class RetryHandler:
    """
    Handles retry logic with exponential backoff and jitter.

    Strategies:
    - Exponential backoff: 2s, 4s, 8s, 16s (max)
    - Jitter: Add random 0-1s to prevent thundering herd
    - Per-error-type backoff: Captchas get longer waits
    - Circuit breaker: Stop after N consecutive failures
    """

    def __init__(self, circuit_breaker_threshold: int = 5):
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self._consecutive_failures = 0
        self._circuit_open = False

    async def retry_with_backoff(
        self,
        func: Callable,
        max_attempts: int = 3,
        base_delay: float = 2.0,
        backoff_multiplier: float = 2.0,
        max_delay: float = 60.0,
        jitter: bool = True,
        retry_on: tuple = (Exception,),
    ) -> Any:
        """
        Execute function with retry logic.

        Example:
            result = await retry_handler.retry_with_backoff(
                func=lambda: submit_form(page, data),
                max_attempts=3,
                base_delay=2.0,
                retry_on=(TimeoutError, RateLimitError)
            )
        """
        if self._circuit_open:
            logger.warning("circuit_breaker_open")
            raise RuntimeError("Circuit breaker is open. Too many consecutive failures.")

        last_exception = None
        for attempt in range(max_attempts):
            try:
                result = await func()
                self._consecutive_failures = 0
                return result
            except retry_on as e:
                last_exception = e
                self._consecutive_failures += 1

                if self._consecutive_failures >= self.circuit_breaker_threshold:
                    self._circuit_open = True
                    logger.error(
                        "circuit_breaker_triggered",
                        failures=self._consecutive_failures,
                    )
                    raise

                delay = self.calculate_delay(attempt, type(e).__name__, base_delay, backoff_multiplier, max_delay, jitter)
                logger.warning(
                    "retry_attempt",
                    attempt=attempt + 1,
                    max_attempts=max_attempts,
                    delay=round(delay, 2),
                    error=str(e),
                )
                await asyncio.sleep(delay)

        raise last_exception

    def calculate_delay(
        self,
        attempt: int,
        error_type: str | None = None,
        base_delay: float = 2.0,
        backoff_multiplier: float = 2.0,
        max_delay: float = 60.0,
        jitter: bool = True,
    ) -> float:
        """
        Calculate delay for given attempt.

        error_type affects base_delay:
        - 'captcha': 30s base (they need human time)
        - 'rate_limit': 60s base (site is protecting themselves)
        - 'timeout': 5s base (might be temporary)
        - default: 2s base
        """
        adjusted_base = base_delay
        if error_type:
            error_lower = error_type.lower()
            if "captcha" in error_lower:
                adjusted_base = 30.0
            elif "rate" in error_lower and "limit" in error_lower:
                adjusted_base = 60.0
            elif "timeout" in error_lower:
                adjusted_base = 5.0

        delay = adjusted_base * (backoff_multiplier ** attempt)
        if jitter:
            delay += random.uniform(0, 1)
        return min(delay, max_delay)

    def reset_circuit_breaker(self) -> None:
        """Manually reset circuit breaker."""
        self._consecutive_failures = 0
        self._circuit_open = False
        logger.info("circuit_breaker_reset")

    @property
    def is_circuit_open(self) -> bool:
        return self._circuit_open


retry_handler = RetryHandler()
