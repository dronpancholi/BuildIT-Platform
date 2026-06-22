from __future__ import annotations

from seo_platform.core.auth import get_validated_tenant_id
from uuid import UUID

from fastapi import Depends,  APIRouter, HTTPException, Query

from seo_platform.services.semantic_search import semantic_search_service

router = APIRouter()


@router.post("/index")
async def index_semantic_content(
    tenant_id: UUID = Depends(get_validated_tenant_id),
) -> dict:
    try:
        stats = await semantic_search_service.index_all(tenant_id)
        return {"success": True, "data": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def semantic_search(
    tenant_id: UUID = Depends(get_validated_tenant_id),
    query: str = Query(..., description="Search query"),
    source: str | None = Query(None, description="Filter by source type"),
    limit: int = Query(10, ge=1, le=100),
) -> dict:
    if not query.strip():
        raise HTTPException(status_code=400, detail="Query is required")
    try:
        results = await semantic_search_service.search(tenant_id, query, source, limit)
        return {"success": True, "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
