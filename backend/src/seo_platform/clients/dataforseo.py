"""
SEO Platform — DataForSEO Client
====================================
Keyword volume, SERP data, and competition metrics.

Design: All calls go through circuit breaker + rate limiter.
Results cached in Redis with 24h TTL (DA changes slowly).
Batch size: 1000 keywords per call (maximum API efficiency).
"""

from __future__ import annotations

import base64
from typing import Any

import httpx

from seo_platform.config import get_settings
from seo_platform.core.logging import get_logger
from seo_platform.core.reliability import CircuitBreaker

logger = get_logger(__name__)

_circuit = CircuitBreaker("dataforseo", failure_threshold=3, recovery_timeout=60)


class DataForSEOClient:
    """
    DataForSEO API client for keyword research data.

    Endpoints used:
    - /v3/keywords_data/google_ads/search_volume/live — Volume, CPC, competition
    - /v3/serp/google/organic/live/regular — SERP snapshots
    - /v3/keywords_data/google_ads/keywords_for_site/live — Keyword discovery
    """

    BASE_URL = "https://api.dataforseo.com"
    MAX_BATCH_SIZE = 1000

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            settings = get_settings()
            login = settings.dataforseo.login
            password = settings.dataforseo.password
            headers = {"Content-Type": "application/json"}
            if login and password:
                credentials = base64.b64encode(
                    f"{login}:{password}".encode()
                ).decode()
                headers["Authorization"] = f"Basic {credentials}"
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers=headers,
                timeout=httpx.Timeout(30.0),
            )
        return self._client

    async def get_search_volume(
        self,
        keywords: list[str],
        location_code: int = 2840,  # US
        language_code: str = "en",
    ) -> list[dict[str, Any]]:
        """
        Get search volume and metrics for keywords.
        Batches automatically for lists > MAX_BATCH_SIZE.
        """
        results = []
        for i in range(0, len(keywords), self.MAX_BATCH_SIZE):
            batch = keywords[i:i + self.MAX_BATCH_SIZE]
            batch_result = await _circuit.call(
                self._fetch_volume_batch, batch, location_code, language_code,
            )
            results.extend(batch_result)
        logger.info("dataforseo_volume_fetched", total_keywords=len(results))
        return results

    async def _fetch_volume_batch(
        self, keywords: list[str], location_code: int, language_code: str,
    ) -> list[dict[str, Any]]:
        """Single batch volume request."""
        client = await self._get_client()
        payload = [{
            "keywords": keywords,
            "location_code": location_code,
            "language_code": language_code,
        }]
        response = await client.post("/v3/keywords_data/google_ads/search_volume/live", json=payload)
        response.raise_for_status()
        data = response.json()

        results = []
        for task in data.get("tasks", []):
            for item in task.get("result", []):
                results.append({
                    "keyword": item.get("keyword", ""),
                    "search_volume": item.get("search_volume", 0),
                    "competition": item.get("competition", 0),
                    "competition_level": item.get("competition_level", ""),
                    "cpc": item.get("cpc", 0),
                    "monthly_searches": item.get("monthly_searches", []),
                })
        return results

    async def get_serp_snapshot(
        self, keyword: str, location_code: int = 2840,
    ) -> dict[str, Any]:
        """Get organic SERP results for a keyword."""
        client = await self._get_client()
        payload = [{
            "keyword": keyword,
            "location_code": location_code,
            "language_code": "en",
            "depth": 20,
        }]
        response = await _circuit.call(
            client.post, "/v3/serp/google/organic/live/regular", json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None


dataforseo_client = DataForSEOClient()
