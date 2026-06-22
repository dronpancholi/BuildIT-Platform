#!/usr/bin/env python3
"""
Phase 6 Master Deduplication + Validation Script
Runs after all region seed scripts to deduplicate and validate the citation_sites table.
"""

import psycopg2
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

def get_connection():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="seo_platform",
        user="seo_platform",
        password="seo_platform_dev"
    )

def deduplicate_sites(conn):
    """Remove duplicate sites by URL (keep highest importance_score)."""
    cursor = conn.cursor()
    cursor.execute("""
        WITH duplicates AS (
            SELECT id, url,
                   ROW_NUMBER() OVER (PARTITION BY url ORDER BY importance_score DESC) as rn
            FROM citation_sites
        )
        DELETE FROM citation_sites
        WHERE id IN (SELECT id FROM duplicates WHERE rn > 1)
        RETURNING id
    """)
    deleted = cursor.rowcount
    conn.commit()
    return deleted

def fix_empty_slugs(conn):
    """Set slug = NULL for sites with empty string slugs (will be regenerated)."""
    cursor = conn.cursor()
    cursor.execute("UPDATE citation_sites SET slug = NULL WHERE slug = ''")
    conn.commit()

def validate_data(conn):
    """Validate and report data quality issues."""
    cursor = conn.cursor()
    issues = []

    # Check for NULL URLs
    cursor.execute("SELECT COUNT(*) FROM citation_sites WHERE url IS NULL")
    count = cursor.fetchone()[0]
    if count > 0:
        issues.append(f"  - {count} sites with NULL url")

    # Check for NULL names
    cursor.execute("SELECT COUNT(*) FROM citation_sites WHERE name IS NULL")
    count = cursor.fetchone()[0]
    if count > 0:
        issues.append(f"  - {count} sites with NULL name")

    # Check for NULL regions
    cursor.execute("SELECT COUNT(*) FROM citation_sites WHERE region IS NULL")
    count = cursor.fetchone()[0]
    if count > 0:
        issues.append(f"  - {count} sites with NULL region")

    # Check importance_score range
    cursor.execute("SELECT COUNT(*) FROM citation_sites WHERE importance_score < 1 OR importance_score > 100")
    count = cursor.fetchone()[0]
    if count > 0:
        issues.append(f"  - {count} sites with importance_score outside 1-100 range")

    # Check for empty categories
    cursor.execute("SELECT COUNT(*) FROM citation_sites WHERE category IS NULL")
    count = cursor.fetchone()[0]
    if count > 0:
        issues.append(f"  - {count} sites with NULL/empty category")

    return issues

def generate_final_report(conn):
    """Generate the final site count report."""
    cursor = conn.cursor()

    # Total count
    cursor.execute("SELECT COUNT(*) FROM citation_sites")
    total = cursor.fetchone()[0]

    # By region
    cursor.execute("""
        SELECT region, COUNT(*) as cnt
        FROM citation_sites
        GROUP BY region
        ORDER BY cnt DESC
    """)
    regions = cursor.fetchall()

    # By importance tier
    cursor.execute("""
        SELECT
            CASE
                WHEN importance_score >= 80 THEN 'Tier 1 (80-100)'
                WHEN importance_score >= 60 THEN 'Tier 2 (60-79)'
                WHEN importance_score >= 40 THEN 'Tier 3 (40-59)'
                ELSE 'Tier 4 (1-39)'
            END as tier,
            COUNT(*) as cnt
        FROM citation_sites
        GROUP BY tier
        ORDER BY tier DESC
    """)
    tiers = cursor.fetchall()

    # By category
    cursor.execute("""
        SELECT category, COUNT(*) as cnt
        FROM citation_sites
        GROUP BY category
        ORDER BY cnt DESC
    """)
    categories = cursor.fetchall()

    # Premium vs free
    cursor.execute("SELECT is_premium, COUNT(*) FROM citation_sites GROUP BY is_premium")
    premium = cursor.fetchall()

    # Average importance score
    cursor.execute("SELECT ROUND(AVG(importance_score), 1) FROM citation_sites")
    avg_score = cursor.fetchone()[0]

    # Average estimated field count
    cursor.execute("SELECT ROUND(AVG(estimated_field_count), 1) FROM citation_sites")
    avg_fields = cursor.fetchone()[0]

    # Sites with form mappings (from JSON file)
    try:
        cursor.execute("SELECT COUNT(DISTINCT site_slug) FROM site_form_mappings")
        mappings_count = cursor.fetchone()[0]
    except Exception:
        mappings_count = 0

    # Email patterns (from JSON file)
    try:
        cursor.execute("SELECT COUNT(*) FROM email_verification_patterns")
        patterns_count = cursor.fetchone()[0]
    except Exception:
        patterns_count = 0

    report = f"""
{'='*70}
  CITATION SITES DATABASE - FINAL REPORT
{'='*70}

  Total Sites: {total}

  BY REGION:
"""
    for region, count in regions:
        pct = (count / total * 100) if total > 0 else 0
        report += f"    {region or 'NULL':12s} {count:5d} ({pct:.1f}%)\n"

    report += f"""
  BY IMPORTANCE TIER:
"""
    for tier, count in tiers:
        report += f"    {tier:20s} {count:5d}\n"

    report += f"""
  BY CATEGORY:
"""
    for cat, count in categories:
        report += f"    {cat or 'NULL':20s} {count:5d}\n"

    report += f"""
  PREMIUM SITES:
"""
    for is_premium, count in premium:
        label = "Premium" if is_premium else "Free"
        report += f"    {label:10s} {count:5d}\n"

    report += f"""
  STATS:
    Average Importance Score: {avg_score}
    Average Field Count:      {avg_fields}
    Form Mappings:            {mappings_count}
    Email Patterns:           {patterns_count}
{'='*70}
"""
    return report

def main():
    print("="*60)
    print("  PHASE 6: MASTER DEDUPLICATION + VALIDATION")
    print("="*60)

    conn = get_connection()

    # Step 1: Deduplicate
    print("\n[1/3] Deduplicating by URL...")
    deleted = deduplicate_sites(conn)
    print(f"  Removed {deleted} duplicate rows")

    # Step 2: Fix empty slugs
    print("\n[2/3] Fixing empty slugs...")
    fix_empty_slugs(conn)
    print("  Done")

    # Step 3: Validate
    print("\n[3/3] Validating data quality...")
    issues = validate_data(conn)
    if issues:
        print("  ISSUES FOUND:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("  All checks passed")

    # Generate report
    print("\nGenerating final report...")
    report = generate_final_report(conn)
    print(report)

    conn.close()
    print("Phase 6 seed complete!")

if __name__ == "__main__":
    main()
