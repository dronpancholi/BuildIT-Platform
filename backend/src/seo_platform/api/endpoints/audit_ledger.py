"""
Audit Ledger API — Phase 2 Final Section 6 gap fix.

Exposes the immutable audit ledger for compliance, debugging, and forensics.
All entries are append-only (enforced by DB trigger) and tenant-scoped.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from seo_platform.core.database import get_tenant_session
from seo_platform.core.auth import get_current_user, get_validated_tenant_id
from seo_platform.core.rbac import RequirePermission
from seo_platform.models.audit_ledger import ActorType, AuditLedgerEntry, DecisionType
from seo_platform.schemas import APIResponse

router = APIRouter()


class AuditLedgerEntryResponse(BaseModel):
    id: str
    action_name: str
    actor_id: str
    actor_type: str
    target_type: str
    target_id: str
    summary: str
    decision: Optional[str] = None
    risk_level: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    semantic_hash: str
    immutable_at: datetime
    created_at: datetime


@router.get("/ledger", response_model=APIResponse[list[AuditLedgerEntryResponse]])
async def list_audit_ledger(
    action_name: Optional[str] = Query(None, description="Filter by action name (e.g. 'rbac_denied:campaigns:read')"),
    actor_id: Optional[uuid.UUID] = Query(None, description="Filter by actor (user/agent) UUID"),
    target_type: Optional[str] = Query(None, description="Filter by target entity type"),
    target_id: Optional[uuid.UUID] = Query(None, description="Filter by target entity UUID"),
    decision: Optional[DecisionType] = Query(None, description="Filter by decision type"),
    since: Optional[datetime] = Query(None, description="Return entries with immutable_at >= since"),
    until: Optional[datetime] = Query(None, description="Return entries with immutable_at <= until"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    _user = Depends(RequirePermission("audit:read")),
) -> APIResponse[list[AuditLedgerEntryResponse]]:
    """List audit ledger entries for the current tenant, newest first.

    RLS enforces tenant isolation at the database level; the WHERE clause
    here is a defence-in-depth filter.
    """
    async with get_tenant_session(tenant_id) as session:
        stmt = select(AuditLedgerEntry).where(AuditLedgerEntry.tenant_id == tenant_id)
        if action_name:
            stmt = stmt.where(AuditLedgerEntry.action_name == action_name)
        if actor_id:
            stmt = stmt.where(AuditLedgerEntry.actor_id == actor_id)
        if target_type:
            stmt = stmt.where(AuditLedgerEntry.target_type == target_type)
        if target_id:
            stmt = stmt.where(AuditLedgerEntry.target_id == target_id)
        if decision:
            stmt = stmt.where(AuditLedgerEntry.decision == decision)
        if since:
            stmt = stmt.where(AuditLedgerEntry.immutable_at >= since)
        if until:
            stmt = stmt.where(AuditLedgerEntry.immutable_at <= until)

        stmt = stmt.order_by(AuditLedgerEntry.immutable_at.desc()).limit(limit).offset(offset)
        result = await session.execute(stmt)
        entries = result.scalars().all()

    return APIResponse(
        success=True,
        data=[
            AuditLedgerEntryResponse(
                id=str(e.id),
                action_name=e.action_name,
                actor_id=str(e.actor_id),
                actor_type=e.actor_type.value,
                target_type=e.target_type,
                target_id=str(e.target_id),
                summary=e.summary,
                decision=e.decision.value if e.decision else None,
                risk_level=e.risk_level,
                ip_address=e.ip_address,
                user_agent=e.user_agent,
                semantic_hash=e.semantic_hash,
                immutable_at=e.immutable_at,
                created_at=e.created_at,
            )
            for e in entries
        ],
        meta={"total": len(entries), "limit": limit, "offset": offset},
    )


@router.get("/ledger/stats", response_model=APIResponse[dict])
async def audit_ledger_stats(
    since: Optional[datetime] = Query(None, description="Stats since this timestamp"),
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    _user = Depends(RequirePermission("audit:read")),
) -> APIResponse[dict]:
    """Aggregate audit ledger statistics: counts by action, decision, actor type.

    Used by the operator dashboard and SRE for trend analysis.
    """
    from sqlalchemy import func

    async with get_tenant_session(tenant_id) as session:
        base = select(AuditLedgerEntry).where(AuditLedgerEntry.tenant_id == tenant_id)
        if since:
            base = base.where(AuditLedgerEntry.immutable_at >= since)

        by_action: dict[str, int] = {}
        by_decision: dict[str, int] = {}
        by_actor_type: dict[str, int] = {}
        by_risk: dict[str, int] = {}

        result = await session.execute(base)
        for e in result.scalars().all():
            by_action[e.action_name] = by_action.get(e.action_name, 0) + 1
            if e.decision:
                by_decision[e.decision.value] = by_decision.get(e.decision.value, 0) + 1
            by_actor_type[e.actor_type.value] = by_actor_type.get(e.actor_type.value, 0) + 1
            by_risk[e.risk_level] = by_risk.get(e.risk_level, 0) + 1

    return APIResponse(
        success=True,
        data={
            "by_action": by_action,
            "by_decision": by_decision,
            "by_actor_type": by_actor_type,
            "by_risk_level": by_risk,
            "total": sum(by_action.values()),
            "since": since.isoformat() if since else None,
        },
    )
