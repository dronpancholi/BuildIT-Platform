"""
SEO Platform — Semantic Operational Memory Endpoints
=====================================================
REST endpoints exposing memory storage, retrieval, search, lineage,
linking, operational context reconstruction, prospect history,
and campaign timeline.

All memory is advisory — it provides context for recommendations and UI,
NOT execution decisions.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from seo_platform.services.semantic_memory import semantic_memory

router = APIRouter()


@router.put("")
async def store_memory(payload: dict) -> dict:
    """Store operational memory in Redis."""
    namespace = payload.get("namespace", "")
    key = payload.get("key", "")
    content = payload.get("content", {})
    metadata = payload.get("metadata", {})
    ttl_days = payload.get("ttl_days", 90)

    if not namespace or not key:
        raise HTTPException(status_code=400, detail="namespace and key are required")
    if namespace not in ("workflow", "prospect", "campaign", "outreach", "keyword", "citation"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid namespace. Valid: workflow, prospect, campaign, outreach, keyword, citation",
        )

    try:
        entry = await semantic_memory.store_memory(namespace, key, content, metadata, ttl_days)
        return {"success": True, "data": entry.model_dump()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{namespace}/{key}")
async def get_memory(namespace: str, key: str) -> dict:
    """Retrieve a stored memory entry."""
    try:
        entry = await semantic_memory.get_memory(namespace, key)
        if not entry:
            raise HTTPException(status_code=404, detail="Memory not found")
        return {"success": True, "data": entry.model_dump()}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_memories(
    namespace: str = Query(..., description="Memory namespace"),
    tags: str = Query("", description="Comma-separated tag filter"),
    limit: int = Query(20, description="Max results"),
) -> dict:
    """Search memories by namespace and tags."""
    query_tags = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    try:
        entries = await semantic_memory.search_memory(namespace, query_tags, limit)
        return {"success": True, "data": [e.model_dump() for e in entries]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lineage/{key}")
async def get_memory_lineage(key: str) -> dict:
    """Trace memory change history."""
    try:
        lineage = await semantic_memory.get_memory_lineage(key)
        return {"success": True, "data": [l.model_dump() for l in lineage]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/link")
async def link_memories(payload: dict) -> dict:
    """Link two memories with a typed relationship."""
    source_key = payload.get("source_key", "")
    target_key = payload.get("target_key", "")
    relationship_type = payload.get("relationship_type", "")

    if not source_key or not target_key or not relationship_type:
        raise HTTPException(status_code=400, detail="source_key, target_key, and relationship_type are required")

    try:
        link = await semantic_memory.link_memories(source_key, target_key, relationship_type)
        return {"success": True, "data": link.model_dump()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/context/{workflow_run_id}")
async def reconstruct_operational_context(
    workflow_run_id: str,
    tenant_id: UUID = Query(..., description="Tenant ID"),
) -> dict:
    """Reconstruct full operational context for a workflow execution."""
    try:
        context = await semantic_memory.reconstruct_operational_context(tenant_id, workflow_run_id)
        return {"success": True, "data": context.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prospect/{prospect_domain}")
async def get_prospect_history(
    prospect_domain: str,
    tenant_id: UUID = Query(..., description="Tenant ID"),
) -> dict:
    """Get full interaction timeline for a prospect."""
    try:
        history = await semantic_memory.get_prospect_history(tenant_id, prospect_domain)
        return {"success": True, "data": [h.model_dump() for h in history]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/campaign/{campaign_id}")
async def get_campaign_timeline(campaign_id: UUID) -> dict:
    """Get full campaign execution timeline."""
    try:
        timeline = await semantic_memory.get_campaign_timeline(campaign_id)
        return {"success": True, "data": [m.model_dump() for m in timeline]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Task 7b — Advanced Operational Memory Endpoints
# ---------------------------------------------------------------------------


@router.post("/long-term-workflow")
async def store_long_term_workflow_memory(payload: dict) -> dict:
    """Store enriched long-term workflow memory with LLM summarization."""
    workflow_id = payload.get("workflow_id", "")
    workflow_type = payload.get("workflow_type", "")
    execution_data = payload.get("execution_data", {})

    if not workflow_id or not workflow_type:
        raise HTTPException(status_code=400, detail="workflow_id and workflow_type are required")

    try:
        entry = await semantic_memory.store_long_term_workflow_memory(
            workflow_id, workflow_type, execution_data,
        )
        return {"success": True, "data": entry.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/organizational-memory")
async def get_organizational_memory(
    org_id: str = Query(..., description="Organization identifier"),
) -> dict:
    """Reconstruct organization-level operational memory."""
    try:
        report = await semantic_memory.get_organization_operational_memory(org_id)
        return {"success": True, "data": report.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/infrastructure-history")
async def store_infrastructure_history(payload: dict) -> dict:
    """Store infrastructure history event in memory."""
    component = payload.get("component", "")
    event_data = payload.get("event_data", {})

    if not component or not event_data:
        raise HTTPException(status_code=400, detail="component and event_data are required")

    try:
        entry = await semantic_memory.store_infrastructure_history(component, event_data)
        return {"success": True, "data": entry.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/incident-memory")
async def reconstruct_incident_memory(
    incident_id: str = Query(..., description="Incident identifier"),
) -> dict:
    """Reconstruct incident from memory entries across all namespaces."""
    try:
        reconstruction = await semantic_memory.reconstruct_incident_memory(incident_id)
        return {"success": True, "data": reconstruction.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/replay-cognition")
async def replay_operational_cognition(
    workflow_id: str = Query(..., description="Workflow identifier"),
) -> dict:
    """Replay operational cognition from memory."""
    try:
        replay = await semantic_memory.replay_operational_cognition(workflow_id)
        return {"success": True, "data": replay.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/historical-learnings")
async def get_historical_optimization_learnings() -> dict:
    """Analyze optimization history and extract learning patterns."""
    try:
        report = await semantic_memory.learn_from_historical_optimizations()
        return {"success": True, "data": report.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
