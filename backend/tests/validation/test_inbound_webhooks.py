import pytest
from uuid import uuid4
from datetime import datetime, UTC
from sqlalchemy import select

from seo_platform.core.database import get_tenant_session
from seo_platform.models.backlink import (
    BacklinkCampaign,
    BacklinkProspect,
    OutreachThread,
    CampaignType,
    CampaignStatus,
    ProspectStatus,
    ThreadStatus,
)
from seo_platform.api.endpoints.inbound_webhooks import (
    NormalisedInbound,
    _process_inbound_reply,
)
from seo_platform.core.auth import CurrentUser

pytestmark = pytest.mark.asyncio(loop_scope="module")

async def _ensure_test_tenant(session, tenant_id):
    from sqlalchemy import text
    existing = await session.execute(
        text("SELECT id FROM tenants WHERE id = :id"), {"id": tenant_id}
    )
    if not existing.scalar_one_or_none():
        await session.execute(
            text("INSERT INTO tenants (id, name, slug, plan) VALUES (:id, :name, :slug, :plan) ON CONFLICT DO NOTHING"),
            {"id": tenant_id, "name": f"Test Tenant {tenant_id}", "slug": f"test-{tenant_id}", "plan": "growth"},
        )

async def _ensure_test_client(session, tenant_id, client_id):
    from sqlalchemy import text
    await _ensure_test_tenant(session, tenant_id)
    existing = await session.execute(
        text("SELECT id FROM clients WHERE id = :id"), {"id": client_id}
    )
    if not existing.scalar_one_or_none():
        await session.execute(
            text(
                "INSERT INTO clients (id, tenant_id, name, domain, onboarding_status) "
                "VALUES (:id, :tid, :name, :domain, :status) ON CONFLICT DO NOTHING"
            ),
            {
                "id": client_id, "tid": tenant_id,
                "name": f"Test Client {client_id}",
                "domain": "example.com",
                "status": "pending",
            },
        )

async def test_inbound_reply_processing_persists_to_db():
    tenant_id = uuid4()
    client_id = uuid4()

    async with get_tenant_session(tenant_id) as session:
        await _ensure_test_tenant(session, tenant_id)
        await _ensure_test_client(session, tenant_id, client_id)

        # 1. Create a campaign
        campaign = BacklinkCampaign(
            tenant_id=tenant_id,
            client_id=client_id,
            name="Inbound Webhook Test Campaign",
            campaign_type=CampaignType.GUEST_POST,
            status=CampaignStatus.ACTIVE,
        )
        session.add(campaign)
        await session.flush()

        # 2. Create a prospect
        prospect = BacklinkProspect(
            tenant_id=tenant_id,
            campaign_id=campaign.id,
            domain="example-blog.com",
            url="http://example-blog.com/contact",
            status=ProspectStatus.CONTACTED,
            contact_email="blogger@example-blog.com",
        )
        session.add(prospect)
        await session.flush()

        # 3. Create a thread
        msg_id = f"msg-id-{uuid4()}"
        thread = OutreachThread(
            tenant_id=tenant_id,
            campaign_id=campaign.id,
            prospect_id=prospect.id,
            from_email="outreach@my-tenant.com",
            to_email="blogger@example-blog.com",
            subject="Collaboration request",
            status=ThreadStatus.SENT,
            provider_message_id=msg_id,
        )
        session.add(thread)
        await session.flush()
        await session.commit()

    # 4. Invoke processing with normalized inbound payload
    payload = NormalisedInbound(
        from_email="blogger@example-blog.com",
        to_email="outreach@my-tenant.com",
        subject="Re: Collaboration request",
        body_text="Sure, we can collaborate!",
        message_id=f"reply-msg-{uuid4()}",
        in_reply_to=msg_id,
        provider="sendgrid",
    )

    user = CurrentUser(
        id=uuid4(),
        tenant_id=tenant_id,
        email="operator@my-tenant.com",
        role="operator",
    )

    result = await _process_inbound_reply(payload, user)
    assert result["status"] == "ok"
    assert result["thread_id"] == str(thread.id)

    # 5. Check database states after processing
    async with get_tenant_session(tenant_id) as session:
        # Check thread status updated to REPLIED
        db_thread = await session.get(OutreachThread, thread.id)
        assert db_thread.status == ThreadStatus.REPLIED
        assert db_thread.replied_at is not None

        # Check prospect status updated to REPLIED
        db_prospect = await session.get(BacklinkProspect, prospect.id)
        assert db_prospect.status == ProspectStatus.REPLIED

        # Check campaign stats updated
        db_campaign = await session.get(BacklinkCampaign, campaign.id)
        assert db_campaign.reply_rate > 0.0
