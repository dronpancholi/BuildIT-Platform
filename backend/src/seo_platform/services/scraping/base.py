"""
SEO Platform — Base Scraping Infrastructure
===========================================
Provides deterministic, resilient Playwright-based browser automation.
Features:
- Browser reuse for efficiency
- Retry logic with exponential backoff
- Multiple selector fallbacks
- Anti-bot evasion
- Rate limiting
- Extraction confidence scoring
- Structured normalization
- Session persistence
"""

import asyncio
import random
import time
from collections.abc import Callable
from typing import Any

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from seo_platform.config import get_settings
from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


class ExtractionResult:
    """Result with confidence scoring for deterministic quality assessment."""
    def __init__(self, data: Any, confidence: float, selectors_used: list[str] = None):
        self.data = data
        self.confidence = confidence
        self.selectors_used = selectors_used or []


class BaseScraper:
    """
    Resilient scraper foundation with:
    - Browser reuse to avoid repeated launches
    - Retry with exponential backoff
    - Multiple selector fallbacks
    - Anti-bot handling
    - Rate limiting
    - Confidence scoring
    """

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.settings = get_settings()
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._last_request_time = 0
        self._min_request_interval = 2.0

    async def _get_browser(self) -> Browser:
        """Reuse browser instance for efficiency."""
        if self._browser is None or not self._browser.is_connected():
            p = await async_playwright().start()
            self._browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                ]
            )
            self._context = await self._browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
            )
            self._context.set_default_timeout(30000)
        return self._browser

    async def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            await asyncio.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    async def _extract_with_fallback(
        self,
        page: Page,
        selectors: list[str],
        extractor: Callable[[Any], Any],
    ) -> ExtractionResult:
        """
        Try multiple selectors with fallbacks and return confidence score.
        """
        for i, selector in enumerate(selectors):
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    data = extractor(elements)
                    confidence = 1.0 - (i * 0.2)
                    return ExtractionResult(
                        data=data,
                        confidence=confidence,
                        selectors_used=selectors[:i+1],
                    )
            except Exception as e:
                logger.debug("selector_failed", selector=selector, error=str(e))
                continue

        return ExtractionResult(data=None, confidence=0.0, selectors_used=[])

    async def execute_task(
        self,
        url: str,
        parser: Callable[[Page], Any],
        max_retries: int = 3,
    ) -> Any:
        """
        Execute scraping task with retry logic and exponential backoff.
        """
        logger.info("scraping_task_started", service=self.service_name, url=url)

        for attempt in range(max_retries):
            try:
                await self._rate_limit()

                browser = await self._get_browser()
                page = await self._context.new_page()

                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    await asyncio.sleep(random.uniform(1, 3))

                    result = await parser(page)

                    logger.info("scraping_task_completed", service=self.service_name, attempt=attempt + 1)
                    return result

                finally:
                    await page.close()

            except Exception as e:
                logger.warning("scraping_attempt_failed", service=self.service_name, attempt=attempt + 1, error=str(e))
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("scraping_all_retries_failed", service=self.service_name, url=url)
                    raise

    async def search_google(self, query: str, parser: Callable[[Page], Any]) -> Any:
        """Helper for Google Search with anti-bot handling."""
        safe_query = query.replace(" ", "+").replace("'", "%27")
        url = f"https://www.google.com/search?q={safe_query}&hl=en&gl=us"
        return await self.execute_task(url, parser)

    async def close(self) -> None:
        """Clean up browser resources."""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        self._browser = None
        self._context = None
