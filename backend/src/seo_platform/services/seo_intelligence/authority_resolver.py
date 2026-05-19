"""
SEO Platform — Centralized Domain Authority & Quality Resolver
==================================================================
Manages cached domain rating lookups, spam detection, and trust evaluation.
"""

from __future__ import annotations

import json
import logging

from pydantic import BaseModel

from seo_platform.core.redis import get_redis
from seo_platform.providers.seo import DomainAuthority, calculate_local_authority

logger = logging.getLogger(__name__)


class DomainQualityMetrics(BaseModel):
    domain: str
    authority: float
    trust_score: float
    spam_score: float
    outbound_link_ratio: float
    is_link_farm: bool
    source: str


class AuthorityResolver:
    """
    Centralizes domain rating lookups and quality evaluations.
    Caches results in Redis to prevent redundant API queries.
    """

    CACHE_TTL = 604800  # 7 days

    @classmethod
    async def get_metrics(cls, domain: str, raw_html: str = "") -> DomainQualityMetrics:
        """
        Retrieves domain metrics from cache, or calculates them using
        OpenPageRank and local heuristics.
        """
        redis = await get_redis()
        cache_key = f"authority:{domain}"

        try:
            cached = await redis.get(cache_key)
            if cached:
                return DomainQualityMetrics.model_validate(json.loads(cached))
        except Exception as e:
            logger.warning("authority_cache_read_failed", error=str(e))

        from seo_platform.providers.seo import get_seo_provider
        provider = get_seo_provider()

        try:
            da = await provider.get_domain_authority(domain)
            authority = da.authority
            source = da.source
        except Exception:
            authority = calculate_local_authority(domain)
            source = "fallback_heuristics"

        outbound_ratio = 0.0
        is_link_farm = False
        spam_score = 0.02

        if raw_html:
            from scrapling import Fetcher
            fetcher = Fetcher(raw_html)
            links = fetcher.css("a::attr(href)").all()
            ext_links = [l for l in links if domain not in l and l.startswith("http")]

            if links:
                outbound_ratio = len(ext_links) / len(links)
                if len(ext_links) > 80 and outbound_ratio > 0.85:
                    is_link_farm = True
                    spam_score = 0.80

        trust_score = authority * (1.0 - spam_score)

        metrics = DomainQualityMetrics(
            domain=domain,
            authority=authority,
            trust_score=trust_score,
            spam_score=spam_score,
            outbound_link_ratio=outbound_ratio,
            is_link_farm=is_link_farm,
            source=source,
        )

        try:
            await redis.setex(cache_key, cls.CACHE_TTL, metrics.model_dump_json())
        except Exception as e:
            logger.warning("authority_cache_write_failed", error=str(e))

        return metrics
