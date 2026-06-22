#!/usr/bin/env python3
"""Create real template records in database for validation"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import text
from seo_platform.core.database import get_session

async def main():
    templates = [
        {
            "title": "Initial Outreach - Guest Post",
            "category": "outreach",
            "subject": "Quick question about {{domain}}",
            "body": """Hi {{prospect_name}},

I noticed {{domain}} publishes great content about digital marketing.

We recently published a comprehensive guide on [topic] that your audience might find valuable.

Would you be open to a guest post contribution?

Best regards,
{{sender_name}}""",
            "variables": ["prospect_name", "domain", "sender_name"]
        },
        {
            "title": "Follow-up #1 - No Reply",
            "category": "followup",
            "subject": "Re: {{previous_subject}}",
            "body": """Hi {{prospect_name}},

Just following up on my previous email about contributing to {{domain}}.

Would you be interested in collaborating?

Best,
{{sender_name}}""",
            "variables": ["prospect_name", "sender_name", "previous_subject"]
        },
        {
            "title": "Link Insertion Request",
            "category": "link_insertion",
            "subject": "Adding value to your {{domain}} article",
            "body": """Hi {{prospect_name}},

I love your article about [topic] on {{domain}}.

We have a resource that would complement it perfectly. Would you consider adding a link?

Thanks,
{{sender_name}}""",
            "variables": ["prospect_name", "domain", "sender_name"]
        },
        {
            "title": "Partnership Proposal",
            "category": "partnership",
            "subject": "Partnership opportunity with {{domain}}",
            "body": """Hi {{prospect_name}},

I'm reaching out because I see a great partnership opportunity between our companies.

{{domain}} and our platform serve similar audiences.

Interested in exploring a partnership?

Best,
{{sender_name}}""",
            "variables": ["prospect_name", "domain", "sender_name"]
        },
        {
            "title": "Monthly Report Delivery",
            "category": "report",
            "subject": "Your {{report_type}} Report - {{period}}",
            "body": """Hi {{customer_name}},

Attached is your {{report_type}} for {{period}}.

Key highlights:
- Campaigns active: {{active_campaigns}}
- Links acquired: {{links_acquired}}
- Response rate: {{response_rate}}%

Let me know if you have questions.

Best,
{{sender_name}}""",
            "variables": ["customer_name", "report_type", "period", "active_campaigns", "links_acquired", "response_rate", "sender_name"]
        },
        {
            "title": "Thank You - Link Acquired",
            "category": "followup",
            "subject": "Thank you!",
            "body": """Hi {{prospect_name}},

Thank you so much for publishing our contribution on {{domain}}!

We really appreciate the opportunity.

Best regards,
{{sender_name}}""",
            "variables": ["prospect_name", "domain", "sender_name"]
        }
    ]
    
    tenant_id = UUID("00000000-0000-0000-0000-000000000001")
    created_count = 0
    
    async with get_session() as session:
        for tpl in templates:
            try:
                await session.execute(text("""
                    INSERT INTO communication_templates 
                    (tenant_id, title, category, subject, body, variables, created_at, updated_at)
                    VALUES 
                    (:tenant_id, :title, :category, :subject, :body, :variables, :created_at, :updated_at)
                """), {
                    "tenant_id": str(tenant_id),
                    "title": tpl["title"],
                    "category": tpl["category"],
                    "subject": tpl["subject"],
                    "body": tpl["body"],
                    "variables": json.dumps(tpl["variables"]),
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                })
                await session.commit()
                created_count += 1
                print(f"✅ Created: {tpl['title']}")
            except Exception as e:
                await session.rollback()
                print(f"⚠️  Skipped (may exist): {tpl['title']} - {e}")
    
    print(f"\n✅ Created {created_count} templates")

if __name__ == "__main__":
    asyncio.run(main())
