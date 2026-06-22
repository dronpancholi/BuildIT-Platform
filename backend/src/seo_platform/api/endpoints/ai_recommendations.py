from __future__ import annotations

from seo_platform.core.auth import get_validated_tenant_id
from uuid import UUID

from fastapi import Depends,  APIRouter, HTTPException, Query

from seo_platform.services.ai_recommendations import ai_recommendation_engine

router = APIRouter()


@router.get("/ai")
async def get_ai_recommendations(
    tenant_id: UUID = Depends(get_validated_tenant_id),
) -> dict:
    try:
        recs = await ai_recommendation_engine.get_recommendations(tenant_id)
        return {
            "success": True,
            "data": {
                category: [r.model_dump() for r in recs_list]
                for category, recs_list in recs.items()
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
