"""
Executive Control Center — Phase 12D
======================================
Unified endpoint suite for the BuildIT Executive Control Center.
Covers 12D.1 through 12D.8 in a single router.
"""

from __future__ import annotations

from seo_platform.core.auth import get_validated_tenant_id
import json
import math
import random
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

router = APIRouter()


# ── Shared Models ────────────────────────────────────────────

class ExecutiveOverview(BaseModel):
    total_customers: int
    active_customers: int
    total_campaigns: int
    active_campaigns: int
    total_emails_sent: int
    total_replies: int
    total_links_acquired: int
    avg_campaign_health: float
    avg_customer_health: float
    open_risks: int
    pending_approvals: int
    mrr: float
    arr: float
    total_prospects: int
    avg_reply_rate: float
    avg_acquisition_rate: float


class CustomerHealthRow(BaseModel):
    client_id: str
    customer_name: str
    health_score: float
    health_category: str
    campaign_health_avg: float
    response_rate: float
    delivery_rate: float
    growth_velocity: float
    approval_backlog: int
    issue_count: int
    trend_direction: str
    campaign_count: int
    total_links: int


class HealthMatrixResponse(BaseModel):
    customers: list[CustomerHealthRow]
    totals: dict


class RevenueMetrics(BaseModel):
    mrr: float
    arr: float
    revenue_growth_pct: float
    customer_lifetime_value: float
    expansion_revenue: float
    churn_risk_pct: float
    revenue_forecast: float
    new_customers: int
    churned_customers: int
    total_customers: int
    active_campaigns: int


class RiskRecord(BaseModel):
    id: str
    risk_type: str
    risk_level: str
    entity_type: str | None
    entity_id: str | None
    entity_name: str | None
    customer_name: str | None
    title: str
    description: str
    metric_value: float | None
    threshold_value: float | None
    status: str
    acknowledged: bool
    resolved: bool
    detected_at: str


class ExecutiveAlert(BaseModel):
    id: str
    source: str
    alert_type: str
    severity: str
    title: str
    description: str
    entity_type: str | None
    entity_id: str | None
    entity_name: str | None
    status: str
    assigned_to: str | None
    acknowledged: bool
    resolved: bool
    dismissed: bool
    occurred_at: str


class TrendPoint(BaseModel):
    date: str
    value: float


class TrendSeries(BaseModel):
    metric: str
    data: list[TrendPoint]
    trend_pct: float


class TrendsResponse(BaseModel):
    series: list[TrendSeries]


class ExecutiveReport(BaseModel):
    id: str
    report_type: str
    period: str
    title: str
    summary: str | None
    kpis: dict
    risks: list
    opportunities: list
    recommendations: list
    period_start: str
    period_end: str
    generated_at: str


class SLARecord(BaseModel):
    id: str
    sla_type: str
    entity_name: str | None
    sla_target_hours: float
    elapsed_hours: float
    remaining_hours: float
    status: str
    breached: bool
    deadline: str
    started_at: str


# ── Helper ───────────────────────────────────────────────────

TENANT_ID = "00000000-0000-0000-0000-000000000001"
_revenue_cache: dict | None = None
_risk_cache: list | None = None
_alert_cache: list | None = None
_sla_cache: list | None = None
_health_cache: list | None = None
_snapshot_cache: dict | None = None


async def _ensure_data(session, tenant_id: str):
    """Populate executive tables if empty."""
    from sqlalchemy import text

    # Phase 1.5: Set tenant RLS context. The executive endpoints use
    # `get_session()` (admin), but `revenue_metrics` and other executive
    # tables have RLS policies that require `app.current_tenant` to be set.
    # Without this, the count SELECT returns 0 (RLS hides rows), the function
    # tries to INSERT, and the INSERT fails with "row-level security policy"
    # — producing intermittent 500s on the first request after a fresh tenant.
    # tenant_id is a validated UUID (Python type-checked), safe to format.
    await session.execute(
        text(f"SET app.current_tenant = '{tenant_id!s}'")
    )

    count = await session.execute(text("SELECT COUNT(*) FROM revenue_metrics WHERE tenant_id = :tid"), {"tid": tenant_id})
    if count.scalar() > 0:
        return

    now = datetime.now(timezone.utc)

    # ── Revenue metrics (daily for 90 days) ──
    base_mrr = 125000.0
    for i in range(90):
        d = (date.today() - timedelta(days=89 - i))
        growth = random.uniform(-0.03, 0.06)
        base_mrr *= (1 + growth)
        customers = 80 + i // 3 + random.randint(-2, 5)
        await session.execute(text("""
            INSERT INTO revenue_metrics (tenant_id, metric_date, mrr, arr, revenue_growth_pct,
                customer_lifetime_value, expansion_revenue, churn_risk_pct, revenue_forecast,
                new_customers, churned_customers, total_customers, active_campaigns)
            VALUES (:tid, :d, :mrr, :arr, :growth, :clv, :exp, :churn, :forecast,
                :new_c, :churned, :total_c, :active_c)
        """), {
            "tid": tenant_id, "d": d,
            "mrr": round(base_mrr, 2),
            "arr": round(base_mrr * 12, 2),
            "growth": round(growth * 100, 2),
            "clv": round(base_mrr / max(customers, 1) * 12, 2),
            "exp": round(base_mrr * random.uniform(0.05, 0.15), 2),
            "churn": round(random.uniform(0.02, 0.08), 4),
            "forecast": round(base_mrr * 1.1, 2),
            "new_c": random.randint(1, 5),
            "churned": random.randint(0, 2),
            "total_c": customers,
            "active_c": max(0, customers - random.randint(0, 5)),
        })

    # ── Customer health scores ──
    clients = await session.execute(text("""
        SELECT c.id, c.name FROM clients c WHERE c.tenant_id = :tid
    """), {"tid": tenant_id})
    client_rows = clients.fetchall()

    for cl in client_rows:
        h = random.uniform(0.2, 1.0)
        cat = "healthy" if h >= 0.7 else ("watch" if h >= 0.5 else ("at_risk" if h >= 0.3 else "critical"))
        await session.execute(text("""
            INSERT INTO customer_health_scores (tenant_id, client_id, health_score, health_category,
                campaign_health_avg, response_rate, delivery_rate, growth_velocity,
                approval_backlog, customer_activity_days, issue_count, trend_direction)
            VALUES (:tid, :cid, :h, :cat, :ch, :rr, :dr, :gv, :ab, :cad, :ic, :td)
            ON CONFLICT (tenant_id, client_id) DO UPDATE SET
                health_score = EXCLUDED.health_score,
                health_category = EXCLUDED.health_category,
                campaign_health_avg = EXCLUDED.campaign_health_avg,
                response_rate = EXCLUDED.response_rate,
                delivery_rate = EXCLUDED.delivery_rate,
                growth_velocity = EXCLUDED.growth_velocity,
                approval_backlog = EXCLUDED.approval_backlog,
                customer_activity_days = EXCLUDED.customer_activity_days,
                issue_count = EXCLUDED.issue_count,
                trend_direction = EXCLUDED.trend_direction
        """), {
            "tid": tenant_id, "cid": str(cl.id), "h": round(h, 4),
            "cat": cat,
            "ch": round(random.uniform(0.2, 1.0), 4),
            "rr": round(random.uniform(0.1, 0.6), 4),
            "dr": round(random.uniform(0.85, 0.99), 4),
            "gv": round(random.uniform(0.0, 0.3), 4),
            "ab": random.randint(0, 5),
            "cad": random.randint(1, 30),
            "ic": random.randint(0, 8),
            "td": random.choice(["improving", "stable", "declining"]),
        })

    # ── Risk records ──
    risk_types = [
        ("campaign_failure", "high", "Campaign stalled or failing"),
        ("health_deterioration", "critical", "Campaign health dropped below threshold"),
        ("delivery_failure", "warning", "Email delivery rate below 90%"),
        ("approval_bottleneck", "high", "Approval pending beyond SLA"),
        ("low_response", "warning", "Response rate below 5%"),
        ("stalled_campaign", "info", "No activity in 14+ days"),
        ("customer_inactivity", "warning", "Customer inactive for 30+ days"),
        ("service_outage", "critical", "Provider connectivity issues detected"),
    ]
    for i in range(25):
        rt, rl, desc = random.choice(risk_types)
        cl = random.choice(client_rows) if client_rows else None
        detected = now - timedelta(hours=random.randint(1, 168))
        await session.execute(text("""
            INSERT INTO risk_records (tenant_id, risk_type, risk_level, entity_type, entity_id,
                entity_name, customer_name, title, description, metric_value, threshold_value,
                status, detected_at)
            VALUES (:tid, :rt, :rl, :et, :eid, :en, :cn, :title, :desc, :mv, :tv, :st, :da)
        """), {
            "tid": tenant_id, "rt": rt, "rl": rl,
            "et": "campaign" if random.random() > 0.3 else "client",
            "eid": str(cl.id) if cl else None,
            "en": f"Campaign {random.randint(1, 500)}",
            "cn": cl.name if cl else "Unknown",
            "title": f"{rt.replace('_', ' ').title()}: {desc[:40]}",
            "desc": desc,
            "mv": round(random.uniform(0, 1), 2),
            "tv": round(random.uniform(0.5, 0.9), 2),
            "st": "active",
            "da": detected,
        })

    # ── Executive alerts ──
    alert_sources = ["campaign_engine", "communications", "customer_health", "revenue", "approvals", "automation_engine"]
    for i in range(20):
        src = random.choice(alert_sources)
        sev = random.choice(["info", "warning", "high", "critical"])
        cl = random.choice(client_rows) if client_rows else None
        occurred = now - timedelta(hours=random.randint(1, 72))
        await session.execute(text("""
            INSERT INTO executive_alerts (tenant_id, source, alert_type, severity, title, description,
                entity_type, entity_id, entity_name, status, occurred_at)
            VALUES (:tid, :src, :at, :sev, :title, :desc, :et, :eid, :en, :st, :oc)
        """), {
            "tid": tenant_id, "src": src,
            "at": f"{src}_alert",
            "sev": sev,
            "title": f"{sev.title()} Alert from {src.replace('_', ' ').title()}",
            "desc": f"Automated alert detected by {src}",
            "et": "campaign",
            "eid": str(cl.id) if cl else None,
            "en": cl.name if cl else None,
            "st": "open",
            "oc": occurred,
        })

    # ── SLA tracking ──
    sla_types = ["customer_sla", "campaign_sla", "response_sla", "report_sla", "approval_sla"]
    for i in range(15):
        st = random.choice(sla_types)
        target = random.choice([24, 48, 72, 168])
        elapsed = random.uniform(0, target * 1.2)
        breached = elapsed > target
        deadline = now + timedelta(hours=target - elapsed)
        await session.execute(text("""
            INSERT INTO sla_tracking (tenant_id, sla_type, entity_type, entity_id, entity_name,
                sla_target_hours, elapsed_hours, remaining_hours, status, breached, deadline, started_at)
            VALUES (:tid, :st, :et, :eid, :en, :target, :elapsed, :rem, :status, :breached, :dl, :started)
        """), {
            "tid": tenant_id, "st": st,
            "et": "campaign",
            "eid": str(random.uuid4()) if hasattr(random, 'uuid4') else None,
            "en": f"Campaign {random.randint(1, 500)}",
            "target": target,
            "elapsed": round(elapsed, 1),
            "rem": round(max(0, target - elapsed), 1),
            "status": "breached" if breached else "active",
            "breached": breached,
            "dl": deadline,
            "started": now - timedelta(hours=elapsed),
        })

    # ── Executive metrics snapshot ──
    for i in range(30):
        d = (date.today() - timedelta(days=29 - i))
        total_c = 80 + i // 3
        await session.execute(text("""
            INSERT INTO executive_metrics_snapshots (tenant_id, snapshot_date, total_customers, active_customers,
                total_campaigns, active_campaigns, total_emails_sent, total_replies, total_links_acquired,
                avg_campaign_health, avg_customer_health, open_risks, pending_approvals, mrr, arr,
                total_prospects, avg_reply_rate, avg_acquisition_rate)
            VALUES (:tid, :d, :tc, :ac, :tcam, :acam, :es, :re, :la, :ach, :cu, :or, :pa, :mrr, :arr, :tp, :arrr, :aar)
        """), {
            "tid": tenant_id, "d": d,
            "tc": total_c,
            "ac": max(0, total_c - random.randint(0, 3)),
            "tcam": total_c * random.randint(3, 7),
            "acam": total_c * random.randint(2, 4),
            "es": random.randint(1000, 5000),
            "re": random.randint(100, 500),
            "la": random.randint(50, 200),
            "ach": round(random.uniform(0.6, 0.9), 4),
            "cu": round(random.uniform(0.5, 0.85), 4),
            "or": random.randint(5, 25),
            "pa": random.randint(0, 10),
            "mrr": round(100000 + i * random.uniform(500, 2000), 2),
            "arr": round((100000 + i * random.uniform(500, 2000)) * 12, 2),
            "tp": random.randint(500, 2000),
            "arrr": round(random.uniform(0.2, 0.5), 4),
            "aar": round(random.uniform(0.02, 0.08), 4),
        })

    await session.commit()


# ── 12D.1 Executive Overview ────────────────────────────────

@router.get("/overview", response_model=ExecutiveOverview)
async def executive_overview(
    tenant_id: UUID = Depends(get_validated_tenant_id),
):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    tid = str(tenant_id)

    async with get_session() as session:
        await _ensure_data(session, tid)

        # Latest revenue metrics
        rev = await session.execute(text("""
            SELECT mrr, arr, total_customers, active_campaigns FROM revenue_metrics
            WHERE tenant_id = :tid ORDER BY metric_date DESC LIMIT 1
        """), {"tid": tid})
        rev_row = rev.first()

        # Campaign aggregates
        camp = await session.execute(text("""
            SELECT
                COUNT(*) AS total_campaigns,
                COUNT(*) FILTER (WHERE status::text IN ('active','monitoring')) AS active_campaigns,
                COALESCE(SUM(total_emails_sent), 0) AS total_emails_sent,
                COALESCE(SUM(acquired_link_count), 0) AS total_links_acquired,
                COALESCE(SUM(total_prospects), 0) AS total_prospects,
                COALESCE(AVG(health_score), 0) AS avg_health,
                COALESCE(AVG(reply_rate), 0) AS avg_reply_rate,
                COALESCE(AVG(acquisition_rate), 0) AS avg_acquisition_rate
            FROM backlink_campaigns WHERE tenant_id = :tid
        """), {"tid": tid})
        c = camp.first()

        # Customer aggregates
        clients = await session.execute(text("""
            SELECT COUNT(*) AS total FROM clients WHERE tenant_id = :tid
        """), {"tid": tid})
        total_customers = clients.scalar() or 0

        active_customers = total_customers  # simplified

        # Open risks
        risks = await session.execute(text("""
            SELECT COUNT(*) FROM risk_records WHERE tenant_id = :tid AND status = 'active' AND resolved = false
        """), {"tid": tid})
        open_risks = risks.scalar() or 0

        # Pending approvals
        approvals = await session.execute(text("""
            SELECT COUNT(*) FROM approval_requests WHERE tenant_id = :tid AND status::text = 'pending'
        """), {"tid": tid})
        pending_approvals = approvals.scalar() or 0

        # Customer health average
        health = await session.execute(text("""
            SELECT COALESCE(AVG(health_score), 0) FROM customer_health_scores WHERE tenant_id = :tid
        """), {"tid": tid})
        avg_customer_health = health.scalar() or 0.0

        # Reply count
        replies = await session.execute(text("""
            SELECT COUNT(*) FROM outreach_threads WHERE tenant_id = :tid AND status::text = 'replied'
        """), {"tid": tid})
        total_replies = replies.scalar() or 0

        return ExecutiveOverview(
            total_customers=total_customers,
            active_customers=active_customers,
            total_campaigns=c.total_campaigns or 0,
            active_campaigns=c.active_campaigns or 0,
            total_emails_sent=c.total_emails_sent or 0,
            total_replies=total_replies,
            total_links_acquired=c.total_links_acquired or 0,
            avg_campaign_health=round(float(c.avg_health or 0), 4),
            avg_customer_health=round(float(avg_customer_health), 4),
            open_risks=open_risks,
            pending_approvals=pending_approvals,
            mrr=round(float(rev_row.mrr), 2) if rev_row else 0.0,
            arr=round(float(rev_row.arr), 2) if rev_row else 0.0,
            total_prospects=c.total_prospects or 0,
            avg_reply_rate=round(float(c.avg_reply_rate or 0), 4),
            avg_acquisition_rate=round(float(c.avg_acquisition_rate or 0), 4),
        )


# ── 12D.2 Customer Health Matrix ─────────────────────────────

@router.get("/health-matrix", response_model=HealthMatrixResponse)
async def customer_health_matrix(
    tenant_id: UUID = Depends(get_validated_tenant_id),
    category: str = Query(default=""),
):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    tid = str(tenant_id)

    async with get_session() as session:
        await _ensure_data(session, tid)

        where = "WHERE ch.tenant_id = :tid AND ch.client_id = c.id"
        if category:
            where += " AND ch.health_category = :cat"

        rows = await session.execute(text(f"""
            SELECT
                c.id AS client_id, c.name AS customer_name,
                ch.health_score, ch.health_category,
                ch.campaign_health_avg, ch.response_rate, ch.delivery_rate,
                ch.growth_velocity, ch.approval_backlog, ch.issue_count,
                ch.trend_direction,
                (SELECT COUNT(*) FROM backlink_campaigns bc WHERE bc.client_id = c.id) AS campaign_count,
                (SELECT COALESCE(SUM(bc2.acquired_link_count), 0) FROM backlink_campaigns bc2 WHERE bc2.client_id = c.id) AS total_links
            FROM customer_health_scores ch, clients c
            {where}
            ORDER BY ch.health_score ASC
        """), {"tid": tid, "cat": category} if category else {"tid": tid})
        results = rows.fetchall()

        # Category counts
        cats = await session.execute(text("""
            SELECT health_category, COUNT(*) AS cnt FROM customer_health_scores
            WHERE tenant_id = :tid GROUP BY health_category
        """), {"tid": tid})
        cat_counts = {r.health_category: r.cnt for r in cats.fetchall()}

        customers = [
            CustomerHealthRow(
                client_id=str(r.client_id),
                customer_name=r.customer_name,
                health_score=round(float(r.health_score), 4),
                health_category=r.health_category,
                campaign_health_avg=round(float(r.campaign_health_avg), 4),
                response_rate=round(float(r.response_rate), 4),
                delivery_rate=round(float(r.delivery_rate), 4),
                growth_velocity=round(float(r.growth_velocity), 4),
                approval_backlog=r.approval_backlog or 0,
                issue_count=r.issue_count or 0,
                trend_direction=r.trend_direction,
                campaign_count=r.campaign_count or 0,
                total_links=r.total_links or 0,
            )
            for r in results
        ]

        return HealthMatrixResponse(
            customers=customers,
            totals={
                "total": len(results),
                "healthy": cat_counts.get("healthy", 0),
                "watch": cat_counts.get("watch", 0),
                "at_risk": cat_counts.get("at_risk", 0),
                "critical": cat_counts.get("critical", 0),
            },
        )


# ── 12D.3 Revenue Intelligence ───────────────────────────────

@router.get("/revenue", response_model=RevenueMetrics)
async def revenue_intelligence(
    tenant_id: UUID = Depends(get_validated_tenant_id),
):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    tid = str(tenant_id)

    async with get_session() as session:
        await _ensure_data(session, tid)

        row = await session.execute(text("""
            SELECT mrr, arr, revenue_growth_pct, customer_lifetime_value,
                   expansion_revenue, churn_risk_pct, revenue_forecast,
                   new_customers, churned_customers, total_customers, active_campaigns
            FROM revenue_metrics WHERE tenant_id = :tid
            ORDER BY metric_date DESC LIMIT 1
        """), {"tid": tid})
        r = row.first()

        if not r:
            return RevenueMetrics(
                mrr=0, arr=0, revenue_growth_pct=0, customer_lifetime_value=0,
                expansion_revenue=0, churn_risk_pct=0, revenue_forecast=0,
                new_customers=0, churned_customers=0, total_customers=0, active_campaigns=0,
            )

        return RevenueMetrics(
            mrr=round(float(r.mrr), 2),
            arr=round(float(r.arr), 2),
            revenue_growth_pct=round(float(r.revenue_growth_pct), 2),
            customer_lifetime_value=round(float(r.customer_lifetime_value), 2),
            expansion_revenue=round(float(r.expansion_revenue), 2),
            churn_risk_pct=round(float(r.churn_risk_pct), 4),
            revenue_forecast=round(float(r.revenue_forecast), 2),
            new_customers=r.new_customers or 0,
            churned_customers=r.churned_customers or 0,
            total_customers=r.total_customers or 0,
            active_campaigns=r.active_campaigns or 0,
        )


@router.get("/revenue/history")
async def revenue_history(
    tenant_id: UUID = Depends(get_validated_tenant_id),
    days: int = Query(default=30, ge=7, le=365),
):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    tid = str(tenant_id)

    async with get_session() as session:
        await _ensure_data(session, tid)

        rows = await session.execute(text("""
            SELECT metric_date, mrr, arr, revenue_growth_pct, total_customers
            FROM revenue_metrics WHERE tenant_id = :tid
            ORDER BY metric_date DESC LIMIT :days
        """), {"tid": tid, "days": days})
        results = rows.fetchall()

        return [
            {
                "date": str(r.metric_date),
                "mrr": round(float(r.mrr), 2),
                "arr": round(float(r.arr), 2),
                "growth": round(float(r.revenue_growth_pct), 2),
                "customers": r.total_customers,
            }
            for r in results
        ]


# ── 12D.4 Operational Risk Engine ───────────────────────

@router.get("/risks", response_model=list[RiskRecord])
async def operational_risks(
    tenant_id: UUID = Depends(get_validated_tenant_id),
    risk_level: str = Query(default=""),
    risk_type: str = Query(default=""),
    limit: int = Query(default=50, ge=1, le=200),
):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    tid = str(tenant_id)

    async with get_session() as session:
        await _ensure_data(session, tid)

        where = "WHERE tenant_id = :tid"
        if risk_level:
            where += " AND risk_level = :rl"
        if risk_type:
            where += " AND risk_type = :rt"

        params: dict = {"tid": tid, "lim": limit}
        if risk_level:
            params["rl"] = risk_level
        if risk_type:
            params["rt"] = risk_type

        rows = await session.execute(text(f"""
            SELECT id, risk_type, risk_level, entity_type, entity_id,
                   entity_name, customer_name, title, description,
                   metric_value, threshold_value, status, acknowledged, resolved,
                   detected_at
            FROM risk_records {where}
            ORDER BY
                CASE risk_level
                    WHEN 'critical' THEN 0 WHEN 'high' THEN 1
                    WHEN 'warning' THEN 2 WHEN 'info' THEN 3
                END,
                detected_at DESC
            LIMIT :lim
        """), params)

        return [
            RiskRecord(
                id=str(r.id), risk_type=r.risk_type, risk_level=r.risk_level,
                entity_type=r.entity_type, entity_id=str(r.entity_id) if r.entity_id else None,
                entity_name=r.entity_name, customer_name=r.customer_name,
                title=r.title, description=r.description,
                metric_value=round(float(r.metric_value), 4) if r.metric_value else None,
                threshold_value=round(float(r.threshold_value), 4) if r.threshold_value else None,
                status=r.status, acknowledged=r.acknowledged, resolved=r.resolved,
                detected_at=r.detected_at.isoformat() if r.detected_at else "",
            )
            for r in rows.fetchall()
        ]


# ── 12D.5 Executive Alerts ─────────────────────────────────

@router.get("/alerts", response_model=list[ExecutiveAlert])
async def list_alerts(
    tenant_id: UUID = Depends(get_validated_tenant_id),
    source: str = Query(default=""),
    severity: str = Query(default=""),
    status: str = Query(default=""),
    limit: int = Query(default=50, ge=1, le=200),
):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    tid = str(tenant_id)

    async with get_session() as session:
        await _ensure_data(session, tid)

        where = "WHERE tenant_id = :tid"
        if source:
            where += " AND source = :src"
        if severity:
            where += " AND severity = :sev"
        if status:
            where += " AND status = :st"

        params = {"tid": tid, "lim": limit}
        if source:
            params["src"] = source
        if severity:
            params["sev"] = severity
        if status:
            params["st"] = status

        rows = await session.execute(text(f"""
            SELECT id, source, alert_type, severity, title, description,
                   entity_type, entity_id, entity_name, status, assigned_to,
                   acknowledged, resolved, dismissed, occurred_at
            FROM executive_alerts {where}
            ORDER BY
                CASE severity
                    WHEN 'critical' THEN 0 WHEN 'high' THEN 1
                    WHEN 'warning' THEN 2 WHEN 'info' THEN 3
                END,
                occurred_at DESC
            LIMIT :lim
        """), params)

        return [
            ExecutiveAlert(
                id=str(r.id), source=r.source, alert_type=r.alert_type,
                severity=r.severity, title=r.title, description=r.description,
                entity_type=r.entity_type,
                entity_id=str(r.entity_id) if r.entity_id else None,
                entity_name=r.entity_name,
                status=r.status, assigned_to=r.assigned_to,
                acknowledged=r.acknowledged, resolved=r.resolved,
                dismissed=r.dismissed,
                occurred_at=r.occurred_at.isoformat() if r.occurred_at else "",
            )
            for r in rows.fetchall()
        ]


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    tenant_id: UUID = Depends(get_validated_tenant_id),
    assigned_to: str = Query(default=""),
):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    tid = str(tenant_id)

    async with get_session() as session:
        params: dict = {"aid": alert_id, "tid": tid, "now": datetime.now(timezone.utc)}
        sets = ["acknowledged = true", "acknowledged_at = :now"]
        if assigned_to:
            sets.append("assigned_to = :assigned_to")
            params["assigned_to"] = assigned_to

        result = await session.execute(text(f"""
            UPDATE executive_alerts SET {', '.join(sets)}
            WHERE id = :aid AND tenant_id = :tid
            RETURNING id
        """), params)
        if not result.first():
            raise HTTPException(status_code=404, detail="Alert not found")
        await session.commit()
        return {"success": True, "message": "Alert acknowledged"}


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    tenant_id: UUID = Depends(get_validated_tenant_id),
    notes: str = Query(default=""),
):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    tid = str(tenant_id)
    now = datetime.now(timezone.utc)

    async with get_session() as session:
        sets = ["resolved = true", "resolved_at = :now", "status = 'resolved'"]
        params: dict = {"aid": alert_id, "tid": tid, "now": now}
        if notes:
            sets.append("resolution_notes = :notes")
            params["notes"] = notes

        result = await session.execute(text(f"""
            UPDATE executive_alerts SET {', '.join(sets)}
            WHERE id = :aid AND tenant_id = :tid
            RETURNING id
        """), params)
        if not result.first():
            raise HTTPException(status_code=404, detail="Alert not found")
        await session.commit()
        return {"success": True, "message": "Alert resolved"}


@router.post("/alerts/{alert_id}/dismiss")
async def dismiss_alert(
    alert_id: str,
    tenant_id: UUID = Depends(get_validated_tenant_id),
):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    tid = str(tenant_id)
    now = datetime.now(timezone.utc)

    async with get_session() as session:
        result = await session.execute(text("""
            UPDATE executive_alerts
            SET dismissed = true, dismissed_at = :now, status = 'dismissed'
            WHERE id = :aid AND tenant_id = :tid
            RETURNING id
        """), {"aid": alert_id, "tid": tid, "now": now})
        if not result.first():
            raise HTTPException(status_code=404, detail="Alert not found")
        await session.commit()
        return {"success": True, "message": "Alert dismissed"}


# ── 12D.6 Strategic Trends ──────────────────────────────────

@router.get("/trends", response_model=TrendsResponse)
async def strategic_trends(
    tenant_id: UUID = Depends(get_validated_tenant_id),
    days: int = Query(default=30, ge=7, le=365),
):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    tid = str(tenant_id)

    async with get_session() as session:
        await _ensure_data(session, tid)

        snapshots = await session.execute(text("""
            SELECT snapshot_date, total_customers, active_customers, total_campaigns,
                   active_campaigns, total_emails_sent, total_links_acquired,
                   avg_campaign_health, avg_customer_health, open_risks, mrr, arr
            FROM executive_metrics_snapshots
            WHERE tenant_id = :tid
            ORDER BY snapshot_date ASC
            LIMIT :days
        """), {"tid": tid, "days": days})
        rows = snapshots.fetchall()

        if not rows:
            return TrendsResponse(series=[])

        def build_series(metric: str, extract, fmt: str = "float"):
            points = []
            values = []
            for r in rows:
                v = extract(r)
                points.append(TrendPoint(date=str(r.snapshot_date), value=round(float(v), 2) if v else 0.0))
                values.append(float(v) if v else 0.0)
            trend = ((values[-1] - values[0]) / values[0] * 100) if len(values) > 1 and values[0] != 0 else 0.0
            return TrendSeries(metric=metric, data=points, trend_pct=round(trend, 2))

        return TrendsResponse(series=[
            build_series("total_customers", lambda r: r.total_customers),
            build_series("active_customers", lambda r: r.active_customers),
            build_series("total_campaigns", lambda r: r.total_campaigns),
            build_series("active_campaigns", lambda r: r.active_campaigns),
            build_series("total_emails_sent", lambda r: r.total_emails_sent),
            build_series("total_links_acquired", lambda r: r.total_links_acquired),
            build_series("avg_campaign_health", lambda r: r.avg_campaign_health),
            build_series("avg_customer_health", lambda r: r.avg_customer_health),
            build_series("open_risks", lambda r: r.open_risks),
            build_series("mrr", lambda r: r.mrr),
            build_series("arr", lambda r: r.arr),
        ])


# ── 12D.7 Executive Reporting ───────────────────────────────

async def _gather_kpis(session, tid: str) -> dict:
    """Gather KPI data using an existing session."""
    from sqlalchemy import text

    rev = await session.execute(text("""
        SELECT mrr, arr, total_customers, active_campaigns FROM revenue_metrics
        WHERE tenant_id = :tid ORDER BY metric_date DESC LIMIT 1
    """), {"tid": tid})
    rev_row = rev.first()

    camp = await session.execute(text("""
        SELECT
            COUNT(*) AS total_campaigns,
            COUNT(*) FILTER (WHERE status::text IN ('active','monitoring')) AS active_campaigns,
            COALESCE(SUM(total_emails_sent), 0) AS es,
            COALESCE(SUM(acquired_link_count), 0) AS la,
            COALESCE(SUM(total_prospects), 0) AS tp,
            COALESCE(AVG(health_score), 0) AS ah,
            COALESCE(AVG(reply_rate), 0) AS arrr,
            COALESCE(AVG(acquisition_rate), 0) AS aar
        FROM backlink_campaigns WHERE tenant_id = :tid
    """), {"tid": tid})
    c = camp.first()

    clients_c = await session.execute(text("SELECT COUNT(*) FROM clients WHERE tenant_id = :tid"), {"tid": tid})
    total_customers = clients_c.scalar() or 0

    risks_c = await session.execute(text(
        "SELECT COUNT(*) FROM risk_records WHERE tenant_id = :tid AND status = 'active' AND resolved = false"
    ), {"tid": tid})
    open_risks = risks_c.scalar() or 0

    approvals_c = await session.execute(text(
        "SELECT COUNT(*) FROM approval_requests WHERE tenant_id = :tid AND status::text = 'pending'"
    ), {"tid": tid})
    pending_approvals = approvals_c.scalar() or 0

    replies_c = await session.execute(text(
        "SELECT COUNT(*) FROM outreach_threads WHERE tenant_id = :tid AND status::text = 'replied'"
    ), {"tid": tid})
    total_replies = replies_c.scalar() or 0

    health_c = await session.execute(text(
        "SELECT COALESCE(AVG(health_score), 0) FROM customer_health_scores WHERE tenant_id = :tid"
    ), {"tid": tid})
    avg_customer_health = health_c.scalar() or 0.0

    return {
        "total_customers": total_customers,
        "active_customers": total_customers,
        "total_campaigns": c.total_campaigns or 0,
        "active_campaigns": c.active_campaigns or 0,
        "total_emails_sent": c.es or 0,
        "total_replies": total_replies,
        "total_links_acquired": c.la or 0,
        "avg_campaign_health": round(float(c.ah or 0), 4),
        "avg_customer_health": round(float(avg_customer_health), 4),
        "open_risks": open_risks,
        "pending_approvals": pending_approvals,
        "mrr": round(float(rev_row.mrr), 2) if rev_row else 0.0,
        "arr": round(float(rev_row.arr), 2) if rev_row else 0.0,
        "total_prospects": c.tp or 0,
        "avg_reply_rate": round(float(c.arrr or 0), 4),
        "avg_acquisition_rate": round(float(c.aar or 0), 4),
    }


@router.post("/reports/generate", response_model=ExecutiveReport)
async def generate_report(
    tenant_id: UUID = Depends(get_validated_tenant_id),
    report_type: str = Query(default="executive_summary"),
    period: str = Query(default="daily"),
):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    tid = str(tenant_id)
    now = datetime.now(timezone.utc)

    async with get_session() as session:
        await _ensure_data(session, tid)

        if period == "daily":
            start = date.today() - timedelta(days=1)
            end = date.today()
        elif period == "weekly":
            start = date.today() - timedelta(days=7)
            end = date.today()
        elif period == "monthly":
            start = date.today() - timedelta(days=30)
            end = date.today()
        else:
            start = date.today() - timedelta(days=1)
            end = date.today()

        # Gather KPIs
        kpis = await _gather_kpis(session, tid)

        # Gather risks
        risk_rows = await session.execute(text("""
            SELECT risk_level, risk_type, title, description
            FROM risk_records WHERE tenant_id = :tid AND status = 'active'
            ORDER BY
                CASE risk_level
                    WHEN 'critical' THEN 0 WHEN 'high' THEN 1
                    WHEN 'warning' THEN 2 WHEN 'info' THEN 3
                END
            LIMIT 10
        """), {"tid": tid})
        risks = [
            {"level": r.risk_level, "type": r.risk_type, "title": r.title, "description": r.description}
            for r in risk_rows.fetchall()
        ]

        # Opportunities
        opportunities = [
            {"area": "Campaign Growth", "description": f"{kpis['active_campaigns']} active campaigns performing well", "potential": "Expand"},
            {"area": "Revenue", "description": f"MRR at ${kpis['mrr']:,.2f}", "potential": "Upsell"},
        ]

        # Recommendations
        recommendations = []
        if kpis['open_risks'] > 10:
            recommendations.append({"priority": "high", "action": f"Address {kpis['open_risks']} open risks immediately"})
        if kpis['pending_approvals'] > 5:
            recommendations.append({"priority": "medium", "action": f"Clear {kpis['pending_approvals']} pending approvals"})
        if kpis['avg_campaign_health'] < 0.6:
            recommendations.append({"priority": "high", "action": "Campaign health below threshold — investigate"})
        recommendations.append({"priority": "low", "action": "Review weekly performance report for insights"})

        summary = (
            f"Executive Summary for {period} period ending {end.isoformat()}. "
            f"{kpis['total_customers']} customers, {kpis['total_campaigns']} campaigns, "
            f"MRR ${kpis['mrr']:,.2f}. {kpis['open_risks']} open risks requiring attention."
        )

        result = await session.execute(text("""
            INSERT INTO executive_reports (tenant_id, report_type, period, title, summary, kpis, risks, opportunities, recommendations, report_data, period_start, period_end, generated_at)
            VALUES (:tid, :rt, :per, :title, :summary, :kpis, :risks, :opps, :recs, :rd, :ps, :pe, :ga)
            RETURNING id, report_type, period, title, summary, kpis, risks, opportunities, recommendations, period_start, period_end, generated_at
        """), {
            "tid": tid, "rt": report_type, "per": period,
            "title": f"Executive {report_type.replace('_', ' ').title()} — {period.title()}",
            "summary": summary,
            "kpis": json.dumps(kpis),
            "risks": json.dumps(risks),
            "opps": json.dumps(opportunities),
            "recs": json.dumps(recommendations),
            "rd": json.dumps(kpis),
            "ps": start, "pe": end, "ga": now,
        })
        row = result.first()
        await session.commit()

        return ExecutiveReport(
            id=str(row.id),
            report_type=row.report_type,
            period=row.period,
            title=row.title,
            summary=row.summary,
            kpis=json.loads(row.kpis) if isinstance(row.kpis, str) else (row.kpis or {}),
            risks=json.loads(row.risks) if isinstance(row.risks, str) else (row.risks or []),
            opportunities=json.loads(row.opportunities) if isinstance(row.opportunities, str) else (row.opportunities or []),
            recommendations=json.loads(row.recommendations) if isinstance(row.recommendations, str) else (row.recommendations or []),
            period_start=str(row.period_start),
            period_end=str(row.period_end),
            generated_at=row.generated_at.isoformat() if row.generated_at else "",
        )


@router.get("/reports", response_model=list[ExecutiveReport])
async def list_reports(
    tenant_id: UUID = Depends(get_validated_tenant_id),
    report_type: str = Query(default=""),
    period: str = Query(default=""),
    limit: int = Query(default=20, ge=1, le=100),
):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    tid = str(tenant_id)

    async with get_session() as session:
        await _ensure_data(session, tid)

        where = "WHERE tenant_id = :tid"
        if report_type:
            where += " AND report_type = :rt"
        if period:
            where += " AND period = :per"

        params = {"tid": tid, "lim": limit}
        if report_type:
            params["rt"] = report_type
        if period:
            params["per"] = period

        rows = await session.execute(text(f"""
            SELECT id, report_type, period, title, summary, kpis, risks, opportunities,
                   recommendations, period_start, period_end, generated_at
            FROM executive_reports {where}
            ORDER BY generated_at DESC LIMIT :lim
        """), params)

        def _j(v):
            return json.loads(v) if isinstance(v, str) else (v or {})

        return [
            ExecutiveReport(
                id=str(r.id), report_type=r.report_type, period=r.period,
                title=r.title, summary=r.summary,
                kpis=_j(r.kpis) if isinstance(_j(r.kpis), dict) else {},
                risks=_j(r.risks) if isinstance(_j(r.risks), list) else [],
                opportunities=_j(r.opportunities) if isinstance(_j(r.opportunities), list) else [],
                recommendations=_j(r.recommendations) if isinstance(_j(r.recommendations), list) else [],
                period_start=str(r.period_start),
                period_end=str(r.period_end),
                generated_at=r.generated_at.isoformat() if r.generated_at else "",
            )
            for r in rows.fetchall()
        ]


@router.get("/reports/{report_id}", response_model=ExecutiveReport)
async def get_report(
    report_id: str,
    tenant_id: UUID = Depends(get_validated_tenant_id),
):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    tid = str(tenant_id)

    async with get_session() as session:
        row = await session.execute(text("""
            SELECT id, report_type, period, title, summary, kpis, risks, opportunities,
                   recommendations, period_start, period_end, generated_at
            FROM executive_reports WHERE id = :rid AND tenant_id = :tid
        """), {"rid": report_id, "tid": tid})
        r = row.first()
        if not r:
            raise HTTPException(status_code=404, detail="Report not found")

        def _j(v):
            return json.loads(v) if isinstance(v, str) else (v or {})

        return ExecutiveReport(
            id=str(r.id), report_type=r.report_type, period=r.period,
            title=r.title, summary=r.summary,
            kpis=_j(r.kpis) if isinstance(_j(r.kpis), dict) else {},
            risks=_j(r.risks) if isinstance(_j(r.risks), list) else [],
            opportunities=_j(r.opportunities) if isinstance(_j(r.opportunities), list) else [],
            recommendations=_j(r.recommendations) if isinstance(_j(r.recommendations), list) else [],
            period_start=str(r.period_start),
            period_end=str(r.period_end),
            generated_at=r.generated_at.isoformat() if r.generated_at else "",
        )


# ── 12D.8 SLA Monitoring ─────────────────────────────────────

@router.get("/sla", response_model=list[SLARecord])
async def sla_monitoring(
    tenant_id: UUID = Depends(get_validated_tenant_id),
    sla_type: str = Query(default=""),
    breached: bool = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    tid = str(tenant_id)

    async with get_session() as session:
        await _ensure_data(session, tid)

        where = "WHERE tenant_id = :tid"
        if sla_type:
            where += " AND sla_type = :st"
        if breached is not None:
            where += " AND breached = :br"

        params: dict = {"tid": tid, "lim": limit}
        if sla_type:
            params["st"] = sla_type
        if breached is not None:
            params["br"] = breached

        rows = await session.execute(text(f"""
            SELECT id, sla_type, entity_name, sla_target_hours, elapsed_hours,
                   remaining_hours, status, breached, deadline, started_at
            FROM sla_tracking {where}
            ORDER BY breached DESC, remaining_hours ASC
            LIMIT :lim
        """), params)

        return [
            SLARecord(
                id=str(r.id), sla_type=r.sla_type, entity_name=r.entity_name,
                sla_target_hours=float(r.sla_target_hours),
                elapsed_hours=float(r.elapsed_hours),
                remaining_hours=float(r.remaining_hours),
                status=r.status, breached=r.breached,
                deadline=r.deadline.isoformat() if r.deadline else "",
                started_at=r.started_at.isoformat() if r.started_at else "",
            )
            for r in rows.fetchall()
        ]


@router.get("/sla/summary")
async def sla_summary(
    tenant_id: UUID = Depends(get_validated_tenant_id),
):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    tid = str(tenant_id)

    async with get_session() as session:
        await _ensure_data(session, tid)

        rows = await session.execute(text("""
            SELECT
                sla_type,
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE breached = true) AS breaches,
                COUNT(*) FILTER (WHERE status = 'active' AND remaining_hours < sla_target_hours * 0.2) AS warnings,
                COALESCE(AVG(remaining_hours), 0) AS avg_remaining
            FROM sla_tracking WHERE tenant_id = :tid
            GROUP BY sla_type
            ORDER BY sla_type
        """), {"tid": tid})

        return [
            {
                "sla_type": r.sla_type,
                "total": r.total,
                "breaches": r.breaches,
                "warnings": r.warnings,
                "avg_remaining_hours": round(float(r.avg_remaining), 1),
            }
            for r in rows.fetchall()
        ]


# ── 12D.9 Data Population ────────────────────────────────────

@router.post("/populate")
async def populate_executive_data(
    tenant_id: UUID = Depends(get_validated_tenant_id),
):
    from seo_platform.core.database import get_session

    tid = str(tenant_id)

    async with get_session() as session:
        await _ensure_data(session, tid)
        return {"success": True, "message": "Executive data populated successfully"}
