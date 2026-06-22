from __future__ import annotations

import time
import uuid
from typing import Any
from uuid import UUID

from sqlalchemy import text
from pydantic import BaseModel, Field

from seo_platform.core.database import get_tenant_session
from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


class CopilotSource(BaseModel):
    type: str
    id: str
    label: str
    snippet: str


class CopilotResponse(BaseModel):
    conversation_id: str
    answer: str
    sources: list[CopilotSource] = Field(default_factory=list)
    latency_ms: float = 0.0


class ExecutiveCopilotService:
    async def ask(self, question: str, tenant_id: UUID, conversation_id: str | None = None) -> CopilotResponse:
        start = time.monotonic()
        conv_id = conversation_id or str(uuid.uuid4())
        sources: list[CopilotSource] = []
        question_lower = question.lower()

        async with get_tenant_session(tenant_id) as session:
            insights = []

            if any(w in question_lower for w in ["kpi", "key performance", "overview", "summary", "status"]):
                row = (await session.execute(
                    text("SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE onboarding_status='complete') as active FROM clients WHERE tenant_id = :tid"),
                    {"tid": tenant_id},
                )).fetchone()
                insights.append(f"Total customers: {row[0]}, Onboarded: {row[1]}")
                sources.append(CopilotSource(type="customer", id="all", label="Customer Summary", snippet=f"{row[0]} total, {row[1]} onboarded"))

            if any(w in question_lower for w in ["revenue", "mrr", "earning"]):
                row = (await session.execute(
                    text("SELECT mrr, revenue_growth_pct FROM revenue_metrics WHERE tenant_id = :tid ORDER BY metric_date DESC LIMIT 1"),
                    {"tid": tenant_id},
                )).fetchone()
                if row and row[0] is not None:
                    insights.append(f"Current MRR: ${float(row[0]):,.2f}")
                    sources.append(CopilotSource(type="revenue", id="latest", label="Revenue", snippet=f"${float(row[0]):,.2f} MRR"))

            if any(w in question_lower for w in ["campaign", "active campaign"]):
                row = (await session.execute(
                    text("SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE status='active') as active, COUNT(*) FILTER (WHERE status='draft') as draft FROM backlink_campaigns WHERE tenant_id = :tid"),
                    {"tid": tenant_id},
                )).fetchone()
                insights.append(f"Campaigns: {row[0]} total, {row[1]} active, {row[2]} draft")
                sources.append(CopilotSource(type="campaign", id="all", label="Campaign Overview", snippet=f"{row[0]} total, {row[1]} active"))

            if any(w in question_lower for w in ["risk", "at risk", "issue"]):
                rows = (await session.execute(
                    text("SELECT id, title, risk_level FROM risk_records WHERE tenant_id = :tid AND status = 'active' LIMIT 5"),
                    {"tid": tenant_id},
                )).fetchall()
                if rows:
                    risk_summary = [f"{r[1]} ({r[2]})" for r in rows]
                    insights.append(f"Active risks ({len(rows)}): {'; '.join(risk_summary)}")
                    for r in rows:
                        sources.append(CopilotSource(type="risk", id=str(r[0]), label=r[1], snippet=f"Level: {r[2]}"))

            if any(w in question_lower for w in ["alert", "warning"]):
                rows = (await session.execute(
                    text("SELECT id, title, severity FROM executive_alerts WHERE tenant_id = :tid AND status='open' ORDER BY occurred_at DESC LIMIT 5"),
                    {"tid": tenant_id},
                )).fetchall()
                if rows:
                    alerts_info = [f"{r[1]} ({r[2]})" for r in rows]
                    insights.append(f"Active alerts ({len(rows)}): {'; '.join(alerts_info)}")
                    for r in rows:
                        sources.append(CopilotSource(type="alert", id=str(r[0]), label=r[1], snippet=f"Severity: {r[2]}"))

            if any(w in question_lower for w in ["automation", "auto"]):
                row = (await session.execute(
                    text("SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE enabled=true) as active FROM automation_rules WHERE tenant_id = :tid"),
                    {"tid": tenant_id},
                )).fetchone()
                insights.append(f"Automation rules: {row[0]} total, {row[1]} active")
                sources.append(CopilotSource(type="automation", id="all", label="Automation", snippet=f"{row[0]} total, {row[1]} active"))

            if any(w in question_lower for w in ["keyword", "seo"]):
                row = (await session.execute(
                    text("SELECT COUNT(*) as total, AVG(search_volume) as avg_vol FROM keywords WHERE tenant_id = :tid"),
                    {"tid": tenant_id},
                )).fetchone()
                insights.append(f"Keywords tracked: {row[0]}, Avg search volume: {float(row[1] or 0):.0f}")
                sources.append(CopilotSource(type="keyword", id="all", label="Keywords", snippet=f"{row[0]} keywords tracked"))

        if not insights:
            answer = "I couldn't find specific data for that question. Try asking about KPIs, revenue, campaigns, risks, alerts, automation, or keywords."
        else:
            answer = "Based on your data:\n\n" + "\n".join(f"- {i}" for i in insights)

        return CopilotResponse(
            conversation_id=conv_id, answer=answer,
            sources=sources,
            latency_ms=round((time.monotonic() - start) * 1000, 1),
        )


executive_copilot = ExecutiveCopilotService()
