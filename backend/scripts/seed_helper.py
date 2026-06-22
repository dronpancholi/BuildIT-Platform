#!/usr/bin/env python3
"""
Shared seed helper — Database operations for all regional seed scripts.
"""

from __future__ import annotations

import uuid
import psycopg2
from psycopg2.extras import execute_values

TENANT_ID = "00000000-0000-0000-0000-000000000001"


def get_connection():
    """Get database connection."""
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="seo_platform",
        user="seo_platform",
        password="seo_platform_dev",
    )


def slugify(name: str) -> str:
    """Convert name to slug format."""
    return (
        name.lower()
        .replace(" ", "-")
        .replace("&", "and")
        .replace("'", "")
        .replace(".", "")
        .replace(",", "")
        .replace("(", "")
        .replace(")", "")
        .replace("/", "-")
        .replace("---", "-")
        .replace("--", "-")
        .strip("-")
    )


def seed_sites(sites: list[dict], region: str) -> int:
    """Insert sites into database. Returns count of inserted sites."""
    conn = get_connection()
    cur = conn.cursor()

    # Get existing URLs to avoid duplicates
    cur.execute("SELECT url FROM citation_sites")
    existing_urls = {row[0] for row in cur.fetchall()}

    rows = []
    skipped = 0
    for site in sites:
        url = site.get("url", "")
        if url in existing_urls:
            skipped += 1
            continue

        # Auto-generate slug if not provided
        slug = site.get("slug") or slugify(site.get("name", ""))

        rows.append((
            str(uuid.uuid4()),
            TENANT_ID,
            site.get("name", ""),
            url,
            site.get("submission_url"),
            site.get("registration_url"),
            site.get("category", "general"),
            site.get("niche"),
            site.get("geo_target"),
            site.get("has_logo_upload", False),
            site.get("has_description", True),
            site.get("has_hours", False),
            site.get("has_social_links", False),
            site.get("has_images", False),
            site.get("has_video", False),
            site.get("requires_email_verification", True),
            site.get("difficulty_score", 50),
            site.get("monthly_visitors", 0),
            site.get("domain_authority", 30),
            site.get("is_free", True),
            True,  # is_active
            region,
            site.get("importance_score", 50),
            site.get("is_premium", False),
            min(site.get("monthly_audience") or 0, 2147483647),
            site.get("language", "en"),
            site.get("submission_difficulty", "medium"),
            site.get("estimated_field_count", 15),
            slug,
        ))

    if rows:
        execute_values(
            cur,
            """INSERT INTO citation_sites (
                id, tenant_id, name, url, submission_url, registration_url,
                category, niche, geo_target,
                has_logo_upload, has_description, has_hours, has_social_links,
                has_images, has_video, requires_email_verification,
                difficulty_score, monthly_visitors, domain_authority,
                is_free, is_active,
                region, importance_score, is_premium, monthly_audience,
                language, submission_difficulty, estimated_field_count, slug
            ) VALUES %s""",
            rows,
            page_size=500,
        )

    conn.commit()
    cur.close()
    conn.close()

    inserted = len(rows)
    print(f"[{region}] Inserted: {inserted}, Skipped (duplicates): {skipped}")
    return inserted
