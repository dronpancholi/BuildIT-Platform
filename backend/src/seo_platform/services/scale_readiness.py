from __future__ import annotations

import statistics
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


class TenantCapacityUsage(BaseModel):
    active_workflows: int = 0
    campaign_count: int = 0
    email_volume_7d: int = 0
    scraping_volume: int = 0
    llm_inference_count: int = 0
    keyword_count: int = 0
    cluster_count: int = 0
    prospect_count: int = 0
    storage_estimate_mb: float = 0.0


class TenantCapacityReport(BaseModel):
    tenant_id: UUID
    usage: TenantCapacityUsage
    estimated_limit: TenantCapacityUsage
    cpu_usage_pct: float = 0.0
    memory_usage_pct: float = 0.0
    storage_usage_pct: float = 0.0
    overall_capacity_pct: float = 0.0
    needs_scale_up: bool = False
    recommendations: list[str] = Field(default_factory=list)


class PartitionRecommendation(BaseModel):
    queue_name: str
    current_depth: int
    growth_rate: float
    worker_count: int
    recommended_partitions: int
    reason: str


class WorkerScalingRecommendation(BaseModel):
    queue_name: str
    pending_tasks: int
    active_workers: int
    max_concurrency: int
    utilization_pct: float
    recommended_action: str
    recommended_count: int | None = None
    reason: str


class InfraScalingEstimate(BaseModel):
    db_connections_current: int = 0
    db_connections_max: int = 50
    db_connection_pool_pct: float = 0.0
    redis_memory_estimate_mb: float = 0.0
    redis_max_memory_mb: float = 256.0
    redis_memory_pct: float = 0.0
    kafka_partition_count: int = 0
    temporal_workflow_count: int = 0


class ScalingRecommendations(BaseModel):
    tenant_capacity: list[TenantCapacityReport] = Field(default_factory=list)
    queue_partitions: list[PartitionRecommendation] = Field(default_factory=list)
    worker_scaling: list[WorkerScalingRecommendation] = Field(default_factory=list)
    infra_scaling: InfraScalingEstimate = Field(default_factory=InfraScalingEstimate)
    urgent_actions: list[str] = Field(default_factory=list)


class ScaleReadinessService:

    async def analyze_tenant_capacity(self, tenant_id: UUID) -> TenantCapacityReport:
        usage = TenantCapacityUsage()
        limits = TenantCapacityUsage(
            active_workflows=100,
            campaign_count=50,
            email_volume_7d=50000,
            scraping_volume=100000,
            llm_inference_count=10000,
            keyword_count=500000,
            cluster_count=50000,
            prospect_count=200000,
            storage_estimate_mb=10240,
        )

        try:
            from sqlalchemy import func, select

            from seo_platform.core.database import get_tenant_session

            async with get_tenant_session(tenant_id) as session:
                from seo_platform.models.tenant import Campaign

                campaign_result = await session.execute(
                    select(func.count()).select_from(Campaign).where(Campaign.tenant_id == tenant_id)
                )
                usage.campaign_count = campaign_result.scalar_one() or 0

                from seo_platform.models.keyword import Keyword, KeywordCluster

                keyword_result = await session.execute(
                    select(func.count()).select_from(Keyword).where(Keyword.tenant_id == tenant_id)
                )
                usage.keyword_count = keyword_result.scalar_one() or 0

                cluster_result = await session.execute(
                    select(func.count()).select_from(KeywordCluster).where(KeywordCluster.tenant_id == tenant_id)
                )
                usage.cluster_count = cluster_result.scalar_one() or 0

                try:
                    from seo_platform.models.communication import OutreachEmail

                    email_cutoff = datetime.now(UTC) - timedelta(days=7)
                    email_result = await session.execute(
                        select(func.count()).select_from(OutreachEmail).where(
                            OutreachEmail.tenant_id == tenant_id,
                            OutreachEmail.sent_at >= email_cutoff,
                        )
                    )
                    usage.email_volume_7d = email_result.scalar_one() or 0
                except Exception:
                    pass

                try:
                    from seo_platform.models.backlink import Prospect

                    prospect_result = await session.execute(
                        select(func.count()).select_from(Prospect).where(Prospect.tenant_id == tenant_id)
                    )
                    usage.prospect_count = prospect_result.scalar_one() or 0
                except Exception:
                    pass
        except Exception as e:
            logger.warning("tenant_capacity_db_query_failed", tenant_id=str(tenant_id), error=str(e))

        try:
            from temporalio.client import WorkflowExecutionStatus

            from seo_platform.core.temporal_client import get_temporal_client

            client = await get_temporal_client()
            now = datetime.now(UTC)
            window_start = now - timedelta(hours=1)
            query = f"StartTime >= '{window_start.isoformat()}'"
            wf_count = 0
            async for _ in client.list_workflows(query=query):
                wf_count += 1
            usage.active_workflows = wf_count
        except Exception as e:
            logger.warning("temporal_query_failed", error=str(e))

        try:
            from prometheus_client.registry import REGISTRY

            for metric in REGISTRY.collect():
                if metric.name == "seo_llm_requests_total":
                    for sample in metric.samples:
                        usage.llm_inference_count += int(sample.value)
        except Exception:
            pass

        total_records = usage.keyword_count + usage.cluster_count + usage.prospect_count
        usage.storage_estimate_mb = round(total_records * 0.005, 2)

        cpu_pct = min(100.0, (usage.active_workflows / max(limits.active_workflows, 1)) * 100)
        storage_pct = min(100.0, (usage.storage_estimate_mb / max(limits.storage_estimate_mb, 1)) * 100)
        overall = round((cpu_pct + storage_pct) / 2, 1)

        recommendations: list[str] = []
        if cpu_pct > 80:
            recommendations.append("High active workflow count — consider increasing Temporal worker pool")
        if storage_pct > 80:
            recommendations.append("Storage approaching limits — consider data archival or partition")
        if usage.campaign_count > limits.campaign_count * 0.8:
            recommendations.append("Campaign count near limit — evaluate campaign lifecycle policies")

        return TenantCapacityReport(
            tenant_id=tenant_id,
            usage=usage,
            estimated_limit=limits,
            cpu_usage_pct=round(cpu_pct, 1),
            memory_usage_pct=round(cpu_pct, 1),
            storage_usage_pct=round(storage_pct, 1),
            overall_capacity_pct=overall,
            needs_scale_up=overall > 80,
            recommendations=recommendations,
        )

    async def estimate_queue_partitions(self) -> list[PartitionRecommendation]:
        try:
            from seo_platform.core.redis import get_redis

            redis = await get_redis()
            queue_depth_threshold = 1000
            recommendations: list[PartitionRecommendation] = []

            queue_names = [
                "seo-platform-onboarding",
                "seo-platform-ai-orchestration",
                "seo-platform-seo-intelligence",
                "seo-platform-backlink-engine",
                "seo-platform-communication",
                "seo-platform-reporting",
            ]

            for queue_name in queue_names:
                try:
                    depth_key = f"temporal:queue_depth:{queue_name}"
                    depth_str = await redis.get(depth_key)
                    depth = int(depth_str) if depth_str else 0

                    worker_key = f"temporal:worker_count:{queue_name}"
                    worker_str = await redis.get(worker_key)
                    workers = int(worker_str) if worker_str else 2

                    history_key = f"temporal:queue_growth:{queue_name}"
                    history_str = await redis.get(history_key)
                    growth_rate = float(history_str) if history_str else 0.0

                    recommended = 1
                    reason = "Queue depth within normal range"
                    if depth > queue_depth_threshold:
                        recommended = max(2, depth // queue_depth_threshold)
                        if recommended > 10:
                            recommended = 10
                        reason = f"Queue depth ({depth}) exceeds threshold ({queue_depth_threshold})"
                    elif growth_rate > 10:
                        recommended = 2
                        reason = f"High growth rate ({growth_rate:.1f} tasks/s)"

                    recommendations.append(PartitionRecommendation(
                        queue_name=queue_name,
                        current_depth=depth,
                        growth_rate=round(growth_rate, 2),
                        worker_count=workers,
                        recommended_partitions=recommended,
                        reason=reason,
                    ))
                except Exception as e:
                    logger.warning("queue_analysis_failed", queue=queue_name, error=str(e))
                    recommendations.append(PartitionRecommendation(
                        queue_name=queue_name,
                        current_depth=0,
                        growth_rate=0.0,
                        worker_count=2,
                        recommended_partitions=1,
                        reason="Unable to read queue metrics",
                    ))

            return recommendations

        except Exception as e:
            logger.warning("queue_partition_estimation_failed", error=str(e))
            return []

    async def analyze_worker_scaling(self) -> list[WorkerScalingRecommendation]:
        try:
            from seo_platform.core.redis import get_redis

            redis = await get_redis()
            recommendations: list[WorkerScalingRecommendation] = []

            queue_names = [
                "seo-platform-onboarding",
                "seo-platform-ai-orchestration",
                "seo-platform-seo-intelligence",
                "seo-platform-backlink-engine",
                "seo-platform-communication",
                "seo-platform-reporting",
            ]

            for queue_name in queue_names:
                try:
                    depth_key = f"temporal:queue_depth:{queue_name}"
                    depth_str = await redis.get(depth_key)
                    pending = int(depth_str) if depth_str else 0

                    worker_key = f"temporal:worker_count:{queue_name}"
                    worker_str = await redis.get(worker_key)
                    active_workers = int(worker_str) if worker_str else 2

                    from seo_platform.config import get_settings
                    settings = get_settings()
                    max_concurrency = settings.temporal.max_concurrent_activities

                    effective_capacity = active_workers * max_concurrency
                    utilization = (pending / max(effective_capacity, 1)) * 100
                    utilization = min(100.0, utilization)

                    action = "maintain"
                    recommended = None
                    reason = "Utilization within normal range"

                    if utilization > 80:
                        recommended = active_workers + 1
                        if recommended > 10:
                            recommended = 10
                        action = "scale_up"
                        reason = f"Utilization {utilization:.0f}% exceeds 80% threshold"
                    elif utilization < 20 and active_workers > 2:
                        recommended = max(2, active_workers - 1)
                        action = "scale_down"
                        reason = f"Utilization {utilization:.0f}% below 20% threshold with {active_workers} workers"

                    recommendations.append(WorkerScalingRecommendation(
                        queue_name=queue_name,
                        pending_tasks=pending,
                        active_workers=active_workers,
                        max_concurrency=max_concurrency,
                        utilization_pct=round(utilization, 1),
                        recommended_action=action,
                        recommended_count=recommended if recommended else active_workers,
                        reason=reason,
                    ))
                except Exception as e:
                    logger.warning("worker_analysis_failed", queue=queue_name, error=str(e))

            return recommendations

        except Exception as e:
            logger.warning("worker_scaling_analysis_failed", error=str(e))
            return []

    async def estimate_infra_scaling(self) -> InfraScalingEstimate:
        estimate = InfraScalingEstimate()

        try:
            from seo_platform.config import get_settings
            settings = get_settings()

            estimate.db_connections_max = settings.database.pool_size + settings.database.max_overflow
            estimate.db_connections_current = settings.database.pool_size
            estimate.db_connection_pool_pct = round(
                (estimate.db_connections_current / max(estimate.db_connections_max, 1)) * 100, 1
            )

            try:
                from seo_platform.core.redis import get_redis
                redis = await get_redis()
                info = await redis.info("memory")
                used_memory = info.get("used_memory", 0)
                estimate.redis_memory_estimate_mb = round(used_memory / (1024 * 1024), 1)
                estimate.redis_memory_pct = round(
                    (estimate.redis_memory_estimate_mb / max(estimate.redis_max_memory_mb, 1)) * 100, 1
                )
            except Exception:
                pass

            try:
                from seo_platform.core.temporal_client import get_temporal_client
                client = await get_temporal_client()
                now = datetime.now(UTC)
                window_start = now - timedelta(hours=1)
                query = f"StartTime >= '{window_start.isoformat()}'"
                wf_count = 0
                async for _ in client.list_workflows(query=query):
                    wf_count += 1
                estimate.temporal_workflow_count = wf_count
            except Exception:
                pass

        except Exception as e:
            logger.warning("infra_scaling_estimation_failed", error=str(e))

        return estimate

    async def get_scaling_recommendations(self) -> ScalingRecommendations:
        from seo_platform.core.database import get_session

        tenant_capacity: list[TenantCapacityReport] = []

        try:
            from sqlalchemy import select

            from seo_platform.models.tenant import Tenant

            async with get_session() as session:
                result = await session.execute(select(Tenant.id))
                tenant_ids = [row[0] for row in result]

            for tid in tenant_ids[:20]:
                try:
                    report = await self.analyze_tenant_capacity(tid)
                    tenant_capacity.append(report)
                except Exception as e:
                    logger.warning("tenant_capacity_failed", tenant_id=str(tid), error=str(e))
        except Exception as e:
            logger.warning("tenant_list_failed", error=str(e))

        queue_partitions = await self.estimate_queue_partitions()
        worker_scaling = await self.analyze_worker_scaling()
        infra_scaling = await self.estimate_infra_scaling()

        urgent_actions = []
        for report in tenant_capacity:
            if report.needs_scale_up:
                urgent_actions.append(
                    f"Tenant {report.tenant_id} at {report.overall_capacity_pct}% capacity — scale recommended"
                )
        for qp in queue_partitions:
            if qp.recommended_partitions > 1:
                urgent_actions.append(
                    f"Queue {qp.queue_name} recommends {qp.recommended_partitions} partitions (depth: {qp.current_depth})"
                )
        for ws in worker_scaling:
            if ws.recommended_action == "scale_up":
                urgent_actions.append(
                    f"Worker pool {ws.queue_name} recommends scale up ({ws.utilization_pct:.0f}% utilization)"
                )

        return ScalingRecommendations(
            tenant_capacity=tenant_capacity,
            queue_partitions=queue_partitions,
            worker_scaling=worker_scaling,
            infra_scaling=infra_scaling,
            urgent_actions=urgent_actions[:10],
        )


scale_readiness = ScaleReadinessService()
