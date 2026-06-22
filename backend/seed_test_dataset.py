"""
Phase 11.5G — Internal Test Dataset
====================================
Seeds the database with realistic test data for operator walkthrough.
ALL DATA IS MARKED "DEVELOPMENT DATASET — NOT PRODUCTION".

Usage:
    cd backend
    .venv/bin/python seed_test_dataset.py
"""

import asyncio
import sys
import os
from uuid import uuid4
from datetime import datetime, timedelta
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from sqlalchemy import text
from seo_platform.core.database import get_engine

TENANT_ID = "00000000-0000-0000-0000-000000000001"
DEV_MARKER = "DEVELOPMENT DATASET — NOT PRODUCTION"

CLIENTS = [
    {"name": "Acme Corp", "domain": "acme.com", "niche": "SaaS", "status": "active"},
    {"name": "GreenLeaf Organics", "domain": "greenleaforganics.com", "niche": "E-commerce", "status": "active"},
    {"name": "Urban Realty Group", "domain": "urbanrealtygroup.com", "niche": "Real Estate", "status": "active"},
    {"name": "TechStart Inc", "domain": "techstart.io", "niche": "Technology", "status": "active"},
    {"name": "HealthFirst Clinic", "domain": "healthfirstclinic.com", "niche": "Healthcare", "status": "archived"},
]

CAMPAIGNS = [
    {"client_idx": 0, "name": "Acme Backlink Sprint Q1", "type": "guest_post", "status": "active", "target_count": 50, "acquired": 12},
    {"client_idx": 0, "name": "Acme Guest Posts", "type": "guest_post", "status": "draft", "target_count": 30, "acquired": 0},
    {"client_idx": 1, "name": "GreenLeaf Local Citations", "type": "resource_page", "status": "active", "target_count": 100, "acquired": 45},
    {"client_idx": 1, "name": "GreenLeaf Outreach", "type": "guest_post", "status": "complete", "target_count": 25, "acquired": 22},
    {"client_idx": 2, "name": "Urban Realty Link Building", "type": "guest_post", "status": "cancelled", "target_count": 40, "acquired": 3},
    {"client_idx": 2, "name": "Urban Citation Blast", "type": "resource_page", "status": "paused", "target_count": 80, "acquired": 30},
    {"client_idx": 3, "name": "TechStart Authority Build", "type": "guest_post", "status": "active", "target_count": 60, "acquired": 8},
    {"client_idx": 3, "name": "TechStart Directory Submissions", "type": "resource_page", "status": "draft", "target_count": 50, "acquired": 0},
    {"client_idx": 4, "name": "HealthFirst Community Links", "type": "guest_post", "status": "active", "target_count": 35, "acquired": 15},
    {"client_idx": 4, "name": "HealthFirst Local SEO", "type": "resource_page", "status": "complete", "target_count": 40, "acquired": 38},
]


async def seed():
    engine = get_engine()
    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT COUNT(*) FROM clients WHERE tenant_id = :tid"),
            {"tid": TENANT_ID},
        )
        existing = result.scalar()

        # Check which domains already exist
        result = await conn.execute(
            text("SELECT domain FROM clients WHERE tenant_id = :tid"),
            {"tid": TENANT_ID},
        )
        existing_domains = {row[0] for row in result.fetchall()}

        print(f"🌱 Seeding internal test dataset ({DEV_MARKER})")
        print(f"   Tenant: {TENANT_ID}\n")

        # 1. Create clients
        client_ids = []
        for c in CLIENTS:
            if c["domain"] in existing_domains:
                # Get existing client ID
                result = await conn.execute(
                    text("SELECT id FROM clients WHERE tenant_id = :tid AND domain = :domain"),
                    {"tid": TENANT_ID, "domain": c["domain"]},
                )
                cid = result.scalar()
                client_ids.append(cid)
                print(f"   ⏭️  Client exists: {c['name']} ({c['domain']})")
                continue
            cid = str(uuid4())
            client_ids.append(cid)
            await conn.execute(
                text("""
                    INSERT INTO clients (id, tenant_id, name, domain, niche, onboarding_status, status, created_at, updated_at)
                    VALUES (:id, :tid, :name, :domain, :niche, :onboard, :status, NOW(), NOW())
                """),
                {"id": cid, "tid": TENANT_ID, "name": c["name"], "domain": c["domain"],
                 "niche": c["niche"], "onboard": "complete", "status": c["status"]},
            )
            print(f"   ✅ Client: {c['name']} ({c['domain']})")

        # 2. Create campaigns
        campaign_ids = []
        for camp in CAMPAIGNS:
            camp_id = str(uuid4())
            campaign_ids.append(camp_id)
            started = datetime.utcnow() - timedelta(days=random.randint(1, 30)) if camp["status"] not in ("draft",) else None
            completed = datetime.utcnow() if camp["status"] == "complete" else None
            reply_rate = round(random.uniform(0.05, 0.25), 2) if camp["acquired"] > 0 else 0
            health = round(random.uniform(0.4, 0.95), 2) if camp["status"] == "active" else 0.5

            await conn.execute(
                text("""
                    INSERT INTO backlink_campaigns
                    (id, tenant_id, client_id, name, campaign_type, status,
                     target_link_count, acquired_link_count, total_prospects,
                     total_emails_sent, reply_rate, acquisition_rate, health_score,
                     started_at, completed_at, created_at, updated_at)
                    VALUES (:id, :tid, :cid, :name, :type, :status,
                            :target, :acquired, :prospects, :sent, :reply, :arate, :health,
                            :started, :completed, NOW(), NOW())
                """),
                {"id": camp_id, "tid": TENANT_ID, "cid": client_ids[camp["client_idx"]],
                 "name": camp["name"], "type": camp["type"], "status": camp["status"],
                 "target": camp["target_count"], "acquired": camp["acquired"],
                 "prospects": camp["acquired"] * random.randint(3, 8),
                 "sent": camp["acquired"] * random.randint(2, 5),
                 "reply": reply_rate,
                 "arate": round(camp["acquired"] / max(camp["target_count"], 1), 2),
                 "health": health,
                 "started": started, "completed": completed},
            )
            print(f"   ✅ Campaign: {camp['name']} [{camp['status']}]")

        # Get actual user ID for audit trail
        result = await conn.execute(
            text("SELECT id FROM users WHERE tenant_id = :tid LIMIT 1"),
            {"tid": TENANT_ID},
        )
        user_id = result.scalar() or str(uuid4())

        # 3. Create audit trail entries in audit_ledger
        actions = ["campaign.launched", "campaign.paused", "campaign.cancelled",
                    "campaign.complete", "email.sent", "link.acquired"]
        audit_count = 0
        for _ in range(20):
            action = random.choice(actions)
            days_ago = random.randint(0, 14)
            ts = datetime.utcnow() - timedelta(days=days_ago)
            await conn.execute(
                text("""
                    INSERT INTO audit_ledger
                    (id, tenant_id, action_name, actor_id, actor_type, target_type, target_id,
                     summary, risk_level, created_at, updated_at)
                    VALUES (:id, :tid, :action, :actor, 'user', :ttype, :tid2,
                            :summary, :risk, :ts, :ts)
                """),
                {"id": str(uuid4()), "tid": TENANT_ID, "action": action,
                 "actor": user_id,
                 "ttype": action.split(".")[0],
                 "tid2": str(random.choice(campaign_ids)),
                 "summary": f"{action} — {DEV_MARKER}",
                 "risk": random.choice(["low", "low", "medium"]),
                 "ts": ts},
            )
            audit_count += 1
        print(f"   ✅ Audit Trail Entries: {audit_count}")

        await conn.commit()

    print(f"\n🎉 Seed complete! Data created:")
    print(f"   • 5 clients (1 archived)")
    print(f"   • 10 campaigns (active/draft/completed/failed/paused)")
    print(f"   • {audit_count} audit trail entries")
    print(f"\n⚠️  ALL DATA IS {DEV_MARKER}")


if __name__ == "__main__":
    asyncio.run(seed())
