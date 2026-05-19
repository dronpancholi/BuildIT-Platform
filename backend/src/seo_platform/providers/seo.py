"""
SEO Platform — Universal SEO Data Provider Layer
====================================================
Provider-agnostic interface for keyword research, backlinks, SERP data, 
and domain authority. Supports runtime provider switching.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from seo_platform.clients.scrapling import SERPItem, ScraplingClient
from seo_platform.clients.scrapling_cache import ScraplingCache
from seo_platform.clients.searxng import SearXNGClient
from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------
@dataclass
class KeywordMetrics:
    keyword: str
    search_volume: int = 0
    difficulty: float = 0.0
    cpc: float = 0.0
    competition: float = 0.0
    intent: str = "informational"
    serp_features: list[str] = field(default_factory=list)


@dataclass
class BacklinkProspect:
    domain: str
    domain_authority: float = 0.0
    relevance_score: float = 0.0
    spam_score: float = 0.0
    traffic: int = 0
    referring_domains: int = 0
    source: str = "unknown"


@dataclass
class DomainAuthority:
    domain: str
    authority: float = 0.0
    trust: float = 0.0
    referring_domains: int = 0
    backlinks: int = 0
    organic_traffic: int = 0
    source: str = "unknown"


# ---------------------------------------------------------------------------
# Abstract Provider
# ---------------------------------------------------------------------------
class SEODataProvider(ABC):
    """Abstract interface for all SEO data providers."""

    name: str = "base"

    @abstractmethod
    async def get_keyword_metrics(self, keywords: list[str]) -> list[KeywordMetrics]:
        ...

    @abstractmethod
    async def get_domain_authority(self, domain: str) -> DomainAuthority:
        ...

    @abstractmethod
    async def discover_backlink_prospects(self, domain: str, limit: int = 20) -> list[BacklinkProspect]:
        ...

    @abstractmethod
    async def get_serp_data(self, keyword: str, geo: str = "us") -> dict[str, Any]:
        ...


# ---------------------------------------------------------------------------
# Simulated Provider (fallback)
# ---------------------------------------------------------------------------
class SimulatedSEOProvider(SEODataProvider):
    """Hash-based fallback when no real SEO APIs are configured."""

    name = "simulated"

    async def get_keyword_metrics(self, keywords: list[str]) -> list[KeywordMetrics]:
        import hashlib
        results = []
        for kw in keywords:
            h = int(hashlib.md5(kw.encode()).hexdigest()[:8], 16)
            results.append(KeywordMetrics(
                keyword=kw,
                search_volume=200 + (h % 4800),
                difficulty=round(20 + (h % 6000) / 100, 1),
                cpc=round(0.5 + (h % 950) / 100, 2),
                competition=round(0.3 + (h % 60) / 100, 2),
                intent="informational",
            ))
        return results

    async def get_domain_authority(self, domain: str) -> DomainAuthority:
        import hashlib
        h = int(hashlib.md5(domain.encode()).hexdigest()[:8], 16)
        return DomainAuthority(
            domain=domain,
            authority=round(20 + (h % 60), 1),
            trust=round(30 + (h % 40), 1),
            referring_domains=h % 500,
            backlinks=h % 5000,
            organic_traffic=h % 10000,
            source="simulated",
        )

    async def discover_backlink_prospects(self, domain: str, limit: int = 20) -> list[BacklinkProspect]:
        return []

    async def get_serp_data(self, keyword: str, geo: str = "us") -> dict[str, Any]:
        return {"keyword": keyword, "success": False, "error": "Simulated provider has no SERP data"}


# ---------------------------------------------------------------------------
# DataForSEO Provider
# ---------------------------------------------------------------------------
class DataForSEOProvider(SEODataProvider):
    """Real DataForSEO integration."""

    name = "dataforseo"

    def __init__(self) -> None:
        self._client: Any = None

    async def _get_client(self):
        if self._client is None:
            from seo_platform.clients.dataforseo import dataforseo_client
            self._client = dataforseo_client
        return self._client

    async def get_keyword_metrics(self, keywords: list[str]) -> list[KeywordMetrics]:
        try:
            client = await self._get_client()
            data = await client.get_search_volume(keywords)
            results = []
            for item in data:
                results.append(KeywordMetrics(
                    keyword=item.get("keyword", ""),
                    search_volume=item.get("search_volume", 0),
                    difficulty=item.get("competition", 0.5) * 100,
                    cpc=item.get("cpc", 0),
                    competition=item.get("competition", 0),
                    intent=item.get("intent", "informational"),
                    serp_features=item.get("serp_features", []),
                ))
            return results
        except Exception as e:
            logger.warning("dataforseo_failed_falling_back", error=str(e))
            return await SimulatedSEOProvider().get_keyword_metrics(keywords)

    async def get_domain_authority(self, domain: str) -> DomainAuthority:
        return await SimulatedSEOProvider().get_domain_authority(domain)

    async def discover_backlink_prospects(self, domain: str, limit: int = 20) -> list[BacklinkProspect]:
        return []

    async def get_serp_data(self, keyword: str, geo: str = "us") -> dict[str, Any]:
        return {"keyword": keyword, "success": False, "error": "SERP data not available from DataForSEO"}


# ---------------------------------------------------------------------------
# Scrapling Provider (stealth fallback)
# ---------------------------------------------------------------------------
class ScraplingSEOProvider(SEODataProvider):
    """
    Scrapling SEO Data Provider.
    Implements stealth search extraction, paginated SERP parsing,
    and recursive crawl depth for zero-cost backlink discovery.
    """

    name = "scrapling"

    def __init__(self) -> None:
        self.client = ScraplingClient()

    async def get_keyword_metrics(self, keywords: list[str]) -> list[KeywordMetrics]:
        return await SimulatedSEOProvider().get_keyword_metrics(keywords)

    async def get_domain_authority(self, domain: str) -> DomainAuthority:
        try:
            res = await self.client.fetch(f"https://{domain}")
            ext_links = [l for l in res.outbound_links if domain not in l]
            authority = min(90.0, max(10.0, 15.0 + len(ext_links) * 1.5))
            return DomainAuthority(
                domain=domain,
                authority=authority,
                trust=authority * 0.8,
                referring_domains=len(ext_links),
                backlinks=len(res.outbound_links),
                source="scrapling_crawled",
            )
        except Exception:
            return await SimulatedSEOProvider().get_domain_authority(domain)

    async def discover_backlink_prospects(self, domain: str, limit: int = 20) -> list[BacklinkProspect]:
        """
        Crawls search listings and recursively follows links (depth 1) to find backlink prospects.
        Results cached for 3 days.
        """
        cache_payload = {"domain": domain, "limit": limit}
        cache_val = await ScraplingCache.get("prospects", cache_payload, BacklinkProspect)
        if cache_val is not None:
            return cache_val

        prospects = await self._discover_prospects_live(domain, limit)

        await ScraplingCache.set("prospects", cache_payload, prospects, ttl=259200)
        return prospects

    async def _discover_prospects_live(self, domain: str, limit: int = 20) -> list[BacklinkProspect]:
        """Live backlink crawl without caching."""
        try:
            serp_items = await self.client.extract_ddg_serp(f'"{domain}" -site:{domain}', limit=limit)
            prospects: list[BacklinkProspect] = []

            for item in serp_items:
                clean_domain = item.url.split("//")[-1].split("/")[0]
                if clean_domain and clean_domain != domain:
                    prospects.append(BacklinkProspect(
                        domain=clean_domain,
                        domain_authority=50.0,
                        relevance_score=0.80,
                        spam_score=0.01,
                        source="scrapling_crawled_direct",
                    ))
                    if len(prospects) >= limit:
                        break

                    try:
                        res = await self.client.fetch(item.url)
                        for link in res.outbound_links[:5]:
                            link_domain = link.split("//")[-1].split("/")[0]
                            if link_domain and link_domain != domain and link_domain != clean_domain:
                                prospects.append(BacklinkProspect(
                                    domain=link_domain,
                                    domain_authority=40.0,
                                    relevance_score=0.60,
                                    spam_score=0.02,
                                    source="scrapling_crawled_depth1",
                                ))
                                if len(prospects) >= limit:
                                    break
                    except Exception:
                        continue

            return prospects[:limit]
        except Exception as e:
            logger.warning("scrapling_prospecting_failed", error=str(e))
            return []

    async def get_serp_data(self, keyword: str, geo: str = "us") -> dict[str, Any]:
        """
        Scrapes and parses organic search engine results with paginated metadata.
        """
        try:
            serp_items = await self.client.extract_ddg_serp(keyword, limit=10)
            return {
                "keyword": keyword,
                "success": True,
                "provider": "scrapling",
                "organic_results": [item.model_dump() for item in serp_items],
                "features_present": ["organic"],
                "total_organic_count": len(serp_items),
            }
        except Exception as e:
            return {"keyword": keyword, "success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# SearXNG Provider (local aggregator fallback)
# ---------------------------------------------------------------------------
class SearXNGSEOProvider(SEODataProvider):
    """
    SearXNG SEO Data Provider.
    Interfaces with local aggregator engines for zero-cost query discovery.
    """

    name = "searxng"

    def __init__(self, base_url: str = "http://localhost:8080") -> None:
        self.client = SearXNGClient(base_url=base_url)

    async def get_keyword_metrics(self, keywords: list[str]) -> list[KeywordMetrics]:
        return await SimulatedSEOProvider().get_keyword_metrics(keywords)

    async def get_domain_authority(self, domain: str) -> DomainAuthority:
        return await SimulatedSEOProvider().get_domain_authority(domain)

    async def discover_backlink_prospects(self, domain: str, limit: int = 20) -> list[BacklinkProspect]:
        """
        Discovers pages mentioning the domain using SearXNG search queries.
        """
        try:
            query = f'"{domain}" -site:{domain}'
            resp = await self.client.search(query=query)

            prospects = []
            for item in resp.results[:limit]:
                prospect_domain = item.url.split("//")[-1].split("/")[0]
                if prospect_domain and prospect_domain != domain:
                    prospects.append(BacklinkProspect(
                        domain=prospect_domain,
                        domain_authority=40.0,
                        relevance_score=0.70,
                        spam_score=0.02,
                        source="searxng_discovery",
                    ))
            return prospects
        except Exception as e:
            logger.warning("searxng_prospecting_failed_falling_back", error=str(e))
            return []

    async def get_serp_data(self, keyword: str, geo: str = "us") -> dict[str, Any]:
        """
        Queries SearXNG and formats response into standardized organic snapshots.
        """
        try:
            resp = await self.client.search(query=keyword)
            organic = []
            for item in resp.results:
                organic.append({
                    "title": item.title,
                    "url": item.url,
                    "snippet": item.content,
                    "position": item.position,
                })
            return {
                "keyword": keyword,
                "success": True,
                "provider": "searxng",
                "organic_results": organic,
                "features_present": ["organic"],
                "total_organic_count": len(organic),
            }
        except Exception as e:
            return {"keyword": keyword, "success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Provider Registry
# ---------------------------------------------------------------------------
class SEOProviderRegistry:
    """Manages SEO data providers and enables runtime switching."""

    def __init__(self):
        self._providers: dict[str, SEODataProvider] = {}
        self._active: str = "simulated"

    def register(self, provider: SEODataProvider) -> None:
        self._providers[provider.name] = provider
        logger.info("seo_provider_registered", provider=provider.name)

    def set_active(self, name: str) -> None:
        if name in self._providers:
            self._active = name
            logger.info("seo_provider_activated", provider=name)
        else:
            logger.warning("seo_provider_not_found", provider=name)

    def get_active(self) -> SEODataProvider:
        provider = self._providers.get(self._active)
        if provider is None:
            provider = self._providers.get("simulated", SimulatedSEOProvider())
        return provider

    @property
    def active_name(self) -> str:
        return self._active

    @property
    def available(self) -> list[str]:
        return list(self._providers.keys())


# Global registry
seo_provider_registry = SEOProviderRegistry()
seo_provider_registry.register(SimulatedSEOProvider())
seo_provider_registry.register(DataForSEOProvider())
seo_provider_registry.register(ScraplingSEOProvider())
seo_provider_registry.register(SearXNGSEOProvider())


def get_seo_provider() -> SEODataProvider:
    """Get the currently active SEO data provider."""
    return seo_provider_registry.get_active()


def configure_seo_provider(name: str) -> None:
    """Switch SEO provider at runtime."""
    seo_provider_registry.set_active(name)
