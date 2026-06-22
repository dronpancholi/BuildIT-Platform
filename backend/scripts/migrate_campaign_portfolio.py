"""
Campaign Portfolio Migration — Creates saved_views + portfolio indexes
========================================================================
"""

import asyncio
import asyncpg

DSN = "postgresql://seo_platform:seo_platform_dev@localhost:5432/seo_platform"


async def migrate():
    conn = await asyncpg.connect(DSN)
    try:
        # campaign_saved_views table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS campaign_saved_views (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                filters JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS ix_campaign_saved_views_tenant
            ON campaign_saved_views(tenant_id)
        """)
        print("✓ campaign_saved_views table created")

        # Portfolio performance indexes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS ix_backlink_campaigns_client
            ON backlink_campaigns(client_id)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS ix_backlink_campaigns_health
            ON backlink_campaigns(health_score)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS ix_backlink_campaigns_status
            ON backlink_campaigns(status)
        """)
        print("✓ Portfolio indexes created")

        # Verify
        tables = await conn.fetch(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name='campaign_saved_views'"
        )
        if tables:
            print(f"✓ campaign_saved_views table exists: {tables[0]['table_name']}")
        else:
            print("✗ campaign_saved_views table NOT found")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(migrate())
