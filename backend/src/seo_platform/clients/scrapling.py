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

from seo_platform.clients.scrapling_cache import ScraplingCache
from seo_platform.clients.trafilatura import TrafilaturaClient
from seo_platform.core.reliability import CircuitBreaker
from seo_platform.services.provider_health import provider_health_center

logger = logging.getLogger(__name__)

_scrapling_circuit_breaker = CircuitBreaker("scrapling_client", failure_threshold=3, recovery_timeout=30)


class ScraplingResult(BaseModel):
    url: str
    status_code: int
    title: str | None = None
    text_content: str = ""
    html_content: str = ""
    outbound_links: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SERPItem(BaseModel):
    title: str
    url: str
    snippet: str
    position: int


class ScraplingClient:
    """
    Stealth client using Scrapling Fetcher to scrape, bypass blocks,
    and parse HTML content.
    """

    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout

    async def fetch(self, url: str) -> ScraplingResult:
        """
        Fetches and extracts clean content from a target page with 7-day caching.
        """
        cache_val = await ScraplingCache.get("page", {"url": url}, ScraplingResult)
        if cache_val:
            return cache_val

        result = await self._fetch_live(url)

        await ScraplingCache.set("page", {"url": url}, result, ttl=604800)
        return result

    async def _fetch_live(self, url: str) -> ScraplingResult:
        """Live page fetch without caching. Wrapped in circuit breaker."""
        from seo_platform.api.endpoints.realtime.sse import emit_telemetry_event

        async def _do_fetch() -> ScraplingResult:
            try:
                from scrapling import Fetcher

                fetcher = Fetcher(
                    url=url,
                    timeout=self.timeout,
                    auto_match=True,
                )

                title = fetcher.get_title()
                html = fetcher.text

                try:
                    tra_res = await TrafilaturaClient.extract(html, url=url)
                    text_content = tra_res.markdown_content
                except Exception:
                    paragraphs = fetcher.css("p::text").all()
                    text_content = "\n".join(p.strip() for p in paragraphs if p.strip())

                content_quality_warning = len(text_content) < 100

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
                        "content_quality_warning": content_quality_warning,
                        "low_quality": content_quality_warning,
                    },
                )
            except ImportError:
                logger.warning("scrapling_not_installed_falling_back", url=url)
                raise RuntimeError(f"Scrapling library not installed. Install with: pip install scrapling")
            except Exception as e:
                logger.error("scrapling_fetch_failed", url=url, error=str(e))
                raise RuntimeError(f"Scrapling failed for {url}: {e}")

        from uuid import UUID
        import time
        t0 = time.monotonic()
        try:
            await emit_telemetry_event(UUID(int=0), "scrapling_fetch", {"url": url, "status": "started"})
            result = await _scrapling_circuit_breaker.call(_do_fetch)
            latency = (time.monotonic() - t0) * 1000
            await provider_health_center.record_provider_call(
                provider_name="Scrapling",
                latency_ms=latency,
                success=True,
                breaker_state=_scrapling_circuit_breaker.state,
            )
            await emit_telemetry_event(UUID(int=0), "scrapling_fetch", {"url": url, "status": "completed"})
            return result
        except Exception as e:
            latency = (time.monotonic() - t0) * 1000
            await provider_health_center.record_provider_call(
                provider_name="Scrapling",
                latency_ms=latency,
                success=False,
                breaker_state=_scrapling_circuit_breaker.state,
            )
            await emit_telemetry_event(UUID(int=0), "scrapling_fetch", {"url": url, "status": "failed", "error": str(e)})
            raise

    async def extract_ddg_serp(self, query: str, limit: int = 20) -> list[SERPItem]:
        """
        Queries DuckDuckGo HTML with 24-hour caching and pagination.
        """
        cache_payload = {"query": query, "limit": limit}
        cache_val = await ScraplingCache.get("serp", cache_payload, SERPItem)
        if cache_val:
            return cache_val

        result = await self._extract_ddg_serp_live(query, limit)

        await ScraplingCache.set("serp", cache_payload, result, ttl=86400)
        return result

    async def _extract_ddg_serp_live(self, query: str, limit: int = 20) -> list[SERPItem]:
        """Live DuckDuckGo SERP scrape without caching."""
        import time
        from scrapling import Fetcher
        from urllib.parse import unquote

        t0 = time.monotonic()

        results: list[SERPItem] = []
        offset = 0

        while len(results) < limit and offset < 50:
            url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}&s={offset}"
            try:
                fetcher = Fetcher(url=url, timeout=self.timeout, auto_match=True)

                elements = fetcher.css("div.result").all()
                if not elements:
                    break

                for el in elements:
                    title_el = el.css("a.result__a")
                    title = title_el.text().strip() if title_el else ""

                    href = title_el.attrib.get("href") if title_el else ""
                    if "uddg=" in href:
                        href = href.split("uddg=")[-1].split("&")[0]
                        href = unquote(href)

                    snippet_el = el.css("a.result__snippet")
                    snippet = snippet_el.text().strip() if snippet_el else ""

                    if title and href and "duckduckgo.com" not in href:
                        results.append(SERPItem(
                            title=title,
                            url=href,
                            snippet=snippet,
                            position=len(results) + 1,
                        ))
                        if len(results) >= limit:
                            break

                next_btn = fetcher.css("input[value='Next']")
                if not next_btn:
                    break
                offset += 30
            except Exception as e:
                logger.warning("ddg_serp_scrape_page_failed", offset=offset, error=str(e))
                break

        latency = (time.monotonic() - t0) * 1000
        await provider_health_center.record_provider_call(
            provider_name="Scrapling",
            latency_ms=latency,
            success=True,
            breaker_state=_scrapling_circuit_breaker.state,
        )
        return results
