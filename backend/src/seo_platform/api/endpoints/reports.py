"""
SEO Platform — Reporting API
=================================
Handle generation of enterprise-grade SEO performance reports.
"""

from __future__ import annotations

from datetime import UTC
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from seo_platform.core.logging import get_logger
from seo_platform.schemas import APIResponse

logger = get_logger(__name__)
router = APIRouter()

class ReportRequest(BaseModel):
    tenant_id: UUID
    client_id: UUID
    report_type: str = Field(..., pattern="^(performance|technical|backlink|citation)$")
    date_range: str = Field(default="last_30_days")
    format: str = Field(default="pdf")

class ReportResponse(BaseModel):
    id: str
    status: str
    download_url: str | None = None
    created_at: str

@router.post("", response_model=APIResponse[ReportResponse])
async def generate_report(request: ReportRequest) -> APIResponse[ReportResponse]:
    """Trigger a real Temporal ReportGenerationWorkflow."""
    from datetime import datetime

    from seo_platform.core.temporal_client import get_temporal_client
    from seo_platform.workflows import TaskQueue
    from seo_platform.workflows.reporting import ReportGenerationInput

    now = datetime.now(UTC).isoformat()
    logger.info("report_generation_requested",
                client_id=str(request.client_id),
                report_type=request.report_type)

    workflow_id = f"report-{request.tenant_id}-{request.report_type}-{int(datetime.now(UTC).timestamp())}"

    try:
        client = await get_temporal_client()
        workflow_input = ReportGenerationInput(
            tenant_id=request.tenant_id,
            report_type=request.report_type,
            client_id=request.client_id,
        )
        handle = await client.start_workflow(
            "ReportGenerationWorkflow",
            args=[workflow_input.model_dump_json()],
            id=workflow_id,
            task_queue=TaskQueue.REPORTING,
        )
        report_id = handle.run_id
        logger.info("report_workflow_started", workflow_id=workflow_id, run_id=report_id)
    except Exception as e:
        logger.warning("report_workflow_start_failed", error=str(e))
        report_id = "pending"

    return APIResponse(data=ReportResponse(
        id=report_id or "pending",
        status="pending",
        created_at=now,
    ))

@router.get("", response_model=APIResponse[list[ReportResponse]])
async def list_reports(
    tenant_id: UUID = Query(...),
    client_id: UUID | None = None
) -> APIResponse[list[ReportResponse]]:
    """List generated reports for a tenant/client from the database."""
    from sqlalchemy import select

    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.seo import ReportModel

    reports: list[ReportResponse] = []
    try:
        async with get_tenant_session(tenant_id) as session:
            query = select(ReportModel).where(ReportModel.tenant_id == tenant_id)
            if client_id:
                query = query.where(ReportModel.client_id == client_id)
            query = query.order_by(ReportModel.generated_at.desc())
            result = await session.execute(query)
            for row in result.scalars().all():
                reports.append(ReportResponse(
                    id=str(row.id),
                    status="completed",
                    created_at=row.generated_at.isoformat() if row.generated_at else "",
                ))
    except Exception as e:
        logger.warning("report_list_failed", error=str(e))

    return APIResponse(data=reports)
