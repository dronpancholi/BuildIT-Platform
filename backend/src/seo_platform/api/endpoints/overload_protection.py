from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Body, Query
from pydantic import BaseModel

from seo_platform.services.overload_protection import overload_protection

router = APIRouter()


class ThrottleQueueRequest(BaseModel):
    queue_name: str


class ReleaseQueueRequest(BaseModel):
    queue_name: str


class AdjustScrapingRequest(BaseModel):
    target_concurrency: int


class IsolateOperationRequest(BaseModel):
    operation_type: str
    tenant_id: UUID | None = None


class RestoreOperationRequest(BaseModel):
    operation_type: str
    tenant_id: UUID | None = None


class EnforceQuotaRequest(BaseModel):
    tenant_id: UUID
    resource_type: str  # workflow | ai_inference | email


@router.get("/overload/queue-status")
async def get_queue_overload() -> dict:
    reports = await overload_protection.check_queue_overload()
    return {"success": True, "data": [r.to_dict() for r in reports], "count": len(reports)}


@router.post("/overload/throttle-queue")
async def throttle_queue(request: ThrottleQueueRequest) -> dict:
    config = await overload_protection.throttle_queue(request.queue_name)
    return {"success": True, "data": config.to_dict()}


@router.post("/overload/release-queue")
async def release_queue_throttle(request: ReleaseQueueRequest) -> dict:
    result = await overload_protection.release_queue_throttle(request.queue_name)
    return {"success": True, "data": result.to_dict()}


@router.get("/overload/scraping-throttle")
async def get_scraping_throttle() -> dict:
    state = await overload_protection.check_scraping_throttle()
    return {"success": True, "data": state.to_dict()}


@router.post("/overload/adjust-scraping")
async def adjust_scraping(request: AdjustScrapingRequest) -> dict:
    config = await overload_protection.adjust_scraping_concurrency(request.target_concurrency)
    return {"success": True, "data": config.to_dict()}


@router.get("/overload/ai-throttle")
async def get_ai_throttle(
    tenant_id: UUID | None = Query(None),
    task_type: str = Query("seo_analysis"),
) -> dict:
    check = await overload_protection.check_ai_throttle(tenant_id, task_type)
    return {"success": True, "data": check.to_dict()}


@router.get("/overload/pressure")
async def get_pressure_telemetry() -> dict:
    telemetry = await overload_protection.get_pressure_telemetry()
    return {"success": True, "data": telemetry.to_dict()}


@router.get("/overload/saturation-alerts")
async def get_saturation_alerts() -> dict:
    alerts = await overload_protection.get_saturation_alerts()
    return {"success": True, "data": [a.to_dict() for a in alerts], "count": len(alerts)}


@router.get("/overload/tenant-usage")
async def get_tenant_usage(tenant_id: UUID = Query(...)) -> dict:
    usage = await overload_protection.get_tenant_resource_usage(tenant_id)
    return {"success": True, "data": usage.to_dict()}


@router.post("/overload/enforce-quota")
async def enforce_quota(request: EnforceQuotaRequest) -> dict:
    result = await overload_protection.enforce_tenant_quota(
        request.tenant_id, request.resource_type,
    )
    return {"success": True, "data": result.to_dict()}
