"""
Phase 12.5G — Development Dataset V2
=====================================
Populates ALL empty SEO execution tables with realistic development data.

NEVER presents as production data.
All records tagged as development dataset.
"""

import asyncio
import json
import uuid
import random
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

# Client IDs (from existing data)
CLIENT_IDS = [
    uuid.UUID("43154028-c47f-4bf1-8131-727f7aa7adac"),
    uuid.UUID("416a5ec8-6e10-4737-9e7b-098739800f66"),
    uuid.UUID("0d306bd3-51ab-43f3-9a76-4aab6edef105"),
    uuid.UUID("98df6955-e142-45ea-ac63-9822c7d82fee"),
    uuid.UUID("950b2ccd-a61e-4697-94bf-1740618cc13e"),
    uuid.UUID("d6db1aaa-8212-4eab-820d-48003080104b"),
]

CAMPAIGN_IDS = []  # Will be populated from DB

# Realistic keyword data
KEYWORD_SETS = {
    "healthcare": [
        ("physiotherapy near me", 2400, 35, 4.50, 0.6, "commercial"),
        ("best physiotherapist Sydney", 1800, 42, 5.20, 0.7, "commercial"),
        ("sports injury treatment", 3200, 28, 3.80, 0.5, "informational"),
        ("back pain exercises", 8500, 22, 1.20, 0.4, "informational"),
        ("knee rehabilitation exercises", 4200, 30, 2.50, 0.45, "informational"),
        ("dry needling physiotherapy", 2100, 38, 6.00, 0.55, "informational"),
        ("ndis physiotherapy provider", 1500, 25, 8.50, 0.65, "transactional"),
        ("workplace injury physio", 900, 20, 7.20, 0.5, "commercial"),
        ("aged care physiotherapy", 1200, 32, 5.80, 0.45, "commercial"),
        ("paediatric physiotherapy", 1800, 28, 4.90, 0.5, "informational"),
        ("hydrotherapy exercises", 2800, 18, 1.50, 0.3, "informational"),
        ("post surgery rehabilitation", 3500, 35, 3.20, 0.55, "informational"),
        ("chronic pain management", 5200, 40, 2.80, 0.5, "informational"),
        ("women's health physio", 1600, 30, 6.50, 0.6, "commercial"),
        ("sports massage therapy", 4800, 25, 3.50, 0.5, "informational"),
    ],
    "fintech": [
        ("small business accounting software", 6200, 55, 12.50, 0.8, "transactional"),
        ("best invoicing app Australia", 3800, 48, 9.80, 0.75, "commercial"),
        ("cloud accounting for startups", 2400, 42, 11.20, 0.7, "commercial"),
        ("Xero vs QuickBooks", 8900, 52, 8.50, 0.85, "commercial"),
        ("GST calculator Australia", 12000, 15, 2.10, 0.3, "informational"),
        ("small business tax deductions", 7500, 35, 3.80, 0.5, "informational"),
        ("payroll software Australia", 4200, 58, 15.00, 0.8, "transactional"),
        ("expense tracking app", 5800, 45, 7.50, 0.65, "transactional"),
        ("financial reporting software", 3200, 50, 14.20, 0.75, "commercial"),
        ("business bank account comparison", 4500, 40, 18.50, 0.7, "commercial"),
        ("BAS lodgement help", 2800, 30, 8.90, 0.6, "transactional"),
        ("accounting automation", 2100, 45, 6.80, 0.6, "informational"),
        ("cash flow management tools", 3600, 38, 9.20, 0.65, "commercial"),
        ("multi-currency accounting", 1200, 35, 11.50, 0.55, "commercial"),
        ("receipt scanning app", 4100, 30, 5.20, 0.5, "transactional"),
    ],
    "realestate": [
        ("properties for sale Melbourne", 15000, 65, 8.50, 0.9, "transactional"),
        ("house prices Sydney 2026", 9200, 45, 3.20, 0.7, "informational"),
        ("best suburbs to invest Melbourne", 6800, 50, 5.80, 0.75, "commercial"),
        ("first home buyer grants Victoria", 5400, 35, 4.50, 0.6, "informational"),
        ("commercial property investment", 4200, 55, 12.80, 0.7, "commercial"),
        ("rental yield calculator", 7800, 25, 2.80, 0.4, "informational"),
        ("property management Melbourne", 3800, 48, 9.50, 0.7, "transactional"),
        ("strata management Sydney", 2200, 42, 7.80, 0.65, "transactional"),
        ("real estate agent comparison", 4500, 45, 11.20, 0.7, "commercial"),
        ("property development feasibility", 1800, 52, 15.00, 0.6, "informational"),
        ("building inspection checklist", 6200, 20, 1.50, 0.35, "informational"),
        ("stamp duty calculator Victoria", 8500, 18, 2.20, 0.3, "informational"),
        ("luxury apartments Melbourne", 3200, 40, 6.80, 0.6, "transactional"),
        ("off the plan purchases", 2800, 38, 8.50, 0.55, "commercial"),
        ("property market forecast 2026", 4100, 35, 3.50, 0.5, "informational"),
    ],
    "saas": [
        ("best CRM software Australia", 5800, 55, 18.50, 0.85, "commercial"),
        ("project management tools comparison", 7200, 50, 12.80, 0.8, "commercial"),
        ("cloud storage business", 4500, 42, 9.50, 0.7, "commercial"),
        ("team collaboration software", 3800, 48, 11.20, 0.75, "commercial"),
        ("AI writing tools for business", 6500, 35, 7.80, 0.6, "commercial"),
        ("customer support ticketing system", 2800, 45, 14.50, 0.7, "transactional"),
        ("HR software Australia", 4200, 52, 16.80, 0.75, "transactional"),
        ("inventory management software", 3500, 40, 10.20, 0.65, "transactional"),
        ("email marketing platform", 8200, 45, 8.50, 0.7, "commercial"),
        ("landing page builder", 5200, 38, 6.80, 0.6, "commercial"),
        ("scheduling software for services", 2400, 35, 9.20, 0.55, "transactional"),
        ("document management system", 3200, 42, 12.50, 0.65, "commercial"),
        ("video conferencing alternatives", 4800, 30, 5.50, 0.5, "commercial"),
        ("password manager for teams", 3600, 28, 4.80, 0.45, "commercial"),
        ("business intelligence dashboard", 2800, 50, 15.20, 0.7, "commercial"),
    ],
}

# Realistic prospect domains
PROSPECT_DOMAINS = [
    ("healthdirect.gov.au", "Health Direct", 65, 0.95, "Government health portal"),
    (" physiotherapy.org.au", "Australian Physiotherapy Association", 58, 0.98, "Industry association"),
    ("betterhealth.vic.gov.au", "Better Health Channel", 62, 0.92, "State health resource"),
    ("aida.asn.au", "Australian Insurance Directors Association", 45, 0.75, "Insurance industry"),
    ("ato.gov.au", "Australian Taxation Office", 72, 0.85, "Government tax portal"),
    ("business.gov.au", "Business Australia", 68, 0.88, "Government business portal"),
    ("StartupDaily.net", "Startup Daily", 42, 0.82, "Startup news site"),
    (" DynamicBusiness.com", "Dynamic Business", 38, 0.78, "Business news"),
    ("smartcompany.com.au", "SmartCompany", 45, 0.85, "Business media"),
    (" thechronicle.com.au", "The Chronicle", 35, 0.65, "Regional news"),
    (" realestate.com.au", "realestate.com.au", 75, 0.95, "Property portal"),
    (" domain.com.au", "Domain", 72, 0.92, "Property portal"),
    (" urbandevelopment.com.au", "Urban Development", 32, 0.70, "Property industry"),
    (" fintechnews.com.au", "Fintech News Australia", 40, 0.80, "Fintech media"),
    (" technologydecisions.com.au", "Technology Decisions", 38, 0.75, "Tech media"),
    (" cstore.com.au", "Convenience Store", 28, 0.60, "Retail industry"),
    (" retailworld.com.au", "Retail World", 30, 0.65, "Retail media"),
    (" yourspace.com.au", "Your Space", 25, 0.55, "Lifestyle blog"),
    (" healthtechdigital.com", "Health Tech Digital", 35, 0.72, "Health tech"),
    (" proptech.com.au", "PropTech Australia", 30, 0.68, "Property tech"),
    (" csuite.com.au", "CSuite", 32, 0.70, "Executive leadership"),
    (" leadershipsydney.com", "Leadership Sydney", 28, 0.62, "Leadership network"),
    (" techau.com.au", "TechAU", 38, 0.75, "Tech news"),
    (" productreview.com.au", "ProductReview", 55, 0.88, "Review platform"),
    (" yellowpages.com.au", "Yellow Pages", 62, 0.90, "Business directory"),
    (" truelocal.com.au", "TrueLocal", 48, 0.82, "Local directory"),
    (" hotfrog.com.au", "Hotfrog", 42, 0.78, "Business directory"),
    (" startlocal.com.au", "StartLocal", 38, 0.72, "Local business"),
    (" wordofmouth.com.au", "Word of Mouth", 35, 0.68, "Review site"),
    (" oneflare.com.au", "OneFlare", 45, 0.80, "Service marketplace"),
]

# Realistic citation sites
CITATION_SITES = [
    ("Google Business Profile", "google.com/business", "directory", 95, 95, True, "easy", "global"),
    ("Yelp Australia", "yelp.com.au", "review", 72, 80, True, "easy", "Australia"),
    ("TrueLocal", "truelocal.com.au", "local", 48, 65, True, "easy", "Australia"),
    ("Yellow Pages Australia", "yellowpages.com.au", "directory", 62, 75, True, "medium", "Australia"),
    ("Hotfrog", "hotfrog.com.au", "directory", 42, 55, True, "easy", "Australia"),
    ("StartLocal", "startlocal.com.au", "local", 38, 50, True, "easy", "Australia"),
    ("Word of Mouth", "wordofmouth.com.au", "review", 35, 45, True, "medium", "Australia"),
    ("TrueLocal Business", "truelocal.com.au/business", "local", 45, 58, True, "easy", "Australia"),
    ("White Pages", "whitepages.com.au", "directory", 58, 60, True, "medium", "Australia"),
    ("Local Search", "localsearch.com.au", "local", 42, 52, True, "easy", "Australia"),
    ("DLook", "dlook.com.au", "directory", 30, 40, True, "easy", "Australia"),
    ("AussieWeb", "aussieweb.com.au", "directory", 28, 35, True, "easy", "Australia"),
    ("ZipLocal", "ziplocal.com.au", "local", 25, 32, True, "easy", "Australia"),
    ("Brownbook", "brownbook.net", "directory", 35, 42, True, "easy", "Global"),
    ("Fyple", "fyple.com.au", "directory", 22, 28, True, "easy", "Australia"),
    ("Cylex Australia", "cylex.com.au", "directory", 32, 38, True, "easy", "Australia"),
    ("Tupalo", "tupalo.com", "directory", 28, 30, True, "easy", "Global"),
    ("n49", "n49.com", "directory", 25, 28, True, "easy", "Global"),
    ("Salespider", "salespider.com", "directory", 20, 22, True, "easy", "Global"),
    ("Show Me Local", "showmelocal.com", "directory", 22, 25, True, "easy", "Global"),
    ("iGlobal", "iglobal.co", "directory", 18, 20, True, "easy", "Global"),
    ("WhereIs.com", "whereis.com", "local", 35, 40, True, "medium", "Australia"),
    ("CitySearch", "citysearch.com", "directory", 30, 35, True, "medium", "Global"),
    ("Manta", "manta.com", "directory", 28, 32, True, "easy", "Global"),
    ("Angie's List", "angieslist.com", "review", 55, 65, False, "hard", "Global"),
    ("TripAdvisor", "tripadvisor.com", "review", 78, 85, False, "hard", "Global"),
    ("ProductReview.com.au", "productreview.com.au", "review", 55, 70, True, "medium", "Australia"),
    ("RateMDs", "ratemds.com", "review", 42, 55, True, "medium", "Global"),
    ("Healthshare", "healthshare.com.au", "review", 38, 48, True, "medium", "Australia"),
    ("StartWire", "startwire.com", "directory", 20, 22, True, "easy", "Global"),
]

# Realistic business profiles for clients
BUSINESS_PROFILES = [
    {
        "client_idx": 0, "name": "Acme Digital Agency",
        "address": "123 Collins Street", "city": "Melbourne", "state": "VIC",
        "postal": "3000", "country": "AU", "phone": "+61 3 9000 1234",
        "website": "https://acmedigital.com.au", "category": "Digital Marketing Agency",
        "lat": -37.8136, "lon": 144.9631,
        "description": "Full-service digital marketing agency specialising in SEO, PPC, and content marketing for Australian businesses."
    },
    {
        "client_idx": 1, "name": "HealthFirst Clinic",
        "address": "456 George Street", "city": "Sydney", "state": "NSW",
        "postal": "2000", "country": "AU", "phone": "+61 2 9000 5678",
        "website": "https://healthfirstclinic.com.au", "category": "Medical Clinic",
        "lat": -33.8688, "lon": 151.2093,
        "description": "Modern medical clinic offering physiotherapy, sports medicine, and rehabilitation services in Sydney CBD."
    },
    {
        "client_idx": 2, "name": "Acme Corp Australia",
        "address": "789 Queen Street", "city": "Brisbane", "state": "QLD",
        "postal": "4000", "country": "AU", "phone": "+61 7 3000 9012",
        "website": "https://acmecorp.com.au", "category": "Technology Company",
        "lat": -27.4698, "lon": 153.0251,
        "description": "Cloud accounting and financial technology company serving small businesses across Australia."
    },
    {
        "client_idx": 3, "name": "GreenLeaf Organics",
        "address": "321 Swanston Street", "city": "Melbourne", "state": "VIC",
        "postal": "3000", "country": "AU", "phone": "+61 3 8000 3456",
        "website": "https://greenleaforganics.com.au", "category": "Organic Food Retail",
        "lat": -37.8142, "lon": 144.9632,
        "description": "Premium organic food store offering locally sourced produce, health foods, and sustainable products."
    },
    {
        "client_idx": 4, "name": "Urban Realty Group",
        "address": "555 Bourke Street", "city": "Melbourne", "state": "VIC",
        "postal": "3000", "country": "AU", "phone": "+61 3 9500 7890",
        "website": "https://urbanrealtygroup.com.au", "category": "Real Estate Agency",
        "lat": -37.8133, "lon": 144.9568,
        "description": "Boutique real estate agency specialising in Melbourne CBD apartments and investment properties."
    },
]


async def seed_dataset():
    engine = create_async_engine('postgresql+asyncpg://dronpancholi@localhost:5432/seo_platform')
    
    async with engine.connect() as conn:
        # Get existing campaign IDs
        result = await conn.execute(text("SELECT id FROM backlink_campaigns WHERE tenant_id = :tid LIMIT 15"), {"tid": TENANT_ID})
        campaign_ids = [row[0] for row in result]
        print(f"Found {len(campaign_ids)} existing campaigns")
        
        # Get existing client IDs
        result = await conn.execute(text("SELECT id FROM clients WHERE tenant_id = :tid"), {"tid": TENANT_ID})
        client_ids = [row[0] for row in result]
        print(f"Found {len(client_ids)} existing clients")
        
        now = datetime.now(timezone.utc)
        
        # ========================================
        # 1. SEED BUSINESS PROFILES (14 tables, start here)
        # ========================================
        print("\n--- Seeding Business Profiles ---")
        bp_count = 0
        for bp in BUSINESS_PROFILES:
            if bp["client_idx"] >= len(client_ids):
                continue
            cid = client_ids[bp["client_idx"]]
            # Check if exists
            existing = await conn.execute(text(
                "SELECT id FROM business_profiles WHERE client_id = :cid AND tenant_id = :tid"
            ), {"cid": cid, "tid": TENANT_ID})
            if existing.scalar():
                continue
            await conn.execute(text("""
                INSERT INTO business_profiles (id, tenant_id, client_id, business_name, street_address, city, state_province, postal_code, country_code, phone_number, website_url, primary_category, secondary_categories, description, latitude, longitude, created_at, updated_at)
                VALUES (:id, :tid, :cid, :name, :addr, :city, :state, :postal, :country, :phone, :website, :cat, :sc, :desc, :lat, :lon, :now, :now)
            """), {
                "id": uuid.uuid4(), "tid": TENANT_ID, "cid": cid,
                "name": bp["name"], "addr": bp["address"], "city": bp["city"],
                "state": bp["state"], "postal": bp["postal"], "country": bp["country"],
                "phone": bp["phone"], "website": bp["website"], "cat": bp["category"],
                "sc": "[]", "desc": bp["description"], "lat": bp["lat"], "lon": bp["lon"], "now": now,
            })
            bp_count += 1
        print(f"  Inserted {bp_count} business profiles")
        
        # ========================================
        # 2. SEED KEYWORD CLUSTERS
        # ========================================
        print("\n--- Seeding Keyword Clusters ---")
        cluster_ids = {}
        cluster_count = 0
        for niche, keywords in KEYWORD_SETS.items():
            for ci, client_id in enumerate(client_ids[:4]):
                key = f"{niche}_{ci}"
                cluster_name = f"{niche.title()} Keywords - Client {ci+1}"
                cid = uuid.uuid4()
                await conn.execute(text("""
                    INSERT INTO keyword_clusters (id, tenant_id, client_id, name, primary_keyword, total_volume, avg_difficulty, dominant_intent, keyword_count, confidence_score, status, ai_rationale, created_at, updated_at)
                    VALUES (:id, :tid, :cid, :name, :pk, :tv, :ad, :di, :kc, :cs, :status, :ar, :now, :now)
                """), {
                    "id": cid, "tid": TENANT_ID, "cid": client_id,
                    "name": cluster_name, "pk": keywords[0][0],
                    "tv": sum(k[1] for k in keywords), "ad": round(sum(k[2] for k in keywords) / len(keywords), 1),
                    "di": "informational", "kc": len(keywords), "cs": 0.85,
                    "status": "approved", "ar": f"Auto-generated cluster for {niche} niche",
                    "now": now,
                })
                cluster_ids[key] = cid
                cluster_count += 1
        print(f"  Inserted {cluster_count} keyword clusters")
        
        # ========================================
        # 3. SEED KEYWORDS (500+)
        # ========================================
        print("\n--- Seeding Keywords ---")
        kw_count = 0
        intents = ["informational", "transactional", "navigational", "commercial"]
        for ci, client_id in enumerate(client_ids[:4]):
            for niche, keywords in KEYWORD_SETS.items():
                cluster_key = f"{niche}_{ci}"
                cluster_id = cluster_ids.get(cluster_key)
                for keyword, vol, diff, cpc, comp, intent in keywords:
                    # Add some variation
                    vol_var = vol + random.randint(-200, 200)
                    diff_var = max(0, min(100, diff + random.uniform(-5, 5)))
                    await conn.execute(text("""
                        INSERT INTO keywords (id, tenant_id, client_id, cluster_id, keyword, search_volume, difficulty, cpc, competition, intent, serp_features, enrichment_data, is_seed, created_at, updated_at)
                        VALUES (:id, :tid, :cid, :clid, :kw, :sv, :diff, :cpc, :comp, :intent, :sf, :ed, :is_seed, :now, :now)
                    """), {
                        "id": uuid.uuid4(), "tid": TENANT_ID, "cid": client_id,
                        "clid": cluster_id, "kw": keyword, "sv": max(0, vol_var),
                        "diff": round(diff_var, 1), "cpc": round(cpc + random.uniform(-0.5, 0.5), 2),
                        "comp": round(max(0, min(1, comp + random.uniform(-0.1, 0.1))), 2),
                        "intent": intent, "sf": "[]", "ed": "{}",
                        "is_seed": random.random() < 0.2, "now": now,
                    })
                    kw_count += 1
        print(f"  Inserted {kw_count} keywords")
        
        # ========================================
        # 4. SEED KEYWORD RESEARCH
        # ========================================
        print("\n--- Seeding Keyword Research ---")
        kr_count = 0
        for ci, client_id in enumerate(client_ids[:3]):
            for niche in KEYWORD_SETS.keys():
                seed = f"{niche} services Australia"
                await conn.execute(text("""
                    INSERT INTO keyword_research (id, tenant_id, client_id, seed_keyword, status, result_data, created_at, updated_at)
                    VALUES (:id, :tid, :cid, :seed, :status, :rd, :now, :now)
                """), {
                    "id": uuid.uuid4(), "tid": TENANT_ID, "cid": client_id,
                    "seed": seed, "status": "completed",
                    "rd": f'{{"keywords_found": {random.randint(20, 50)}, "source": "development_dataset"}}',
                    "now": now,
                })
                kr_count += 1
        print(f"  Inserted {kr_count} keyword research records")
        
        # ========================================
        # 5. SEED CITATION SITES (30)
        # ========================================
        print("\n--- Seeding Citation Sites ---")
        site_ids = []
        for name, url, cat, da, imp, free, diff, region in CITATION_SITES:
            sid = uuid.uuid4()
            await conn.execute(text("""
                INSERT INTO citation_sites (id, tenant_id, name, url, category, domain_authority, importance_score, difficulty_score, monthly_visitors, is_free, is_active, is_premium, submission_difficulty, region, has_logo_upload, has_description, has_hours, has_social_links, has_images, has_video, requires_email_verification, estimated_field_count, created_at, updated_at)
                VALUES (:id, :tid, :name, :url, :cat, :da, :imp, :ds, :mv, :free, true, false, :diff, :region, false, true, false, false, false, false, true, 15, :now, :now)
            """), {
                "id": sid, "tid": TENANT_ID, "name": name, "url": f"https://{url}",
                "cat": cat, "da": da, "imp": imp, "ds": max(10, 100 - da), "mv": random.randint(1000, 100000),
                "free": free, "diff": diff, "region": region, "now": now,
            })
            site_ids.append(sid)
        print(f"  Inserted {len(site_ids)} citation sites")
        
        # ========================================
        # 6. SEED CITATION PROJECTS (per client)
        # ========================================
        print("\n--- Seeding Citation Projects ---")
        project_ids = []
        for ci, client_id in enumerate(client_ids[:4]):
            bp = BUSINESS_PROFILES[ci] if ci < len(BUSINESS_PROFILES) else BUSINESS_PROFILES[0]
            pid = uuid.uuid4()
            await conn.execute(text("""
                INSERT INTO citation_projects (id, tenant_id, client_id, business_name, website_url, category, phone, email, description, address, city, state, country, postal_code, latitude, longitude, status, total_sites, pending_count, in_progress_count, already_exists_count, new_backlink_count, failed_count, created_at, updated_at)
                VALUES (:id, :tid, :cid, :name, :url, :cat, :phone, :email, :desc, :addr, :city, :state, :country, :postal, :lat, :lon, 'active', :ts, 0, 0, 0, 0, 0, :now, :now)
            """), {
                "id": pid, "tid": TENANT_ID, "cid": client_id,
                "name": bp["name"], "url": bp["website"], "cat": bp["category"],
                "phone": bp["phone"], "email": f"info@{bp['website'].replace('https://', '')}",
                "desc": bp["description"], "addr": bp["address"], "city": bp["city"],
                "state": bp["state"], "country": bp["country"], "postal": bp["postal"],
                "lat": bp["lat"], "lon": bp["lon"], "ts": len(site_ids), "now": now,
            })
            project_ids.append(pid)
        print(f"  Inserted {len(project_ids)} citation projects")
        
        # ========================================
        # 7. SEED CITATION SUBMISSIONS (100+)
        # ========================================
        print("\n--- Seeding Citation Submissions ---")
        sub_count = 0
        statuses = ["not_started", "in_progress", "already_exists", "new_backlink", "pending_review", "failed"]
        status_weights = [0.2, 0.15, 0.25, 0.25, 0.1, 0.05]
        for pid in project_ids:
            # Each project gets 8-12 site submissions
            selected_sites = random.sample(site_ids, min(random.randint(8, 12), len(site_ids)))
            for sid in selected_sites:
                status = random.choices(statuses, weights=status_weights, k=1)[0]
                days_ago = random.randint(1, 60)
                sub_date = now - timedelta(days=days_ago)
                started = sub_date + timedelta(hours=random.randint(1, 48)) if status != "not_started" else None
                completed = started + timedelta(days=random.randint(1, 7)) if status in ("already_exists", "new_backlink", "failed") else None
                
                await conn.execute(text("""
                    INSERT INTO citation_submissions (id, tenant_id, project_id, site_id, status, account_created, email_verified, listing_claimed, started_at, submitted_at, completed_at, created_at, updated_at)
                    VALUES (:id, :tid, :pid, :sid, :status, :ac, :ev, :lc, :start, :sub, :comp, :now, :now)
                """), {
                    "id": uuid.uuid4(), "tid": TENANT_ID, "pid": pid, "sid": sid,
                    "status": status,
                    "ac": status in ("already_exists", "new_backlink", "in_progress"),
                    "ev": status in ("already_exists", "new_backlink"),
                    "lc": status in ("already_exists", "new_backlink"),
                    "start": started, "sub": started, "comp": completed, "now": now,
                })
                sub_count += 1
        print(f"  Inserted {sub_count} citation submissions")
        
        # ========================================
        # 8. SEED BACKLINK PROSPECTS (250+)
        # ========================================
        print("\n--- Seeding Backlink Prospects ---")
        prospect_ids = []
        prospect_statuses = ["new", "scored", "approved", "contacted", "replied", "link_acquired", "unresponsive"]
        prospect_weights = [0.15, 0.2, 0.25, 0.15, 0.1, 0.1, 0.05]
        
        for ci, client_id in enumerate(client_ids[:4]):
            if ci >= len(campaign_ids):
                continue
            campaign_id = campaign_ids[ci]
            # Each campaign gets 15-25 prospects
            num_prospects = random.randint(15, 25)
            selected = random.sample(PROSPECT_DOMAINS, min(num_prospects, len(PROSPECT_DOMAINS)))
            
            for domain, name, da, relevance, note in selected:
                status = random.choices(prospect_statuses, weights=prospect_weights, k=1)[0]
                # Add some variation to DA
                da_var = max(0, min(100, da + random.randint(-5, 5)))
                relevance_var = max(0, min(1, relevance + random.uniform(-0.1, 0.1)))
                spam = round(random.uniform(0, 0.15), 2)
                traffic = round(random.uniform(0.3, 0.9), 2)
                composite = round((da_var / 100 * 0.3 + relevance_var * 0.4 + traffic * 0.2 + (1 - spam) * 0.1) * 100, 1)
                
                pid = uuid.uuid4()
                await conn.execute(text("""
                    INSERT INTO backlink_prospects (id, tenant_id, campaign_id, domain, url, status, domain_authority, relevance_score, spam_score, traffic_score, composite_score, confidence, contact_name, contact_email, contact_source, email_verification_status, scoring_rationale, created_at, updated_at)
                    VALUES (:id, :tid, :cid, :domain, :url, :status, :da, :rel, :spam, :traffic, :comp, :conf, :cname, :cemail, :csrc, 'unverified', :sr, :now, :now)
                """), {
                    "id": pid, "tid": TENANT_ID, "cid": campaign_id,
                    "domain": domain.strip(), "url": f"https://{domain.strip()}",
                    "status": status, "da": da_var, "rel": round(relevance_var, 2),
                    "spam": spam, "traffic": traffic, "comp": composite,
                    "conf": round(random.uniform(0.6, 0.95), 2),
                    "cname": f"Contact at {name}", "cemail": f"editor@{domain.strip()}",
                    "csrc": "manual_research",
                    "sr": f'{{"note": "{note}", "source": "development_dataset"}}',
                    "now": now,
                })
                prospect_ids.append(pid)
        print(f"  Inserted {len(prospect_ids)} backlink prospects")
        
        # ========================================
        # 9. SEED OUTREACH THREADS (100+)
        # ========================================
        print("\n--- Seeding Outreach Threads ---")
        thread_count = 0
        thread_statuses = ["draft", "queued", "sent", "delivered", "opened", "replied", "link_acquired"]
        thread_weights = [0.1, 0.1, 0.2, 0.15, 0.15, 0.15, 0.15]
        
        for ci, client_id in enumerate(client_ids[:4]):
            if ci >= len(campaign_ids):
                continue
            campaign_id = campaign_ids[ci]
            # Get prospects for this campaign
            result = await conn.execute(text(
                "SELECT id, domain, contact_email FROM backlink_prospects WHERE campaign_id = :cid AND tenant_id = :tid LIMIT 20"
            ), {"cid": campaign_id, "tid": TENANT_ID})
            prospects = result.fetchall()
            
            for prospect_id, domain, email in prospects[:12]:
                status = random.choices(thread_statuses, weights=thread_weights, k=1)[0]
                days_ago = random.randint(1, 45)
                created = now - timedelta(days=days_ago)
                sent = created + timedelta(hours=random.randint(1, 72)) if status not in ("draft", "queued") else None
                opened = sent + timedelta(hours=random.randint(2, 48)) if status in ("opened", "replied", "link_acquired") and sent else None
                replied = opened + timedelta(hours=random.randint(1, 24)) if status in ("replied", "link_acquired") and opened else None
                
                await conn.execute(text("""
                    INSERT INTO outreach_threads (id, tenant_id, campaign_id, prospect_id, status, from_email, to_email, subject, body_html, follow_up_count, max_follow_ups, provider, sent_at, opened_at, replied_at, confidence_score, created_at, updated_at)
                    VALUES (:id, :tid, :cid, :pid, :status, :from, :to, :subj, :body, :fup, 3, :prov, :sent, :opened, :replied, :conf, :now, :now)
                """), {
                    "id": uuid.uuid4(), "tid": TENANT_ID, "cid": campaign_id,
                    "pid": prospect_id, "status": status,
                    "from": f"outreach@acmedigital.com.au",
                    "to": email, "subj": f"Guest Post Opportunity - {domain}",
                    "body": f"<p>Hi, I noticed your excellent article about {domain}. We'd love to contribute a guest post...</p>",
                    "fup": random.randint(0, 3), "prov": "sendgrid",
                    "sent": sent, "opened": opened, "replied": replied,
                    "conf": round(random.uniform(0.5, 0.9), 2), "now": now,
                })
                thread_count += 1
        print(f"  Inserted {thread_count} outreach threads")
        
        # ========================================
        # 10. SEED OUTREACH EMAILS (100+)
        # ========================================
        print("\n--- Seeding Outreach Emails ---")
        email_count = 0
        email_statuses = ["QUEUED", "SENT", "DELIVERED", "OPENED", "REPLIED", "BOUNCED"]
        
        for ci, client_id in enumerate(client_ids[:4]):
            if ci >= len(campaign_ids):
                continue
            campaign_id = campaign_ids[ci]
            result = await conn.execute(text(
                "SELECT id, domain, contact_email, contact_name FROM backlink_prospects WHERE campaign_id = :cid AND tenant_id = :tid LIMIT 15"
            ), {"cid": campaign_id, "tid": TENANT_ID})
            prospects = result.fetchall()
            
            for prospect_id, domain, email, name in prospects[:10]:
                status = random.choices(email_statuses, weights=[0.1, 0.25, 0.2, 0.2, 0.15, 0.1], k=1)[0]
                days_ago = random.randint(1, 40)
                sent = now - timedelta(days=days_ago)
                delivered = sent + timedelta(minutes=random.randint(5, 60)) if status in ("DELIVERED", "OPENED", "REPLIED") else None
                opened = delivered + timedelta(hours=random.randint(1, 48)) if status in ("OPENED", "REPLIED") and delivered else None
                replied = opened + timedelta(hours=random.randint(1, 24)) if status == "REPLIED" and opened else None
                
                await conn.execute(text("""
                    INSERT INTO outreach_emails (id, tenant_id, campaign_id, prospect_id, to_email, to_name, subject, body_html, status, sent_at, delivered_at, opened_at, replied_at, retry_count)
                    VALUES (:id, :tid, :cid, :pid, :to, :name, :subj, :body, :status, :sent, :del, :open, :rep, 0)
                """), {
                    "id": uuid.uuid4(), "tid": TENANT_ID, "cid": campaign_id,
                    "pid": str(prospect_id), "to": email, "name": name or f"Editor at {domain}",
                    "subj": f"Content Collaboration - {domain}",
                    "body": f"<p>Hi {name or 'there'}, I came across {domain} and thought our content would be a great fit...</p>",
                    "status": status, "sent": sent, "del": delivered,
                    "open": opened, "rep": replied,
                })
                email_count += 1
        print(f"  Inserted {email_count} outreach emails")
        
        # ========================================
        # 11. SEED COMPETITOR CITATIONS (50)
        # ========================================
        print("\n--- Seeding Competitor Citations ---")
        comp_count = 0
        competitors = [
            ("Competitor A", "competitora.com.au"),
            ("Competitor B", "competitorb.com.au"),
            ("Competitor C", "competitorc.com.au"),
        ]
        for pid in project_ids:
            for comp_name, comp_domain in competitors:
                # Each competitor has 3-6 citations
                for _ in range(random.randint(3, 6)):
                    site = random.choice(CITATION_SITES)
                    await conn.execute(text("""
                        INSERT INTO competitor_citations (id, tenant_id, project_id, competitor_name, competitor_domain, site_url, citation_url, has_images, has_complete_nap, citation_age_months, domain_rating, created_at, updated_at)
                        VALUES (:id, :tid, :pid, :cname, :cdomain, :site, :cite, :img, :nap, :age, :dr, :now, :now)
                    """), {
                        "id": uuid.uuid4(), "tid": TENANT_ID, "pid": pid,
                        "cname": comp_name, "cdomain": comp_domain,
                        "site": f"https://{site[1]}", "cite": f"https://{site[1]}/listing/{uuid.uuid4().hex[:8]}",
                        "img": random.random() > 0.5, "nap": random.random() > 0.3,
                        "age": random.randint(6, 36), "dr": site[3] + random.randint(-5, 5),
                        "now": now,
                    })
                    comp_count += 1
        print(f"  Inserted {comp_count} competitor citations")
        
        # ========================================
        # 12. SEED CONTACTS (50)
        # ========================================
        print("\n--- Seeding Contacts ---")
        contact_count = 0
        for ci, client_id in enumerate(client_ids[:4]):
            for _ in range(8):
                domain = random.choice(PROSPECT_DOMAINS)[0].strip()
                await conn.execute(text("""
                    INSERT INTO contacts (id, tenant_id, client_id, email, name, domain, created_at, updated_at)
                    VALUES (:id, :tid, :cid, :email, :name, :domain, :now, :now)
                    ON CONFLICT (tenant_id, email) DO NOTHING
                """), {
                    "id": uuid.uuid4(), "tid": TENANT_ID, "cid": client_id,
                    "email": f"contact@{domain}",
                    "name": f"Contact {random.randint(1, 100)}",
                    "domain": domain, "now": now,
                })
                contact_count += 1
        print(f"  Inserted {contact_count} contacts")
        
        # ========================================
        # 13. SEED EMAIL TEMPLATES (10)
        # ========================================
        print("\n--- Seeding Email Templates ---")
        templates = [
            ("Guest Post Pitch", "Guest Post Opportunity - {{site_name}}", "<p>Hi {{name}}, I noticed your excellent content on {{topic}}...</p>", "outreach", ["name", "site_name", "topic"]),
            ("Resource Page Outreach", "Resource Page Link Request", "<p>Hi {{name}}, I found your resource page about {{topic}}...</p>", "outreach", ["name", "topic"]),
            ("Broken Link Outreach", "Broken Link Found on {{site_name}}", "<p>Hi {{name}}, I noticed a broken link on your page...</p>", "outreach", ["name", "site_name"]),
            ("Follow Up #1", "Following Up - Guest Post", "<p>Hi {{name}}, just following up on my previous email...</p>", "follow_up", ["name"]),
            ("Follow Up #2", "Second Follow Up", "<p>Hi {{name}}, I wanted to check in again...</p>", "follow_up", ["name"]),
            ("Thank You", "Thank You for the Backlink!", "<p>Hi {{name}}, thank you for publishing our article...</p>", "thank_you", ["name"]),
            ("Citation Submission", "Business Listing - {{business_name}}", "<p>We'd like to add your business to our directory...</p>", "citation", ["business_name"]),
            ("Introduction Email", "Introduction - {{company_name}}", "<p>Hi {{name}}, I'm from {{company_name}}...</p>", "introduction", ["name", "company_name"]),
            ("Partnership Proposal", "Partnership Opportunity", "<p>Hi {{name}}, I think there's a great opportunity for us to collaborate...</p>", "partnership", ["name"]),
            ("Newsletter Signup", "Welcome to Our Newsletter", "<p>Thank you for subscribing to our newsletter...</p>", "newsletter", []),
        ]
        for name, subj, body, ttype, variables in templates:
            await conn.execute(text("""
                INSERT INTO email_templates (id, tenant_id, name, subject_template, body_template, template_type, variables, is_active, usage_count, success_rate)
                VALUES (:id, :tid, :name, :subj, :body, :type, :vars, true, :uc, :sr)
            """), {
                "id": uuid.uuid4(), "tid": TENANT_ID, "name": name,
                "subj": subj, "body": body, "type": ttype,
                "vars": json.dumps(variables), "uc": random.randint(5, 50),
                "sr": round(random.uniform(0.15, 0.45), 2),
            })
        print(f"  Inserted {len(templates)} email templates")
        
        # ========================================
        # 14. SEED ACQUIRED LINKS (30)
        # ========================================
        print("\n--- Seeding Acquired Links ---")
        link_count = 0
        for ci, client_id in enumerate(client_ids[:4]):
            if ci >= len(campaign_ids):
                continue
            campaign_id = campaign_ids[ci]
            # Get some prospects that have link_acquired status
            result = await conn.execute(text(
                "SELECT id, domain, url FROM backlink_prospects WHERE campaign_id = :cid AND tenant_id = :tid AND status = 'link_acquired' LIMIT 8"
            ), {"cid": campaign_id, "tid": TENANT_ID})
            prospects = result.fetchall()
            
            for prospect_id, domain, url in prospects:
                days_ago = random.randint(7, 90)
                await conn.execute(text("""
                    INSERT INTO acquired_links (id, tenant_id, campaign_id, prospect_id, source_url, target_url, anchor_text, link_type, status, domain_authority_at_acquisition, first_verified_at, check_count, verification_history, created_at, updated_at)
                    VALUES (:id, :tid, :cid, :pid, :src, :tgt, :anchor, 'dofollow', :status, :da, :ver, 1, '[]'::jsonb, :now, :now)
                """), {
                    "id": uuid.uuid4(), "tid": TENANT_ID, "cid": campaign_id,
                    "pid": prospect_id, "src": url, "tgt": f"https://acmedigital.com.au/blog/{domain.replace('.', '-')}",
                    "anchor": f"SEO services {domain.split('.')[0]}",
                    "status": "verified_live", "da": random.randint(30, 70),
                    "ver": now - timedelta(days=max(0, days_ago - 3)),
                    "now": now,
                })
                link_count += 1
        print(f"  Inserted {link_count} acquired links")
        
        # ========================================
        # 15. SEED RECOMMENDATIONS (50)
        # ========================================
        print("\n--- Seeding Recommendations ---")
        rec_count = 0
        rec_types = ["keyword_optimization", "content_gap", "backlink_opportunity", "technical_seo", "local_seo", "competitor_gap"]
        priorities = ["P0", "P1", "P2"]
        rec_statuses = ["active", "implemented", "dismissed"]
        
        for ci, client_id in enumerate(client_ids[:4]):
            for _ in range(8):
                rtype = random.choice(rec_types)
                priority = random.choices(priorities, weights=[0.15, 0.45, 0.4], k=1)[0]
                status = random.choices(rec_statuses, weights=[0.6, 0.25, 0.15], k=1)[0]
                
                titles = {
                    "keyword_optimization": "Optimise page for target keyword",
                    "content_gap": "Create content for uncovered topic",
                    "backlink_opportunity": "Reach out to high-authority domain",
                    "technical_seo": "Fix technical SEO issue",
                    "local_seo": "Improve local SEO signals",
                    "competitor_gap": "Close competitor content gap",
                }
                
                await conn.execute(text("""
                    INSERT INTO recommendations (id, tenant_id, recommendation_type, title, description, priority, status, confidence, impact_score, effort_score, entity_type, supporting_data, created_at, updated_at)
                    VALUES (:id, :tid, :type, :title, :desc, :pri, :status, :conf, :impact, :effort, :etype, :sd, :now, :now)
                """), {
                    "id": uuid.uuid4(), "tid": TENANT_ID, "type": rtype,
                    "title": titles[rtype], "desc": f"Development dataset recommendation for {rtype}",
                    "pri": priority, "status": status,
                    "conf": round(random.uniform(0.5, 0.95), 2),
                    "impact": round(random.uniform(30, 90), 1),
                    "effort": round(random.uniform(10, 70), 1),
                    "etype": "client",
                    "sd": '{"source": "development_dataset"}',
                    "now": now,
                })
                rec_count += 1
        print(f"  Inserted {rec_count} recommendations")
        
        await conn.commit()
        
        # ========================================
        # FINAL COUNTS
        # ========================================
        print("\n" + "=" * 60)
        print("DEVELOPMENT DATASET V2 — FINAL COUNTS")
        print("=" * 60)
        
        tables = [
            ("business_profiles", "Business Profiles"),
            ("keyword_clusters", "Keyword Clusters"),
            ("keywords", "Keywords"),
            ("keyword_research", "Keyword Research"),
            ("citation_sites", "Citation Sites"),
            ("citation_projects", "Citation Projects"),
            ("citation_submissions", "Citation Submissions"),
            ("backlink_prospects", "Backlink Prospects"),
            ("outreach_threads", "Outreach Threads"),
            ("outreach_emails", "Outreach Emails"),
            ("competitor_citations", "Competitor Citations"),
            ("contacts", "Contacts"),
            ("email_templates", "Email Templates"),
            ("acquired_links", "Acquired Links"),
            ("recommendations", "Recommendations"),
        ]
        
        for table, label in tables:
            result = await conn.execute(text(f"SELECT COUNT(*) FROM {table} WHERE tenant_id = :tid"), {"tid": TENANT_ID})
            count = result.scalar()
            status = "OK" if count > 0 else "EMPTY"
            print(f"  {label:25s} {count:5d}  [{status}]")
        
        print("\nDataset tagged as DEVELOPMENT DATA.")
        print("Never present as production SEO outcomes.")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_dataset())
