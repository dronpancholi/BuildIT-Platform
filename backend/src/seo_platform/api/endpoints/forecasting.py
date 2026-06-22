from __future__ import annotations

from seo_platform.core.auth import get_validated_tenant_id
from uuid import UUID

from fastapi import Depends,  APIRouter, HTTPException, Query

from seo_platform.services.forecasting import forecasting_service

router = APIRouter()


@router.post("/revenue")
async def forecast_revenue(
    tenant_id: UUID = Depends(get_validated_tenant_id),
    periods: int = Query(12, ge=1, le=36, description="Number of forecast periods"),
) -> dict:
    try:
        result = await forecasting_service.forecast_revenue(tenant_id, periods)
        return {"success": True, "data": result.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/campaign")
async def forecast_campaign(
    tenant_id: UUID = Depends(get_validated_tenant_id),
    campaign_id: UUID = Query(..., description="Campaign ID"),
    periods: int = Query(12, ge=1, le=36),
) -> dict:
    try:
        result = await forecasting_service.forecast_campaign(tenant_id, campaign_id, periods)
        return {"success": True, "data": result.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/customer")
async def forecast_customer(
    tenant_id: UUID = Depends(get_validated_tenant_id),
    customer_id: UUID = Query(..., description="Customer ID"),
    periods: int = Query(12, ge=1, le=36),
) -> dict:
    try:
        result = await forecasting_service.forecast_customer(tenant_id, customer_id, periods)
        return {"success": True, "data": result.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/backtest")
async def backtest_forecast(
    tenant_id: UUID = Depends(get_validated_tenant_id),
) -> dict:
    try:
        result = await forecasting_service.backtest_revenue(tenant_id)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
