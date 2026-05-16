"""
SEO Platform — Firecrawl Client
=================================
AI-powered headless website scraper with markdown output.
Circuit-breaker wrapped. Graceful empty API key fallback.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import httpx

from seo_platform.config import get_settings
from seo_platform.core.logging import get_logger
from seo_platform.core.reliability import CircuitBreaker

logger = get_logger(__name__)


class FirecrawlError(Exception):
    """Base exception for Firecrawl API errors."""


class FirecrawlRateLimitError(FirecrawlError):
    """Raised when Firecrawl returns 429."""


class FirecrawlAuthError(FirecrawlError):
    """Raised when API key is invalid (401/403)."""


class FirecrawlScrapeError(FirecrawlError):
    """Raised when scraping fails."""


@dataclass
class FirecrawlScrapeResult:
    url: str
    markdown: str = ""
    html: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    success: bool = False
    error: str = ""


_circuit = CircuitBreaker("firecrawl", failure_threshold=3, recovery_timeout=30)
_semaphore = asyncio.Semaphore(5)


class FirecrawlClient:
    """
    Firecrawl API v1 client for deep headless website scraping.

    Endpoints used:
    - /v1/scrape — Full page scrape returning markdown + metadata
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.firecrawl.api_key
        self.api_url = settings.firecrawl.api_url
        self.timeout = settings.firecrawl.request_timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers: dict[str, str] = {
                "Content-Type": "application/json",
            }
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._client = httpx.AsyncClient(
                base_url=self.api_url.rstrip("/"),
                headers=headers,
                timeout=httpx.Timeout(self.timeout),
            )
        return self._client

    async def scrape_url(
        self,
        url: str,
        formats: list[str] | None = None,
    ) -> FirecrawlScrapeResult:
        """
        Scrape a URL via Firecrawl. Returns markdown, HTML, and metadata.

        Args:
            url: Full URL to scrape (e.g. https://example.com)
            formats: Output formats (default: ["markdown", "html"])

        Returns:
            FirecrawlScrapeResult with scraped content and metadata.
        """
        if formats is None:
            formats = ["markdown", "html"]

        if not self.api_key:
            logger.info("firecrawl_skipped_no_api_key", url=url)
            return FirecrawlScrapeResult(
                url=url, success=False, error="no_api_key"
            )

        result = FirecrawlScrapeResult(url=url)
        client = await self._get_client()

        try:
            async with _semaphore:
                response = await _circuit.call(
                    client.post,
                    "/scrape",
                    json={
                        "url": url,
                        "formats": formats,
                        "onlyMainContent": True,
                    },
                )

            if response.status_code == 429:
                raise FirecrawlRateLimitError(f"Firecrawl rate limited: {url}")
            if response.status_code in (401, 403):
                raise FirecrawlAuthError("Firecrawl authentication failed")
            response.raise_for_status()

            data = response.json()
            scrape_data = data.get("data", {})

            result.markdown = scrape_data.get("markdown", "")
            result.html = scrape_data.get("html", "")
            result.metadata = scrape_data.get("metadata", {})
            result.success = True

            logger.info(
                "firecrawl_scrape_success",
                url=url,
                markdown_len=len(result.markdown),
                title=result.metadata.get("title", ""),
            )

        except FirecrawlError:
            raise
        except Exception as e:
            logger.warning("firecrawl_scrape_failed", url=url, error=str(e))
            result.error = str(e)

        return result

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None


firecrawl_client = FirecrawlClient()
