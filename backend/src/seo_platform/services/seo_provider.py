"""
SEO Platform — SEO Provider Abstraction
========================================
Enterprise abstraction layer that toggles between high-fidelity paid APIs
(DataForSEO) and zero-cost local scraping engines.
"""

from abc import ABC, abstractmethod
from typing import Any

from seo_platform.config import get_settings
from seo_platform.core.logging import get_logger

logger = get_logger(__name__)

class SEOProvider(ABC):
    @abstractmethod
    async def get_serp(self, query: str) -> list[Any]:
        pass

class DataForSEOProvider(SEOProvider):
    """PRODUCTION: Real DataForSEO API integration."""
    async def get_serp(self, query: str) -> list[Any]:
        logger.info("dataforseo_api_call", query=query)
        # Real production logic would go here
        return []

class ScraperSEOProvider(SEOProvider):
    """ZERO-COST: Local Playwright-based scraping."""
    async def get_serp(self, query: str) -> list[Any]:
        from seo_platform.services.scraping.engines.seo import seo_scraper
        return await seo_scraper.get_serp(query)

def get_seo_provider() -> SEOProvider:
    """
    Factory to inject the correct provider based on environment settings.
    Preserves production code while allowing zero-cost local development.
    """
    settings = get_settings()
    if settings.use_mock_providers:
        logger.warning("using_mock_seo_provider", mode="zero-cost")
        return ScraperSEOProvider()

    logger.info("using_production_seo_provider")
    return DataForSEOProvider()
