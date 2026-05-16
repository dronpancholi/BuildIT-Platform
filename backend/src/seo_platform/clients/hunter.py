"""
SEO Platform — Hunter.io Client
===================================
Contact email discovery from domain data.

Design: Cache lookups per domain for 30 days.
Only query if prospect passes spam filter (don't waste on junk domains).

No mock data fallback — all calls execute against live API or raise.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from seo_platform.config import get_settings
from seo_platform.core.logging import get_logger
from seo_platform.core.reliability import CircuitBreaker

logger = get_logger(__name__)


class HunterError(Exception):
    """Base exception for Hunter.io API errors."""


class HunterRateLimitError(HunterError):
    """Raised when Hunter returns 429 Too Many Requests."""


class HunterAPIError(HunterError):
    """Raised when Hunter returns a non-2xx response."""


class HunterAuthError(HunterError):
    """Raised when API key is invalid or unauthorized."""


_circuit = CircuitBreaker("hunter_io", failure_threshold=10, recovery_timeout=30)
_semaphore = asyncio.Semaphore(5)


class HunterClient:
    """
    Hunter.io API client for contact email discovery.

    Endpoints used:
    - /v2/domain-search — Find emails associated with a domain
    - /v2/email-finder — Find specific contact email by name + domain
    - /v2/email-verifier — Verify email deliverability
    """

    BASE_URL = "https://api.hunter.io"

    def __init__(self, api_key: str = "") -> None:
        settings = get_settings()
        self.api_key = api_key or settings.hunter.api_key
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                timeout=httpx.Timeout(15.0),
            )
        return self._client

    async def domain_search(self, domain: str, limit: int = 10) -> list[dict[str, Any]]:
        """Find email addresses associated with a domain."""
        client = await self._get_client()
        async with _semaphore:
            response = await _circuit.call(
                client.get, "/v2/domain-search",
                params={"domain": domain, "api_key": self.api_key, "limit": limit},
            )

        if response.status_code == 429:
            raise HunterRateLimitError(f"Hunter rate limit exceeded for domain: {domain}")
        if response.status_code in (401, 403):
            raise HunterAuthError(f"Hunter authentication failed for domain: {domain}")
        response.raise_for_status()

        data = response.json()
        emails = data.get("data", {}).get("emails", [])
        logger.info("hunter_domain_search", domain=domain, results=len(emails))
        return [
            {
                "email": e.get("value", ""),
                "type": e.get("type", ""),
                "confidence": e.get("confidence", 0),
                "first_name": e.get("first_name", ""),
                "last_name": e.get("last_name", ""),
                "position": e.get("position", ""),
            }
            for e in emails
        ]

    async def find_email(self, domain: str, first_name: str, last_name: str) -> dict[str, Any]:
        """Find a specific person's email at a domain."""
        client = await self._get_client()
        async with _semaphore:
            response = await _circuit.call(
                client.get, "/v2/email-finder",
                params={
                    "domain": domain,
                    "first_name": first_name,
                    "last_name": last_name,
                    "api_key": self.api_key,
                },
            )

        if response.status_code == 429:
            raise HunterRateLimitError(f"Hunter rate limit exceeded for {domain}")
        if response.status_code in (401, 403):
            raise HunterAuthError(f"Hunter authentication failed")
        response.raise_for_status()

        data = response.json().get("data", {})
        return {
            "email": data.get("email", ""),
            "confidence": data.get("score", 0),
            "sources": data.get("sources", []),
        }

    async def verify_email(self, email: str) -> dict[str, Any]:
        """Verify email deliverability."""
        client = await self._get_client()
        async with _semaphore:
            response = await _circuit.call(
                client.get, "/v2/email-verifier",
                params={"email": email, "api_key": self.api_key},
            )

        if response.status_code == 429:
            raise HunterRateLimitError(f"Hunter rate limit exceeded for {email}")
        if response.status_code in (401, 403):
            raise HunterAuthError(f"Hunter authentication failed")
        response.raise_for_status()

        data = response.json().get("data", {})
        return {
            "email": email,
            "result": data.get("result", ""),
            "score": data.get("score", 0),
            "status": data.get("status", ""),
        }

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None


hunter_client = HunterClient()
