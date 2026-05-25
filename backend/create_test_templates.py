#!/usr/bin/env python3
"""Create test communication templates"""

import asyncio
import sys
sys.path.insert(0, '.')

from datetime import datetime, timezone
from uuid import UUID

async def create_templates():
    from seo_platform.core.database import get_session
    
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
            "title": "Follow-up #1",
            "category": "followup",
            "subject": "Re: {{subject}}",
            "body": """Hi {{prospect_name}},

Just following up on my previous email. 

Would you be interested in collaborating?

Best,
{{sender_name}}""",
            "variables": ["prospect_name", "sender_name", "subject"]
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
            "title": "Report Delivery",
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
        }
    ]
    
    async with get_session() as session:
        tenant_id = UUID("00000000-0000-0000-0000-000000000001")
        
        for tpl in templates:
            try:
                await session.execute(f"""
                    INSERT INTO communication_templates 
                    (tenant_id, title, category, subject, body, variables, created_at, updated_at)
                    VALUES 
                    ('{tenant_id}', '{tpl["title"]}', '{tpl["category"]}', 
                     '{tpl["subject"]}', '{tpl["body"]}', 
                     '{tpl["variables"]}', NOW(), NOW())
                """)
                print(f"✅ Created: {tpl['title']}")
            except Exception as e:
                print(f"❌ Failed {tpl['title']}: {e}")
        
        await session.commit()
        print("\nDone!")

if __name__ == "__main__":
    asyncio.run(create_templates())
