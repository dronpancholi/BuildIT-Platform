#!/usr/bin/env python3
"""Stage and commit files by phase for BuildIT Platform."""
import subprocess
import sys

def run(cmd):
    """Run a shell command."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd="/Users/dronpancholi/Developer/01_Strategic/Project 31A")
    if result.returncode != 0 and 'did not match' not in result.stderr:
        print(f"  WARN: {result.stderr.strip()}")
    return result

def reset():
    run("git reset HEAD")

def add_files(files):
    """Add specific files."""
    if not files:
        return
    for f in files:
        run(f'git add -- "{f}"')

def add_pattern(pattern):
    """Add files matching a pattern."""
    run(f'git add -- {pattern}')

def commit(msg):
    """Create a commit."""
    result = run(f'git commit -m "{msg}"')
    if result.returncode == 0:
        print(f"  COMMITTED: {msg}")
    else:
        print(f"  SKIP (nothing to commit): {msg}")
    return result

def staged_count():
    result = run("git diff --cached --name-only")
    return len([l for l in result.stdout.strip().split('\n') if l])

# Phase definitions - files to stage for each phase
PHASES = [
    {
        "name": "Phase 12C — Database Hardening, Data Integrity & Infrastructure Foundation",
        "files": [
            # Alembic migrations - database hardening
            "backend/alembic/versions/c4d5e6f7a8b9_add_critical_foreign_keys.py",
            "backend/alembic/versions/a1b2c3d4e5f7_enable_row_level_security.py",
            "backend/alembic/versions/d4e5f6a7b8c9_add_email_verification_columns.py",
            "backend/alembic/versions/e5f6a7b8c9d0_add_link_verification.py",
            "backend/alembic/versions/h8i9j0k1l2m3_add_processed_webhook_events.py",
            "backend/alembic/versions/k1_credential_vault.py",
            "backend/alembic/versions/i16_add_updated_at_columns.py",
            "backend/alembic/versions/i17_create_provider_keys_table.py",
            "backend/alembic/versions/z1_add_seo_tasks_table.py",
            "backend/alembic/versions/83096a7c3e45_add_archived_to_campaign_status.py",
            "backend/alembic/versions/s5bfix0001_extend_campaignstatus.py",
            "backend/alembic/versions/i13_recover_missing_tables.py",
            "backend/alembic/versions/i14_align_action_definitions.py",
            "backend/alembic/versions/i15_add_action_def_max_retries.py",
            "backend/alembic/versions/b3c4d5e6f7a8_merge_dual_heads.py",
            "backend/alembic/versions/f6a7b8c9d0e1_merge_phase_1_2_heads.py",
            "backend/alembic/versions/8efe6a0f6459_merge_seo_tasks.py",
            # Credential & provider management
            "backend/src/seo_platform/api/endpoints/credentials.py",
            "backend/src/seo_platform/api/endpoints/provider_management.py",
            "backend/src/seo_platform/api/endpoints/link_verification.py",
            "backend/src/seo_platform/api/endpoints/proxies.py",
            "backend/src/seo_platform/api/endpoints/identity.py",
            "backend/src/seo_platform/api/endpoints/inbound_webhooks.py",
            "backend/src/seo_platform/api/endpoints/email_attachments.py",
            "backend/src/seo_platform/api/endpoints/email_drafts.py",
        ],
        "patterns": [
            "backend/src/seo_platform/governance/",
            "backend/src/seo_platform/rules_engine/",
            "backend/tests/security/",
            "backend/tests/integration/test_tenant_isolation.py",
            "backend/tests/validation/test_inbound_webhooks.py",
        ],
        "deleted": True,  # Include all deleted top-level .md reports (cleanup)
    },
    {
        "name": "Phase 12D-E — Executive Intelligence, Planning & Automation Engine",
        "files": [
            # Phase 12D - Executive tables
            "backend/alembic/versions/1a2b3c4d5e6f_add_phase12d_executive_tables.py",
            "backend/alembic/versions/f2c3d4e5f6g7_add_planning_engine_tables.py",
            # Executive & planning endpoints
            "backend/src/seo_platform/api/endpoints/executive.py",
            "backend/src/seo_platform/api/endpoints/forecasting.py",
            "backend/src/seo_platform/api/endpoints/goals.py",
            "backend/src/seo_platform/api/endpoints/plans.py",
            "backend/src/seo_platform/api/endpoints/business_intelligence.py",
            "backend/src/seo_platform/api/endpoints/ai_recommendations.py",
            # Phase 12E - Automation tables
            "backend/alembic/versions/2a3b4c5d6e7f_add_phase12e_automation_tables.py",
            # Automation endpoints
            "backend/src/seo_platform/api/endpoints/automation.py",
            "backend/src/seo_platform/api/endpoints/action_center.py",
            "backend/src/seo_platform/api/endpoints/action_registry.py",
        ],
        "patterns": [
            "frontend/src/app/dashboard/automation/",
            "frontend/src/app/dashboard/action-center/",
            "frontend/src/app/dashboard/executive/",
            "frontend/src/app/dashboard/plans/",
            "frontend/src/app/dashboard/tasks/",
            "docs/certification/AUTOMATION_ENGINE_REPORT.md",
            "docs/certification/AUTOMATION_AUDIT_REPORT.md",
            "docs/certification/AUTOMATION_SCALE_REPORT.md",
            "docs/certification/PHASE_12E_FINAL_CERTIFICATION.md",
            "docs/certification/FORECASTING_REPORT.md",
        ],
    },
    {
        "name": "Phase 12F-G — Unified Customer Workspace, Global Command Bar & Production Hardening",
        "files": [
            # Phase 12F - Customer workspace
            "backend/src/seo_platform/api/endpoints/customers.py",
            "backend/src/seo_platform/api/endpoints/search.py",
            "backend/src/seo_platform/api/endpoints/copilot.py",
            "backend/src/seo_platform/api/endpoints/copilot_v2.py",
            # Phase 12G - Production hardening
            "backend/src/seo_platform/api/endpoints/alerting.py",
            "backend/src/seo_platform/api/endpoints/advanced_sre.py",
            "backend/src/seo_platform/api/endpoints/deployment.py",
            "backend/src/seo_platform/api/endpoints/audit_ledger.py",
            "backend/src/seo_platform/api/endpoints/approval_workflow.py",
            "backend/src/seo_platform/api/endpoints/approvals_v2.py",
        ],
        "patterns": [
            "frontend/src/app/dashboard/customers/",
            "frontend/src/app/dashboard/command-center/",
            "frontend/src/app/dashboard/copilot-v2/",
            "frontend/src/app/dashboard/audit/",
            "frontend/src/app/dashboard/recovery/",
            "frontend/src/app/dashboard/system-health/",
            "frontend/src/app/dashboard/advanced-sre/",
            "frontend/src/app/dashboard/approvals-center/",
            "frontend/src/components/command-bar.tsx",
            "frontend/src/components/command-palette/",
            "frontend/src/components/rbac/",
            "frontend/src/hooks/use-auth.ts",
            "frontend/src/hooks/use-rbac.ts",
            "frontend/src/types/auth.ts",
            "frontend/src/config/",
            "frontend/src/providers/",
            "frontend/src/services/",
            "frontend/src/stores/",
            "frontend/src/lib/errors.ts",
            "frontend/src/lib/safe.ts",
            "frontend/src/lib/api-url.ts",
            "frontend/src/components/layout/",
            "frontend/src/components/error-boundary.tsx",
            "frontend/src/app/error.tsx",
            "frontend/src/app/not-found.tsx",
            "frontend/src/app/dashboard/error.tsx",
            "docs/certification/PHASE_12F_FINAL_CERTIFICATION.md",
            "docs/certification/PHASE_12G_FINAL_CERTIFICATION.md",
            "docs/certification/GLOBAL_COMMAND_BAR_REPORT.md",
            "docs/certification/SECURITY_AUDIT_REPORT.md",
            "docs/certification/MULTITENANT_AUDIT_REPORT.md",
            "docs/certification/DATABASE_PERFORMANCE_REPORT.md",
            "docs/certification/CI_CD_CERTIFICATION.md",
            "docs/certification/BACKUP_RECOVERY_REPORT.md",
            "docs/certification/DISASTER_RECOVERY_REPORT.md",
        ],
    },
    {
        "name": "Phase 13 — AI Operating System: Knowledge Graph, Semantic Search, Citations & Copilot",
        "files": [
            "backend/alembic/versions/j1_add_citation_tables.py",
            "backend/citation_schema.sql",
            "backend/src/seo_platform/api/endpoints/agents.py",
            "backend/src/seo_platform/api/endpoints/ai_query.py",
            "backend/src/seo_platform/api/endpoints/knowledge.py",
            "backend/src/seo_platform/api/endpoints/citations.py",
            "backend/src/seo_platform/api/endpoints/citation_automation.py",
            "backend/src/seo_platform/api/endpoints/citation_export.py",
            "backend/src/seo_platform/api/endpoints/citation_intelligence.py",
            "backend/src/seo_platform/api/endpoints/citation_operations.py",
            "backend/src/seo_platform/api/endpoints/citation_projects.py",
            "backend/src/seo_platform/api/endpoints/citation_sites.py",
            "backend/src/seo_platform/api/endpoints/citation_submissions.py",
            "backend/src/seo_platform/api/endpoints/citation_verification.py",
            "backend/src/seo_platform/api/endpoints/competitor_intelligence.py",
            "backend/src/seo_platform/api/endpoints/cross_tenant_intelligence.py",
            "backend/src/seo_platform/api/endpoints/semantic_memory.py",
            "backend/src/seo_platform/api/endpoints/seo_intelligence.py",
            "backend/src/seo_platform/api/endpoints/seo_strategic.py",
            "backend/src/seo_platform/api/endpoints/serp_intelligence.py",
            "backend/src/seo_platform/api/endpoints/intelligence.py",
            "backend/src/seo_platform/api/endpoints/intelligence_queries.py",
            "backend/src/seo_platform/api/endpoints/predictive_intelligence.py",
            "backend/src/seo_platform/api/endpoints/outreach_intelligence.py",
        ],
        "patterns": [
            "frontend/src/app/dashboard/citation-intelligence/",
            "frontend/src/app/dashboard/citation-operations/",
            "frontend/src/app/dashboard/citations/",
            "frontend/src/app/dashboard/competitor-intelligence/",
            "frontend/src/app/dashboard/cross-tenant/",
            "frontend/src/app/dashboard/intelligence/",
            "frontend/src/app/dashboard/predictive/",
            "frontend/src/app/dashboard/seo-intelligence/",
            "frontend/src/app/dashboard/seo-health/",
            "frontend/src/app/dashboard/strategic/",
            "frontend/src/app/dashboard/strategic-seo/",
            "frontend/src/components/citations/",
            "docs/certification/PHASE_13_FINAL_CERTIFICATION.md",
            "docs/certification/KNOWLEDGE_GRAPH_REPORT.md",
            "docs/certification/SEMANTIC_SEARCH_REPORT.md",
            "docs/certification/AI_QUERY_ENGINE_REPORT.md",
            "docs/certification/COPILOT_REPORT.md",
            "docs/certification/RECOMMENDATION_ENGINE_REPORT.md",
        ],
    },
    {
        "name": "Phase 13.5-14 — Recommendation Engine, Outreach Operations & Campaign Execution",
        "files": [
            # Phase 14 orchestrator tables
            "backend/alembic/versions/f1b2c3d4e5f6_add_phase14_orchestrator_tables.py",
            "backend/alembic/versions/g7h8i9j0k1l2_add_outreach_communication_tables.py",
            # Outreach & campaign endpoints
            "backend/src/seo_platform/api/endpoints/campaign_agent.py",
            "backend/src/seo_platform/api/endpoints/campaign_operations.py",
            "backend/src/seo_platform/api/endpoints/campaign_portfolio.py",
            "backend/src/seo_platform/api/endpoints/outreach_operations.py",
            "backend/src/seo_platform/api/endpoints/outreach_quality.py",
            "backend/src/seo_platform/api/endpoints/backlink_acquisition.py",
            "backend/src/seo_platform/api/endpoints/backlink_intelligence.py",
            "backend/src/seo_platform/api/endpoints/prospects.py",
            "backend/src/seo_platform/api/endpoints/prospect_graph.py",
            "backend/src/seo_platform/api/endpoints/communication_reliability.py",
            "backend/src/seo_platform/api/endpoints/communication_templates.py",
            "backend/src/seo_platform/api/endpoints/recommendations.py",
        ],
        "patterns": [
            "frontend/src/app/dashboard/outreach-operations/",
            "frontend/src/app/dashboard/campaign-operations/",
            "frontend/src/app/dashboard/backlink-intelligence/",
            "frontend/src/app/dashboard/prospect-list/",
            "frontend/src/app/dashboard/prospect-graph/",
            "frontend/src/app/dashboard/recommendations/",
            "frontend/src/app/dashboard/recommendations-v2/",
            "frontend/src/components/email/",
            "frontend/src/components/operator/",
            "frontend/src/lib/merge-variables.ts",
            "reports/RBV_1_2_DELIVERABLES/",
            "reports/PHASE_14_5_DELIVERABLES/",
            "reports/PROSPECT_DISCOVERY_CLOSURE_REPORT.md",
            "reports/PROSPECT_DISCOVERY_DEPENDENCY_REPORT.md",
            "reports/PROSPECT_DISCOVERY_EVIDENCE_LOG.md",
            "reports/PROSPECT_DISCOVERY_FINAL_VERDICT.md",
            "reports/PROSPECT_DISCOVERY_FIX_REPORT.md",
            "reports/PROSPECT_DISCOVERY_REALITY_REPORT.md",
            "reports/PROSPECT_DISCOVERY_RETEST_REPORT.md",
            "reports/PROSPECT_DISCOVERY_SCORECARD.md",
        ],
    },
    {
        "name": "Phase 14.5-15 — Campaign Effectiveness, Link Acquisition & Strategic SEO",
        "files": [
            "backend/src/seo_platform/api/endpoints/local_seo.py",
            "backend/src/seo_platform/api/endpoints/keyword_priority.py",
            "backend/src/seo_platform/api/endpoints/strategic_growth.py",
            "backend/src/seo_platform/api/endpoints/strategic_seo_cognition.py",
        ],
        "patterns": [
            "frontend/src/app/dashboard/local-seo/",
            "frontend/src/app/dashboard/keywords/",
            "reports/PHASE_15_DELIVERABLES/",
            "reports/PHASE_15_5_DELIVERABLES/",
        ],
    },
    {
        "name": "Phase 15.5-R2 — Enterprise Scale, Production Rollout & Observability",
        "files": [
            "backend/src/seo_platform/api/endpoints/ai_ops.py",
            "backend/src/seo_platform/api/endpoints/ai_quality.py",
            "backend/src/seo_platform/api/endpoints/ai_resilience.py",
            "backend/src/seo_platform/api/endpoints/anomaly_prediction.py",
            "backend/src/seo_platform/api/endpoints/autonomous_coordination.py",
            "backend/src/seo_platform/api/endpoints/autonomy_orchestrator.py",
            "backend/src/seo_platform/api/endpoints/adaptive_optimization.py",
            "backend/src/seo_platform/api/endpoints/advanced_analytics.py",
            "backend/src/seo_platform/api/endpoints/complexity_management.py",
            "backend/src/seo_platform/api/endpoints/distributed_hardening.py",
            "backend/src/seo_platform/api/endpoints/ecosystem_maturity.py",
            "backend/src/seo_platform/api/endpoints/enterprise_cognition.py",
            "backend/src/seo_platform/api/endpoints/enterprise_ecosystem.py",
            "backend/src/seo_platform/api/endpoints/enterprise_lifecycle.py",
            "backend/src/seo_platform/api/endpoints/event_infrastructure.py",
            "backend/src/seo_platform/api/endpoints/event_lineage.py",
            "backend/src/seo_platform/api/endpoints/extreme_scale_orchestration.py",
            "backend/src/seo_platform/api/endpoints/global_infrastructure.py",
            "backend/src/seo_platform/api/endpoints/global_orchestration.py",
            "backend/src/seo_platform/api/endpoints/governance_service.py",
            "backend/src/seo_platform/api/endpoints/incident_evolution.py",
            "backend/src/seo_platform/api/endpoints/incident_intelligence.py",
            "backend/src/seo_platform/api/endpoints/incident_response.py",
            "backend/src/seo_platform/api/endpoints/infrastructure_economics.py",
            "backend/src/seo_platform/api/endpoints/infrastructure_intelligence.py",
            "backend/src/seo_platform/api/endpoints/infrastructure_self_analysis.py",
            "backend/src/seo_platform/api/endpoints/maintainability_dominance.py",
            "backend/src/seo_platform/api/endpoints/maintainability_service.py",
            "backend/src/seo_platform/api/endpoints/observability.py",
            "backend/src/seo_platform/api/endpoints/operational_assistant.py",
            "backend/src/seo_platform/api/endpoints/operational_evolution.py",
            "backend/src/seo_platform/api/endpoints/operational_lifecycle.py",
            "backend/src/seo_platform/api/endpoints/operations_feed.py",
            "backend/src/seo_platform/api/endpoints/orchestration_intelligence.py",
            "backend/src/seo_platform/api/endpoints/organizational_intelligence.py",
            "backend/src/seo_platform/api/endpoints/overload_protection.py",
            "backend/src/seo_platform/api/endpoints/platform_stewardship.py",
            "backend/src/seo_platform/api/endpoints/production_economics.py",
            "backend/src/seo_platform/api/endpoints/realtime_telemetry.py",
            "backend/src/seo_platform/api/endpoints/scraping_resilience.py",
            "backend/src/seo_platform/api/endpoints/scraping_scaling.py",
            "backend/src/seo_platform/api/endpoints/sre_observability.py",
            "backend/src/seo_platform/api/endpoints/workflow_resilience.py",
            "backend/src/seo_platform/api/endpoints/kill_switches.py",
            "backend/src/seo_platform/api/endpoints/scale.py",
            "backend/src/seo_platform/api/endpoints/providers.py",
            "backend/src/seo_platform/api/endpoints/providers_unified.py",
            "backend/src/seo_platform/api/endpoints/provider_health.py",
            "backend/src/seo_platform/api/endpoints/health.py",
        ],
        "patterns": [
            "frontend/src/app/dashboard/ai-ops/",
            "frontend/src/app/dashboard/advanced-sre/",
            "frontend/src/app/dashboard/enterprise-ecosystem/",
            "frontend/src/app/dashboard/ecosystem-maturity/",
            "frontend/src/app/dashboard/events/",
            "frontend/src/app/dashboard/extreme-scale-orchestration/",
            "frontend/src/app/dashboard/global-infra/",
            "frontend/src/app/dashboard/global-orchestration/",
            "frontend/src/app/dashboard/governance/",
            "frontend/src/app/dashboard/incident-evolution/",
            "frontend/src/app/dashboard/incidents/",
            "frontend/src/app/dashboard/lineage/",
            "frontend/src/app/dashboard/maintainability/",
            "frontend/src/app/dashboard/maintainability-dominance/",
            "frontend/src/app/dashboard/operational-evolution/",
            "frontend/src/app/dashboard/operations/",
            "frontend/src/app/dashboard/operations-lifecycle/",
            "frontend/src/app/dashboard/organizational-intelligence/",
            "frontend/src/app/dashboard/outbox/",
            "frontend/src/app/dashboard/platform-stewardship/",
            "frontend/src/app/dashboard/production-economics/",
            "frontend/src/app/dashboard/providers/",
            "frontend/src/app/dashboard/providers-v2/",
            "frontend/src/app/dashboard/killswitches/",
            "frontend/src/app/dashboard/scraping/",
            "frontend/src/app/dashboard/topology/",
            "frontend/src/app/dashboard/traces/",
            "frontend/src/app/dashboard/deployment/",
            "frontend/src/app/dashboard/economics/",
            "frontend/src/app/dashboard/workflow-status/",
            "frontend/src/app/dashboard/temporal/",
            "frontend/src/app/dashboard/settings/",
            "frontend/src/components/unified/",
            "frontend/src/components/operational/",
            "frontend/src/components/ui/",
            "frontend/src/components/editable/",
            "docs/certification/OBSERVABILITY_CERTIFICATION.md",
            "docs/certification/LOAD_TEST_REPORT.md",
            "docs/certification/RESILIENCE_VALIDATION_REPORT.md",
            "docs/certification/WORKSPACE_SCALE_REPORT.md",
            "docs/certification/AGENT_CERTIFICATION_REPORT.md",
            "docs/certification/AI_OBSERVABILITY_REPORT.md",
            "docs/certification/executive-api-certification-report.md",
            "docs/certification/executive-frontend-certification-report.md",
            "docs/certification/executive-scale-performance-report.md",
            "docs/certification/api-scale-report.md",
            "docs/certification/comprehensive-validation-report.md",
            "docs/certification/filter-integration-report.md",
            "reports/PHASE_R1_DELIVERABLES/",
            "reports/PHASE_R2_DELIVERABLES/",
        ],
    },
]

def main():
    print("=" * 70)
    print("BuildIT Platform — Phase-based Git Commits")
    print("=" * 70)

    # First, reset any staged changes
    reset()

    for i, phase in enumerate(PHASES):
        print(f"\n[{i+1}/{len(PHASES)}] {phase['name']}")

        # Add specific files
        if phase.get("files"):
            add_files(phase["files"])

        # Add patterns (directories and specific files)
        if phase.get("patterns"):
            for p in phase["patterns"]:
                add_pattern(p)

        # Add deleted files if requested
        if phase.get("deleted"):
            # Add all deleted files (old reports moved to reports/)
            result = run('git status --short | grep "^ D" | awk \'{print $2}\'')
            deleted = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
            if deleted:
                for d in deleted:
                    run(f'git add -- "{d}"')

        count = staged_count()
        print(f"  Staged: {count} files")

        if count > 0:
            commit(f"feat: {phase['name']}")
        else:
            print("  SKIP: No files to commit")

    # Now handle remaining files
    print(f"\n[{len(PHASES)+1}] Infrastructure, CI/CD & Docker")
    add_pattern(".github/")
    add_pattern("infrastructure/")
    add_pattern("scripts/")
    add_pattern("Makefile")
    add_pattern(".env")
    add_pattern(".env.development")
    add_pattern(".env.example")
    add_pattern(".env.production")
    add_pattern(".env.testing")
    add_pattern("backend/.env.example")
    add_pattern("backend/Dockerfile")
    add_pattern("frontend/Dockerfile")
    add_pattern("frontend/.env.development")
    add_pattern("frontend/.env.local")
    add_pattern("frontend/next.config.js")
    add_pattern("frontend/package-lock.json")
    count = staged_count()
    print(f"  Staged: {count} files")
    if count > 0:
        commit("feat: Infrastructure — CI/CD, Docker, Kubernetes, Terraform & Environment Configuration")

    # Project Omega
    print(f"\n[{len(PHASES)+2}] Project Omega — Strategic Analysis")
    add_pattern("reports/PROJECT_OMEGA/")
    count = staged_count()
    print(f"  Staged: {count} files")
    if count > 0:
        commit("docs: Project Omega — Strategic Investment Analysis & Valuation")

    # Frontend V2 docs and remaining reports
    print(f"\n[{len(PHASES)+3}] Documentation & Reports")
    add_pattern("frontend/FRONTEND_V2_*")
    add_pattern("docs/")
    add_pattern("reports/")
    add_pattern("backend/reports/")
    add_pattern("backend/certification/")
    add_pattern("backend/data/")
    add_pattern("backend/scripts/")
    add_pattern("backend/tests/")
    add_pattern("PHASE_SUMMARY.md")
    add_pattern("PHASE_IMPLEMENTATION_SUMMARY.md")
    add_pattern("DEPLOY.md")
    count = staged_count()
    print(f"  Staged: {count} files")
    if count > 0:
        commit("docs: Phase Reports, Certification, Validation & Documentation")

    # All remaining backend source changes (modified endpoints, services, models, etc.)
    print(f"\n[{len(PHASES)+4}] Backend Source Updates")
    add_pattern("backend/src/")
    add_pattern("backend/pyproject.toml")
    add_pattern("backend/uv.lock")
    add_pattern("backend/alembic/")
    add_pattern("backend/*.py")
    add_pattern("backend/*.log")
    add_pattern("backend/*.sql")
    count = staged_count()
    print(f"  Staged: {count} files")
    if count > 0:
        commit("feat: Backend — Enhanced Services, Models, Workflows & Core Platform Updates")

    # All remaining frontend changes
    print(f"\n[{len(PHASES)+5}] Frontend Source Updates")
    add_pattern("frontend/src/")
    add_pattern("frontend/package.json")
    add_pattern("frontend/pnpm-lock.yaml")
    add_pattern("frontend/tsconfig.json")
    add_pattern("frontend/tsconfig.tsbuildinfo")
    add_pattern("frontend/next.config.ts")
    add_pattern("frontend/eslint.config.mjs")
    add_pattern("frontend/postcss.config.mjs")
    add_pattern("frontend/*.log")
    count = staged_count()
    print(f"  Staged: {count} files")
    if count > 0:
        commit("feat: Frontend — Enhanced Components, Stores, Hooks & UI Updates")

    # Graphify and everything else
    print(f"\n[{len(PHASES)+6}] Remaining Changes")
    add_pattern("graphify-out/")
    run("git add -A")
    count = staged_count()
    print(f"  Staged: {count} files")
    if count > 0:
        commit("chore: Remaining Changes — Graph Analysis, Logs & Miscellaneous Updates")

    # Summary
    print("\n" + "=" * 70)
    print("COMMIT SUMMARY")
    print("=" * 70)
    result = run("git log --oneline -20")
    print(result.stdout)

if __name__ == "__main__":
    main()
