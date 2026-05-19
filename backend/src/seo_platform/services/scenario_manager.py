"""
SEO Platform — Scenario Manager
==================================
Reads pre-defined JSON scenario configs (TechStart, LocalFlorist, etc.)
and seeds the database with target niches, brand voice rules, negative
personas, and keywords for instant demo environment setup.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)

SCENARIOS: dict[str, dict[str, Any]] = {
    "TechStart": {
        "niche": "enterprise-saas",
        "target_keywords": [
            "cloud infrastructure pricing",
            "kubernetes cost optimization",
            "multi-cloud management",
            "devops automation tools",
            "infrastructure as code best practices",
        ],
        "brand_voice_rules": {
            "tone": "professional_authoritative",
            "max_sentence_length": 25,
            "prohibited_words": [
                "synergy", "leverage", "game-changer", "revolutionary",
                "i noticed your excellent article",
            ],
            "formality_level": "formal",
        },
        "negative_personas": [
            "budget_conscious_startup", "agency_reseller",
        ],
        "target_domain_authority_min": 30.0,
        "target_link_count": 15,
        "max_spam_score": 5.0,
    },
    "LocalFlorist": {
        "niche": "local-floral",
        "target_keywords": [
            "flower delivery near me",
            "wedding bouquets",
            "same day flower delivery",
            "local florist shop",
            "plant delivery service",
        ],
        "brand_voice_rules": {
            "tone": "warm_friendly",
            "max_sentence_length": 20,
            "prohibited_words": [
                "synergy", "leverage", "game-changer",
                "i noticed your excellent article",
            ],
            "formality_level": "casual",
        },
        "negative_personas": [
            "national_chain_affiliate",
        ],
        "target_domain_authority_min": 15.0,
        "target_link_count": 5,
        "max_spam_score": 8.0,
    },
}


class ScenarioManager:
    """Manages injection of pre-built demo scenarios into the database."""

    async def load_scenario(
        self, tenant_id: UUID, name: str,
    ) -> dict[str, Any]:
        """Load a named scenario, clearing existing demo data first."""
        name_normalized = name.replace(" ", "")
        scenario = SCENARIOS.get(name_normalized)
        if not scenario:
            raise ValueError(f"Unknown scenario '{name}'. Available: {list(SCENARIOS.keys())}")

        await self._clear_tenant_data(tenant_id)
        await self._inject_personas(tenant_id, name_normalized, scenario)
        await self._inject_keywords(tenant_id, scenario)
        await self._inject_campaign_config(tenant_id, scenario)

        logger.info("scenario_loaded", tenant_id=str(tenant_id), scenario=name_normalized)
        return {
            "scenario": name_normalized,
            "niche": scenario["niche"],
            "keyword_count": len(scenario["target_keywords"]),
            "status": "loaded",
        }

    def list_scenarios(self) -> list[dict[str, Any]]:
        """Return available scenarios with metadata."""
        return [
            {"name": name, "niche": cfg["niche"], "keyword_count": len(cfg["target_keywords"])}
            for name, cfg in SCENARIOS.items()
        ]

    @staticmethod
    async def _clear_tenant_data(tenant_id: UUID) -> None:
        """Remove previous demo data for a clean scenario load."""
        from seo_platform.core.database import get_db_session
        from seo_platform.models.backlink import BacklinkCampaign, BacklinkProspect
        from seo_platform.models.keywords import KeywordResearch
        from seo_platform.models.seo import Keyword
        from sqlalchemy import delete

        async with get_db_session() as session:
            for model in [BacklinkProspect, BacklinkCampaign, Keyword, KeywordResearch]:
                await session.execute(
                    delete(model).where(model.tenant_id == tenant_id)
                )

    @staticmethod
    async def _inject_personas(
        tenant_id: UUID, scenario_name: str, scenario: dict[str, Any],
    ) -> None:
        """Register personas matching the scenario brand voice."""
        try:
            from seo_platform.services.client_persona import client_persona_service

            await client_persona_service.ingest_persona_guidelines(
                tenant_id=tenant_id,
                client_id=tenant_id,
                guidelines={
                    "voice_rules": scenario["brand_voice_rules"],
                    "negative_personas": scenario.get("negative_personas", []),
                },
            )
        except Exception as e:
            logger.warning("persona_injection_skipped", error=str(e))

    @staticmethod
    async def _inject_keywords(tenant_id: UUID, scenario: dict[str, Any]) -> None:
        """Seed target keywords for the scenario."""
        from seo_platform.core.database import get_db_session
        from seo_platform.models.keywords import KeywordResearch

        async with get_db_session() as session:
            for kw in scenario["target_keywords"]:
                kr = KeywordResearch(
                    tenant_id=tenant_id,
                    keyword=kw,
                    search_volume=0,
                    difficulty=0.0,
                    cpc=0.0,
                    intent="informational",
                    status="demo_seed",
                    data={},
                )
                session.add(kr)

    @staticmethod
    async def _inject_campaign_config(
        tenant_id: UUID, scenario: dict[str, Any],
    ) -> None:
        """Seed a demo campaign configuration."""
        from seo_platform.core.database import get_db_session
        from seo_platform.models.backlink import BacklinkCampaign

        async with get_db_session() as session:
            campaign = BacklinkCampaign(
                tenant_id=tenant_id,
                campaign_type=scenario["niche"],
                status="draft",
                name=f"Demo Campaign — {scenario['niche']}",
                target_domain_authority_min=scenario["target_domain_authority_min"],
                max_spam_score=scenario["max_spam_score"],
                target_link_count=scenario["target_link_count"],
                competitor_domains=[],
                approved_prospects=[],
            )
            session.add(campaign)


    async def reset_workspace(self, tenant_id: UUID) -> dict[str, Any]:
        """Wipe all demo data, clear Redis caches, reset circuit breakers."""
        await self._clear_tenant_data(tenant_id)
        try:
            from seo_platform.core.redis import get_redis
            redis = await get_redis()
            await redis.flushdb()
        except Exception:
            logger.warning("redis_flush_skipped")
        logger.info("workspace_reset", tenant_id=str(tenant_id))
        return {"status": "reset", "tenant_id": str(tenant_id)}


scenario_manager = ScenarioManager()
