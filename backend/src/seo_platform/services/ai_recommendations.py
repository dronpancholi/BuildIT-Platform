from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from pydantic import BaseModel, Field

from seo_platform.core.database import get_tenant_session
from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


class AIRecommendation(BaseModel):
    type: str
    title: str
    description: str
    confidence: float
    impact: str = "medium"
    source_evidence: list[dict[str, Any]] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class AIRecommendationEngine:
    async def get_recommendations(self, tenant_id: UUID) -> dict[str, list[AIRecommendation]]:
        recs: dict[str, list[AIRecommendation]] = {
            "revenue": [], "campaign": [], "outreach": [],
            "risk_mitigation": [], "sla": [], "executive": [],
        }

        async with get_tenant_session(tenant_id) as session:
            recs["revenue"] = await self._revenue_recs(session, tenant_id)
            recs["campaign"] = await self._campaign_recs(session, tenant_id)
            recs["outreach"] = await self._outreach_recs(session, tenant_id)
            recs["risk_mitigation"] = await self._risk_recs(session, tenant_id)
            recs["sla"] = await self._sla_recs(session, tenant_id)
            recs["executive"] = await self._executive_recs(session, tenant_id)

        return recs

    async def _revenue_recs(self, session: Any, tenant_id: UUID) -> list[AIRecommendation]:
        row = (await session.execute(
            text("SELECT mrr, revenue_growth_pct FROM revenue_metrics WHERE tenant_id = :tid ORDER BY metric_date DESC LIMIT 1"),
            {"tid": tenant_id},
        )).fetchone()
        if row and row[0] is not None and float(row[0]) < 100000:
            return [AIRecommendation(
                type="revenue", title="Revenue Growth Opportunity",
                description=f"Current MRR ${float(row[0]):,.0f} is below $100K target. Growth rate: {float(row[1] or 0):.1f}%. Consider launching new campaigns.",
                confidence=0.75, impact="high",
                source_evidence=[{"mrr": float(row[0]), "growth_pct": float(row[1] or 0)}],
            )]
        return []

    async def _campaign_recs(self, session: Any, tenant_id: UUID) -> list[AIRecommendation]:
        recs = []
        rows = (await session.execute(
            text("SELECT id, name, status FROM backlink_campaigns WHERE tenant_id = :tid ORDER BY created_at DESC LIMIT 10"),
            {"tid": tenant_id},
        )).fetchall()
        for row in rows:
            if row.status in ("draft", "paused"):
                recs.append(AIRecommendation(
                    type="campaign", title=f"Activate Campaign: {row.name}",
                    description=f"Campaign '{row.name}' is {row.status}. Review and activate.",
                    confidence=0.85, impact="high",
                    source_evidence=[{"campaign_id": str(row.id), "status": row.status}],
                ))
        return recs

    async def _outreach_recs(self, session: Any, tenant_id: UUID) -> list[AIRecommendation]:
        row = (await session.execute(
            text("SELECT COUNT(*) as sent, COUNT(*) FILTER (WHERE opened_at IS NOT NULL) as opened FROM outreach_emails WHERE tenant_id = :tid"),
            {"tid": tenant_id},
        )).fetchone()
        sent, opened = int(row[0]), int(row[1])
        if sent > 0:
            rate = opened / sent
            if rate < 0.3:
                return [AIRecommendation(
                    type="outreach", title="Improve Email Open Rate",
                    description=f"Open rate is {rate:.0%}. Consider A/B testing subject lines.",
                    confidence=0.80, impact="medium",
                    source_evidence=[{"opens": opened, "sent": sent, "rate": round(rate, 2)}],
                )]
        return []

    async def _risk_recs(self, session: Any, tenant_id: UUID) -> list[AIRecommendation]:
        recs = []
        rows = (await session.execute(
            text("SELECT id, title, description, risk_level FROM risk_records WHERE tenant_id = :tid AND status = 'active' LIMIT 5"),
            {"tid": tenant_id},
        )).fetchall()
        for row in rows:
            recs.append(AIRecommendation(
                type="risk_mitigation", title=f"Risk: {row.title}",
                description=row.description[:200],
                confidence=0.90, impact="high",
                source_evidence=[{"risk_id": str(row.id), "risk_level": row.risk_level}],
            ))
        return recs

    async def _sla_recs(self, session: Any, tenant_id: UUID) -> list[AIRecommendation]:
        rows = (await session.execute(
            text("SELECT id, summary, risk_level, sla_deadline FROM approval_requests WHERE tenant_id = :tid AND status = 'pending' AND sla_deadline IS NOT NULL ORDER BY sla_deadline ASC LIMIT 5"),
            {"tid": tenant_id},
        )).fetchall()
        return [
            AIRecommendation(
                type="sla", title=f"SLA Approaching: {r.summary[:50]}",
                description=f"Approval deadline is {r.sla_deadline}. Prioritize to avoid SLA breach.",
                confidence=0.85, impact="high",
                source_evidence=[{"approval_id": str(r.id), "deadline": str(r.sla_deadline)}],
            )
            for r in rows
        ]

    async def _executive_recs(self, session: Any, tenant_id: UUID) -> list[AIRecommendation]:
        row = (await session.execute(
            text("SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE status='active') as active FROM backlink_campaigns WHERE tenant_id = :tid"),
            {"tid": tenant_id},
        )).fetchone()
        total, active = int(row[0]), int(row[1])
        if active == 0 and total > 0:
            return [AIRecommendation(
                type="executive", title="No Active Campaigns",
                description=f"{total} campaigns exist but none active. Launch one to maintain pipeline.",
                confidence=0.95, impact="high",
                source_evidence=[{"total": total, "active": active}],
            )]
        if total == 0:
            return [AIRecommendation(
                type="executive", title="No Campaigns Created",
                description="No campaigns found. Create your first campaign to start generating backlinks.",
                confidence=0.90, impact="high",
            )]
        return []


ai_recommendation_engine = AIRecommendationEngine()
