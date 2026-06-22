from __future__ import annotations

import json
import time
import uuid
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from pydantic import BaseModel, Field

from seo_platform.core.database import get_tenant_session
from seo_platform.core.logging import get_logger
from seo_platform.llm.gateway import LLMGateway, TaskType, RenderedPrompt, LLMResult

logger = get_logger(__name__)


class AgentAction(BaseModel):
    action_type: str
    description: str
    reasoning: str
    target_campaign_id: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    requires_approval: bool = True


class AgentRunResult(BaseModel):
    run_id: str
    tenant_id: str
    campaign_id: str | None
    status: str  # completed, pending_approval, failed
    analysis: dict[str, Any] = Field(default_factory=dict)
    actions: list[AgentAction] = Field(default_factory=list)
    reasoning_trace: list[str] = Field(default_factory=list)
    started_at: str
    completed_at: str | None = None
    error: str | None = None


class CampaignAgent:
    def __init__(self) -> None:
        self._llm = LLMGateway()

    async def run(
        self, tenant_id: UUID, campaign_id: UUID | None = None,
    ) -> AgentRunResult:
        run_id = str(uuid.uuid4())
        started = datetime.utcnow().isoformat()
        trace: list[str] = []

        try:
            async with get_tenant_session(tenant_id) as session:
                trace.append("phase:load_campaign_state")

                if campaign_id:
                    campaigns = (await session.execute(
                        text("""
                            SELECT id, name, status, campaign_type, config::text, created_at
                            FROM backlink_campaigns
                            WHERE tenant_id = :tid AND id = :cid
                        """),
                        {"tid": tenant_id, "cid": campaign_id},
                    )).fetchall()
                else:
                    campaigns = (await session.execute(
                        text("""
                            SELECT id, name, status, campaign_type, config::text, created_at
                            FROM backlink_campaigns
                            WHERE tenant_id = :tid
                            ORDER BY created_at DESC LIMIT 5
                        """),
                        {"tid": tenant_id},
                    )).fetchall()

                if not campaigns:
                    return AgentRunResult(
                        run_id=run_id, tenant_id=str(tenant_id),
                        campaign_id=str(campaign_id) if campaign_id else None,
                        status="failed", reasoning_trace=trace,
                        started_at=started, error="No campaigns found",
                    )

                trace.append(f"phase:loaded_{len(campaigns)}_campaigns")

                for c in campaigns:
                    cid, name, status, ctype, metrics_str, created = c
                    trace.append(f"analyze:{name}(status={status})")

                    if status in ("draft", "paused"):
                        trace.append(f"action:activate_{name}")
                        action = AgentAction(
                            action_type="activate_campaign",
                            description=f"Activate campaign '{name}' from {status} status",
                            reasoning=f"Campaign '{name}' has been in '{status}' status since {created}. Activation will start prospect discovery and outreach.",
                            target_campaign_id=str(cid),
                            requires_approval=True,
                        )
                        return AgentRunResult(
                            run_id=run_id, tenant_id=str(tenant_id),
                            campaign_id=str(cid),
                            status="pending_approval",
                            analysis={
                                "campaign_name": name,
                                "current_status": status,
                                "campaign_type": ctype,
                            },
                            actions=[action],
                            reasoning_trace=trace,
                            started_at=started,
                        )

                trace.append("phase:no_issues_found")
                return AgentRunResult(
                    run_id=run_id, tenant_id=str(tenant_id),
                    campaign_id=str(campaign_id) if campaign_id else None,
                    status="completed",
                    actions=[],
                    reasoning_trace=trace,
                    started_at=started, completed_at=datetime.utcnow().isoformat(),
                )

        except Exception as e:
            logger.error("campaign_agent_failed", error=str(e))
            return AgentRunResult(
                run_id=run_id, tenant_id=str(tenant_id),
                campaign_id=str(campaign_id) if campaign_id else None,
                status="failed", reasoning_trace=trace,
                started_at=started, error=str(e),
            )


campaign_agent = CampaignAgent()
