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
        "campaign_type": "guest_post",
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
        "campaign_type": "resource_page",
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
    async def load_scenario(
        self, tenant_id: UUID, name: str,
    ) -> dict[str, Any]:
        """Load a named scenario, clearing existing demo data first."""
        name_normalized = name.replace(" ", "")
        scenario = SCENARIOS.get(name_normalized)
        if not scenario:
            raise ValueError(f"Unknown scenario '{name}'. Available: {list(SCENARIOS.keys())}")

        await self._clear_tenant_data(tenant_id)
        client_id = await self._ensure_client(tenant_id, scenario)
        await self._inject_personas(tenant_id, client_id, name_normalized, scenario)
        campaign_id = await self._inject_campaign_config(tenant_id, client_id, scenario)
        await self._inject_keywords_and_clusters(tenant_id, client_id, name_normalized, scenario)
        await self._inject_prospects_outreach_and_links(tenant_id, client_id, campaign_id, name_normalized, scenario)
        await self._inject_approvals(tenant_id, client_id, campaign_id, name_normalized, scenario)
        await self._inject_citations(tenant_id, client_id, name_normalized, scenario)
        await self._inject_health_snapshots_and_recommendations(tenant_id, client_id, campaign_id, name_normalized, scenario)

        # Build prospect graph in Redis
        try:
            from seo_platform.services.prospect_graph import prospect_graph_system
            await prospect_graph_system.build_prospect_graph(tenant_id, campaign_id)
        except Exception as e:
            logger.warning("failed_to_build_prospect_graph: %s", str(e))

        logger.info("scenario_loaded tenant=%s scenario=%s", str(tenant_id), name_normalized)
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
    async def _ensure_client(tenant_id: UUID, scenario: dict[str, Any]) -> UUID:
        """Create or return a demo client matching the scenario."""
        from seo_platform.core.database import get_db_session
        from seo_platform.models.tenant import Client

        async with get_db_session() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(Client).where(
                    Client.tenant_id == tenant_id,
                    Client.domain == f"{scenario['niche'].replace('-', '')}.io",
                ).limit(1)
            )
            existing = result.scalar_one_or_none()
            if existing:
                return existing.id

            client = Client(
                tenant_id=tenant_id,
                name=f"Demo {scenario['niche'].replace('-', ' ').title()} Client",
                domain=f"{scenario['niche'].replace('-', '')}.io",
                niche=scenario["niche"],
            )
            session.add(client)
            await session.flush()
            return client.id

    @staticmethod
    async def _clear_tenant_data(tenant_id: UUID) -> None:
        """Remove previous demo data for a clean scenario load."""
        from seo_platform.core.database import get_db_session
        from seo_platform.models.backlink import BacklinkCampaign, BacklinkProspect, OutreachThread, AcquiredLink
        from seo_platform.models.seo import Keyword, KeywordCluster
        from seo_platform.models.tenant import Client
        from seo_platform.models.approval import ApprovalRequestModel
        from seo_platform.models.citation import BusinessProfile, CitationSubmission
        from seo_platform.models.business_memory import (
            CampaignHealthSnapshot,
            KeywordMetricSnapshot,
            ProspectScoreHistory,
            BusinessIntelligenceEvent,
            RecommendationModel,
            SerpVolatilitySnapshot
        )
        from sqlalchemy import delete

        async with get_db_session() as session:
            for model in [
                AcquiredLink,
                OutreachThread,
                ProspectScoreHistory,
                CampaignHealthSnapshot,
                KeywordMetricSnapshot,
                BacklinkProspect,
                BacklinkCampaign,
                Keyword,
                KeywordCluster,
                CitationSubmission,
                BusinessProfile,
                ApprovalRequestModel,
                BusinessIntelligenceEvent,
                RecommendationModel,
                SerpVolatilitySnapshot,
            ]:
                await session.execute(
                    delete(model).where(model.tenant_id == tenant_id)
                )
            await session.execute(
                delete(Client).where(Client.tenant_id == tenant_id)
            )

    @staticmethod
    async def _inject_personas(
        tenant_id: UUID, client_id: UUID, scenario_name: str, scenario: dict[str, Any],
    ) -> None:
        """Register personas matching the scenario brand voice."""
        try:
            from seo_platform.services.client_persona import client_persona_service

            await client_persona_service.ingest_persona_guidelines(
                tenant_id=tenant_id,
                client_id=client_id,
                guidelines={
                    "voice_rules": scenario["brand_voice_rules"],
                    "negative_personas": scenario.get("negative_personas", []),
                },
            )
        except Exception as e:
            logger.warning("persona_injection_skipped: %s", str(e))

    @staticmethod
    async def _inject_keywords_and_clusters(
        tenant_id: UUID, client_id: UUID, scenario_name: str, scenario: dict[str, Any]
    ) -> None:
        """Seed target keywords and clusters for the scenario."""
        from seo_platform.core.database import get_db_session
        from seo_platform.models.seo import Keyword, KeywordCluster, SearchIntent, ClusterStatus

        async with get_db_session() as session:
            if scenario_name == "TechStart":
                c1 = KeywordCluster(
                    tenant_id=tenant_id,
                    client_id=client_id,
                    name="Kubernetes Costs",
                    primary_keyword="kubernetes cost optimization",
                    total_volume=4500,
                    avg_difficulty=65.0,
                    dominant_intent=SearchIntent.COMMERCIAL,
                    keyword_count=3,
                    confidence_score=0.95,
                    status=ClusterStatus.APPROVED,
                    ai_rationale="High commercial intent search terms relating to container budgeting."
                )
                c2 = KeywordCluster(
                    tenant_id=tenant_id,
                    client_id=client_id,
                    name="Cloud Infrastructure Management",
                    primary_keyword="cloud infrastructure pricing",
                    total_volume=8200,
                    avg_difficulty=72.0,
                    dominant_intent=SearchIntent.INFORMATIONAL,
                    keyword_count=3,
                    confidence_score=0.92,
                    status=ClusterStatus.DRAFT,
                    ai_rationale="Broad volume informational keywords about major cloud providers."
                )
                session.add_all([c1, c2])
                await session.flush()

                kws = [
                    ("kubernetes cost optimization", 1200, 68.0, c1.id, SearchIntent.COMMERCIAL),
                    ("kubernetes cost savings", 800, 62.0, c1.id, SearchIntent.COMMERCIAL),
                    ("reduce kubernetes bill", 2500, 65.0, c1.id, SearchIntent.TRANSACTIONAL),
                    ("cloud infrastructure pricing", 5000, 75.0, c2.id, SearchIntent.INFORMATIONAL),
                    ("multi-cloud management", 2200, 70.0, c2.id, SearchIntent.COMMERCIAL),
                    ("cloud pricing comparison", 1000, 71.0, c2.id, SearchIntent.INFORMATIONAL),
                ]
            else:
                c1 = KeywordCluster(
                    tenant_id=tenant_id,
                    client_id=client_id,
                    name="Local Flower Delivery",
                    primary_keyword="flower delivery near me",
                    total_volume=12000,
                    avg_difficulty=35.0,
                    dominant_intent=SearchIntent.TRANSACTIONAL,
                    keyword_count=3,
                    confidence_score=0.98,
                    status=ClusterStatus.APPROVED,
                    ai_rationale="High-intent transactional keywords targeting immediate local florist needs."
                )
                c2 = KeywordCluster(
                    tenant_id=tenant_id,
                    client_id=client_id,
                    name="Special Events & Plants",
                    primary_keyword="wedding bouquets",
                    total_volume=3500,
                    avg_difficulty=42.0,
                    dominant_intent=SearchIntent.COMMERCIAL,
                    keyword_count=2,
                    confidence_score=0.94,
                    status=ClusterStatus.DRAFT,
                    ai_rationale="Seasonal event-based inquiries for bouquet designs and home plant delivery."
                )
                session.add_all([c1, c2])
                await session.flush()

                kws = [
                    ("flower delivery near me", 8000, 38.0, c1.id, SearchIntent.TRANSACTIONAL),
                    ("same day flower delivery", 3000, 34.0, c1.id, SearchIntent.TRANSACTIONAL),
                    ("local florist shop", 1000, 33.0, c1.id, SearchIntent.TRANSACTIONAL),
                    ("wedding bouquets", 2500, 45.0, c2.id, SearchIntent.COMMERCIAL),
                    ("plant delivery service", 1000, 39.0, c2.id, SearchIntent.COMMERCIAL),
                ]

            for kw_text, vol, diff, cluster_id, intent in kws:
                keyword = Keyword(
                    tenant_id=tenant_id,
                    client_id=client_id,
                    cluster_id=cluster_id,
                    keyword=kw_text,
                    search_volume=vol,
                    difficulty=diff,
                    cpc=1.5,
                    competition=0.5,
                    intent=intent,
                    is_seed=True,
                )
                session.add(keyword)

    @staticmethod
    async def _inject_campaign_config(
        tenant_id: UUID, client_id: UUID, scenario: dict[str, Any],
    ) -> UUID:
        """Seed a demo campaign configuration and return campaign_id."""
        from seo_platform.core.database import get_db_session
        from seo_platform.models.backlink import BacklinkCampaign, CampaignType, CampaignStatus

        ct_map = {
            "guest_post": CampaignType.GUEST_POST,
            "resource_page": CampaignType.RESOURCE_PAGE,
            "niche_edit": CampaignType.NICHE_EDIT,
            "broken_link": CampaignType.BROKEN_LINK,
            "skyscraper": CampaignType.SKYSCRAPER,
            "haro": CampaignType.HARO,
        }

        async with get_db_session() as session:
            campaign = BacklinkCampaign(
                tenant_id=tenant_id,
                client_id=client_id,
                campaign_type=ct_map.get(scenario.get("campaign_type", "guest_post"), CampaignType.GUEST_POST),
                status=CampaignStatus.ACTIVE,
                name=f"Demo Campaign — {scenario['niche']}",
                target_link_count=scenario["target_link_count"],
                config={
                    "target_domain_authority_min": scenario["target_domain_authority_min"],
                    "max_spam_score": scenario["max_spam_score"],
                },
            )
            session.add(campaign)
            await session.flush()
            return campaign.id

    @staticmethod
    async def _inject_prospects_outreach_and_links(
        tenant_id: UUID, client_id: UUID, campaign_id: UUID, scenario_name: str, scenario: dict[str, Any]
    ) -> None:
        """Seed prospects, outreach emails and acquired links."""
        from seo_platform.core.database import get_db_session
        from seo_platform.models.backlink import BacklinkProspect, ProspectStatus, OutreachThread, ThreadStatus, AcquiredLink, LinkStatus
        from datetime import datetime, timedelta, UTC

        async with get_db_session() as session:
            if scenario_name == "TechStart":
                prospect_configs = [
                    ("techcrunch.com", "https://techcrunch.com/startups", ProspectStatus.APPROVED, 93, 0.90, 0.05, "Sarah Jenkins", "sarah@techcrunch.com"),
                    ("venturebeat.com", "https://venturebeat.com/cloud", ProspectStatus.CONTACTED, 91, 0.85, 0.08, "David Miller", "david.m@venturebeat.com"),
                    ("hackernoon.com", "https://hackernoon.com/k8s", ProspectStatus.REPLIED, 85, 0.80, 0.10, "Elena Rostova", "elena@hackernoon.com"),
                    ("dzone.com", "https://dzone.com/devops", ProspectStatus.LINK_ACQUIRED, 82, 0.75, 0.12, "Mark Vance", "mark@dzone.com"),
                    ("infoq.com", "https://infoq.com/development", ProspectStatus.SCORED, 86, 0.88, 0.07, "Michael Wu", "wu@infoq.com"),
                    ("dev.to", "https://dev.to/k8s-cost", ProspectStatus.NEW, 80, 0.70, 0.15, "Community User", "editors@dev.to"),
                ]
            else:
                prospect_configs = [
                    ("yelp.com", "https://yelp.com/c/sf/florists", ProspectStatus.LINK_ACQUIRED, 94, 0.90, 0.02, "Yelp Editor", "local@yelp.com"),
                    ("yellowpages.com", "https://yellowpages.com/sf/florists", ProspectStatus.LINK_ACQUIRED, 85, 0.80, 0.05, "YP Support", "support@yellowpages.com"),
                    ("tripadvisor.com", "https://tripadvisor.com/restaurants", ProspectStatus.CONTACTED, 93, 0.70, 0.08, "Trip Editor", "info@tripadvisor.com"),
                    ("localguides.com", "https://localguides.com/flowers", ProspectStatus.APPROVED, 45, 0.75, 0.10, "Lisa Bloom", "lisa@localguides.com"),
                    ("citysearch.com", "https://citysearch.com/sf/flowers", ProspectStatus.NEW, 62, 0.82, 0.05, "City Editor", "editor@citysearch.com"),
                ]

            prospects_created = []
            for domain, url, status, da, rel, spam, contact_name, contact_email in prospect_configs:
                comp_score = (da / 100) * 0.4 + rel * 0.4 + (1 - spam) * 0.2
                prospect = BacklinkProspect(
                    tenant_id=tenant_id,
                    campaign_id=campaign_id,
                    domain=domain,
                    url=url,
                    status=status,
                    domain_authority=da,
                    relevance_score=rel,
                    spam_score=spam,
                    traffic_score=80.0,
                    composite_score=comp_score,
                    confidence=1.0 - spam,
                    contact_name=contact_name,
                    contact_email=contact_email,
                    contact_source="hunter",
                    page_data={
                        "page_title": f"Resource Guide for {scenario['niche']}",
                        "page_url": url,
                        "source_competitor": f"competitor-for-{scenario['niche']}.com",
                    },
                    scoring_rationale={
                        "has_resource_page": True,
                        "estimated_broken_links": 3,
                        "source_competitor": f"competitor-for-{scenario['niche']}.com",
                    }
                )
                session.add(prospect)
                prospects_created.append((prospect, status))

            await session.flush()

            # Seed OutreachThreads and AcquiredLinks based on prospect status
            for prospect, status in prospects_created:
                if status in (ProspectStatus.CONTACTED, ProspectStatus.REPLIED, ProspectStatus.LINK_ACQUIRED):
                    thread_status = (
                        ThreadStatus.SENT if status == ProspectStatus.CONTACTED else
                        ThreadStatus.REPLIED if status == ProspectStatus.REPLIED else
                        ThreadStatus.LINK_ACQUIRED
                    )

                    domain = prospect.domain
                    name = prospect.contact_name or "there"
                    first_name = name.split()[0] if name != "there" else "there"

                    if scenario_name == "TechStart":
                        topic = "enterprise SaaS and DevOps"
                        client_name = "TechStart Inc."
                    else:
                        topic = "local business and flower delivery"
                        client_name = "LocalFlorist"

                    pitch_subj = f"Quick question regarding your recent thoughts on {topic}"
                    pitch_body = (
                        f"<p>Hi {first_name},</p>"
                        f"<p>I really enjoyed your recent piece on {domain.split('.')[0]} "
                        f"regarding {topic}. It's rare to see someone address the nuances so directly.</p>"
                        f"<p>We recently compiled exclusive benchmark data at {client_name} "
                        f"exploring this exact space. I thought the custom charts might be a "
                        f"perfect addition for your upcoming coverage.</p>"
                        f"<p>Would you be open to me sending over a quick preview link?</p>"
                        f"<p>Best regards,<br/>{client_name} Team</p>"
                    )

                    thread = OutreachThread(
                        tenant_id=tenant_id,
                        campaign_id=campaign_id,
                        prospect_id=prospect.id,
                        status=thread_status,
                        from_email="alex@techstart.io" if scenario_name == "TechStart" else "alex@localflorist.io",
                        to_email=prospect.contact_email or f"contact@{domain}",
                        subject=pitch_subj,
                        body_html=pitch_body,
                        follow_up_count=0,
                        max_follow_ups=3,
                        provider="smartlead",
                        sent_at=datetime.now(UTC) - timedelta(days=2),
                        replied_at=datetime.now(UTC) - timedelta(days=1) if thread_status in (ThreadStatus.REPLIED, ThreadStatus.LINK_ACQUIRED) else None,
                        confidence_score=0.88,
                        ai_personalization={"icebreaker": "I really enjoyed your recent piece on industry trends.", "generation_source": "elite_deterministic_fallback"}
                    )
                    session.add(thread)

                if status == ProspectStatus.LINK_ACQUIRED:
                    acquired = AcquiredLink(
                        tenant_id=tenant_id,
                        campaign_id=campaign_id,
                        prospect_id=prospect.id,
                        source_url=prospect.url,
                        target_url=f"https://{scenario['niche'].replace('-', '')}.io/blog/post-1",
                        anchor_text="container cost optimization" if scenario_name == "TechStart" else "best local florist",
                        link_type="contextual",
                        status=LinkStatus.VERIFIED_LIVE,
                        domain_authority_at_acquisition=prospect.domain_authority,
                        first_verified_at=datetime.now(UTC) - timedelta(days=1)
                    )
                    session.add(acquired)

    @staticmethod
    async def _inject_approvals(
        tenant_id: UUID, client_id: UUID, campaign_id: UUID, scenario_name: str, scenario: dict[str, Any]
    ) -> None:
        """Seed approval queue requests."""
        from seo_platform.core.database import get_db_session
        from seo_platform.models.approval import ApprovalRequestModel, ApprovalCategory, RiskLevelEnum, ApprovalStatusEnum
        from datetime import datetime, timedelta, UTC

        async with get_db_session() as session:
            app1 = ApprovalRequestModel(
                tenant_id=tenant_id,
                workflow_run_id=f"wf-campaign-launch-{campaign_id}",
                category=ApprovalCategory.CAMPAIGN_LAUNCH,
                risk_level=RiskLevelEnum.HIGH,
                status=ApprovalStatusEnum.PENDING,
                summary=f"Launch '{scenario['niche']} outreach' targeting top-tier niche publishers.",
                ai_risk_summary="Low risk. Email templates comply with brand guidelines and max sentence lengths.",
                context_snapshot={"campaign_id": str(campaign_id), "niche": scenario["niche"], "prospect_count": 6},
                sla_deadline=datetime.now(UTC) + timedelta(hours=4),
                escalation_count=0
            )

            app2 = ApprovalRequestModel(
                tenant_id=tenant_id,
                workflow_run_id=f"wf-template-approval-{campaign_id}",
                category=ApprovalCategory.OUTREACH_TEMPLATES,
                risk_level=RiskLevelEnum.CRITICAL,
                status=ApprovalStatusEnum.PENDING,
                summary="Approve generated AI personalization template for VentureBeat editor.",
                ai_risk_summary="High risk. System detected a potential buzzword 'leverage' and sentence length of 26 words.",
                context_snapshot={
                    "campaign_id": str(campaign_id),
                    "prospect": "venturebeat.com",
                    "draft_subject": "Resource suggestion: container optimization",
                    "draft_body": "We should leverage our joint resources to build a better community."
                },
                sla_deadline=datetime.now(UTC) + timedelta(hours=1),
                escalation_count=1
            )
            session.add_all([app1, app2])

    @staticmethod
    async def _inject_citations(
        tenant_id: UUID, client_id: UUID, scenario_name: str, scenario: dict[str, Any]
    ) -> None:
        """Seed citation submissions for LocalFlorist."""
        from seo_platform.core.database import get_db_session
        from seo_platform.models.citation import BusinessProfile, CitationSubmission, VerificationState

        if scenario_name != "LocalFlorist":
            return

        async with get_db_session() as session:
            profile = BusinessProfile(
                tenant_id=tenant_id,
                client_id=client_id,
                business_name="Demo Local Florist Inc.",
                street_address="123 Flower Lane",
                city="San Francisco",
                state_province="CA",
                postal_code="94102",
                country_code="US",
                phone_number="+14155550199",
                website_url="https://localflorist.io",
                primary_category="Florist",
                secondary_categories=["Wedding Planner", "Gift Shop"],
                description="Premium local florist offering same day delivery across SF."
            )
            session.add(profile)
            await session.flush()

            sub1 = CitationSubmission(
                tenant_id=tenant_id,
                profile_id=profile.id,
                workflow_run_id="wf-citation-yelp",
                directory_adapter="yelp",
                submission_status="submitted",
                verification_state=VerificationState.LIVE.value,
                live_url="https://yelp.com/biz/demo-local-florist",
                nap_consistency_score=0.95
            )
            sub2 = CitationSubmission(
                tenant_id=tenant_id,
                profile_id=profile.id,
                workflow_run_id="wf-citation-yellowpages",
                directory_adapter="yellowpages",
                submission_status="submitted",
                verification_state=VerificationState.LIVE.value,
                live_url="https://yellowpages.com/biz/demo-local-florist",
                nap_consistency_score=0.98
            )
            sub3 = CitationSubmission(
                tenant_id=tenant_id,
                profile_id=profile.id,
                workflow_run_id="wf-citation-tripadvisor",
                directory_adapter="tripadvisor",
                submission_status="submitted",
                verification_state=VerificationState.PENDING.value,
                live_url=None,
                nap_consistency_score=0.88
            )
            sub4 = CitationSubmission(
                tenant_id=tenant_id,
                profile_id=profile.id,
                workflow_run_id="wf-citation-justdial",
                directory_adapter="justdial",
                submission_status="queued",
                verification_state=VerificationState.PENDING.value,
                live_url=None,
                nap_consistency_score=0.0
            )
            session.add_all([sub1, sub2, sub3, sub4])

    @staticmethod
    async def _inject_health_snapshots_and_recommendations(
        tenant_id: UUID, client_id: UUID, campaign_id: UUID, scenario_name: str, scenario: dict[str, Any]
    ) -> None:
        """Seed campaign health histories, recommendations, and events."""
        from seo_platform.core.database import get_db_session
        from seo_platform.models.business_memory import CampaignHealthSnapshot, RecommendationModel, BusinessIntelligenceEvent
        from datetime import datetime, timedelta, UTC

        async with get_db_session() as session:
            for i in range(5):
                snap = CampaignHealthSnapshot(
                    tenant_id=tenant_id,
                    campaign_id=campaign_id,
                    health_score=0.75 + (i * 0.03),
                    acquisition_rate=0.1 + (i * 0.02),
                    reply_rate=0.2 + (i * 0.03),
                    progress=0.2 + (i * 0.1),
                    momentum=0.8 + (i * 0.02),
                    velocity=0.05 * (i + 1),
                    snapshot_data={"active_prospects": 10 + i, "sent_emails": 20 + (i * 5)},
                    captured_at=datetime.now(UTC) - timedelta(days=(5 - i))
                )
                session.add(snap)

            r1 = RecommendationModel(
                tenant_id=tenant_id,
                recommendation_type="backlink_opportunity",
                title="Acquire backlink from hackernoon.com",
                description="Elena Rostova (editor) replied to our pitch. Follow up within 24 hours to secure the link placement.",
                priority="P0",
                status="active",
                confidence=0.92,
                impact_score=8.5,
                effort_score=2.0,
                entity_id=campaign_id,
                entity_type="campaign",
                supporting_data={"domain": "hackernoon.com", "da": 85}
            )
            r2 = RecommendationModel(
                tenant_id=tenant_id,
                recommendation_type="keyword_cluster",
                title="Approve 'Kubernetes Costs' keyword cluster",
                description="Cluster contains 3 highly relevant commercial intent keywords with 4,500 total volume.",
                priority="P1",
                status="active",
                confidence=0.88,
                impact_score=7.0,
                effort_score=1.5,
                entity_id=campaign_id,
                entity_type="campaign",
                supporting_data={"cluster": "Kubernetes Costs"}
            )
            session.add_all([r1, r2])

            evt1 = BusinessIntelligenceEvent(
                tenant_id=tenant_id,
                event_type="link_acquired",
                domain="dzone.com",
                severity="success",
                title="Backlink Verified Live on dzone.com",
                description="A contextual link pointing to the container blog post was verified live.",
                entity_id=campaign_id,
                entity_type="campaign",
                delta={"old_status": "replied", "new_status": "link_acquired"},
                action_required=False
            )
            evt2 = BusinessIntelligenceEvent(
                tenant_id=tenant_id,
                event_type="response_received",
                domain="hackernoon.com",
                severity="info",
                title="Response Received from hackernoon.com",
                description="Elena Rostova replied asking for the draft URL. AI sentiment scored positive.",
                entity_id=campaign_id,
                entity_type="campaign",
                delta={"sentiment": "positive"},
                action_required=True
            )
            session.add_all([evt1, evt2])

    async def reset_workspace(self, tenant_id: UUID) -> dict[str, Any]:
        """Wipe all demo data, clear Redis caches, reset circuit breakers."""
        await self._clear_tenant_data(tenant_id)
        try:
            from seo_platform.core.redis import get_redis
            redis = await get_redis()
            await redis.flushdb()
        except Exception:
            logger.warning("redis_flush_skipped")
        logger.info("workspace_reset tenant=%s", str(tenant_id))
        return {"status": "reset", "tenant_id": str(tenant_id)}


scenario_manager = ScenarioManager()
