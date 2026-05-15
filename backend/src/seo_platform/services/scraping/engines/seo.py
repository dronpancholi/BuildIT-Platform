"""
SEO Platform — SEO Scraper Engine
==================================
Resilient SERP, PAA, autocomplete extraction with fallback selectors.
"""


from playwright.async_api import Page

from seo_platform.core.cache import operational_cache
from seo_platform.core.logging import get_logger
from seo_platform.services.scraping.base import BaseScraper

logger = get_logger(__name__)


class SERPResult:
    def __init__(self, title: str, url: str, description: str, position: int, confidence: float = 1.0):
        self.title = title
        self.url = url
        self.description = description
        self.position = position
        self.confidence = confidence


class SEOScraperEngine(BaseScraper):
    """
    Hardened SEO scraper with multiple selector fallbacks and confidence scoring.
    """

    SERP_SELECTORS = [
        "div.g",
        "div[data-hk]",
        "div.v4uxe",
        "div.ezO7jd",
        "li.b_algo",
    ]

    TITLE_SELECTORS = [
        "h3",
        "h2",
        "div[data-attrid] a",
        "a.pqEyA",
    ]

    DESC_SELECTORS = [
        "div.VwiC3b",
        "div.UAiS1",
        "span.aCOpRe",
        "div.line_height_1dot25",
    ]

    PAA_SELECTORS = [
        "div.dn799",
        "div.related-question-pair",
        "div.nMdas",
        "div.relatedQuestionsWrapper",
    ]

    def __init__(self):
        super().__init__(service_name="seo_scraper")

    @operational_cache(ttl=43200)
    async def get_serp(self, query: str) -> list[SERPResult]:
        """Extracts top organic results with resilient selectors."""

        async def parse_serp(page: Page) -> list[SERPResult]:
            results = []

            result_extraction = await self._extract_with_fallback(
                page,
                self.SERP_SELECTORS,
                lambda elements: elements,
            )

            if not result_extraction.data:
                logger.warning("no_serp_results_found", query=query)
                return results

            for i, el in enumerate(result_extraction.data[:10]):
                title = ""
                url = ""
                desc = ""

                for selector in self.TITLE_SELECTORS:
                    try:
                        title_el = await el.query_selector(selector)
                        if title_el:
                            title = await title_el.inner_text()
                            break
                    except:
                        continue

                for selector in ["a", "div.r a"]:
                    try:
                        link_el = await el.query_selector(selector)
                        if link_el:
                            url = await link_el.get_attribute("href")
                            break
                    except:
                        continue

                for selector in self.DESC_SELECTORS:
                    try:
                        desc_el = await el.query_selector(selector)
                        if desc_el:
                            desc = await desc_el.inner_text()
                            break
                    except:
                        continue

                if title and url and "http" in url:
                    results.append(SERPResult(
                        title=title[:200],
                        url=url,
                        description=desc[:300],
                        position=i + 1,
                        confidence=result_extraction.confidence,
                    ))

            logger.info("serp_extracted", query=query, count=len(results))
            return results

        return await self.search_google(query, parse_serp)

    async def get_paa(self, query: str) -> list[str]:
        """Extracts People Also Ask questions with fallbacks."""

        async def parse_paa(page: Page) -> list[str]:
            paa_extraction = await self._extract_with_fallback(
                page,
                self.PAA_SELECTORS,
                lambda elements: elements,
            )

            if not paa_extraction.data:
                return []

            questions = []
            for el in paa_extraction.data[:5]:
                try:
                    text = await el.inner_text()
                    if text and len(text) > 10:
                        questions.append(text)
                except:
                    continue

            return questions

        return await self.search_google(query, parse_paa)

    async def get_autocomplete(self, query: str) -> list[str]:
        """Extracts Google autocomplete suggestions."""

        async def parse_autocomplete(page: Page) -> list[str]:
            selectors = [
                "ul.sbct",
                "ul.gBAw7c",
                "div.ulDAd",
                "ul.Aci",
            ]

            extraction = await self._extract_with_fallback(
                page,
                selectors,
                lambda elements: elements,
            )

            if not extraction.data:
                return []

            suggestions = []
            for el in extraction.data[:8]:
                try:
                    text = await el.inner_text()
                    if text and len(text) > 2:
                        suggestions.append(text)
                except:
                    continue

            return suggestions

        url = f"https://www.google.com/complete/search?q={query.replace(' ', '+')}&cp=1"
        return await self.execute_task(url, parse_autocomplete, max_retries=2)


seo_scraper = SEOScraperEngine()
