from __future__ import annotations

from seo_platform.core.auth import get_validated_tenant_id
from uuid import UUID

from fastapi import Depends,  APIRouter, HTTPException, Query

from seo_platform.services.campaign_agent import campaign_agent

router = APIRouter()


@router.post("/campaign/run")
async def run_campaign_agent(
    tenant_id: UUID = Depends(get_validated_tenant_id),
    campaign_id: UUID | None = Query(None, description="Optional campaign ID"),
) -> dict:
    try:
        result = await campaign_agent.run(tenant_id, campaign_id)
        return {"success": True, "data": result.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/campaign/history")
async def get_campaign_agent_history(
    tenant_id: UUID = Depends(get_validated_tenant_id),
) -> dict:
    return {"success": True, "data": []}
