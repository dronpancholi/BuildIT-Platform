#!/usr/bin/env python3
"""Create communication_templates table"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from seo_platform.core.database import get_session

async def main():
    async with get_session() as session:
        try:
            # Create table
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS communication_templates (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tenant_id UUID NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    category VARCHAR(100) NOT NULL,
                    subject TEXT NOT NULL,
                    body TEXT NOT NULL,
                    variables JSONB DEFAULT '[]'::jsonb,
                    is_archived BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
            await session.commit()
            print("✅ Created communication_templates table")
            
            # Create index
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_comm_templates_tenant 
                ON communication_templates(tenant_id)
            """))
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_comm_templates_category 
                ON communication_templates(category)
            """))
            await session.commit()
            print("✅ Created indexes")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(main())
