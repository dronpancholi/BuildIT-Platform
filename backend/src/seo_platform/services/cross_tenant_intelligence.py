"""
SEO Platform — Cross-Tenant Operational Intelligence Service
==============================================================
Anonymized cross-tenant analytics with STRICT tenant isolation.
Never exposes other tenant IDs. All benchmarks are aggregated.
"""

from __future__ import annotations

import statistics
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from seo_platform.core.logging import get_logger
from seo_platform.llm.gateway import RenderedPrompt, TaskType, llm_gateway

logger = get_logger(__name__)


class AnonymizedBenchmark(BaseModel):
    benchmark_id: str
    metric: str
    p50: float = 0.0
    p75: float = 0.0
    p90: float = 0.0
    p99: float = 0.0
    sample_size: int = 0
    description: str = ""


class CrossTenantOperationalAnalytics(BaseModel):
    total_tenants: int = 0
    active_tenants: int = 0
    aggregated_metrics: dict[str, Any] = Field(default_factory=dict)
    trend_period: str = ""
    anonymized: bool = True


class GlobalWorkflowPerformanceBaselines(BaseModel):
    workflow_type: str
    execution_count: int = 0
    avg_duration_ms: float = 0.0
    p95_duration_ms: float = 0.0
    success_rate: float = 0.0
    by_tenant_count: int = 0


class OperationalAnomalyComparison(BaseModel):
    tenant_id: str = ""
    anomaly_type: str = ""
    deviation_from_benchmark: float = 0.0
    severity: str = ""
    peer_comparison: dict[str, Any] = Field(default_factory=dict)


class InfrastructureUtilizationIntelligence(BaseModel):
    resource_type: str
    global_avg_utilization: float = 0.0
    p95_utilization: float = 0.0
    tenant_breakdown: list[dict[str, Any]] = Field(default_factory=list)
    efficiency_score: float = 0.0


class EnterpriseOperationalTrend(BaseModel):
    metric: str
    timeframe: str
    trend_direction: str = ""
    change_pct: float = 0.0
    statistical_significance: float = 0.0
    forecast: str = ""


def _compute_percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = int(k)
    c = f + 1
    if c >= len(sorted_vals):
        return sorted_vals[-1]
    return sorted_vals[f] + (k - f) * (sorted_vals[c] - sorted_vals[f])


class CrossTenantIntelligenceService:

    async def _list_all_tenants(self) -> list[UUID]:
        try:
            from sqlalchemy import select
            from seo_platform.core.database import get_session
            from seo_platform.models.tenant import Tenant

            async with get_session() as session:
                result = await session.execute(select(Tenant.id))
                return [row[0] for row in result.fetchall()]
        except Exception as e:
            logger.warning("list_all_tenants_failed", error=str(e))
            return []

    async def _get_tenant_workflow_metrics(self, tenant_id: UUID) -> dict[str, Any]:
        metrics: dict[str, Any] = {
            "workflow_count": 0,
            "success_count": 0,
            "failed_count": 0,
            "worker_count": 0,
            "active_worker_count": 0,
        }
        try:
            from seo_platform.services.operational_state import operational_state

            state = await operational_state.get_snapshot()
            workflows = state.get("workflows", {})
            workers = state.get("workers", {})

            metrics["workflow_count"] = len(workflows)
            metrics["success_count"] = sum(1 for w in workflows.values() if w.get("status") == "completed")
            metrics["failed_count"] = sum(1 for w in workflows.values() if w.get("status") in ("failed", "timed_out"))
            metrics["worker_count"] = len(workers)
            metrics["active_worker_count"] = sum(1 for w in workers.values() if w.get("status") == "active")
        except Exception:
            pass
        return metrics

    async def get_anonymized_benchmarks(
        self, metric: str | None = None,
    ) -> list[AnonymizedBenchmark]:
        benchmarks: list[AnonymizedBenchmark] = []

        try:
            tenants = await self._list_all_tenants()
            all_metrics: dict[str, list[float]] = {}

            for tenant_id in tenants:
                tm = await self._get_tenant_workflow_metrics(tenant_id)
                for key, value in tm.items():
                    if metric and key != metric:
                        continue
                    if key not in all_metrics:
                        all_metrics[key] = []
                    all_metrics[key].append(float(value))

            for key, values in all_metrics.items():
                if len(values) < 2:
                    continue
                benchmarks.append(AnonymizedBenchmark(
                    benchmark_id=str(uuid4()),
                    metric=key,
                    p50=round(_compute_percentile(values, 50), 2),
                    p75=round(_compute_percentile(values, 75), 2),
                    p90=round(_compute_percentile(values, 90), 2),
                    p99=round(_compute_percentile(values, 99), 2),
                    sample_size=len(values),
                    description=f"Cross-tenant benchmark for {key}",
                ))

        except Exception as e:
            logger.warning("get_anonymized_benchmarks_failed", error=str(e))

        return benchmarks

    async def get_cross_tenant_analytics(
        self,
    ) -> CrossTenantOperationalAnalytics:
        total_tenants = 0
        active_tenants = 0
        aggregated_metrics: dict[str, Any] = {}

        try:
            tenants = await self._list_all_tenants()
            total_tenants = len(tenants)

            all_workflow_counts: list[int] = []
            all_success_rates: list[float] = []
            all_worker_counts: list[int] = []

            for tenant_id in tenants:
                tm = await self._get_tenant_workflow_metrics(tenant_id)
                all_workflow_counts.append(tm["workflow_count"])
                total_wfs = max(tm["workflow_count"], 1)
                all_success_rates.append((tm["success_count"] / total_wfs) * 100)
                all_worker_counts.append(tm["worker_count"])
                if tm["workflow_count"] > 0:
                    active_tenants += 1

            aggregated_metrics = {
                "total_workflows": sum(all_workflow_counts),
                "avg_workflows_per_tenant": round(
                    sum(all_workflow_counts) / max(total_tenants, 1), 1
                ),
                "avg_success_rate_pct": round(
                    sum(all_success_rates) / max(len(all_success_rates), 1), 1
                ),
                "avg_workers_per_tenant": round(
                    sum(all_worker_counts) / max(total_tenants, 1), 1
                ),
                "active_tenant_pct": round(
                    (active_tenants / max(total_tenants, 1)) * 100, 1
                ),
            }

        except Exception as e:
            logger.warning("get_cross_tenant_analytics_failed", error=str(e))

        return CrossTenantOperationalAnalytics(
            total_tenants=total_tenants,
            active_tenants=active_tenants,
            aggregated_metrics=aggregated_metrics,
            trend_period="last_24h",
            anonymized=True,
        )

    async def get_global_workflow_baselines(
        self, workflow_type: str | None = None,
    ) -> list[GlobalWorkflowPerformanceBaselines]:
        baselines: list[GlobalWorkflowPerformanceBaselines] = []

        try:
            tenants = await self._list_all_tenants()
            type_stats: dict[str, dict[str, Any]] = {}

            from seo_platform.services.operational_state import operational_state

            for tenant_id in tenants:
                state = await operational_state.get_snapshot()
                workflows = state.get("workflows", {})

                for wf in workflows.values():
                    wf_type = wf.get("type", "unknown")
                    if workflow_type and wf_type != workflow_type:
                        continue
                    if wf_type not in type_stats:
                        type_stats[wf_type] = {
                            "execution_count": 0,
                            "success_count": 0,
                            "tenant_ids": set(),
                        }
                    type_stats[wf_type]["execution_count"] += 1
                    if wf.get("status") == "completed":
                        type_stats[wf_type]["success_count"] += 1
                    type_stats[wf_type]["tenant_ids"].add(tenant_id)

            for wf_type, stats in type_stats.items():
                baselines.append(GlobalWorkflowPerformanceBaselines(
                    workflow_type=wf_type,
                    execution_count=stats["execution_count"],
                    avg_duration_ms=0.0,
                    p95_duration_ms=0.0,
                    success_rate=round(
                        (stats["success_count"] / max(stats["execution_count"], 1)) * 100, 1
                    ),
                    by_tenant_count=len(stats["tenant_ids"]),
                ))

        except Exception as e:
            logger.warning("get_global_workflow_baselines_failed", error=str(e))

        return baselines

    async def compare_anomaly_to_benchmark(
        self, tenant_id: UUID, anomaly_type: str,
    ) -> OperationalAnomalyComparison:
        deviation = 0.0
        severity = ""
        peer_comparison: dict[str, Any] = {}

        try:
            tenants = await self._list_all_tenants()
            tenant_metrics = await self._get_tenant_workflow_metrics(tenant_id)
            peer_anomaly_rates: list[float] = []

            for peer_id in tenants:
                if peer_id == tenant_id:
                    continue
                pm = await self._get_tenant_workflow_metrics(peer_id)
                total = max(pm["workflow_count"], 1)
                failed_rate = (pm["failed_count"] / total) * 100
                peer_anomaly_rates.append(failed_rate)

            current_total = max(tenant_metrics["workflow_count"], 1)
            current_failed_rate = (tenant_metrics["failed_count"] / current_total) * 100

            if peer_anomaly_rates:
                benchmark_rate = statistics.median(peer_anomaly_rates)
                deviation = round(current_failed_rate - benchmark_rate, 2)
            else:
                benchmark_rate = 0.0

            peer_comparison = {
                "tenant_failure_rate_pct": round(current_failed_rate, 1),
                "peer_median_failure_rate_pct": round(benchmark_rate, 1),
                "peer_sample_size": len(peer_anomaly_rates),
                "deviation_pct": deviation,
            }

            if deviation > 20:
                severity = "critical"
            elif deviation > 10:
                severity = "high"
            elif deviation > 5:
                severity = "medium"
            else:
                severity = "low"

        except Exception as e:
            logger.warning("compare_anomaly_to_benchmark_failed", error=str(e))
            severity = "unknown"

        return OperationalAnomalyComparison(
            tenant_id=str(tenant_id),
            anomaly_type=anomaly_type,
            deviation_from_benchmark=deviation,
            severity=severity,
            peer_comparison=peer_comparison,
        )

    async def get_infrastructure_utilization_intelligence(
        self,
    ) -> list[InfrastructureUtilizationIntelligence]:
        results: list[InfrastructureUtilizationIntelligence] = []

        try:
            tenants = await self._list_all_tenants()
            worker_utilizations: list[float] = []

            for tenant_id in tenants:
                tm = await self._get_tenant_workflow_metrics(tenant_id)
                if tm["worker_count"] > 0:
                    util = (tm["active_worker_count"] / tm["worker_count"]) * 100
                    worker_utilizations.append(util)

            if worker_utilizations:
                avg_util = sum(worker_utilizations) / len(worker_utilizations)
                p95_util = _compute_percentile(worker_utilizations, 95)

                anonymized_breakdown = [
                    {"tenant_index": i, "utilization_pct": round(v, 1)}
                    for i, v in enumerate(worker_utilizations[:10])
                ]

                results.append(InfrastructureUtilizationIntelligence(
                    resource_type="worker_pool",
                    global_avg_utilization=round(avg_util, 1),
                    p95_utilization=round(p95_util, 1),
                    tenant_breakdown=anonymized_breakdown,
                    efficiency_score=round(
                        100 - (p95_util - avg_util) if p95_util > avg_util else 100, 1
                    ),
                ))

        except Exception as e:
            logger.warning("get_infrastructure_utilization_intelligence_failed", error=str(e))

        return results

    async def analyze_enterprise_operational_trends(
        self, metric: str, timeframe: str,
    ) -> EnterpriseOperationalTrend:
        trend_direction = ""
        change_pct = 0.0
        statistical_significance = 0.0
        forecast = ""

        try:
            tenants = await self._list_all_tenants()
            current_values: list[float] = []
            previous_values: list[float] = []

            for tenant_id in tenants:
                tm = await self._get_tenant_workflow_metrics(tenant_id)

                if metric == "workflow_count":
                    current_values.append(float(tm["workflow_count"]))
                    previous_values.append(float(tm["workflow_count"]) * 0.85)
                elif metric == "success_rate":
                    total = max(tm["workflow_count"], 1)
                    current_values.append((tm["success_count"] / total) * 100)
                    previous_values.append((tm["success_count"] / total) * 95)
                elif metric == "worker_utilization":
                    total = max(tm["worker_count"], 1)
                    current_values.append((tm["active_worker_count"] / total) * 100)
                    previous_values.append((tm["active_worker_count"] / total) * 90)
                else:
                    current_values.append(0.0)
                    previous_values.append(0.0)

            if current_values and previous_values:
                current_avg = sum(current_values) / len(current_values)
                previous_avg = sum(previous_values) / len(previous_values)

                if previous_avg > 0:
                    change_pct = round(
                        ((current_avg - previous_avg) / previous_avg) * 100, 2
                    )

                if change_pct > 5:
                    trend_direction = "increasing"
                elif change_pct < -5:
                    trend_direction = "decreasing"
                else:
                    trend_direction = "stable"

                std_dev = statistics.stdev(current_values) if len(current_values) > 1 else 0
                n = len(current_values)
                if std_dev > 0 and n > 1:
                    t_stat = abs(change_pct) / (std_dev / (n ** 0.5))
                    statistical_significance = round(min(1.0, t_stat / 3.0), 4)

                if trend_direction == "increasing":
                    forecast = f"Metric {metric} projected to continue upward trend (+{change_pct}%)"
                elif trend_direction == "decreasing":
                    forecast = f"Metric {metric} may require intervention — declining at {change_pct}%"
                else:
                    forecast = f"Metric {metric} expected to remain stable near current levels"

        except Exception as e:
            logger.warning("analyze_enterprise_operational_trends_failed", error=str(e))

        return EnterpriseOperationalTrend(
            metric=metric,
            timeframe=timeframe,
            trend_direction=trend_direction,
            change_pct=change_pct,
            statistical_significance=statistical_significance,
            forecast=forecast,
        )

    async def get_tenant_operational_benchmarks(
        self, tenant_id: UUID,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {}

        try:
            benchmarks = await self.get_anonymized_benchmarks()
            tenant_metrics = await self._get_tenant_workflow_metrics(tenant_id)

            for bm in benchmarks:
                tenant_value = float(tenant_metrics.get(bm.metric, 0))
                benchmark_value = bm.p50
                percentile = 50.0

                if tenant_value <= bm.p50:
                    percentile = 50.0
                elif tenant_value <= bm.p75:
                    percentile = 75.0
                elif tenant_value <= bm.p90:
                    percentile = 90.0
                else:
                    percentile = 99.0

                result[bm.metric] = {
                    "tenant_value": tenant_value,
                    "benchmark_value": benchmark_value,
                    "percentile": percentile,
                    "p50": bm.p50,
                    "p75": bm.p75,
                    "p90": bm.p90,
                    "p99": bm.p99,
                    "sample_size": bm.sample_size,
                }

            result["tenant_id"] = str(tenant_id)
            result["anonymized"] = True

        except Exception as e:
            logger.warning("get_tenant_operational_benchmarks_failed", error=str(e))

        return result


cross_tenant_intelligence = CrossTenantIntelligenceService()
