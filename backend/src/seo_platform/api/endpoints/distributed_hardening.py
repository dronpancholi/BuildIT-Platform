from __future__ import annotations

from seo_platform.core.auth import get_validated_tenant_id
from fastapi import APIRouter, Body, Query
from pydantic import BaseModel

from seo_platform.services.distributed_hardening import distributed_hardening

router = APIRouter()


class KafkaRecoverRequest(BaseModel):
    consumer_group: str


@router.get("/kafka-health")
async def get_kafka_health() -> dict:
    report = await distributed_hardening.check_kafka_partition_health()
    return {"success": True, "data": report.to_dict()}


@router.post("/recover-kafka")
async def recover_kafka_consumer(request: KafkaRecoverRequest) -> dict:
    result = await distributed_hardening.recover_kafka_consumer(request.consumer_group)
    return {"success": True, "data": result}


@router.get("/redis-recovery")
async def get_redis_recovery_state() -> dict:
    report = await distributed_hardening.check_redis_recovery_state()
    return {"success": True, "data": report.to_dict()}


@router.post("/recover-redis")
async def recover_redis_state() -> dict:
    result = await distributed_hardening.recover_redis_state()
    return {"success": True, "data": result.to_dict()}


@router.get("/postgres-health")
async def get_postgres_health() -> dict:
    report = await distributed_hardening.check_postgres_connection_health()
    return {"success": True, "data": report.to_dict()}


@router.post("/recover-postgres")
async def recover_postgres_pool() -> dict:
    result = await distributed_hardening.recover_postgres_pool()
    return {"success": True, "data": result.to_dict()}


@router.get("/temporal-health")
async def get_temporal_health() -> dict:
    report = await distributed_hardening.check_temporal_connection_health()
    return {"success": True, "data": report.to_dict()}


@router.post("/recover-temporal")
async def recover_temporal_connection() -> dict:
    result = await distributed_hardening.recover_temporal_connection()
    return {"success": True, "data": result.to_dict()}


@router.get("/degradation")
async def get_system_degradation() -> dict:
    assessment = await distributed_hardening.assess_system_degradation()
    return {"success": True, "data": assessment.to_dict()}


@router.get("/dependency-graph")
async def get_dependency_graph() -> dict:
    graph = distributed_hardening.build_dependency_graph()
    return {"success": True, "data": graph.to_dict()}
