"""
SEO Platform — Link Verification Endpoints (Workstream E)
============================================================
REST surface for the link verification engine.

Exposes:
- ``POST /link-verification/{acquired_link_id}/verify`` — manual trigger.
- ``GET  /link-verification/{acquired_link_id}/history`` — full history.
- ``POST /link-verification/campaigns/{campaign_id}/verify-all`` — bulk
  verify every link in a campaign.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from seo_platform.core.auth import get_validated_tenant_id
from seo_platform.core.rbac import RequirePermission
from seo_platform.schemas import APIResponse

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------
class VerifyLinkResponse(BaseModel):
    acquired_link_id: str
    campaign_id: str | None = None
    source_url: str | None = None
    target_url: str | None = None
    found: bool
    outcome: str
    link_status: str | None = None
    http_status: int | None = None
    response_time_ms: float | None = None
    matched: bool
    anchor_text: str | None = None
    rel: str | None = None
    link_type: str | None = None
    link_position: int | None = None
    redirect_chain: list[dict[str, Any]] = Field(default_factory=list)
    final_url: str | None = None
    checked_at: str | None = None
    previous_status: str | None = None
    error: str | None = None


class HistoryEntry(BaseModel):
    checked_at: str
    outcome: str
    http_status: int | None = None
    response_time_ms: float | None = None
    matched: bool = False
    anchor_text: str | None = None
    rel: str | None = None
    link_type: str | None = None
    link_position: int | None = None
    error: str | None = None


class HistoryResponse(BaseModel):
    acquired_link_id: str
    current_status: str
    check_count: int
    first_verified_at: str | None = None
    last_checked_at: str | None = None
    last_http_status: int | None = None
    last_response_time_ms: float | None = None
    last_match_anchor: str | None = None
    last_match_rel: str | None = None
    last_match_position: int | None = None
    last_error: str | None = None
    history: list[HistoryEntry] = Field(default_factory=list)


class BulkVerifyResult(BaseModel):
    acquired_link_id: str
    outcome: str
    link_status: str | None = None
    matched: bool
    error: str | None = None


class BulkVerifyResponse(BaseModel):
    campaign_id: str
    started_at: str
    finished_at: str
    total: int
    verified: int
    missing: int
    redirected: int
    broken: int
    errors: int
    results: list[BulkVerifyResult] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _serialize_history_entry(entry: dict[str, Any]) -> HistoryEntry:
    return HistoryEntry(
        checked_at=entry.get("checked_at") or datetime.utcnow().isoformat(),
        outcome=entry.get("outcome") or "error",
        http_status=entry.get("http_status"),
        response_time_ms=entry.get("response_time_ms"),
        matched=bool(entry.get("matched", False)),
        anchor_text=entry.get("anchor_text"),
        rel=entry.get("rel"),
        link_type=entry.get("link_type"),
        link_position=entry.get("link_position"),
        error=entry.get("error"),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post(
    "/{acquired_link_id}/verify",
    response_model=APIResponse[VerifyLinkResponse],
)
async def verify_single_link(
    acquired_link_id: UUID,
    tenant_id: UUID = Depends(get_validated_tenant_id),
    _auth: None = Depends(RequirePermission("campaigns:write")),
) -> APIResponse[VerifyLinkResponse]:
    """Manually trigger a real verification for a single acquired link."""
    from seo_platform.services.link_verification import (
        link_verification_service,
    )

    result = await link_verification_service.verify_link(
        acquired_link_id=acquired_link_id,
        tenant_id=tenant_id,
    )

    if not result.get("found", True):
        raise HTTPException(
            status_code=404,
            detail=result.get("error", "Acquired link not found"),
        )

    payload = VerifyLinkResponse(**result)
    return APIResponse(data=payload)


@router.get(
    "/{acquired_link_id}/history",
    response_model=APIResponse[HistoryResponse],
)
async def get_verification_history(
    acquired_link_id: UUID,
    tenant_id: UUID = Depends(get_validated_tenant_id),
    _auth: None = Depends(RequirePermission("campaigns:read")),
) -> APIResponse[HistoryResponse]:
    """Return the full verification history for an acquired link."""
    from sqlalchemy import select

    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.backlink import AcquiredLink

    async with get_tenant_session(tenant_id) as session:
        result = await session.execute(
            select(AcquiredLink).where(
                AcquiredLink.id == acquired_link_id,
                AcquiredLink.tenant_id == tenant_id,
            )
        )
        link = result.scalar_one_or_none()
        if link is None:
            raise HTTPException(status_code=404, detail="Acquired link not found")

        history = [_serialize_history_entry(e) for e in (link.verification_history or [])]

        payload = HistoryResponse(
            acquired_link_id=str(link.id),
            current_status=(
                link.status.value
                if hasattr(link.status, "value")
                else str(link.status or "")
            ),
            check_count=link.check_count or 0,
            first_verified_at=link.first_verified_at.isoformat() if link.first_verified_at else None,
            last_checked_at=link.last_checked_at.isoformat() if link.last_checked_at else None,
            last_http_status=link.last_http_status,
            last_response_time_ms=link.last_response_time_ms,
            last_match_anchor=link.last_match_anchor,
            last_match_rel=link.last_match_rel,
            last_match_position=link.last_match_position,
            last_error=link.last_error,
            history=history,
        )

    return APIResponse(data=payload)


@router.post(
    "/campaigns/{campaign_id}/verify-all",
    response_model=APIResponse[BulkVerifyResponse],
)
async def verify_all_campaign_links(
    campaign_id: UUID,
    tenant_id: UUID = Depends(get_validated_tenant_id),
    _auth: None = Depends(RequirePermission("campaigns:write")),
) -> APIResponse[BulkVerifyResponse]:
    """Bulk-verify every acquired link in a campaign.

    Reuses the same per-link verification engine as the manual trigger;
    each link is fetched in real time and persisted individually.
    """
    import asyncio
    from datetime import UTC, datetime

    from sqlalchemy import select

    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.backlink import AcquiredLink
    from seo_platform.services.link_verification import (
        link_verification_service,
    )

    started_at = datetime.now(UTC)
    async with get_tenant_session(tenant_id) as session:
        rows = await session.execute(
            select(AcquiredLink.id).where(
                AcquiredLink.tenant_id == tenant_id,
                AcquiredLink.campaign_id == campaign_id,
            )
        )
        link_ids = [row[0] for row in rows.all()]

    if not link_ids:
        finished = datetime.now(UTC)
        payload = BulkVerifyResponse(
            campaign_id=str(campaign_id),
            started_at=started_at.isoformat(),
            finished_at=finished.isoformat(),
            total=0,
            verified=0,
            missing=0,
            redirected=0,
            broken=0,
            errors=0,
            results=[],
        )
        return APIResponse(data=payload)

    semaphore = asyncio.Semaphore(10)

    async def _run(lid: UUID) -> dict[str, Any]:
        async with semaphore:
            try:
                return await link_verification_service.verify_link(
                    acquired_link_id=lid,
                    tenant_id=tenant_id,
                )
            except Exception as exc:
                return {
                    "acquired_link_id": str(lid),
                    "outcome": "error",
                    "link_status": None,
                    "matched": False,
                    "error": str(exc),
                }

    raw_results = await asyncio.gather(*[_run(lid) for lid in link_ids])

    verified = missing = redirected = broken = errors = 0
    bulk_results: list[BulkVerifyResult] = []
    for r in raw_results:
        outcome = (r.get("outcome") or "").lower()
        if outcome == "verified":
            verified += 1
        elif outcome == "missing":
            missing += 1
        elif outcome == "redirected":
            redirected += 1
        elif outcome == "broken":
            broken += 1
        else:
            errors += 1
        bulk_results.append(
            BulkVerifyResult(
                acquired_link_id=r.get("acquired_link_id", ""),
                outcome=outcome or "error",
                link_status=r.get("link_status"),
                matched=bool(r.get("matched", False)),
                error=r.get("error"),
            )
        )

    finished = datetime.now(UTC)
    payload = BulkVerifyResponse(
        campaign_id=str(campaign_id),
        started_at=started_at.isoformat(),
        finished_at=finished.isoformat(),
        total=len(link_ids),
        verified=verified,
        missing=missing,
        redirected=redirected,
        broken=broken,
        errors=errors,
        results=bulk_results,
    )
    return APIResponse(data=payload)
