from __future__ import annotations

from fastapi import APIRouter, Query

from seo_platform.services.production_economics import production_economics

router = APIRouter()


@router.get("/production-economics/cost-forecast")
async def get_cost_forecast(
    horizon_days: int = Query(30, ge=7, le=365, description="Forecast horizon in days"),
):
    forecast = await production_economics.forecast_infra_costs(horizon_days)
    return {"success": True, "data": forecast.model_dump()}


@router.get("/production-economics/ai-inference-optimization")
async def get_ai_inference_optimization(
    service_id: str = Query(..., description="Service ID to optimize"),
):
    opt = await production_economics.optimize_ai_inference(service_id)
    return {"success": True, "data": opt.model_dump()}


@router.get("/production-economics/queue-efficiency")
async def get_queue_efficiency(
    queue_name: str = Query(..., description="Queue name to analyze"),
):
    efficiency = await production_economics.analyze_queue_efficiency(queue_name)
    return {"success": True, "data": efficiency.model_dump()}


@router.get("/production-economics/scraping-cost-optimization")
async def get_scraping_cost_optimization(
    source_type: str = Query(..., description="Source type to optimize"),
):
    opt = await production_economics.optimize_scraping_costs(source_type)
    return {"success": True, "data": opt.model_dump()}


@router.get("/production-economics/worker-allocation")
async def get_worker_allocation(
    workflow_type: str = Query(..., description="Workflow type to analyze"),
):
    alloc = await production_economics.optimize_worker_allocation(workflow_type)
    return {"success": True, "data": alloc.model_dump()}


@router.get("/production-economics/operational-roi")
async def get_operational_roi(
    initiative_id: str = Query(..., description="Initiative ID to calculate ROI for"),
):
    roi = await production_economics.calculate_operational_roi(initiative_id)
    return {"success": True, "data": roi.model_dump()}


@router.get("/production-economics/dynamic-infra-recommendations")
async def get_dynamic_infra_recommendations(
    scope: str = Query("platform", description="Scope for recommendations"),
):
    recs = await production_economics.generate_dynamic_infra_recommendations(scope)
    return {"success": True, "data": [r.model_dump() for r in recs]}


@router.get("/production-economics/efficiency-score")
async def get_efficiency_score(
    service_id: str = Query(..., description="Service ID to score"),
):
    score = await production_economics.calculate_efficiency_score(service_id)
    return {"success": True, "data": score.model_dump()}


@router.get("/production-economics/sustainability-analysis")
async def get_sustainability_analysis(
    service_id: str = Query(..., description="Service ID to analyze"),
):
    analysis = await production_economics.analyze_sustainability(service_id)
    return {"success": True, "data": analysis.model_dump()}
