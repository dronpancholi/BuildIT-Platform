"""
Campaign Portfolio API — Phase 12C Command Center
====================================================
Unified cross-customer campaign management with:
- Portfolio listing (filters, sort, pagination, search)
- Bulk operations (pause, resume, archive, assign, tag)
- Cross-customer queue (approvals, replies, failures, link issues)
- Portfolio analytics (velocity, rates, health, workload)
- Saved views (CRUD)
"""

from __future__ import annotations

from seo_platform.core.auth import get_validated_tenant_id
import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field


router = APIRouter()


# ── Models ──────────────────────────────────────────────

class PortfolioCampaign(BaseModel):
    id: str
    client_id: str
    customer_name: str
    name: str
    campaign_type: str
    status: str
    health_score: float
    total_prospects: int
    total_emails_sent: int
    total_replies: int
    acquired_link_count: int
    target_link_count: int
    last_activity: str | None
    assigned_manager: str | None
    tags: list[str] = []
    created_at: str | None


class PortfolioResponse(BaseModel):
    campaigns: list[PortfolioCampaign]
    total: int
    offset: int
    limit: int
    has_more: bool


class QueueItem(BaseModel):
    id: str
    campaign_id: str
    campaign_name: str
    customer_name: str
    type: str  # approval, reply, failed_send, link_issue, pending_action
    priority: int
    summary: str
    created_at: str
    assignee: str | None


class PortfolioAnalytics(BaseModel):
    total_campaigns: int
    active_campaigns: int
    avg_health: float
    total_prospects: int
    total_emails_sent: int
    total_replies: int
    total_links_acquired: int
    reply_rate: float
    acquisition_rate: float
    approval_backlog: int
    campaign_velocity: float


class SavedView(BaseModel):
    id: str
    name: str
    filters: dict
    created_at: str
    updated_at: str


# ── Portfolio Listing ──────────────────────────────────

@router.get("", response_model=PortfolioResponse)
async def list_portfolio(
    tenant_id: UUID = Depends(get_validated_tenant_id),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    sort_by: str = Query(default="created_at"),
    sort_dir: str = Query(default="desc"),
    search: str = Query(default=""),
    filter_status: str = Query(default="", alias="status"),
    health: str = Query(default=""),
    customer_id: str = Query(default=""),
    min_reply_rate: float = Query(default=0.0, ge=0.0, le=1.0),
    max_reply_rate: float = Query(default=1.0, ge=0.0, le=1.0),
    has_approvals: bool | None = Query(default=None),
    min_acquired: int = Query(default=0),
    max_acquired: int = Query(default=999999),
    date_from: str = Query(default=""),
    date_to: str = Query(default=""),
):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        where_clauses = ["c.tenant_id = :tenant_id"]
        params: dict = {"tenant_id": str(tenant_id)}

        if search:
            where_clauses.append("(c.name ILIKE :search OR cl.name ILIKE :search)")
            params["search"] = f"%{search}%"

        if filter_status:
            statuses = [s.strip() for s in filter_status.split(",")]
            placeholders = ",".join(f"'{s}'" for s in statuses)
            where_clauses.append(f"c.status::text IN ({placeholders})")

        if health == "healthy":
            where_clauses.append("c.health_score >= 0.7")
        elif health == "at_risk":
            where_clauses.append("c.health_score >= 0.4 AND c.health_score < 0.7")
        elif health == "critical":
            where_clauses.append("c.health_score < 0.4")

        if customer_id:
            where_clauses.append("c.client_id = :customer_id")
            params["customer_id"] = customer_id

        where_clauses.append("(c.reply_rate IS NULL OR (c.reply_rate >= :min_rr AND c.reply_rate <= :max_rr))")
        params["min_rr"] = min_reply_rate
        params["max_rr"] = max_reply_rate

        where_clauses.append("c.acquired_link_count >= :min_acq AND c.acquired_link_count <= :max_acq")
        params["min_acq"] = min_acquired
        params["max_acq"] = max_acquired

        if has_approvals is True:
            where_clauses.append("EXISTS (SELECT 1 FROM approval_requests ar WHERE ar.workflow_run_id = c.workflow_run_id AND ar.status = 'pending')")
        elif has_approvals is False:
            where_clauses.append("NOT EXISTS (SELECT 1 FROM approval_requests ar WHERE ar.workflow_run_id = c.workflow_run_id AND ar.status = 'pending')")

        if date_from:
            where_clauses.append("c.updated_at >= :date_from")
            params["date_from"] = date_from
        if date_to:
            where_clauses.append("c.updated_at <= :date_to")
            params["date_to"] = date_to

        where_sql = " AND ".join(where_clauses)

        allowed_sorts = {"name", "status", "health_score", "total_prospects", "total_emails_sent", "acquired_link_count", "reply_rate", "created_at", "updated_at"}
        if sort_by not in allowed_sorts:
            sort_by = "created_at"
        order = "DESC" if sort_dir == "desc" else "ASC"

        count_sql = text(f"""
            SELECT COUNT(*) FROM backlink_campaigns c
            LEFT JOIN clients cl ON c.client_id = cl.id
            WHERE {where_sql}
        """)
        count_result = await session.execute(count_sql, params)
        total = count_result.scalar()

        query_sql = text(f"""
            SELECT
                c.id, c.client_id, COALESCE(cl.name, 'Unknown') AS customer_name,
                c.name, c.campaign_type::text, c.status::text, c.health_score,
                c.total_prospects, c.total_emails_sent, c.acquired_link_count,
                c.target_link_count, c.reply_rate, c.updated_at,
                c.created_at, c.config->>'assigned_manager' AS assigned_manager,
                COALESCE(c.config->>'tags', '[]') AS tags
            FROM backlink_campaigns c
            LEFT JOIN clients cl ON c.client_id = cl.id
            WHERE {where_sql}
            ORDER BY {sort_by} {order}
            OFFSET :offset LIMIT :limit
        """)
        params["offset"] = offset
        params["limit"] = limit

        result = await session.execute(query_sql, params)
        rows = result.fetchall()

        campaigns = []
        for row in rows:
            try:
                tags_list = json.loads(row.tags) if isinstance(row.tags, str) else (row.tags or [])
            except (json.JSONDecodeError, TypeError):
                tags_list = []

            last_activity = row.updated_at.isoformat() if row.updated_at else None

            campaigns.append(PortfolioCampaign(
                id=str(row.id),
                client_id=str(row.client_id),
                customer_name=row.customer_name,
                name=row.name,
                campaign_type=row.campaign_type,
                status=row.status,
                health_score=row.health_score or 0.0,
                total_prospects=row.total_prospects or 0,
                total_emails_sent=row.total_emails_sent or 0,
                total_replies=0,
                acquired_link_count=row.acquired_link_count or 0,
                target_link_count=row.target_link_count or 10,
                last_activity=last_activity,
                assigned_manager=row.assigned_manager,
                tags=tags_list,
                created_at=row.created_at.isoformat() if row.created_at else None,
            ))

        return PortfolioResponse(
            campaigns=campaigns,
            total=total,
            offset=offset,
            limit=limit,
            has_more=(offset + limit) < total,
        )


# ── Portfolio Analytics ─────────────────────────────────

@router.get("/analytics", response_model=PortfolioAnalytics)
async def portfolio_analytics(
    tenant_id: UUID = Depends(get_validated_tenant_id),
):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        result = await session.execute(text("""
            SELECT
                COUNT(*) AS total_campaigns,
                COUNT(*) FILTER (WHERE status::text IN ('active','monitoring')) AS active_campaigns,
                COALESCE(AVG(health_score), 0) AS avg_health,
                COALESCE(SUM(total_prospects), 0) AS total_prospects,
                COALESCE(SUM(total_emails_sent), 0) AS total_emails_sent,
                COALESCE(SUM(acquired_link_count), 0) AS total_links_acquired,
                COALESCE(AVG(reply_rate), 0) AS avg_reply_rate,
                COALESCE(AVG(acquisition_rate), 0) AS avg_acquisition_rate
            FROM backlink_campaigns
            WHERE tenant_id = :tenant_id
        """), {"tenant_id": str(tenant_id)})
        row = result.first()

        approval_count = await session.execute(text("""
            SELECT COUNT(*) FROM approval_requests
            WHERE tenant_id = :tenant_id AND status::text = 'pending'
        """), {"tenant_id": str(tenant_id)})
        approval_backlog = approval_count.scalar() or 0

        reply_count = await session.execute(text("""
            SELECT COUNT(*) FROM outreach_threads
            WHERE tenant_id = :tenant_id AND status::text = 'replied'
        """), {"tenant_id": str(tenant_id)})
        total_replies = reply_count.scalar() or 0

        velocity_result = await session.execute(text("""
            SELECT COALESCE(AVG(acquired_link_count::float / NULLIF(GREATEST(EXTRACT(EPOCH FROM (COALESCE(updated_at, created_at) - created_at)) / 86400, 1), 0)), 0)
            FROM backlink_campaigns
            WHERE tenant_id = :tenant_id AND status::text IN ('active','monitoring')
        """), {"tenant_id": str(tenant_id)})
        campaign_velocity = velocity_result.scalar() or 0.0

        return PortfolioAnalytics(
            total_campaigns=row.total_campaigns,
            active_campaigns=row.active_campaigns,
            avg_health=round(float(row.avg_health), 4),
            total_prospects=row.total_prospects,
            total_emails_sent=row.total_emails_sent,
            total_replies=total_replies,
            total_links_acquired=row.total_links_acquired,
            reply_rate=round(float(row.avg_reply_rate), 4),
            acquisition_rate=round(float(row.avg_acquisition_rate), 4),
            approval_backlog=approval_backlog,
            campaign_velocity=round(float(campaign_velocity), 4),
        )


# ── Cross-Customer Queue ────────────────────────────────

@router.get("/queue", response_model=list[QueueItem])
async def portfolio_queue(
    tenant_id: UUID = Depends(get_validated_tenant_id),
    type: str = Query(default=""),
    limit: int = Query(default=50, ge=1, le=200),
):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        queue: list[QueueItem] = []
        now = datetime.now(timezone.utc)

        if not type or type == "approval":
            result = await session.execute(text("""
                SELECT ar.id, c.id AS campaign_id, c.name AS campaign_name,
                       COALESCE(cl.name, 'Unknown') AS customer_name,
                       ar.created_at, ar.assigned_to::text
                FROM approval_requests ar
                JOIN backlink_campaigns c ON ar.workflow_run_id = c.workflow_run_id
                LEFT JOIN clients cl ON c.client_id = cl.id
                WHERE ar.tenant_id = :tid AND ar.status::text = 'pending'
                ORDER BY ar.created_at ASC
                LIMIT :lim
            """), {"tid": str(tenant_id), "lim": limit})
            rows = result.fetchall()
            for row in rows:
                age_hours = (now - row.created_at).total_seconds() / 3600 if row.created_at else 0
                priority = min(100, int(age_hours * 2)) + 50
                queue.append(QueueItem(
                    id=str(row.id), campaign_id=str(row.campaign_id),
                    campaign_name=row.campaign_name, customer_name=row.customer_name,
                    type="approval", priority=priority,
                    summary=f"Campaign approval requested {int(age_hours)}h ago",
                    created_at=row.created_at.isoformat() if row.created_at else "",
                    assignee=row.assigned_to,
                ))

        if not type or type == "reply":
            result = await session.execute(text("""
                SELECT ot.id, ot.campaign_id, c.name AS campaign_name,
                       COALESCE(cl.name, 'Unknown') AS customer_name,
                       ot.replied_at
                FROM outreach_threads ot
                JOIN backlink_campaigns c ON ot.campaign_id = c.id
                LEFT JOIN clients cl ON c.client_id = cl.id
                WHERE ot.tenant_id = :tid AND ot.status::text = 'replied'
                  AND (ot.replied_at IS NOT NULL)
                ORDER BY ot.replied_at DESC
                LIMIT :lim
            """), {"tid": str(tenant_id), "lim": limit})
            rows = result.fetchall()
            for row in rows:
                age_hours = (now - row.replied_at).total_seconds() / 3600 if row.replied_at else 0
                priority = max(10, 90 - int(age_hours))
                queue.append(QueueItem(
                    id=str(row.id), campaign_id=str(row.campaign_id),
                    campaign_name=row.campaign_name, customer_name=row.customer_name,
                    type="reply", priority=priority,
                    summary=f"New reply received {int(age_hours)}h ago",
                    created_at=row.replied_at.isoformat() if row.replied_at else "",
                    assignee=None,
                ))

        if not type or type == "failed_send":
            result = await session.execute(text("""
                SELECT ot.id, ot.campaign_id, c.name AS campaign_name,
                       COALESCE(cl.name, 'Unknown') AS customer_name,
                       ot.updated_at
                FROM outreach_threads ot
                JOIN backlink_campaigns c ON ot.campaign_id = c.id
                LEFT JOIN clients cl ON c.client_id = cl.id
                WHERE ot.tenant_id = :tid AND ot.status::text = 'bounced'
                ORDER BY ot.updated_at DESC
                LIMIT :lim
            """), {"tid": str(tenant_id), "lim": limit})
            rows = result.fetchall()
            for row in rows:
                priority = 80
                queue.append(QueueItem(
                    id=str(row.id), campaign_id=str(row.campaign_id),
                    campaign_name=row.campaign_name, customer_name=row.customer_name,
                    type="failed_send", priority=priority,
                    summary="Email bounced — review recipient address",
                    created_at=row.updated_at.isoformat() if row.updated_at else "",
                    assignee=None,
                ))

        if not type or type == "link_issue":
            result = await session.execute(text("""
                SELECT al.id, al.campaign_id, c.name AS campaign_name,
                       COALESCE(cl.name, 'Unknown') AS customer_name,
                       al.last_checked_at
                FROM acquired_links al
                JOIN backlink_campaigns c ON al.campaign_id = c.id
                LEFT JOIN clients cl ON c.client_id = cl.id
                WHERE al.tenant_id = :tid AND al.status::text IN ('removed','broken')
                ORDER BY al.last_checked_at DESC
                LIMIT :lim
            """), {"tid": str(tenant_id), "lim": limit})
            rows = result.fetchall()
            for row in rows:
                priority = 70
                queue.append(QueueItem(
                    id=str(row.id), campaign_id=str(row.campaign_id),
                    campaign_name=row.campaign_name, customer_name=row.customer_name,
                    type="link_issue", priority=priority,
                    summary="Acquired link removed or broken — investigate",
                    created_at=row.last_checked_at.isoformat() if row.last_checked_at else "",
                    assignee=None,
                ))

        queue.sort(key=lambda x: -x.priority)
        return queue[:limit]


# ── Bulk Operations ─────────────────────────────────────

class BulkAction(BaseModel):
    campaign_ids: list[str]
    action: str = Field(..., pattern="^(pause|resume|archive|assign|add_tag|remove_tag)$")
    value: str = ""


@router.post("/bulk")
async def bulk_operation(
    tenant_id: UUID = Depends(get_validated_tenant_id),
    action: BulkAction = None,
):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    if not action:
        raise HTTPException(status_code=400, detail="Action data required")

    async with get_session() as session:
        ids_placeholder = ",".join(f"'{cid}'" for cid in action.campaign_ids)
        now = datetime.now(timezone.utc)
        tid = str(tenant_id)

        if action.action == "pause":
            await session.execute(text(f"""
                UPDATE backlink_campaigns SET status = 'paused', updated_at = :now
                WHERE id IN ({ids_placeholder}) AND tenant_id = :tid
            """), {"now": now, "tid": tid})

        elif action.action == "resume":
            await session.execute(text(f"""
                UPDATE backlink_campaigns SET status = 'active', updated_at = :now
                WHERE id IN ({ids_placeholder}) AND tenant_id = :tid
            """), {"now": now, "tid": tid})

        elif action.action == "archive":
            await session.execute(text(f"""
                UPDATE backlink_campaigns SET status = 'complete', updated_at = :now
                WHERE id IN ({ids_placeholder}) AND tenant_id = :tid
            """), {"now": now, "tid": tid})

        elif action.action == "assign":
            await session.execute(text(f"""
                UPDATE backlink_campaigns
                SET config = jsonb_set(COALESCE(config, '{{}}'::jsonb), '{{assigned_manager}}', CAST(:val AS jsonb)),
                    updated_at = :now
                WHERE id IN ({ids_placeholder}) AND tenant_id = :tid
            """), {"val": json.dumps(action.value), "now": now, "tid": tid})

        elif action.action == "add_tag":
            await session.execute(text(f"""
                UPDATE backlink_campaigns
                SET config = jsonb_set(
                    COALESCE(config, '{{}}'::jsonb), '{{tags}}',
                    COALESCE((config->>'tags')::jsonb || CAST(:tag AS jsonb), CAST(:tag AS jsonb))
                ), updated_at = :now
                WHERE id IN ({ids_placeholder}) AND tenant_id = :tid
            """), {"tag": json.dumps(action.value), "now": now, "tid": tid})

        elif action.action == "remove_tag":
            await session.execute(text(f"""
                UPDATE backlink_campaigns
                SET config = jsonb_set(
                    COALESCE(config, '{{}}'::jsonb), '{{tags}}',
                    COALESCE(
                        (SELECT jsonb_agg(t) FROM jsonb_array_elements_text(
                            CASE WHEN jsonb_typeof(config->'tags') = 'array' THEN config->'tags'
                                 WHEN jsonb_typeof(config->'tags') = 'string' THEN to_jsonb(ARRAY[config->>'tags'])
                                 ELSE '[]'::jsonb
                            END
                        ) t WHERE t != CAST(:tag AS text)),
                        '[]'::jsonb
                    ), true
                ), updated_at = :now
                WHERE id IN ({ids_placeholder}) AND tenant_id = :tid
            """), {"tag": action.value, "now": now, "tid": tid})

        await session.commit()
        return {"success": True, "message": f"Bulk {action.action} applied to {len(action.campaign_ids)} campaigns"}


# ── Saved Views ─────────────────────────────────────────

@router.get("/views", response_model=list[SavedView])
async def list_saved_views(
    tenant_id: UUID = Depends(get_validated_tenant_id),
):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        result = await session.execute(text("""
            SELECT id, name, filters, created_at, updated_at
            FROM campaign_saved_views
            WHERE tenant_id = :tid
            ORDER BY created_at DESC
        """), {"tid": str(tenant_id)})
        return [
            SavedView(
                id=str(row.id), name=row.name,
                filters=json.loads(row.filters) if isinstance(row.filters, str) else (row.filters or {}),
                created_at=row.created_at.isoformat() if row.created_at else "",
                updated_at=row.updated_at.isoformat() if row.updated_at else "",
            )
            for row in result.fetchall()
        ]


@router.post("/views", response_model=SavedView)
async def create_saved_view(
    tenant_id: UUID = Depends(get_validated_tenant_id),
    name: str = Query(...),
    filters: str = Query(default="{}"),
):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        result = await session.execute(text("""
            INSERT INTO campaign_saved_views (tenant_id, name, filters, created_at, updated_at)
            VALUES (:tid, :name, CAST(:filters AS jsonb), :now, :now)
            RETURNING id, name, filters, created_at, updated_at
        """), {
            "tid": str(tenant_id), "name": name,
            "filters": filters, "now": datetime.now(timezone.utc),
        })
        row = result.first()
        await session.commit()
        return SavedView(
            id=str(row.id), name=row.name,
            filters=json.loads(row.filters) if isinstance(row.filters, str) else (row.filters or {}),
            created_at=row.created_at.isoformat() if row.created_at else "",
            updated_at=row.updated_at.isoformat() if row.updated_at else "",
        )


@router.put("/views/{view_id}", response_model=SavedView)
async def update_saved_view(
    view_id: str,
    tenant_id: UUID = Depends(get_validated_tenant_id),
    name: str = Query(default=""),
    filters: str = Query(default=""),
):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        sets = ["updated_at = :now"]
        params: dict = {"view_id": view_id, "tid": str(tenant_id), "now": datetime.now(timezone.utc)}
        if name:
            sets.append("name = :name")
            params["name"] = name
        if filters:
            sets.append("filters = CAST(:filters AS jsonb)")
            params["filters"] = filters

        result = await session.execute(text(f"""
            UPDATE campaign_saved_views SET {', '.join(sets)}
            WHERE id = :view_id AND tenant_id = :tid
            RETURNING id, name, filters, created_at, updated_at
        """), params)
        row = result.first()
        if not row:
            raise HTTPException(status_code=404, detail="Saved view not found")
        await session.commit()
        return SavedView(
            id=str(row.id), name=row.name,
            filters=json.loads(row.filters) if isinstance(row.filters, str) else (row.filters or {}),
            created_at=row.created_at.isoformat() if row.created_at else "",
            updated_at=row.updated_at.isoformat() if row.updated_at else "",
        )


@router.delete("/views/{view_id}")
async def delete_saved_view(
    view_id: str,
    tenant_id: UUID = Depends(get_validated_tenant_id),
):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        result = await session.execute(text("""
            DELETE FROM campaign_saved_views
            WHERE id = :view_id AND tenant_id = :tid
        """), {"view_id": view_id, "tid": str(tenant_id)})
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Saved view not found")
        await session.commit()
        return {"success": True, "message": "Saved view deleted"}
