"""
SEO Platform — Scrapling Client
==================================
Stealth scraper using the Scrapling library to fetch, bypass bot filters,
and parse HTML content for SEO data extraction.

Design: Mimics realistic browser headers. Zero-cost fallback provider.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ScraplingResult(BaseModel):
    url: str
    status_code: int
    title: str | None = None
    text_content: str = ""
    html_content: str = ""
    outbound_links: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScraplingClient:
    """
    Stealth client using Scrapling Fetcher to scrape, bypass blocks,
    and parse HTML content.
    """

    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout

    async def fetch(self, url: str) -> ScraplingResult:
        """
        Fetches and extracts clean content from a target page.

        Uses Scrapling's auto-matching headers for stealth and falls
        back gracefully on failure via deterministic defaults.
        """
        try:
            from scrapling import Fetcher

            fetcher = Fetcher(
                url=url,
                timeout=self.timeout,
                auto_match=True,
            )

            title = fetcher.get_title()
            html = fetcher.text

            paragraphs = fetcher.css("p::text").all()
            text_content = "\n".join(p.strip() for p in paragraphs if p.strip())

            links = fetcher.css("a::attr(href)").all()
            outbound_links = list(set(l for l in links if isinstance(l, str) and l.startswith("http")))

            return ScraplingResult(
                url=url,
                status_code=fetcher.status_code,
                title=title,
                text_content=text_content,
                html_content=html,
                outbound_links=outbound_links,
                metadata={
                    "load_time": getattr(fetcher, "load_time", 0),
                    "headers": dict(fetcher.headers) if hasattr(fetcher, "headers") else {},
                },
            )
        except ImportError:
            logger.warning("scrapling_not_installed_falling_back", url=url)
            raise RuntimeError(f"Scrapling library not installed. Install with: pip install scrapling")
        except Exception as e:
            logger.error("scrapling_fetch_failed", url=url, error=str(e))
            raise RuntimeError(f"Scrapling failed for {url}: {e}")
