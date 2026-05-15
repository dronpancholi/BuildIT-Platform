"""
SEO Platform — Backlink & Citation Scraper
===========================================
Resilient backlink and citation discovery with multiple selector fallbacks.
"""

from typing import Any

from playwright.async_api import Page

from seo_platform.core.logging import get_logger
from seo_platform.services.scraping.base import BaseScraper

logger = get_logger(__name__)


class BacklinkScraperEngine(BaseScraper):
    """
    Hardened backlink discovery with resilient selectors and fallback logic.
    """

    BACKLINK_SELECTORS = [
        "cite",
        "div.yuRUbf a",
        "div.g a",
        "div.v4uxe a",
        "a.analytics-link",
    ]

    CITATION_SELECTORS = [
        "div.yuRUbf a",
        "div.g a",
        "div.ellip a",
        "h3 a",
    ]

    def __init__(self):
        super().__init__(service_name="backlink_scraper")

    async def discover_backlinks(self, domain: str) -> list[dict[str, Any]]:
        """
        Uses search operators to discover public backlink records.
        Returns list of backlink data with confidence scores.
        """
        query = f"link:{domain} -site:{domain} -site:www.{domain}"

        async def parse_backlinks(page: Page) -> list[dict[str, Any]]:
            backlinks = []

            extraction = await self._extract_with_fallback(
                page,
                self.BACKLINK_SELECTORS,
                lambda elements: elements,
            )

            if not extraction.data:
                return backlinks

            seen_domains = set()
            for el in extraction.data:
                try:
                    text = await el.inner_text()
                    href = await el.get_attribute("href")

                    if text and "http" in text:
                        domain_match = text.replace("http://", "").replace("https://", "").split("/")[0]
                    elif href:
                        domain_match = href.replace("http://", "").replace("https://", "").split("/")[0]
                    else:
                        continue

                    if domain_match and domain_match not in seen_domains:
                        seen_domains.add(domain_match)
                        backlinks.append({
                            "domain": domain_match,
                            "url": text if "http" in text else f"https://{domain_match}",
                            "source_url": href or "",
                            "confidence": extraction.confidence,
                        })
                except Exception as e:
                    logger.debug("backlink_parse_error", error=str(e))
                    continue

            logger.info("backlinks_discovered", domain=domain, count=len(backlinks))
            return backlinks

        return await self.search_google(query, parse_backlinks)

    async def discover_citations(self, business_name: str, phone: str) -> list[dict[str, Any]]:
        """
        Uses NAP footprints to discover existing local citations.
        """
        query = f'"{business_name}" "{phone}"'

        async def parse_citations(page: Page) -> list[dict[str, Any]]:
            citations = []

            extraction = await self._extract_with_fallback(
                page,
                self.CITATION_SELECTORS,
                lambda elements: elements,
            )

            if not extraction.data:
                return citations

            seen_urls = set()
            for el in extraction.data:
                try:
                    href = await el.get_attribute("href")
                    if href and "http" in href and href not in seen_urls:
                        seen_urls.add(href)
                        citations.append({
                            "url": href,
                            "domain": href.replace("http://", "").replace("https://", "").split("/")[0],
                            "confidence": extraction.confidence,
                        })
                except Exception as e:
                    logger.debug("citation_parse_error", error=str(e))
                    continue

            logger.info("citations_discovered", business_name=business_name, count=len(citations))
            return citations

        return await self.search_google(query, parse_citations)

    async def discover_competitor_backlinks(self, competitor_domain: str) -> list[dict[str, Any]]:
        """Discover backlinks pointing to competitor domains."""
        query = f"link:{competitor_domain}"
        return await self.discover_backlinks(competitor_domain)


backlink_scraper = BacklinkScraperEngine()
