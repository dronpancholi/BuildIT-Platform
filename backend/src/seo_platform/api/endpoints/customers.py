from __future__ import annotations

from seo_platform.core.auth import get_validated_tenant_id
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text

router = APIRouter()

async def _count(session, table: str, tid: str, extra: str = ""):
    sql = f"SELECT COUNT(*) FROM {table} WHERE tenant_id = :tid {extra}"
    row = await session.execute(text(sql), {"tid": tid})
    return row.scalar() or 0


@router.get("/{client_id}/overview")
async def customer_overview(client_id: str, tenant_id: UUID = Depends(get_validated_tenant_id)):
    from seo_platform.core.database import get_session
    from fastapi import HTTPException

    async with get_session() as session:
        tid = str(tenant_id)
        client = await session.execute(
            text("SELECT * FROM clients WHERE id = :id AND tenant_id = :tid"),
            {"id": client_id, "tid": tid},
        )
        client_row = client.mappings().first()
        if not client_row:
            raise HTTPException(status_code=404, detail="Customer not found")
        client_dict = dict(client_row)

        camps = await session.execute(
            text("SELECT id, name, campaign_type, status, health_score, "
                 "target_link_count, acquired_link_count "
                 "FROM backlink_campaigns WHERE client_id = :cid AND tenant_id = :tid"),
            {"cid": client_id, "tid": tid},
        )
        campaign_rows = [dict(r) for r in camps.mappings()]

        active_camps = sum(1 for c in campaign_rows
                           if c.get("status") in ("active", "monitoring"))
        draft_camps = sum(1 for c in campaign_rows
                          if c.get("status") == "draft")
        avg_health = (sum((c.get("health_score") or 0) for c in campaign_rows) /
                      len(campaign_rows)) if campaign_rows else 0
        links_acq = sum((c.get("acquired_link_count") or 0) for c in campaign_rows)

        kw_count = await _count(session, "keywords", tid)
        prospect_count = await _count(session, "backlink_prospects", tid)
        approval_count = await session.execute(
            text("SELECT COUNT(*) FROM approval_requests "
                 "WHERE tenant_id = :tid AND status = 'pending'"),
            {"tid": tid},
        )
        approval_count = approval_count.scalar() or 0
        automation_count = await session.execute(
            text("SELECT COUNT(*) FROM automation_rules "
                 "WHERE tenant_id = :tid AND enabled = true"),
            {"tid": tid},
        )
        automation_count = automation_count.scalar() or 0
        comm_count = await _count(session, "outreach_threads", tid)

        mrr_row = await session.execute(
            text("SELECT COALESCE(SUM(mrr), 0) FROM revenue_metrics "
                 "WHERE tenant_id = :tid"),
            {"tid": tid},
        )
        mrr = float(mrr_row.scalar() or 0)

        health_row = await session.execute(
            text("SELECT health_score, health_category, trend_direction "
                 "FROM customer_health_scores WHERE client_id = :cid "
                 "AND tenant_id = :tid ORDER BY calculated_at DESC LIMIT 1"),
            {"cid": client_id, "tid": tid},
        )
        health = health_row.mappings().first()

    return {
        "customer": {
            "id": str(client_dict["id"]),
            "name": client_dict["name"],
            "domain": client_dict.get("domain", ""),
            "niche": client_dict.get("niche", ""),
            "business_type": str(client_dict.get("business_type") or ""),
            "onboarding_status": str(client_dict.get("onboarding_status") or ""),
        },
        "health": {
            "score": float(health["health_score"]) if health else avg_health,
            "category": health["health_category"] if health else (
                "healthy" if avg_health >= 0.7 else
                "at_risk" if avg_health >= 0.4 else "critical"
            ),
            "trend": health["trend_direction"] if health else "stable",
        },
        "metrics": {
            "mrr": mrr,
            "active_campaigns": active_camps,
            "draft_campaigns": draft_camps,
            "total_campaigns": len(campaign_rows),
            "avg_campaign_health": round(avg_health, 4),
            "links_acquired": links_acq,
            "keyword_count": kw_count,
            "prospect_count": prospect_count,
            "approval_count": approval_count,
            "automation_count": automation_count,
            "communication_count": comm_count,
        },
        "campaigns": campaign_rows,
    }


@router.get("/{client_id}/timeline")
async def customer_timeline(
    client_id: str,
    tenant_id: UUID = Depends(get_validated_tenant_id),
    event_type: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    from seo_platform.core.database import get_session

    events = []
    tid = str(tenant_id)
    async with get_session() as session:
        if not event_type or event_type == "campaign":
            rows = await session.execute(
                text("SELECT id, 'campaign' as type, name as title, "
                     "status as detail, created_at as ts "
                     "FROM backlink_campaigns WHERE client_id = :cid AND tenant_id = :tid "
                     "ORDER BY created_at DESC LIMIT :lim OFFSET :off"),
                {"cid": client_id, "tid": tid, "lim": limit, "off": offset},
            )
            for r in rows.mappings():
                events.append({
                    "id": str(r["id"]), "type": "campaign",
                    "title": r["title"], "detail": r["detail"],
                    "timestamp": r["ts"].isoformat() if r["ts"] else None,
                })

        if not event_type or event_type == "approval":
            rows = await session.execute(
                text("SELECT id, 'approval' as type, summary as title, "
                     "status as detail, created_at as ts "
                     "FROM approval_requests WHERE tenant_id = :tid "
                     "ORDER BY created_at DESC LIMIT :lim OFFSET :off"),
                {"tid": tid, "lim": limit, "off": offset},
            )
            for r in rows.mappings():
                events.append({
                    "id": str(r["id"]), "type": "approval",
                    "title": r["title"], "detail": r["detail"],
                    "timestamp": r["ts"].isoformat() if r["ts"] else None,
                })

        if not event_type or event_type == "automation":
            rows = await session.execute(
                text("SELECT ar.id, 'automation_run' as type, "
                     "ar.status as detail, ar.started_at as ts, "
                     "COALESCE(r.name, 'Automation Run') as title "
                     "FROM automation_runs ar "
                     "LEFT JOIN automation_rules r ON r.id = ar.rule_id "
                     "WHERE ar.tenant_id = :tid "
                     "ORDER BY ar.started_at DESC LIMIT :lim OFFSET :off"),
                {"tid": tid, "lim": limit, "off": offset},
            )
            for r in rows.mappings():
                events.append({
                    "id": str(r["id"]), "type": "automation",
                    "title": r["title"], "detail": r["detail"],
                    "timestamp": r["ts"].isoformat() if r["ts"] else None,
                })

        if not event_type or event_type == "alert":
            rows = await session.execute(
                text("SELECT id, 'alert' as type, title, "
                     "severity as detail, occurred_at as ts "
                     "FROM executive_alerts WHERE tenant_id = :tid "
                     "ORDER BY occurred_at DESC LIMIT :lim OFFSET :off"),
                {"tid": tid, "lim": limit, "off": offset},
            )
            for r in rows.mappings():
                events.append({
                    "id": str(r["id"]), "type": "alert",
                    "title": r["title"], "detail": r["detail"],
                    "timestamp": r["ts"].isoformat() if r["ts"] else None,
                })

        if not event_type or event_type == "report":
            rows = await session.execute(
                text("SELECT id, 'report' as type, report_type as title, "
                     "period as detail, generated_at as ts "
                     "FROM executive_reports WHERE tenant_id = :tid "
                     "ORDER BY generated_at DESC LIMIT :lim OFFSET :off"),
                {"tid": tid, "lim": limit, "off": offset},
            )
            for r in rows.mappings():
                events.append({
                    "id": str(r["id"]), "type": "report",
                    "title": r["title"], "detail": r["detail"],
                    "timestamp": r["ts"].isoformat() if r["ts"] else None,
                })

    events.sort(key=lambda e: e["timestamp"] or "", reverse=True)
    return events[:limit]


@router.get("/{client_id}/health-risk")
async def customer_health_risk(client_id: str, tenant_id: UUID = Depends(get_validated_tenant_id)):
    from seo_platform.core.database import get_session

    tid = str(tenant_id)
    async with get_session() as session:
        health_rows = await session.execute(
            text("SELECT health_score, health_category, trend_direction, "
                 "growth_velocity, calculated_at "
                 "FROM customer_health_scores "
                 "WHERE client_id = :cid AND tenant_id = :tid "
                 "ORDER BY calculated_at DESC LIMIT 30"),
            {"cid": client_id, "tid": tid},
        )
        health_history = [dict(r) for r in health_rows.mappings()]

        risks = await session.execute(
            text("SELECT id, risk_level, risk_type, title, description, "
                 "detected_at, resolved "
                 "FROM risk_records WHERE tenant_id = :tid "
                 "ORDER BY detected_at DESC LIMIT 20"),
            {"tid": tid},
        )
        risk_list = [dict(r) for r in risks.mappings()]

        alerts = await session.execute(
            text("SELECT id, severity, title, description, source, "
                 "occurred_at, resolved, dismissed "
                 "FROM executive_alerts WHERE tenant_id = :tid "
                 "ORDER BY occurred_at DESC LIMIT 20"),
            {"tid": tid},
        )
        alert_list = [dict(r) for r in alerts.mappings()]

        sla_rows = await session.execute(
            text("SELECT sla_type, COUNT(*) as total, "
                 "SUM(CASE WHEN breached THEN 1 ELSE 0 END) as breaches, "
                 "SUM(CASE WHEN warning_sent THEN 1 ELSE 0 END) as warnings, "
                 "COALESCE(AVG(remaining_hours), 0) as avg_remaining_hours "
                 "FROM sla_tracking WHERE tenant_id = :tid "
                 "GROUP BY sla_type"),
            {"tid": tid},
        )
        sla_list = [dict(r) for r in sla_rows.mappings()]

        v = await session.execute(
            text("SELECT COALESCE(AVG(growth_velocity), 0) "
                 "FROM customer_health_scores "
                 "WHERE client_id = :cid AND tenant_id = :tid"),
            {"cid": client_id, "tid": tid},
        )
        avg_velocity = float(v.scalar() or 0)

        comm_row = await session.execute(
            text("SELECT COUNT(*) as total, "
                 "COALESCE(AVG(CASE WHEN status = 'replied' "
                 "THEN 1.0 ELSE 0.0 END), 0) as reply_rate "
                 "FROM outreach_threads WHERE tenant_id = :tid"),
            {"tid": tid},
        )
        comm_stats = comm_row.mappings().first()

    current = health_history[0] if health_history else {}
    return {
        "health": {
            "current_score": float(current.get("health_score", 0)),
            "category": current.get("health_category", "unknown"),
            "trend": current.get("trend_direction", "stable"),
            "velocity": float(avg_velocity),
            "history": [
                {
                    "score": float(h["health_score"]),
                    "ts": h["calculated_at"].isoformat() if h.get("calculated_at") else None,
                }
                for h in health_history
            ],
        },
        "risks": {
            "total": len(risk_list),
            "unresolved": sum(1 for r in risk_list if not r.get("resolved")),
            "items": [{
                "id": str(r["id"]), "level": r.get("risk_level"),
                "type": r.get("risk_type"), "title": r.get("title"),
                "description": r.get("description"),
                "detected_at": r["detected_at"].isoformat() if r.get("detected_at") else None,
                "resolved": r.get("resolved", False),
            } for r in risk_list],
        },
        "alerts": {
            "total": len(alert_list),
            "active": sum(1 for a in alert_list
                          if not a.get("resolved") and not a.get("dismissed")),
            "items": [{
                "id": str(a["id"]), "severity": a.get("severity"),
                "title": a.get("title"), "description": a.get("description"),
                "source": a.get("source"),
                "occurred_at": a["occurred_at"].isoformat() if a.get("occurred_at") else None,
            } for a in alert_list],
        },
        "sla": [{
            "sla_type": s["sla_type"], "total": s["total"],
            "breaches": s["breaches"], "warnings": s["warnings"],
            "avg_remaining_hours": float(s["avg_remaining_hours"]),
        } for s in sla_list],
        "communication": {
            "total": comm_stats["total"] if comm_stats else 0,
            "reply_rate": float(comm_stats["reply_rate"])
            if comm_stats and comm_stats["reply_rate"] else 0,
        },
    }


@router.get("/{client_id}")
async def get_customer(client_id: str, tenant_id: UUID = Depends(get_validated_tenant_id)):
    from seo_platform.core.database import get_session
    from fastapi import HTTPException

    async with get_session() as session:
        row = await session.execute(
            text("SELECT * FROM clients WHERE id = :id AND tenant_id = :tid"),
            {"id": client_id, "tid": str(tenant_id)},
        )
        client = row.mappings().first()
        if not client:
            raise HTTPException(status_code=404, detail="Customer not found")
        return dict(client)


@router.post("/{client_id}/populate")
async def populate_customer_data(client_id: str, tenant_id: UUID = Depends(get_validated_tenant_id)):
    from seo_platform.core.database import get_session

    tid = str(tenant_id)
    cid = client_id
    async with get_session() as session:
        created = {"campaigns": 0, "health_snapshots": 0, "risks": 0,
                   "alerts": 0, "sla_entries": 0, "revenue": 0}

        existing_camps = await session.execute(
            text("SELECT COUNT(*) FROM backlink_campaigns WHERE tenant_id = :tid AND client_id = :cid"),
            {"tid": tid, "cid": cid},
        )
        if existing_camps.scalar() == 0:
            import uuid as uuid_mod
            for i in range(1, 4):
                pcid = str(uuid_mod.uuid4())
                await session.execute(
                    text("""INSERT INTO backlink_campaigns
(id, tenant_id, client_id, name, campaign_type, status,
 target_link_count, acquired_link_count, health_score,
 created_at, updated_at)
VALUES (:id, :tid, :cid, :name, :type, :status,
        :target, :acquired, :health, NOW(), NOW())
ON CONFLICT DO NOTHING"""),
                    {
                        "id": pcid, "tid": tid, "cid": cid,
                        "name": f"Workspace Campaign {i}",
                        "type": ["guest_post", "skyscraper", "niche_edit"][i - 1],
                        "status": ["active", "active", "draft"][i - 1],
                        "target": 50, "acquired": 5 * i, "health": 0.5 + i * 0.15,
                    },
                )
                created["campaigns"] += 1

        hs_count = await session.execute(
            text("SELECT COUNT(*) FROM customer_health_scores "
                 "WHERE tenant_id = :tid AND client_id = :cid"),
            {"tid": tid, "cid": cid},
        )
        if hs_count.scalar() == 0:
            import uuid as uuid_mod
            import datetime as dt
            for i in range(5):
                hid = str(uuid_mod.uuid4())
                score = round(0.3 + i * 0.12, 2)
                await session.execute(
                    text("""INSERT INTO customer_health_scores
(id, tenant_id, client_id, health_score, health_category,
 trend_direction, growth_velocity, calculated_at)
VALUES (:id, :tid, :cid, :score, :cat, :trend, :vel, :ts)
ON CONFLICT DO NOTHING"""),
                    {
                        "id": hid, "tid": tid, "cid": cid,
                        "score": score,
                        "cat": ("healthy" if score >= 0.7
                                else "at_risk" if score >= 0.4 else "critical"),
                        "trend": ["improving", "stable", "declining", "stable", "improving"][i],
                        "vel": round(80 + i * 2, 1),
                        "ts": dt.datetime.utcnow() - dt.timedelta(days=(4 - i) * 7),
                    },
                )
                created["health_snapshots"] += 1

        risk_total = await session.execute(
            text("SELECT COUNT(*) FROM risk_records WHERE tenant_id = :tid"),
            {"tid": tid},
        )
        if risk_total.scalar() == 0:
            import uuid as uuid_mod
            for lvl in ["low", "medium", "high", "critical"]:
                await session.execute(
                    text("""INSERT INTO risk_records
(id, tenant_id, risk_level, risk_type, title, description, detected_at)
VALUES (:id, :tid, :lvl, :type, :title, :desc, NOW())
ON CONFLICT DO NOTHING"""),
                    {
                        "id": str(uuid_mod.uuid4()), "tid": tid,
                        "lvl": lvl, "type": "operational",
                        "title": f"{lvl.capitalize()} risk detected",
                        "desc": f"Sample {lvl} risk record for workspace",
                    },
                )
                created["risks"] += 1

        alert_total = await session.execute(
            text("SELECT COUNT(*) FROM executive_alerts WHERE tenant_id = :tid"),
            {"tid": tid},
        )
        if alert_total.scalar() == 0:
            import uuid as uuid_mod
            for sev in ["info", "warning", "high", "critical"]:
                await session.execute(
                    text("""INSERT INTO executive_alerts
(id, tenant_id, severity, title, description, source, occurred_at)
VALUES (:id, :tid, :sev, :title, :desc, :src, NOW())
ON CONFLICT DO NOTHING"""),
                    {
                        "id": str(uuid_mod.uuid4()), "tid": tid, "sev": sev,
                        "title": f"{sev.capitalize()} alert",
                        "desc": f"Sample {sev} alert for workspace",
                        "src": "workspace_populate",
                    },
                )
                created["alerts"] += 1

        sla_total = await session.execute(
            text("SELECT COUNT(*) FROM sla_tracking WHERE tenant_id = :tid"),
            {"tid": tid},
        )
        if sla_total.scalar() == 0:
            import uuid as uuid_mod
            for stype in ["approval", "email_response", "campaign_launch", "report_generation"]:
                await session.execute(
                    text("""INSERT INTO sla_tracking
(id, tenant_id, sla_type, total, breaches, warnings, avg_remaining_hours)
VALUES (:id, :tid, :type, :total, :breaches, :warnings, :hours)
ON CONFLICT DO NOTHING"""),
                    {
                        "id": str(uuid_mod.uuid4()), "tid": tid, "type": stype,
                        "total": 50, "breaches": 2, "warnings": 5,
                        "hours": float(12 + len(stype)),
                    },
                )
                created["sla_entries"] += 1

        rev_total = await session.execute(
            text("SELECT COUNT(*) FROM revenue_metrics WHERE tenant_id = :tid"),
            {"tid": tid},
        )
        if rev_total.scalar() == 0:
            import uuid as uuid_mod
            await session.execute(
                text("""INSERT INTO revenue_metrics
(id, tenant_id, mrr, arr, metric_date, created_at)
VALUES (:id, :tid, :mrr, :arr, :date, NOW())
ON CONFLICT DO NOTHING"""),
                {
                    "id": str(uuid_mod.uuid4()), "tid": tid,
                    "mrr": 5000.00, "arr": 60000.00,
                    "date": dt.date.today(),
                },
            )
            created["revenue"] += 1

        await session.commit()

    return {"success": True, "created": created}


@router.get("/{client_id}/search")
async def customer_search(client_id: str, tenant_id: UUID = Depends(get_validated_tenant_id), q: str = Query("")):
    from seo_platform.core.database import get_session

    results = []
    tid = str(tenant_id)
    async with get_session() as session:
        if q:
            camps = await session.execute(
                text("SELECT id, name, 'campaign' as type FROM backlink_campaigns "
                     "WHERE client_id = :cid AND tenant_id = :tid AND name ILIKE :q LIMIT 5"),
                {"cid": client_id, "tid": tid, "q": f"%{q}%"},
            )
            for r in camps.mappings():
                results.append({
                    "id": str(r["id"]), "label": r["name"], "type": "campaign",
                })
    return results
