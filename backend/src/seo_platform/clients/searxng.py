"""
SEO Platform — SearXNG Client
================================
Type-safe HTTP client wrapper for querying local SearXNG search aggregators.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SearXNGResultItem(BaseModel):
    title: str
    url: str
    content: str
    score: float = 0.0
    engine: str = "unknown"
    position: int = 1


class SearXNGResponse(BaseModel):
    query: str
    results: list[SearXNGResultItem] = Field(default_factory=list)
    unresponsive_engines: list[str] = Field(default_factory=list)


class SearXNGClient:
    """
    Client wrapper for local SearXNG instances.
    Provides multi-engine search capabilities for sandbox mode.
    """

    def __init__(self, base_url: str = "http://localhost:8080", timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def search(self, query: str, engines: list[str] | None = None) -> SearXNGResponse:
        """
        Executes search queries against SearXNG and returns parsed results.
        """
        params: dict[str, Any] = {
            "q": query,
            "format": "json",
        }
        if engines:
            params["engines"] = ",".join(engines)

        url = f"{self.base_url}/search"
        logger.info("searxng_query_initiated", url=url, query=query)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                if response.status_code != 200:
                    raise RuntimeError(f"SearXNG returned status {response.status_code}")

                data = response.json()
                raw_results = data.get("results", [])

                parsed_items = []
                for idx, item in enumerate(raw_results):
                    if "url" in item and "title" in item:
                        parsed_items.append(SearXNGResultItem(
                            title=item.get("title", ""),
                            url=item.get("url", ""),
                            content=item.get("content", "") or item.get("snippet", ""),
                            score=item.get("score", 0.0),
                            engine=item.get("engine", "unknown"),
                            position=idx + 1,
                        ))

                return SearXNGResponse(
                    query=query,
                    results=parsed_items,
                    unresponsive_engines=data.get("unresponsive_engines", []),
                )
        except Exception as e:
            logger.error("searxng_request_failed", query=query, error=str(e))
            raise RuntimeError(f"SearXNG search request failed: {e}")
