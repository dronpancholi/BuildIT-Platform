"""
SEO Platform — Local Development Seed Script
=============================================
Populates the database with realistic test data for the operations console.
Run with: uv run python -m seo_platform.scripts.seed
"""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from faker import Faker

from seo_platform.core.database import get_session_factory
from seo_platform.core.logging import get_logger
from seo_platform.models.approval import ApprovalCategory, ApprovalRequestModel, ApprovalStatusEnum, RiskLevelEnum
from seo_platform.models.backlink import BacklinkCampaign, CampaignStatus, CampaignType
from seo_platform.models.tenant import Client, Tenant, TenantPlan, User, UserRole

logger = get_logger(__name__)
fake = Faker()

async def seed_database() -> None:
    logger.info("Starting database seed...")

    # Static IDs for predictability
    tenant_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    client_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    user_id = uuid.UUID("22222222-2222-2222-2222-222222222222")

    async_session_maker = get_session_factory()
    async with async_session_maker() as session:
        # Check if already seeded
        existing_tenant = await session.get(Tenant, tenant_id)
        if existing_tenant:
            logger.info("Database already seeded. Exiting.")
            return

        # 1. Tenant
        tenant = Tenant(
            id=tenant_id,
            name="Acme Corp Enterprise",
            slug="acme-corp",
            plan=TenantPlan.ENTERPRISE
        )
        session.add(tenant)

        # 2. User
        user = User(
            id=user_id,
            tenant_id=tenant_id,
            external_id="user_prod_xxxx",
            email="admin@acmecorp.com",
            name="System Administrator",
            role=UserRole.TENANT_ADMIN,
            is_active=True
        )
        session.add(user)

        # 3. Client
        client = Client(
            id=client_id,
            tenant_id=tenant_id,
            name="TechStart Inc.",
            domain="techstart.io",
            niche="B2B SaaS"
        )
        session.add(client)

        # Flush to ensure primary entities are persisted before child associations
        await session.flush()

        # We need to set the RLS policy for the current session to insert into isolated tables
        from sqlalchemy import text
        await session.execute(text("SET LOCAL app.current_tenant = '00000000-0000-0000-0000-000000000001'"))

        # 4. Campaigns
        campaign1 = BacklinkCampaign(
            tenant=client.tenant,
            client=client,
            name="SaaS Resource Page Outreach",
            campaign_type=CampaignType.RESOURCE_PAGE,
            status=CampaignStatus.ACTIVE,
            target_link_count=25,
            acquired_link_count=4,
            total_prospects=450,
            total_emails_sent=120,
            health_score=0.92,
        )
        session.add(campaign1)

        campaign2 = BacklinkCampaign(
            tenant=client.tenant,
            client=client,
            name="Fintech Guest Posting Q3",
            campaign_type=CampaignType.GUEST_POST,
            status=CampaignStatus.MONITORING,
            target_link_count=10,
            acquired_link_count=10,
            total_prospects=150,
            total_emails_sent=150,
            health_score=0.98,
        )
        session.add(campaign2)

        # 5. Approvals
        approval1 = ApprovalRequestModel(
            tenant=tenant,
            workflow_run_id=f"wf-{uuid.uuid4()}",
            category=ApprovalCategory.OUTREACH_TEMPLATES,
            risk_level=RiskLevelEnum.CRITICAL,
            status=ApprovalStatusEnum.PENDING,
            summary="Review 42 generated outreach emails. High risk due to strict tone requirements.",
            ai_risk_summary="Detected highly aggressive CTA language in 2 templates.",
            sla_deadline=datetime.now(UTC) + timedelta(hours=4),
            context_snapshot={"items": 42, "domain": "techstart.io"}
        )
        session.add(approval1)

        approval2 = ApprovalRequestModel(
            tenant=tenant,
            workflow_run_id=f"wf-{uuid.uuid4()}",
            category=ApprovalCategory.PROSPECT_LIST,
            risk_level=RiskLevelEnum.MEDIUM,
            status=ApprovalStatusEnum.PENDING,
            summary="Review 156 scored prospects.",
            ai_risk_summary="Score distribution is nominal.",
            sla_deadline=datetime.now(UTC) + timedelta(days=1),
            context_snapshot={"items": 156}
        )
        session.add(approval2)

        await session.commit()
        logger.info("Database successfully seeded with realistic test data!")

if __name__ == "__main__":
    asyncio.run(seed_database())
