#!/usr/bin/env python3
"""Create email_drafts and email_attachments tables"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from seo_platform.core.database import get_session

async def main():
    async with get_session() as session:
        try:
            # Create email_drafts table
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS email_drafts (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tenant_id UUID NOT NULL,
                    template_id VARCHAR(255),
                    subject TEXT NOT NULL DEFAULT '',
                    body_html TEXT NOT NULL DEFAULT '',
                    to_email VARCHAR(255),
                    variables JSONB DEFAULT '{}'::jsonb,
                    status VARCHAR(50) DEFAULT 'draft',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
            await session.commit()
            print("✅ Created email_drafts table")

            # Create indexes
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_email_drafts_tenant
                ON email_drafts(tenant_id)
            """))
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_email_drafts_status
                ON email_drafts(status)
            """))
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_email_drafts_updated
                ON email_drafts(updated_at DESC)
            """))
            await session.commit()
            print("✅ Created indexes on email_drafts")

            # Create email_attachments table
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS email_attachments (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    draft_id UUID REFERENCES email_drafts(id) ON DELETE CASCADE,
                    tenant_id UUID NOT NULL,
                    filename VARCHAR(255) NOT NULL,
                    file_size INTEGER,
                    mime_type VARCHAR(100),
                    storage_path TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
            await session.commit()
            print("✅ Created email_attachments table")

            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_email_attachments_draft
                ON email_attachments(draft_id)
            """))
            await session.commit()
            print("✅ Created indexes on email_attachments")

        except Exception as e:
            await session.rollback()
            print(f"❌ Error: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(main())
