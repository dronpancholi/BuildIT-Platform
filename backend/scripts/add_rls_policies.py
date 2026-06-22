"""Add RLS policies to all 47 unprotected tenant tables."""

import psycopg2

TABLES = [
    "action_definitions", "action_executions", "agent_conflicts",
    "agent_definitions", "agent_instances", "agent_tasks",
    "approval_policies", "approval_requests", "approval_requests_v2",
    "audit_ledger", "audit_trail_logs", "automation_actions",
    "automation_failures", "automation_rules", "automation_runs",
    "business_intelligence_events", "business_profiles",
    "campaign_health_snapshots", "campaign_saved_views",
    "campaign_timeline_events", "citation_submissions",
    "compliance_results", "contacts", "customer_health_scores",
    "email_templates", "execution_plans", "executive_alerts",
    "executive_metrics_snapshots", "executive_reports",
    "goal_definitions", "goal_executions", "keyword_metric_snapshots",
    "keyword_research", "node_dependencies", "operational_memory",
    "outreach_emails", "plan_forecasts", "plan_nodes",
    "prospect_score_history", "provider_health_metrics",
    "recommendations", "reports", "revenue_metrics", "risk_records",
    "serp_volatility_snapshots", "sla_tracking", "users",
]

DDL = {
    "enable_rls": 'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY',
    "force_rls": 'ALTER TABLE {table} FORCE ROW LEVEL SECURITY',
    "policy": """CREATE POLICY {table}_tenant_isolation ON {table}
  USING (tenant_id = current_setting('app.current_tenant')::uuid)
  WITH CHECK (tenant_id = current_setting('app.current_tenant')::uuid)""",
}


def main():
    conn = psycopg2.connect(
        host="localhost", port=5432,
        dbname="seo_platform", user="seo_platform",
        password="seo_platform_dev",
    )
    conn.autocommit = False
    cur = conn.cursor()

    succeeded, failed = [], []

    for table in TABLES:
        try:
            for key in ("enable_rls", "force_rls", "policy"):
                sql = DDL[key].format(table=table)
                cur.execute(sql)
            conn.commit()
            succeeded.append(table)
            print(f"  ✓ {table}")
        except Exception as e:
            conn.rollback()
            failed.append((table, str(e)))
            print(f"  ✗ {table}: {e}")

    print(f"\n{'='*60}")
    print(f"SUCCESS: {len(succeeded)}/{len(TABLES)} tables protected")
    if failed:
        print(f"FAILED:  {len(failed)}")
        for t, e in failed:
            print(f"  - {t}: {e}")

    # Verification
    print(f"\n{'='*60}")
    print("VERIFICATION")
    print(f"{'='*60}")

    cur.execute("""
        SELECT c.relname
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind = 'r' AND n.nspname = 'public'
        AND EXISTS (
            SELECT 1 FROM pg_attribute a
            WHERE a.attrelid = c.oid AND a.attname = 'tenant_id'
        )
        AND c.relname NOT IN (
            SELECT DISTINCT tablename FROM pg_policies WHERE schemaname = 'public'
        )
        AND c.relname NOT IN ('alembic_version')
        ORDER BY c.relname
    """)
    unprotected = [r[0] for r in cur.fetchall()]
    if unprotected:
        print(f"\n⚠  STILL UNPROTECTED ({len(unprotected)}):")
        for t in unprotected:
            print(f"   - {t}")
    else:
        print("\n✓ ALL tenant_id tables now have RLS policies")

    cur.execute("SELECT COUNT(*) FROM pg_policies WHERE schemaname = 'public'")
    print(f"\nTotal RLS policies in public schema: {cur.fetchone()[0]}")

    cur.execute("""
        SELECT tablename, rowsecurity
        FROM pg_tables
        WHERE schemaname = 'public'
        AND tablename IN %s
        ORDER BY tablename
    """, (tuple(TABLES),))
    print(f"\nRLS status per protected table:")
    for row in cur.fetchall():
        status = "ENABLED" if row[1] else "DISABLED"
        print(f"  {row[0]}: {status}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
