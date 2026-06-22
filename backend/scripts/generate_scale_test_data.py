"""
Scale Test Data Generator — Phase 12C.7 (DEV-ONLY)
====================================================
Generates:
- 100+ customers (clients)
- 500+ campaigns
- 10,000+ prospects
- 10,000+ email threads

This script uses random.uuid4() and hardcoded numbers — it is NOT a
production bootstrap path. It exists for local load/UI testing only.

Phase 2.5.1: Not invoked by the application. Must be run explicitly.

Usage:
    PYTHONPATH=backend/src .venv/bin/python3 backend/scripts/generate_scale_test_data.py
"""

import asyncio
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Tuple

import asyncpg

DSN = "postgresql://seo_platform:seo_platform_dev@localhost:5432/seo_platform"
TENANT_ID = "00000000-0000-0000-0000-000000000001"

CAMPAIGN_TYPES = ["guest_post", "resource_page", "niche_edit", "broken_link", "skyscraper", "haro"]
CAMPAIGN_STATUSES = ["draft", "prospecting", "scoring", "outreach_prep", "awaiting_approval", "active", "paused", "monitoring", "complete", "cancelled"]
PROSPECT_STATUSES = ["new", "scored", "approved", "rejected", "outreach_queued", "contacted", "replied", "link_acquired", "link_lost", "unresponsive"]
THREAD_STATUSES = ["draft", "queued", "sent", "delivered", "opened", "replied", "bounced", "spam_reported", "unsubscribed", "link_acquired"]
LINK_STATUSES = ["pending_verification", "verified_live", "verified_nofollow", "removed", "broken"]

NICHE_PREFIXES = [
    "Tech", "Health", "Finance", "Marketing", "Design", "Legal", "Real Estate",
    "Travel", "Food", "Fashion", "Education", "E-commerce", "SaaS", "Agency",
    "Consulting", "Fitness", "Music", "Photography", "Gaming", "Sports",
]


def random_past_days(max_days: int = 90) -> datetime:
    return datetime.now(timezone.utc) - timedelta(
        days=random.randint(0, max_days),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )


async def generate_scale_data():
    conn = await asyncpg.connect(DSN)
    total_start = datetime.now(timezone.utc)

    try:
        # ── Step 1: 100 Customers ──
        print("Generating 100 customers...")
        client_ids: List[str] = []
        for i in range(100):
            cid = str(uuid.uuid4())
            client_ids.append(cid)
            niche = random.choice(NICHE_PREFIXES)
            name = f"{niche} Client {i+1}"
            domain = f"{name.lower().replace(' ', '-')}-{cid}.com"
            await conn.execute("""
                INSERT INTO clients (id, tenant_id, name, domain, niche, geo_focus, business_type, onboarding_status, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7::business_type, $8::onboarding_status, $9, $10)
                ON CONFLICT (id) DO NOTHING
            """, cid, TENANT_ID, name, domain, niche.lower(), '["us"]', "saas", "complete",
                random_past_days(180), datetime.now(timezone.utc))
        print(f"  ✓ {len(client_ids)} customers created")

        # ── Step 2: 500 Campaigns ──
        print("Generating 500 campaigns...")
        campaign_ids: List[str] = []
        for i in range(500):
            cid = str(uuid.uuid4())
            campaign_ids.append(cid)
            client_id = random.choice(client_ids)
            ctype = random.choice(CAMPAIGN_TYPES)
            status = random.choices(
                CAMPAIGN_STATUSES,
                weights=[5, 5, 5, 3, 3, 30, 5, 20, 15, 5],
                k=1
            )[0]
            target_links = random.randint(5, 50)
            acquired = random.randint(0, target_links) if status in ("monitoring", "complete") else 0
            prospects = random.randint(10, 200)
            emails_sent = random.randint(0, prospects * 2)
            reply_rate = round(random.uniform(0.05, 0.4), 4)
            acq_rate = round(random.uniform(0.02, 0.2), 4)
            health = round(random.uniform(0.3, 1.0), 4)
            created = random_past_days(120)
            updated = created + timedelta(days=random.randint(0, 30))

            await conn.execute("""
                INSERT INTO backlink_campaigns (id, tenant_id, client_id, name, campaign_type, status,
                    target_link_count, acquired_link_count, total_prospects, total_emails_sent,
                    reply_rate, acquisition_rate, health_score, config, created_at, updated_at)
                VALUES ($1,$2,$3,$4,$5::campaign_type,$6::campaign_status,
                    $7,$8,$9,$10,$11,$12,$13,$14,$15,$16)
                ON CONFLICT (id) DO NOTHING
            """, cid, TENANT_ID, client_id,
                f"Campaign {i+1} - {ctype.replace('_', ' ').title()}", ctype, status,
                target_links, acquired, prospects, emails_sent,
                reply_rate, acq_rate, health,
                json.dumps({"assigned_manager": random.choice([None, "Alice", "Bob", "Charlie", "Diana"]),
                            "tags": random.sample(["urgent", "high-value", "experimental", "renewal", "flagship", "test"], k=random.randint(0, 3))}),
                created, updated)
        print(f"  ✓ {len(campaign_ids)} campaigns created")

        # ── Step 3: 10,000 Prospects ──
        print("Generating 10,000 prospects...")
        prospect_ids: List[str] = []
        batch_size = 500
        total_prospects = 10000
        for batch_start in range(0, total_prospects, batch_size):
            batch_end = min(batch_start + batch_size, total_prospects)
            values_batch = []
            for i in range(batch_start, batch_end):
                pid = str(uuid.uuid4())
                prospect_ids.append(pid)
                campaign_id = random.choice(campaign_ids)
                domain = f"example-{i}-{random.randint(1000,9999)}.com"
                status = random.choice(PROSPECT_STATUSES)
                da = round(random.uniform(10, 90), 2)
                relevance = round(random.uniform(0.3, 1.0), 4)
                spam = round(random.uniform(0, 30), 2)
                composite = round((da / 100 * 0.3 + relevance * 0.5 + (1 - spam / 100) * 0.2), 4)
                created = random_past_days(90)
                traffic = round(random.uniform(0, 10000), 2)
                confidence = round(random.uniform(0.5, 1.0), 4)
                values_batch.append((
                    pid, TENANT_ID, campaign_id, domain, f"https://{domain}/page-{i}",
                    status, da, relevance, spam, traffic, composite, confidence,
                    f"contact-{i}@{domain}", f"Contact {i}",
                    random.choice(["email", "linkedin", "twitter", "website"]),
                    "{}", "{}", created, created,
                ))

            await conn.executemany("""
                INSERT INTO backlink_prospects (id, tenant_id, campaign_id, domain, url, status,
                    domain_authority, relevance_score, spam_score, traffic_score, composite_score, confidence,
                    contact_email, contact_name, contact_source, scoring_rationale, page_data, created_at, updated_at)
                VALUES ($1,$2,$3,$4,$5,$6::prospect_status,
                    $7,$8,$9,$10,$11,$12,$13,$14,$15,$16::jsonb,$17::jsonb,$18,$19)
                ON CONFLICT (id) DO NOTHING
            """, values_batch)

            if (batch_end % 2000) == 0:
                print(f"  ... {batch_end}/{total_prospects} prospects")

        print(f"  ✓ {len(prospect_ids)} prospects created")

        # ── Step 4: 10,000 Email Threads ──
        print("Generating 10,000 email threads...")
        thread_ids: List[str] = []
        for batch_start in range(0, 10000, batch_size):
            batch_end = min(batch_start + batch_size, 10000)
            values_batch = []
            for i in range(batch_start, batch_end):
                tid = str(uuid.uuid4())
                thread_ids.append(tid)
                campaign_id = random.choice(campaign_ids)
                prospect_id = random.choice(prospect_ids)
                status = random.choices(THREAD_STATUSES, weights=[2, 5, 25, 20, 15, 10, 3, 2, 1, 5], k=1)[0]
                sent_at = random_past_days(60)
                replied_at = sent_at + timedelta(days=random.randint(1, 14)) if status == "replied" else None
                confidence = round(random.uniform(0.5, 0.99), 4)
                values_batch.append((
                    tid, TENANT_ID, campaign_id, prospect_id,
                    status,
                    f"outbound@{random.choice(['agency-a', 'agency-b', 'platform'])}.com",
                    f"person{i}@example.com",
                    f"Subject: Outreach #{i}", "<p>Test body</p>",
                    random.randint(0, 3), random.randint(0, 5),
                    random.choice(["simulated", "mailgun", "resend"]),
                    f"msg_{i}_{uuid.uuid4().hex[:8]}",
                    sent_at, replied_at,
                    confidence, "{}", sent_at,
                ))

            await conn.executemany("""
                INSERT INTO outreach_threads (id, tenant_id, campaign_id, prospect_id,
                    status, from_email, to_email, subject, body_html,
                    follow_up_count, max_follow_ups, provider, provider_message_id,
                    sent_at, replied_at, confidence_score, ai_personalization, created_at)
                VALUES ($1,$2,$3,$4,$5::thread_status,
                    $6,$7,$8,$9,$10,$11,$12,$13,
                    $14,$15,$16,$17::jsonb, $18)
                ON CONFLICT (id) DO NOTHING
            """, values_batch)

            if (batch_end % 2000) == 0:
                print(f"  ... {batch_end}/10000 threads")

        print(f"  ✓ {len(thread_ids)} email threads created")

        # ── Step 5: Update campaign counts ──
        print("Updating campaign aggregate counts...")
        await conn.execute("""
            UPDATE backlink_campaigns c
            SET total_prospects = sub.p_count,
                total_emails_sent = sub.e_count
            FROM (
                SELECT campaign_id,
                       COUNT(*) AS p_count,
                       COUNT(*) FILTER (WHERE status::text IN ('sent','delivered','opened','replied')) AS e_count
                FROM outreach_threads
                WHERE tenant_id = $1
                GROUP BY campaign_id
            ) sub
            WHERE c.id = sub.campaign_id
        """, TENANT_ID)
        print("  ✓ Campaign counts updated")

        # ── Step 7: Verification ──
        print("\n═══ Verification ═══")
        counts = await conn.fetch("""
            SELECT
                (SELECT COUNT(*) FROM clients WHERE tenant_id = $1) AS clients,
                (SELECT COUNT(*) FROM backlink_campaigns WHERE tenant_id = $1) AS campaigns,
                (SELECT COUNT(*) FROM backlink_prospects WHERE tenant_id = $1) AS prospects,
                (SELECT COUNT(*) FROM outreach_threads WHERE tenant_id = $1) AS threads
        """, TENANT_ID)
        row = counts[0]
        print(f"  Clients:   {row['clients']}")
        print(f"  Campaigns: {row['campaigns']}")
        print(f"  Prospects: {row['prospects']}")
        print(f"  Threads:   {row['threads']}")

        elapsed = (datetime.now(timezone.utc) - total_start).total_seconds()
        print(f"\n✅ Scale data generated in {elapsed:.1f}s")

    finally:
        await conn.close()


if __name__ == "__main__":
    import json
    asyncio.run(generate_scale_data())
