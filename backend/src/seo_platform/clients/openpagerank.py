"""
SEO Platform — OpenPageRank Client
=====================================
Queries the free DomCop OpenPageRank API to get domain popularity metrics.
"""

from __future__ import annotations

import logging

import httpx
from pydantic import BaseModel, Field

from seo_platform.config import get_settings

logger = logging.getLogger(__name__)


class OpenPageRankItem(BaseModel):
    status: str
    domain: str
    page_rank_integer: int = Field(alias="page_rank_integer", default=0)
    page_rank_decimal: float = Field(alias="page_rank_decimal", default=0.0)
    rank: str = "0"


class OpenPageRankResponse(BaseModel):
    status_code: int
    response: list[OpenPageRankItem] = Field(default_factory=list)


class OpenPageRankClient:
    """
    Client for the DomCop OpenPageRank API.
    Used for cost-free domain metrics estimation.
    """

    BASE_URL = "https://openpagerank.com/api/v1.0"

    def __init__(self, api_key: str = "") -> None:
        settings = get_settings()
        self.api_key = api_key or getattr(settings, "openpagerank_api_key", "")
        self.timeout = 10.0

    async def get_domain_ranks(self, domains: list[str]) -> OpenPageRankResponse:
        """
        Fetch PageRank metrics for a batch of domains.
        """
        import time

        if not self.api_key:
            raise ValueError("OpenPageRank API key not configured")

        url = f"{self.BASE_URL}/getPageRank"
        headers = {"API-OPR": self.api_key}
        params = [("domains[]", dom) for dom in domains]

        from seo_platform.services.provider_health import provider_health_center

        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers, params=params)
                if response.status_code != 200:
                    raise RuntimeError(f"OpenPageRank API returned status {response.status_code}")

                latency = (time.monotonic() - t0) * 1000
                try:
                    await provider_health_center.record_provider_call(
                        provider_name="OpenPageRank",
                        latency_ms=latency,
                        success=True,
                    )
                except Exception:
                    pass
                return OpenPageRankResponse.model_validate(response.json())
        except Exception as e:
            latency = (time.monotonic() - t0) * 1000
            try:
                await provider_health_center.record_provider_call(
                    provider_name="OpenPageRank",
                    latency_ms=latency,
                    success=False,
                )
            except Exception:
                pass
            logger.error("openpagerank_request_failed", domains=domains, error=str(e))
            raise RuntimeError(f"OpenPageRank request failed: {e}")
