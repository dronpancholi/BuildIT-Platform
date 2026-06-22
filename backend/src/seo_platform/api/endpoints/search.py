"""
Unified Search API - Minimal implementation for Phase 11
Searches across: customers, campaigns, keywords, approvals, emails, prospects, reports
"""

from __future__ import annotations

from seo_platform.core.auth import get_validated_tenant_id
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")


@router.get("", response_model=dict[str, Any])
async def unified_search(
    q: str = Query(..., description="Search query"),
    tenant_id: UUID = Depends(get_validated_tenant_id),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    """Unified search across all entities."""
    from seo_platform.core.database import get_session
    from sqlalchemy import text
    
    results = {
        "customers": [],
        "campaigns": [],
        "keywords": [],
        "approvals": [],
        "emails": [],
        "prospects": [],
        "reports": [],
    }
    
    async with get_session() as session:
        # Search customers
        try:
            result = await session.execute(
                text("""
                SELECT id, name, domain, niche, created_at 
                FROM clients 
                WHERE tenant_id = :tenant_id 
                AND (name ILIKE :query OR domain ILIKE :query OR niche ILIKE :query)
                LIMIT :limit
                """),
                {"tenant_id": str(tenant_id), "query": f"%{q}%", "limit": limit}
            )
            for row in result.fetchall():
                results["customers"].append({
                    "id": str(row[0]),
                    "name": row[1],
                    "domain": row[2],
                    "type": "customer",
                    "label": "Customer",
                })
        except Exception as e:
            logger.warning(f"Customer search failed: {e}")
        
        # Search campaigns
        try:
            result = await session.execute(
                text("""
                SELECT id, name, status, health_score, created_at 
                FROM backlink_campaigns 
                WHERE tenant_id = :tenant_id 
                AND name ILIKE :query
                LIMIT :limit
                """),
                {"tenant_id": str(tenant_id), "query": f"%{q}%", "limit": limit}
            )
            for row in result.fetchall():
                results["campaigns"].append({
                    "id": str(row[0]),
                    "name": row[1],
                    "status": row[2],
                    "health_score": row[3],
                    "type": "campaign",
                    "label": "Campaign",
                })
        except Exception as e:
            logger.warning(f"Campaign search failed: {e}")
        
        # Search keywords
        try:
            result = await session.execute(
                text("""
                SELECT id, keyword, search_volume, difficulty 
                FROM keywords 
                WHERE tenant_id = :tenant_id 
                AND keyword ILIKE :query
                LIMIT :limit
                """),
                {"tenant_id": str(tenant_id), "query": f"%{q}%", "limit": limit}
            )
            for row in result.fetchall():
                results["keywords"].append({
                    "id": str(row[0]),
                    "keyword": row[1],
                    "search_volume": row[2],
                    "type": "keyword",
                    "label": "Keyword",
                })
        except Exception as e:
            logger.warning(f"Keyword search failed: {e}")
        
        # Search approvals
        try:
            result = await session.execute(
                text("""
                SELECT id, category, status, created_at 
                FROM campaign_approvals 
                WHERE tenant_id = :tenant_id 
                AND (category ILIKE :query OR status ILIKE :query)
                LIMIT :limit
                """),
                {"tenant_id": str(tenant_id), "query": f"%{q}%", "limit": limit}
            )
            for row in result.fetchall():
                results["approvals"].append({
                    "id": str(row[0]),
                    "category": row[1],
                    "status": row[2],
                    "type": "approval",
                    "label": "Approval",
                })
        except Exception as e:
            logger.warning(f"Approval search failed: {e}")
        
        # Search threads/emails
        try:
            result = await session.execute(
                text("""
                SELECT id, subject, to_email, status, created_at 
                FROM outreach_threads 
                WHERE campaign_id IN (
                    SELECT id FROM backlink_campaigns WHERE tenant_id = :tenant_id
                )
                AND (subject ILIKE :query OR to_email ILIKE :query)
                LIMIT :limit
                """),
                {"tenant_id": str(tenant_id), "query": f"%{q}%", "limit": limit}
            )
            for row in result.fetchall():
                results["emails"].append({
                    "id": str(row[0]),
                    "subject": row[1],
                    "to_email": row[2],
                    "status": row[3],
                    "type": "email",
                    "label": "Email",
                })
        except Exception as e:
            logger.warning(f"Email search failed: {e}")
        
        # Search prospects (from backlink_prospects if exists)
        try:
            result = await session.execute(
                text("""
                SELECT id, domain, status, created_at 
                FROM backlink_prospects 
                WHERE tenant_id = :tenant_id 
                AND domain ILIKE :query
                LIMIT :limit
                """),
                {"tenant_id": str(tenant_id), "query": f"%{q}%", "limit": limit}
            )
            for row in result.fetchall():
                results["prospects"].append({
                    "id": str(row[0]),
                    "domain": row[1],
                    "status": row[2],
                    "type": "prospect",
                    "label": "Prospect",
                })
        except Exception as e:
            logger.warning(f"Prospect search failed: {e}")
        
        # Search reports
        try:
            result = await session.execute(
                text("""
                SELECT id, report_type, status, created_at 
                FROM reports 
                WHERE tenant_id = :tenant_id 
                AND report_type ILIKE :query
                LIMIT :limit
                """),
                {"tenant_id": str(tenant_id), "query": f"%{q}%", "limit": limit}
            )
            for row in result.fetchall():
                results["reports"].append({
                    "id": str(row[0]),
                    "report_type": row[1],
                    "status": row[2],
                    "type": "report",
                    "label": "Report",
                })
        except Exception as e:
            logger.warning(f"Report search failed: {e}")
    
    # Count total results
    total = sum(len(v) for v in results.values())
    
    return {
        "success": True,
        "data": {
            "query": q,
            "total": total,
            "results": results,
        },
    }
