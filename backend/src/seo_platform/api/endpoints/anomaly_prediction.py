"""
SEO Platform — Anomaly Prediction Endpoints
==============================================
REST endpoints for operational anomaly prediction.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query

from seo_platform.services.anomaly_prediction import anomaly_prediction

router = APIRouter()


@router.get("/anomaly-prediction/retry-storms")
async def predict_retry_storms(
    lookahead_minutes: int = Query(15, description="Minutes to look ahead"),
) -> dict:
    """Predict imminent retry storms based on retry rate acceleration."""
    prediction = await anomaly_prediction.predict_retry_storms(lookahead_minutes)
    return {"success": True, "data": prediction.model_dump()}


@router.get("/anomaly-prediction/worker-failures")
async def predict_worker_failures(
    lookahead_minutes: int = Query(10, description="Minutes to look ahead"),
) -> dict:
    """Predict worker failures based on heartbeats, failure rates, and resource exhaustion."""
    predictions = await anomaly_prediction.predict_worker_failures(lookahead_minutes)
    return {"success": True, "data": [p.model_dump() for p in predictions]}


@router.get("/anomaly-prediction/event-propagation")
async def detect_event_propagation_anomalies() -> dict:
    """Detect unusual event propagation patterns including consumer lag and missing chains."""
    anomalies = await anomaly_prediction.detect_event_propagation_anomalies()
    return {"success": True, "data": [a.model_dump() for a in anomalies]}


@router.get("/anomaly-prediction/workflow-deadlocks")
async def predict_workflow_deadlocks() -> dict:
    """Predict workflows that may deadlock due to signals, approvals, or circular deps."""
    predictions = await anomaly_prediction.predict_workflow_deadlocks()
    return {"success": True, "data": [p.model_dump() for p in predictions]}


@router.get("/anomaly-prediction/scraping")
async def detect_scraping_anomalies() -> dict:
    """Detect unusual scraping behavior: confidence drops, selector failures, CAPTCHA spikes."""
    anomalies = await anomaly_prediction.detect_scraping_anomalies()
    return {"success": True, "data": [a.model_dump() for a in anomalies]}


@router.get("/anomaly-prediction/ai-quality")
async def detect_ai_quality_anomalies() -> dict:
    """Detect AI quality degradation: confidence drops, schema repair spikes, fallback increases."""
    anomalies = await anomaly_prediction.detect_ai_quality_anomalies()
    return {"success": True, "data": [a.model_dump() for a in anomalies]}


@router.get("/anomaly-prediction/communication")
async def detect_communication_anomalies(
    tenant_id: Optional[str] = Query(None, description="Tenant UUID"),
) -> dict:
    """Detect email communication issues: bounce rate spikes, deliverability drops, provider errors."""
    tid = UUID(tenant_id) if tenant_id else UUID("00000000-0000-0000-0000-000000000000")
    anomalies = await anomaly_prediction.detect_communication_anomalies(tid)
    return {"success": True, "data": [a.model_dump() for a in anomalies]}


@router.get("/anomaly-prediction/dashboard")
async def get_anomaly_intelligence_dashboard() -> dict:
    """Return comprehensive anomaly intelligence dashboard."""
    dashboard = await anomaly_prediction.get_anomaly_intelligence_dashboard()
    return {"success": True, "data": dashboard.model_dump()}
