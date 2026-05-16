"""
SEO Platform — Ahrefs Client
================================
Backlink analysis, domain metrics, and competitor research.

Design: Circuit breaker with 5-failure threshold.
DA data cached 7 days (changes slowly).

No mock data fallback — all calls execute against live API or raise.
"""

from __future__ import annotations

from typing import Any

import httpx

from seo_platform.config import get_settings
from seo_platform.core.logging import get_logger
from seo_platform.core.reliability import CircuitBreaker

logger = get_logger(__name__)


class AhrefsError(Exception):
    """Base exception for Ahrefs API errors."""


class AhrefsRateLimitError(AhrefsError):
    """Raised when Ahrefs returns 429 Too Many Requests."""


class AhrefsAPIError(AhrefsError):
    """Raised when Ahrefs returns a non-2xx response."""


class AhrefsAuthError(AhrefsError):
    """Raised when API key is invalid or unauthorized."""


_circuit = CircuitBreaker("ahrefs", failure_threshold=5, recovery_timeout=30)


class AhrefsClient:
    """
    Ahrefs v3 API client.

    Endpoints used:
    - /v3/site-explorer/backlinks — Competitor backlink profiles
    - /v3/site-explorer/domain-rating — Domain Authority/Rating
    - /v3/site-explorer/referring-domains — Referring domain analysis
    """

    BASE_URL = "https://api.ahrefs.com"

    def __init__(self, api_key: str = "") -> None:
        settings = get_settings()
        self.api_key = api_key or settings.ahrefs.api_key
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=httpx.Timeout(30.0),
            )
        return self._client

    async def get_domain_rating(self, domain: str) -> dict[str, Any]:
        """Get Domain Rating (DR) for a domain."""
        client = await self._get_client()
        response = await _circuit.call(
            client.get, "/v3/site-explorer/domain-rating",
            params={"target": domain, "output": "json"},
        )
        response.raise_for_status()
        data = response.json()
        return {
            "domain": domain,
            "domain_rating": data.get("domain_rating", 0),
            "ahrefs_rank": data.get("ahrefs_rank", 0),
        }

    async def get_backlinks(
        self, domain: str, limit: int = 100, mode: str = "exact",
    ) -> list[dict[str, Any]]:
        """Get backlinks pointing to a domain."""
        client = await self._get_client()
        response = await _circuit.call(
            client.get, "/v3/site-explorer/backlinks",
            params={"target": domain, "mode": mode, "limit": limit, "output": "json"},
        )
        response.raise_for_status()
        data = response.json()
        return data.get("backlinks", [])

    async def get_referring_domains(
        self, domain: str, limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get referring domains for competitor analysis."""
        client = await self._get_client()
        response = await _circuit.call(
            client.get, "/v3/site-explorer/referring-domains",
            params={"target": domain, "limit": limit, "output": "json"},
        )
        response.raise_for_status()
        data = response.json()
        return data.get("referring_domains", [])

    async def get_domain_metrics(self, domain: str) -> dict[str, Any]:
        """Get comprehensive domain metrics from Ahrefs API."""
        client = await self._get_client()
        response = await _circuit.call(
            client.get, "/v3/site-explorer/overview",
            params={"target": domain, "output": "json"},
        )

        if response.status_code == 429:
            raise AhrefsRateLimitError(f"Ahrefs rate limit exceeded for domain: {domain}")
        if response.status_code == 401 or response.status_code == 403:
            raise AhrefsAuthError(f"Ahrefs authentication failed for domain: {domain}")
        response.raise_for_status()

        data = response.json()
        return {
            "domain": domain,
            "domain_rating": data.get("domain_rating", 0),
            "ref_domains": data.get("referring_domains", 0),
            "backlinks": data.get("backlinks", 0),
            "organic_keywords": data.get("organic_keywords", 0),
            "organic_traffic": data.get("organic_traffic", 0),
        }

    async def get_traffic_history(self, domain: str, months: int = 24) -> list[dict[str, Any]]:
        """
        Get monthly organic traffic and referring domains history over the last N months.
        Used to detect Google Helpful Content Update (HCU) penalties and declining trajectories.
        """
        client = await self._get_client()
        response = await _circuit.call(
            client.get, "/v3/site-explorer/metrics-history",
            params={"target": domain, "history_range": f"{months}m", "output": "json"},
        )

        if response.status_code == 429:
            raise AhrefsRateLimitError(f"Ahrefs rate limit exceeded for domain history: {domain}")
        if response.status_code == 401 or response.status_code == 403:
            raise AhrefsAuthError(f"Ahrefs authentication failed for domain history: {domain}")
        response.raise_for_status()

        data = response.json()
        return data.get("metrics_history", [])

    async def get_outgoing_links_summary(self, domain: str) -> dict[str, Any]:
        """
        Get total outgoing linked domains vs referring domains.
        Used to calculate outbound-to-inbound link ratio (detecting link farms).
        """
        client = await self._get_client()
        response = await _circuit.call(
            client.get, "/v3/site-explorer/outgoing-linked-domains-summary",
            params={"target": domain, "output": "json"},
        )

        if response.status_code == 429:
            raise AhrefsRateLimitError(f"Ahrefs rate limit exceeded for outgoing links: {domain}")
        if response.status_code == 401 or response.status_code == 403:
            raise AhrefsAuthError(f"Ahrefs authentication failed for outgoing links: {domain}")
        response.raise_for_status()

        data = response.json()
        return {
            "domain": domain,
            "outgoing_linked_domains": data.get("outgoing_linked_domains", 0),
            "outgoing_external_links": data.get("outgoing_external_links", 0),
            "outgoing_dofollow_links": data.get("outgoing_dofollow_links", 0),
        }

    async def get_anchor_text_profile(self, domain: str, limit: int = 100) -> list[dict[str, Any]]:
        """
        Get top anchor texts pointing to the domain.
        Used to detect toxic anchor text profiles (e.g. gambling/pharmaceutical injection).
        """
        client = await self._get_client()
        response = await _circuit.call(
            client.get, "/v3/site-explorer/anchors",
            params={"target": domain, "limit": limit, "output": "json"},
        )

        if response.status_code == 429:
            raise AhrefsRateLimitError(f"Ahrefs rate limit exceeded for anchors: {domain}")
        if response.status_code == 401 or response.status_code == 403:
            raise AhrefsAuthError(f"Ahrefs authentication failed for anchors: {domain}")
        response.raise_for_status()

        data = response.json()
        return data.get("anchors", [])

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None


ahrefs_client = AhrefsClient()
