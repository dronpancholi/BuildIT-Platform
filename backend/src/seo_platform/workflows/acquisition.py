"""
SEO Platform — Link Acquisition Activity
=======================================
Implements the missing link acquisition automation that records an acquired
backlink when a reply is received for a prospect.
"""

from __future__ import annotations

import uuid
from datetime import datetime, UTC

from sqlalchemy import select

from temporalio import activity

from seo_platform.core.database import get_session
from seo_platform.core.events import EventPublisher, LinkAcquiredEvent
from seo_platform.models.backlink import AcquiredLink, BacklinkCampaign, BacklinkProspect
from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


@activity.defn(name="record_acquired_link_activity")
async def record_acquired_link_activity(
    tenant_id: str,
    prospect_id: str,
    campaign_id: str,
    source_url: str = "https://example.com",
    anchor_text: str = "",
    link_type: str = "dofollow",
) -> dict:
    """Create an ``AcquiredLink`` row and emit a ``LinkAcquiredEvent``.

    This activity is idempotent – if a link already exists for the given
    ``prospect_id`` it will be returned without duplication.
    """
    async with get_session() as session:
        # Verify prospect exists and fetch tenant
        prospect = await session.scalar(
            select(BacklinkProspect).where(BacklinkProspect.id == prospect_id)
        )
        if not prospect:
            raise ValueError(f"Prospect {prospect_id} not found")

        # Check if link already recorded
        existing = await session.scalar(
            select(AcquiredLink).where(AcquiredLink.prospect_id == prospect_id)
        )
        if existing:
            logger.info(
                "acquired_link_already_exists",
                prospect_id=prospect_id,
                link_id=str(existing.id),
            )
            return {"link_id": str(existing.id), "status": existing.status}

        # Create new link record
        new_link = AcquiredLink(
            id=uuid.uuid4(),
            tenant_id=prospect.tenant_id,
            campaign_id=campaign_id,
            prospect_id=prospect_id,
            source_url=source_url,
            target_url=prospect.domain,
            anchor_text=anchor_text,
            link_type=link_type,
            status="pending_verification",
            domain_authority_at_acquisition=0.0,
            first_verified_at=None,
            check_count=0,
            verification_history=[],
        )
        session.add(new_link)
        # Increment campaign counters
        campaign = await session.scalar(
            select(BacklinkCampaign).where(BacklinkCampaign.id == campaign_id)
        )
        if campaign:
            if hasattr(campaign, "acquired_link_count"):
                campaign.acquired_link_count = (campaign.acquired_link_count or 0) + 1
        await session.flush()

        # Emit event
        publisher = EventPublisher()
        await publisher.start()
        await publisher.publish(
            LinkAcquiredEvent(
                tenant_id=prospect.tenant_id,
                payload={
                    "acquired_link_id": str(new_link.id),
                    "prospect_id": prospect_id,
                    "campaign_id": campaign_id,
                },
            )
        )
        await publisher.stop()

        logger.info(
            "acquired_link_created",
            link_id=str(new_link.id),
            prospect_id=prospect_id,
        )
        return {"link_id": str(new_link.id), "status": new_link.status}
