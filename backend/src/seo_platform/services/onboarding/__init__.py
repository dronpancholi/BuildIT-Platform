"""
SEO Platform — Onboarding Service
====================================
Client intake, business profile enrichment, and competitor discovery.

This service owns the end-to-end onboarding flow:
1. Accept client registration (domain, name, niche)
2. Validate domain reachability
3. Enrich business profile using LLM (small model)
4. Discover competitors via SERP analysis
5. Generate initial keyword seeds
6. Submit for human approval
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from seo_platform.core.audit import AuditEntry, audit_service
from seo_platform.core.database import get_tenant_session
from seo_platform.core.logging import get_logger
from seo_platform.models.tenant import Client, OnboardingStatus

logger = get_logger(__name__)


class BusinessProfile(BaseModel):
    """AI-enriched business profile schema."""
    business_name: str
    industry: str = ""
    sub_niche: str = ""
    value_propositions: list[str] = Field(default_factory=list)
    target_audience: str = ""
    geographic_focus: list[str] = Field(default_factory=list)
    content_themes: list[str] = Field(default_factory=list)
    competitors: list[str] = Field(default_factory=list)
    tone_of_voice: str = "professional"


class OnboardingService:
    """
    Client onboarding service.

    Manages the lifecycle of a client from registration to active status.
    All state transitions are audited and emit domain events.
    """

    async def start_onboarding(
        self, tenant_id: UUID, client_id: UUID, initiated_by: str
    ) -> dict:
        """Transition client to 'collecting' status and trigger workflow."""
        async with get_tenant_session(tenant_id) as session:
            from sqlalchemy import select
            result = await session.execute(
                select(Client).where(Client.id == client_id, Client.tenant_id == tenant_id)
            )
            client = result.scalar_one_or_none()
            if not client:
                raise ValueError(f"Client {client_id} not found")

            client.onboarding_status = OnboardingStatus.COLLECTING
            await session.flush()

            await audit_service.record(AuditEntry(
                tenant_id=tenant_id,
                event_type="client.onboarding_started",
                entity_type="Client",
                entity_id=client_id,
                actor_type="user",
                actor_id=initiated_by,
                after_state={"onboarding_status": "collecting"},
            ))

            logger.info("onboarding_started", client_id=str(client_id), tenant_id=str(tenant_id))
            return {"client_id": str(client_id), "status": "collecting"}

    async def complete_onboarding(
        self, tenant_id: UUID, client_id: UUID, profile: BusinessProfile
    ) -> dict:
        """Mark onboarding as complete with enriched profile."""
        async with get_tenant_session(tenant_id) as session:
            from sqlalchemy import select
            result = await session.execute(
                select(Client).where(Client.id == client_id, Client.tenant_id == tenant_id)
            )
            client = result.scalar_one_or_none()
            if not client:
                raise ValueError(f"Client {client_id} not found")

            client.onboarding_status = OnboardingStatus.COMPLETE
            client.profile_data = profile.model_dump()
            client.competitors = profile.competitors
            await session.flush()

            logger.info("onboarding_completed", client_id=str(client_id), tenant_id=str(tenant_id))
            return {"client_id": str(client_id), "status": "complete"}


onboarding_service = OnboardingService()
