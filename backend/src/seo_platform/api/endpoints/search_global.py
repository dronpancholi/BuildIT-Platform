"""
Global Search API for CMD+K Command Bar — Phase 12F.10
Searches across: customers, campaigns, keywords, prospects, emails,
drafts, templates, reports, approvals, automation rules, executions, executive alerts
Returns flat result list with type/label/path for immediate navigation.
"""

from __future__ import annotations

from seo_platform.core.auth import get_validated_tenant_id
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import text

from seo_platform.core.database import get_session
from seo_platform.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

TENANT_ID = "00000000-0000-0000-0000-000000000001"


@router.get("/search/global")
async def global_search(
    q: str = Query(..., description="Search query"),
    tenant_id: str = Query(TENANT_ID),
    limit: int = Query(default=10, ge=1, le=50),
) -> dict[str, Any]:
    """Global search across all entity types for the CMD+K command bar."""
    query = f"%{q}%"
    results: list[dict[str, Any]] = []

    async with get_session() as session:
        # Customers
        try:
            rows = await session.execute(
                text("SELECT id, name, domain FROM clients WHERE tenant_id = :tid AND (name ILIKE :q OR domain ILIKE :q) LIMIT :lim"),
                {"tid": tenant_id, "q": query, "lim": limit},
            )
            for row in rows.fetchall():
                results.append({"id": str(row[0]), "label": str(row[1]), "subtitle": str(row[2] or ""), "type": "customer", "path": f"/dashboard/customers/{row[0]}"})
        except Exception as e:
            logger.warning(f"customer search: {e}")

        # Campaigns
        try:
            rows = await session.execute(
                text("SELECT bc.id, bc.name, c.name AS client_name FROM backlink_campaigns bc LEFT JOIN clients c ON c.id = bc.client_id WHERE bc.tenant_id = :tid AND bc.name ILIKE :q LIMIT :lim"),
                {"tid": tenant_id, "q": query, "lim": limit},
            )
            for row in rows.fetchall():
                results.append({"id": str(row[0]), "label": str(row[1]), "subtitle": f"Campaign — {row[2] or ''}", "type": "campaign", "path": f"/dashboard/customers/{row[0]}"})
        except Exception as e:
            logger.warning(f"campaign search: {e}")

        # Keywords
        try:
            rows = await session.execute(
                text("SELECT id, keyword, search_volume FROM keywords WHERE tenant_id = :tid AND keyword ILIKE :q LIMIT :lim"),
                {"tid": tenant_id, "q": query, "lim": limit},
            )
            for row in rows.fetchall():
                results.append({"id": str(row[0]), "label": str(row[1]), "subtitle": f"Vol: {row[2] or 0}", "type": "keyword", "path": "/dashboard/seo-intelligence"})
        except Exception as e:
            logger.warning(f"keyword search: {e}")

        # Prospects
        try:
            rows = await session.execute(
                text("SELECT id, domain, status FROM backlink_prospects WHERE tenant_id = :tid AND domain ILIKE :q LIMIT :lim"),
                {"tid": tenant_id, "q": query, "lim": limit},
            )
            for row in rows.fetchall():
                results.append({"id": str(row[0]), "label": str(row[1]), "subtitle": f"Status: {row[2] or 'unknown'}", "type": "prospect", "path": "/dashboard/prospect-list"})
        except Exception as e:
            logger.warning(f"prospect search: {e}")

        # Emails (outreach_threads)
        try:
            rows = await session.execute(
                text("SELECT ot.id, ot.subject, ot.to_email FROM outreach_threads ot WHERE ot.campaign_id IN (SELECT id FROM backlink_campaigns WHERE tenant_id = :tid) AND (ot.subject ILIKE :q OR ot.to_email ILIKE :q) LIMIT :lim"),
                {"tid": tenant_id, "q": query, "lim": limit},
            )
            for row in rows.fetchall():
                results.append({"id": str(row[0]), "label": str(row[1] or "(no subject)"), "subtitle": f"To: {row[2]}", "type": "email", "path": "/dashboard/communications"})
        except Exception as e:
            logger.warning(f"email search: {e}")

        # Email drafts
        try:
            rows = await session.execute(
                text("SELECT ed.id, ed.subject, ed.recipient FROM email_drafts ed WHERE ed.tenant_id = :tid AND (ed.subject ILIKE :q OR ed.body ILIKE :q) LIMIT :lim"),
                {"tid": tenant_id, "q": query, "lim": limit},
            )
            for row in rows.fetchall():
                results.append({"id": str(row[0]), "label": f"Draft: {row[1] or '(no subject)'}", "subtitle": f"To: {row[2] or ''}", "type": "draft", "path": "/dashboard/communications"})
        except Exception as e:
            logger.warning(f"draft search: {e}")

        # Email templates
        try:
            rows = await session.execute(
                text("SELECT id, name, subject_template FROM email_templates WHERE tenant_id = :tid AND (name ILIKE :q OR subject_template ILIKE :q) LIMIT :lim"),
                {"tid": tenant_id, "q": query, "lim": limit},
            )
            for row in rows.fetchall():
                results.append({"id": str(row[0]), "label": f"Template: {row[1]}", "subtitle": f"Subject: {row[2] or ''}", "type": "template", "path": "/dashboard/templates"})
        except Exception as e:
            logger.warning(f"template search: {e}")

        # Approvals
        try:
            rows = await session.execute(
                text("SELECT ca.id, ca.category, ca.status FROM campaign_approvals ca WHERE ca.tenant_id = :tid AND (ca.category ILIKE :q OR ca.status ILIKE :q) LIMIT :lim"),
                {"tid": tenant_id, "q": query, "lim": limit},
            )
            for row in rows.fetchall():
                results.append({"id": str(row[0]), "label": f"Approval: {row[1]}", "subtitle": f"Status: {row[2]}", "type": "approval", "path": "/dashboard/approvals"})
        except Exception as e:
            logger.warning(f"approval search: {e}")

        # Reports
        try:
            rows = await session.execute(
                text("SELECT r.id, r.report_type, r.status FROM reports r WHERE r.tenant_id = :tid AND r.report_type ILIKE :q LIMIT :lim"),
                {"tid": tenant_id, "q": query, "lim": limit},
            )
            for row in rows.fetchall():
                results.append({"id": str(row[0]), "label": f"Report: {row[1]}", "subtitle": f"Status: {row[2]}", "type": "report", "path": "/dashboard/reports"})
        except Exception as e:
            logger.warning(f"report search: {e}")

        # Automation rules
        try:
            rows = await session.execute(
                text("SELECT ar.id, ar.name, ar.trigger_type FROM automation_rules ar WHERE ar.tenant_id = :tid AND ar.name ILIKE :q LIMIT :lim"),
                {"tid": tenant_id, "q": query, "lim": limit},
            )
            for row in rows.fetchall():
                results.append({"id": str(row[0]), "label": f"Rule: {row[1]}", "subtitle": f"Trigger: {row[2]}", "type": "automation", "path": "/dashboard/automation"})
        except Exception as e:
            logger.warning(f"automation search: {e}")

        # Automation runs
        try:
            rows = await session.execute(
                text("SELECT arun.id, arun.rule_name, arun.status FROM automation_runs arun WHERE arun.tenant_id = :tid AND arun.rule_name ILIKE :q LIMIT :lim"),
                {"tid": tenant_id, "q": query, "lim": limit},
            )
            for row in rows.fetchall():
                results.append({"id": str(row[0]), "label": f"Run: {row[1]}", "subtitle": f"Status: {row[2]}", "type": "execution", "path": "/dashboard/automation"})
        except Exception as e:
            logger.warning(f"automation run search: {e}")

        # Executive alerts
        try:
            rows = await session.execute(
                text("SELECT ea.id, ea.title, ea.severity FROM executive_alerts ea WHERE ea.tenant_id = :tid AND ea.title ILIKE :q LIMIT :lim"),
                {"tid": tenant_id, "q": query, "lim": limit},
            )
            for row in rows.fetchall():
                results.append({"id": str(row[0]), "label": f"Alert: {row[1]}", "subtitle": f"Severity: {row[2]}", "type": "alert", "path": "/dashboard/executive"})
        except Exception as e:
            logger.warning(f"alert search: {e}")

    return {
        "success": True,
        "data": {
            "query": q,
            "total": len(results),
            "results": results,
        },
    }
