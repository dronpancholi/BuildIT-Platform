from __future__ import annotations

from fastapi import APIRouter, Query

from seo_platform.services.orchestration_intelligence import orchestration_intelligence

router = APIRouter()


@router.get("/workflow-dependencies")
async def get_workflow_dependencies() -> dict:
    graph = await orchestration_intelligence.analyze_workflow_dependencies()
    return {"success": True, "data": graph.model_dump()}


@router.get("/dependency-violations")
async def get_dependency_violations() -> dict:
    violations = await orchestration_intelligence.detect_dependency_violations()
    return {
        "success": True,
        "data": [v.model_dump() for v in violations],
        "count": len(violations),
    }


@router.get("/event-topology")
async def get_event_topology(
    time_window_hours: int = Query(24, ge=1, le=720),
) -> dict:
    topology = await orchestration_intelligence.analyze_event_topology(time_window_hours)
    return {"success": True, "data": topology.model_dump()}


@router.get("/event-topology-anomalies")
async def get_event_topology_anomalies() -> dict:
    anomalies = await orchestration_intelligence.detect_event_topology_anomalies()
    return {
        "success": True,
        "data": [a.model_dump() for a in anomalies],
        "count": len(anomalies),
    }


@router.get("/infra-dependencies")
async def get_infra_dependencies() -> dict:
    graph = await orchestration_intelligence.analyze_infrastructure_dependencies()
    return {"success": True, "data": graph.model_dump()}


@router.get("/critical-paths")
async def get_critical_paths() -> dict:
    paths = await orchestration_intelligence.detect_critical_infrastructure_paths()
    return {
        "success": True,
        "data": [p.model_dump() for p in paths],
        "count": len(paths),
    }


@router.get("/bottlenecks")
async def get_bottlenecks(
    time_window_hours: int = Query(24, ge=1, le=720),
) -> dict:
    bottleneck_map = await orchestration_intelligence.map_orchestration_bottlenecks(
        time_window_hours,
    )
    return {"success": True, "data": bottleneck_map.model_dump()}


@router.get("/operational-graph")
async def get_operational_graph() -> dict:
    graph = await orchestration_intelligence.build_operational_graph()
    return {"success": True, "data": graph.model_dump()}


@router.get("/traverse-graph")
async def traverse_graph(
    start_node: str = Query(...),
    max_depth: int = Query(3, ge=1, le=10),
) -> dict:
    graph = await orchestration_intelligence.traverse_operational_graph(
        start_node, max_depth,
    )
    return {"success": True, "data": graph.model_dump()}


@router.get("/cross-system-awareness")
async def get_cross_system_awareness() -> dict:
    report = await orchestration_intelligence.get_cross_system_awareness()
    return {"success": True, "data": report.model_dump()}
