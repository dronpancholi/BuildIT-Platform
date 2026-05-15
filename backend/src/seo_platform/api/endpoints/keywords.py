"""
SEO Platform — Keyword Research Endpoint
===========================================
Trigger keyword research workflows.
"""

from __future__ import annotations

import traceback
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from seo_platform.schemas import APIResponse

router = APIRouter()


class StartResearchRequest(BaseModel):
    tenant_id: UUID
    client_id: UUID
    domain: str
    niche: str = ""
    seed_keywords: list[str] = Field(default_factory=list)
    geo_target: str = "US"


class ResearchResponse(BaseModel):
    workflow_run_id: str | None = None
    status: str


@router.get("/research", response_model=APIResponse[list[dict]])
async def list_keyword_research(
    tenant_id: UUID = Query(...),
    client_id: UUID | None = None
) -> APIResponse[list[dict]]:
    """List keyword research history."""
    from sqlalchemy import select

    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.keywords import KeywordResearch

    async with get_tenant_session(tenant_id) as session:
        stmt = select(KeywordResearch).where(KeywordResearch.tenant_id == tenant_id)
        if client_id:
            stmt = stmt.where(KeywordResearch.client_id == client_id)

        stmt = stmt.order_by(KeywordResearch.created_at.desc())
        result = await session.execute(stmt)
        history = result.scalars().all()

        return APIResponse(
            data=[
                {
                    "id": str(h.id),
                    "client_id": str(h.client_id),
                    "seed_keyword": h.seed_keyword,
                    "status": h.status,
                    "created_at": h.created_at.isoformat(),
                }
                for h in history
            ]
        )

@router.post("/research", response_model=APIResponse[ResearchResponse])
async def start_keyword_research(request: StartResearchRequest) -> APIResponse[ResearchResponse]:
    """Launch a keyword research workflow."""
    from fastapi import HTTPException

    from seo_platform.core.kill_switch import kill_switch_service
    from seo_platform.core.temporal_client import get_temporal_client
    from seo_platform.workflows import TaskQueue

    # Kill switch check
    kill_check = await kill_switch_service.is_blocked("all_llm_calls", tenant_id=request.tenant_id)
    if kill_check.blocked:
        raise HTTPException(status_code=503, detail=f"Kill switch active: {kill_check.reason}")

    # Save research record to DB
    from seo_platform.core.database import get_tenant_session
    from seo_platform.core.logging import get_logger
    from seo_platform.models.keywords import KeywordResearch

    logger = get_logger(__name__)

    logger.info("creating_research_record", tenant_id=str(request.tenant_id), client_id=str(request.client_id))

    try:
        async with get_tenant_session(request.tenant_id) as session:
            research = KeywordResearch(
                tenant_id=request.tenant_id,
                client_id=request.client_id,
                seed_keyword=request.seed_keywords[0] if request.seed_keywords else "unnamed",
                status="pending"
            )
            session.add(research)
            await session.flush()
            await session.refresh(research)
            logger.info("research_record_created", research_id=str(research.id))

            # Start Temporal workflow
            try:
                logger.info("connecting_to_temporal_client")
                temporal = await get_temporal_client()
                workflow_id = f"keyword-research-{research.id}"

                logger.info("preparing_workflow_input")
                from seo_platform.workflows import KeywordResearchInput
                workflow_input = KeywordResearchInput(
                    tenant_id=request.tenant_id,
                    initiated_by="console_admin",
                    client_id=request.client_id,
                    domain=request.domain,
                    seed_keywords=request.seed_keywords,
                    geo_target=request.geo_target,
                    metadata={
                        "research_id": str(research.id),
                    }
                )

                logger.info("starting_temporal_workflow", workflow_id=workflow_id)
                handle = await temporal.start_workflow(
                    "KeywordResearchWorkflow",
                    args=[workflow_input.model_dump_json()],
                    id=workflow_id,
                    task_queue=TaskQueue.AI_ORCHESTRATION,
                )

                # Update with run ID
                research.workflow_run_id = handle.run_id
                logger.info("workflow_started_successfully", run_id=handle.run_id)

                return APIResponse(
                    data=ResearchResponse(
                        workflow_run_id=handle.run_id,
                        status="started",
                    )
                )
            except Exception as e:
                logger.error("temporal_workflow_failed", error=str(e), traceback=traceback.format_exc())
                research.status = "failed"
                raise HTTPException(status_code=500, detail=f"Failed to start workflow: {e!s}")
    except Exception as e:
        logger.error("research_creation_failed", error=str(e), traceback=traceback.format_exc())
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Internal database error: {e!s}")
