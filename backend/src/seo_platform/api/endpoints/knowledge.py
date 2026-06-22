from __future__ import annotations

from seo_platform.core.auth import get_validated_tenant_id
from uuid import UUID

from fastapi import Depends,  APIRouter, HTTPException, Query, Path

from seo_platform.services.knowledge_graph import knowledge_graph_service

router = APIRouter()


@router.post("/rebuild")
async def rebuild_knowledge_graph(
    tenant_id: UUID = Depends(get_validated_tenant_id),
) -> dict:
    try:
        stats = await knowledge_graph_service.rebuild(tenant_id)
        return {"success": True, "data": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entity/{entity_id}")
async def get_entity(
    entity_id: UUID = Path(..., description="Graph entity ID"),
    tenant_id: UUID = Depends(get_validated_tenant_id),
) -> dict:
    entity = await knowledge_graph_service.get_entity(tenant_id, entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return {"success": True, "data": entity}


@router.get("/related/{entity_id}")
async def get_related_entities(
    entity_id: UUID = Path(..., description="Graph entity ID"),
    tenant_id: UUID = Depends(get_validated_tenant_id),
    depth: int = Query(1, ge=1, le=5, description="Traversal depth"),
    max_results: int = Query(20, ge=1, le=100, description="Max results"),
) -> dict:
    results = await knowledge_graph_service.get_related(tenant_id, entity_id, depth, max_results)
    return {"success": True, "data": results}


@router.get("/search")
async def search_graph(
    tenant_id: UUID = Depends(get_validated_tenant_id),
    query: str = Query(..., description="Search query"),
    entity_type: str | None = Query(None, description="Filter by entity type"),
    limit: int = Query(20, ge=1, le=100),
) -> dict:
    results = await knowledge_graph_service.search_entities(tenant_id, query, entity_type, limit)
    return {"success": True, "data": results}
