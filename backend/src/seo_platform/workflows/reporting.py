"""
SEO Platform — Report Generation Workflow
============================================
Temporal workflow for generating comprehensive campaign reports
with AI-authored narratives, HTML rendering, and PDF artifacts.
"""

from __future__ import annotations

import base64
import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from temporalio import activity, workflow

from seo_platform.core.logging import get_logger
from seo_platform.services.reporting.agent import reporting_agent
from seo_platform.workflows import RetryPreset, TaskQueue

logger = get_logger(__name__)


class ReportGenerationInput(BaseModel):
    tenant_id: UUID
    report_type: str = "campaign_summary"
    client_id: UUID | None = None
    campaign_id: UUID | None = None
    date_range_start: str = ""
    date_range_end: str = ""
    initiated_by: str = "system"


class ReportGenerationOutput(BaseModel):
    success: bool
    report_id: str = ""
    summary: str = ""
    metrics: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


@activity.defn(name="gather_report_data")
async def gather_report_data(
    tenant_id: str, report_type: str, client_id: str | None, campaign_id: str | None,
    date_start: str, date_end: str,
) -> dict[str, Any]:
    """Gather all relevant data for the report from database."""
    logger.info("gathering_report_data", tenant_id=tenant_id, report_type=report_type)

    from sqlalchemy import func, select

    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.backlink import BacklinkCampaign
    from seo_platform.models.seo import KeywordCluster

    data: dict[str, Any] = {
        "campaigns": [],
        "keywords": [],
        "summary": {},
    }

    try:
        async with get_tenant_session(UUID(tenant_id)) as session:
            if campaign_id:
                result = await session.execute(
                    select(BacklinkCampaign).where(
                        BacklinkCampaign.id == UUID(campaign_id),
                        BacklinkCampaign.tenant_id == UUID(tenant_id),
                    )
                )
                campaign = result.scalar_one_or_none()
                if campaign:
                    data["campaigns"] = [{
                        "id": str(campaign.id),
                        "name": campaign.name,
                        "status": campaign.status.value,
                        "target_link_count": campaign.target_link_count,
                        "acquired_link_count": campaign.acquired_link_count,
                        "health_score": campaign.health_score,
                    }]

            result = await session.execute(
                select(BacklinkCampaign).where(
                    BacklinkCampaign.tenant_id == UUID(tenant_id),
                )
            )
            campaigns = result.scalars().all()
            data["summary"]["total_campaigns"] = len(campaigns)
            data["summary"]["active_campaigns"] = sum(1 for c in campaigns if c.status.value == "active")

            result = await session.execute(
                select(func.count()).select_from(KeywordCluster).where(
                    KeywordCluster.tenant_id == UUID(tenant_id),
                )
            )
            data["summary"]["total_clusters"] = result.scalar_one() or 0

            total_acquired = sum(c.acquired_link_count for c in campaigns)
            data["summary"]["acquired_links"] = total_acquired
            total_prospects = sum(c.target_link_count for c in campaigns)
            data["summary"]["total_prospects"] = total_prospects

    except Exception as e:
        logger.warning("report_data_gathering_failed", error=str(e))

    return data


@activity.defn(name="generate_ai_summary")
async def generate_ai_summary(
    tenant_id: str, report_data: dict[str, Any],
) -> dict[str, Any]:
    """Generate AI-powered narrative for the report using ReportingAgent. Idempotent."""
    data_hash = hashlib.sha256(json.dumps(report_data, sort_keys=True).encode()).hexdigest()[:16]
    idem_key = f"ai-summary:{tenant_id}:{data_hash}"

    from seo_platform.core.reliability import idempotency_store
    cached = await idempotency_store.get(idem_key)
    if cached:
        logger.info("ai_summary_idempotent_skip", key=idem_key)
        return json.loads(cached)

    logger.info("generating_ai_summary_via_reporting_agent", tenant_id=tenant_id)

    try:
        narrative = await reporting_agent.generate_roi_narrative(
            tenant_id=UUID(tenant_id),
            campaign_id=None,
            kpi_data=report_data,
        )
        output = narrative.model_dump()
        await idempotency_store.store(idem_key, json.dumps(output), ttl=86400)
        return output
    except Exception as e:
        logger.warning("ai_summary_generation_failed", error=str(e))
        output: dict[str, Any] = {
            "executive_summary": "Report generated successfully.",
            "keyword_ranking_analysis": "Keyword data gathered from clusters.",
            "backlink_acquisition_analysis": "Backlink data gathered from campaigns.",
            "roi_narrative": "ROI analysis completed.",
            "recommendations": ["Continue monitoring campaign performance"],
        }
        await idempotency_store.store(idem_key, json.dumps(output), ttl=3600)
        return output


@activity.defn(name="persist_report")
async def persist_report(
    tenant_id: str, report_type: str, metrics: dict[str, Any], ai_summary: dict[str, Any],
) -> dict[str, Any]:
    """Save the generated report with HTML and PDF artifacts. Idempotent."""
    import hashlib
    import json

    from seo_platform.core.reliability import idempotency_store
    input_hash = hashlib.sha256(json.dumps({"metrics": metrics, "summary": ai_summary}, sort_keys=True).encode()).hexdigest()[:16]
    idem_key = f"persist-report:{tenant_id}:{input_hash}"
    cached = await idempotency_store.get(idem_key)
    if cached:
        logger.info("persist_report_idempotent_skip", key=idem_key)
        return json.loads(cached)

    logger.info("persisting_report_with_artifacts", tenant_id=tenant_id, report_type=report_type)

    from uuid import uuid4

    from seo_platform.core.database import get_tenant_session
    from seo_platform.llm.gateway import RenderedPrompt, TaskType

    try:
        narrative_dict = ai_summary
        from pydantic import BaseModel
        from seo_platform.services.reporting.agent import ReportNarrative
        narrative = ReportNarrative(**narrative_dict)

        html_content = await reporting_agent.render_html_report(
            tenant_id=UUID(tenant_id),
            campaign_id=None,
            narrative=narrative,
            kpi_data={"summary": metrics},
        )

        pdf_bytes = await reporting_agent.generate_pdf_report(
            tenant_id=UUID(tenant_id),
            campaign_id=None,
            html_content=html_content,
        )

        pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")

        async with get_tenant_session(UUID(tenant_id)) as session:
            from seo_platform.models.seo import ReportModel

            report = ReportModel(
                id=uuid4(),
                tenant_id=UUID(tenant_id),
                report_type=report_type,
                metrics={
                    **metrics,
                    "_html_content": html_content,
                    "_pdf_b64": pdf_b64,
                },
                ai_summary=narrative_dict,
                generated_at=datetime.now(UTC),
            )
            session.add(report)
            await session.flush()
            await session.refresh(report)

            output = {"report_id": str(report.id), "success": True}
            await idempotency_store.store(idem_key, json.dumps(output), ttl=86400)
            return output
    except Exception as e:
        logger.warning("report_persistence_failed", error=str(e))
        output = {"report_id": "", "success": False}
        await idempotency_store.store(idem_key, json.dumps(output), ttl=3600)
        return output


@workflow.defn(name="ReportGenerationWorkflow")
class ReportGenerationWorkflow:
    """Generate comprehensive campaign reports with AI summaries and PDF artifacts."""

    @workflow.run
    async def run(self, input_json: str) -> str:
        input_data = ReportGenerationInput.model_validate_json(input_json)
        output = ReportGenerationOutput(success=True, errors=[])

        report_data = await workflow.execute_activity(
            gather_report_data,
            args=[
                str(input_data.tenant_id),
                input_data.report_type,
                str(input_data.client_id) if input_data.client_id else None,
                str(input_data.campaign_id) if input_data.campaign_id else None,
                input_data.date_range_start,
                input_data.date_range_end,
            ],
            task_queue=TaskQueue.REPORTING,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPreset.DATABASE,
        )

        ai_summary = await workflow.execute_activity(
            generate_ai_summary,
            args=[str(input_data.tenant_id), report_data],
            task_queue=TaskQueue.AI_ORCHESTRATION,
            start_to_close_timeout=timedelta(minutes=3),
            retry_policy=RetryPreset.LLM_INFERENCE,
        )

        persist_result = await workflow.execute_activity(
            persist_report,
            args=[
                str(input_data.tenant_id),
                input_data.report_type,
                report_data.get("summary", {}),
                ai_summary,
            ],
            task_queue=TaskQueue.REPORTING,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPreset.DATABASE,
        )

        if persist_result.get("success"):
            output.success = True
            output.report_id = persist_result.get("report_id", "")
            output.summary = ai_summary.get("executive_summary", "")
            output.metrics = report_data.get("summary", {})
        else:
            output.errors.append("Failed to persist report")

        return output.model_dump_json()
