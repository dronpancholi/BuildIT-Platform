from __future__ import annotations

from seo_platform.core.auth import get_validated_tenant_id
from uuid import UUID

from fastapi import Depends,  APIRouter, HTTPException, Query

from seo_platform.services.ai_query import ai_query_engine

router = APIRouter()


@router.post("/query")
async def ai_query(
    question: str = Query(..., description="Natural language query"),
    tenant_id: UUID = Depends(get_validated_tenant_id),
    execute: bool = Query(False, description="Execute SQL against database"),
) -> dict:
    if not question.strip():
        raise HTTPException(status_code=400, detail="Question is required")
    try:
        result = await ai_query_engine.execute_query(question, tenant_id)
        return {"success": True, "data": result.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
