from __future__ import annotations

import statistics
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from seo_platform.config import get_settings
from seo_platform.core.logging import get_logger
from seo_platform.llm.gateway import llm_gateway

logger = get_logger(__name__)

COST_PER_TOKEN: dict[str, tuple[float, float]] = {
    "DeepSeek-V4-Pro": (0.005, 0.015),
    "Gemma 4 31B IT": (0.00015, 0.0006),
    "MiniMax M2.7": (0.001, 0.002),
    "NVIDIA-Nemotron-3-Super-120B-A12B": (0.002, 0.004),
    "nvidia/nv-embedqa-e5-v5": (0.0001, 0.0001),
}


class TaskTypeInferenceStats(BaseModel):
    task_type: str
    total_inferences: int
    avg_latency_ms: float
    avg_input_tokens: float
    avg_output_tokens: float
    avg_confidence: float
    total_cost: float
    model_breakdown: dict[str, int] = Field(default_factory=dict)


class InferenceAnalytics(BaseModel):
    time_window_hours: int
    total_inferences: int
    total_cost: float
    per_task_type: list[TaskTypeInferenceStats] = Field(default_factory=list)


class PromptPerformanceEntry(BaseModel):
    template_id: str
    total_calls: int
    avg_token_count: float
    schema_repair_count: int
    schema_repair_rate: float
    avg_retry_count: float
    cached_count: int
    cached_ratio: float


class HallucinationEvent(BaseModel):
    inference_id: str | None = None
    tenant_id: UUID
    task_type: str
    model: str
    confidence_score: float
    timestamp: str
    reasons: list[str] = Field(default_factory=list)


class HallucinationScanResult(BaseModel):
    tenant_id: UUID
    total_inferences_scanned: int
    potential_hallucinations: list[HallucinationEvent] = Field(default_factory=list)
    alert_count: int


class DriftAlert(BaseModel):
    task_type: str
    baseline_mean: float
    baseline_std: float
    current_mean: float
    current_count: int
    deviation_z: float


class OperationalMetrics(BaseModel):
    circuit_state: str
    kill_switch_active: bool
    kill_switch_reason: str | None = None
    rate_limit_saturation_pct: float
    fallback_count: int
    overall_reliability_score: float


class AIOperationalizationService:

    async def get_inference_analytics(self, time_window_hours: int = 24) -> InferenceAnalytics:
        try:
            from prometheus_client.registry import REGISTRY

            task_metrics: dict[str, dict[str, Any]] = {}

            for metric in REGISTRY.collect():
                if metric.name == "seo_llm_requests_total":
                    for sample in metric.samples:
                        if sample.labels.get("status") == "success":
                            task_type = sample.labels.get("task_type", "unknown")
                            model = sample.labels.get("model", "unknown")
                            if task_type not in task_metrics:
                                task_metrics[task_type] = {
                                    "total": 0,
                                    "latencies": [],
                                    "input_tokens": [],
                                    "output_tokens": [],
                                    "confidences": [],
                                    "models": {},
                                }
                            val = int(sample.value)
                            task_metrics[task_type]["total"] += val
                            task_metrics[task_type]["models"][model] = (
                                task_metrics[task_type]["models"].get(model, 0) + val
                            )

                elif metric.name == "seo_llm_latency_seconds":
                    for sample in metric.samples:
                        task_type = sample.labels.get("task_type", "unknown")
                        if task_type not in task_metrics:
                            task_metrics[task_type] = {
                                "total": 0,
                                "latencies": [],
                                "input_tokens": [],
                                "output_tokens": [],
                                "confidences": [],
                                "models": {},
                            }
                        task_metrics[task_type]["latencies"].append(sample.value * 1000)

                elif metric.name == "seo_llm_tokens_total":
                    for sample in metric.samples:
                        task_type = sample.labels.get("task_type", "unknown")
                        direction = sample.labels.get("direction", "input")
                        if task_type not in task_metrics:
                            task_metrics[task_type] = {
                                "total": 0,
                                "latencies": [],
                                "input_tokens": [],
                                "output_tokens": [],
                                "confidences": [],
                                "models": {},
                            }
                        if direction == "input":
                            task_metrics[task_type]["input_tokens"].append(sample.value)
                        else:
                            task_metrics[task_type]["output_tokens"].append(sample.value)

                elif metric.name == "seo_llm_confidence_score":
                    for sample in metric.samples:
                        task_type = sample.labels.get("task_type", "unknown")
                        if task_type not in task_metrics:
                            task_metrics[task_type] = {
                                "total": 0,
                                "latencies": [],
                                "input_tokens": [],
                                "output_tokens": [],
                                "confidences": [],
                                "models": {},
                            }
                        task_metrics[task_type]["confidences"].append(sample.value)

            per_task: list[TaskTypeInferenceStats] = []
            total_inferences = 0
            total_cost = 0.0

            for task_type, metrics in task_metrics.items():
                latencies = metrics["latencies"]
                confidences = metrics["confidences"]
                tokens_in = metrics["input_tokens"]
                tokens_out = metrics["output_tokens"]

                avg_lat = statistics.mean(latencies) if latencies else 0.0
                avg_conf = statistics.mean(confidences) if confidences else 0.0
                avg_in = statistics.mean(tokens_in) if tokens_in else 0.0
                avg_out = statistics.mean(tokens_out) if tokens_out else 0.0

                task_cost = 0.0
                for model, count in metrics["models"].items():
                    p_rate, c_rate = COST_PER_TOKEN.get(model, (0.001, 0.002))
                    task_cost += (avg_in * p_rate + avg_out * c_rate) * count / 1000
                if not task_cost and metrics["total"] > 0:
                    task_cost = metrics["total"] * 0.002

                per_task.append(TaskTypeInferenceStats(
                    task_type=task_type,
                    total_inferences=metrics["total"],
                    avg_latency_ms=round(avg_lat, 1),
                    avg_input_tokens=round(avg_in, 1),
                    avg_output_tokens=round(avg_out, 1),
                    avg_confidence=round(avg_conf, 4),
                    total_cost=round(task_cost, 4),
                    model_breakdown=metrics["models"],
                ))

                total_inferences += metrics["total"]
                total_cost += task_cost

            return InferenceAnalytics(
                time_window_hours=time_window_hours,
                total_inferences=total_inferences,
                total_cost=round(total_cost, 4),
                per_task_type=per_task,
            )

        except Exception as e:
            logger.warning("inference_analytics_failed", error=str(e))
            return InferenceAnalytics(time_window_hours=time_window_hours)

    async def analyze_prompt_performance(self) -> list[PromptPerformanceEntry]:
        try:
            from seo_platform.core.redis import get_redis

            redis = await get_redis()
            keys = await redis.keys("prompt_performance:*")
            results: list[PromptPerformanceEntry] = []

            for key in keys:
                template_id = key.replace("prompt_performance:", "", 1)
                entries = await redis.lrange(key, 0, -1)
                if not entries:
                    continue

                total_calls = len(entries)
                total_tokens = 0
                repairs = 0
                total_retries = 0
                cached_count = 0

                for entry in entries[:1000]:
                    try:
                        data = eval(entry)
                        total_tokens += data.get("token_count", 0)
                        if data.get("had_schema_repair"):
                            repairs += 1
                        total_retries += data.get("retry_count", 0)
                        if data.get("cached"):
                            cached_count += 1
                    except Exception:
                        continue

                results.append(PromptPerformanceEntry(
                    template_id=template_id,
                    total_calls=total_calls,
                    avg_token_count=round(total_tokens / total_calls, 1) if total_calls else 0.0,
                    schema_repair_count=repairs,
                    schema_repair_rate=round(repairs / total_calls, 4) if total_calls else 0.0,
                    avg_retry_count=round(total_retries / total_calls, 2) if total_calls else 0.0,
                    cached_count=cached_count,
                    cached_ratio=round(cached_count / total_calls, 4) if total_calls else 0.0,
                ))

            return sorted(results, key=lambda x: x.total_calls, reverse=True)

        except Exception as e:
            logger.warning("prompt_performance_analysis_failed", error=str(e))
            return []

    async def detect_hallucinations(self, tenant_id: UUID) -> HallucinationScanResult:
        try:
            from prometheus_client.registry import REGISTRY

            from seo_platform.core.redis import get_redis

            redis = await get_redis()
            events: list[HallucinationEvent] = []

            low_confidence_threshold = 0.5

            for metric in REGISTRY.collect():
                if metric.name == "seo_llm_confidence_score":
                    for sample in metric.samples:
                        if sample.value < low_confidence_threshold:
                            task_type = sample.labels.get("task_type", "unknown")
                            events.append(HallucinationEvent(
                                tenant_id=tenant_id,
                                task_type=task_type,
                                model="unknown",
                                confidence_score=sample.value,
                                timestamp=datetime.now(UTC).isoformat(),
                                reasons=["Low confidence score"],
                            ))

            schema_repair_keys = await redis.keys(f"prompt_performance:*")
            repair_count = 0
            for key in schema_repair_keys:
                entries = await redis.lrange(key, 0, 100)
                for entry in entries:
                    try:
                        data = eval(entry)
                        if data.get("had_schema_repair"):
                            repair_count += 1
                    except Exception:
                        continue

            if repair_count > 0:
                events.append(HallucinationEvent(
                    tenant_id=tenant_id,
                    task_type="aggregate",
                    model="unknown",
                    confidence_score=0.0,
                    timestamp=datetime.now(UTC).isoformat(),
                    reasons=[f"Schema repair events detected: {repair_count}"],
                ))

            fallback_key = "fallback_events"
            fallback_entries = await redis.lrange(fallback_key, 0, 100)
            if fallback_entries:
                events.append(HallucinationEvent(
                    tenant_id=tenant_id,
                    task_type="aggregate",
                    model="unknown",
                    confidence_score=0.0,
                    timestamp=datetime.now(UTC).isoformat(),
                    reasons=[f"Fallback events: {len(fallback_entries)} — may signal unreliable outputs"],
                ))

            return HallucinationScanResult(
                tenant_id=tenant_id,
                total_inferences_scanned=len(events) + 1,
                potential_hallucinations=events[:50],
                alert_count=len(events),
            )

        except Exception as e:
            logger.warning("hallucination_detection_failed", error=str(e))
            return HallucinationScanResult(
                tenant_id=tenant_id,
                total_inferences_scanned=0,
                alert_count=0,
            )

    async def detect_confidence_drift(self, time_window_hours: int = 48) -> list[DriftAlert]:
        try:
            from seo_platform.core.redis import get_redis

            from seo_platform.core.metrics import llm_confidence_score

            redis = await get_redis()
            alerts: list[DriftAlert] = []

            history_keys = await redis.keys("confidence_history:*")
            task_types_seen: set[str] = set()

            for key in history_keys:
                parts = key.split(":")
                if len(parts) >= 3:
                    task_type = parts[-1]
                    task_types_seen.add(task_type)

            for task_type in task_types_seen:
                all_scores_raw = await redis.zrange(
                    f"confidence_history:global:{task_type}", 0, -1, withscores=True
                ) if False else []

                recent_cutoff = (datetime.now(UTC).timestamp()) - (time_window_hours * 3600)
                baseline_cutoff = (datetime.now(UTC).timestamp()) - (time_window_hours * 2 * 3600)

                all_values: list[float] = []
                recent_values: list[float] = []

                for key in history_keys:
                    if not key.endswith(f":{task_type}"):
                        continue
                    entries = await redis.zrangebyscore(key, 0, "+inf", withscores=True)
                    for entry in entries:
                        ts = entry[0]
                        try:
                            score = float(entry[1])
                        except (ValueError, TypeError):
                            continue
                        all_values.append(score)
                        if float(ts) >= recent_cutoff:
                            recent_values.append(score)

                if len(all_values) < 10 or not recent_values:
                    continue

                baseline_mean = statistics.mean(all_values)
                baseline_std = statistics.stdev(all_values) if len(all_values) > 1 else 0.0
                current_mean = statistics.mean(recent_values)

                deviation_z = (baseline_mean - current_mean) / baseline_std if baseline_std > 0 else 0.0

                if deviation_z > 2.0:
                    alerts.append(DriftAlert(
                        task_type=task_type,
                        baseline_mean=round(baseline_mean, 4),
                        baseline_std=round(baseline_std, 4),
                        current_mean=round(current_mean, 4),
                        current_count=len(recent_values),
                        deviation_z=round(deviation_z, 4),
                    ))

            return alerts

        except Exception as e:
            logger.warning("confidence_drift_detection_failed", error=str(e))
            return []

    async def get_operational_metrics(self) -> OperationalMetrics:
        try:
            from seo_platform.core.kill_switch import kill_switch_service
            from prometheus_client.registry import REGISTRY

            circuit_state = llm_gateway._circuit.state.value if llm_gateway._circuit else "unknown"

            ks = await kill_switch_service.is_blocked("all_llm_calls")
            kill_switch_active = ks.blocked

            total_requests = 0
            total_fallback = 0
            for metric in REGISTRY.collect():
                if metric.name == "seo_llm_requests_total":
                    for sample in metric.samples:
                        total_requests += int(sample.value)

            from seo_platform.core.redis import get_redis
            redis = await get_redis()
            fallback_entries = await redis.lrange("fallback_events", 0, -1)
            total_fallback = len(fallback_entries or [])

            rate_saturation = 0.0
            try:
                from seo_platform.core.reliability import rate_limiter
                rate_saturation = 0.0
            except Exception:
                pass

            reliability = 1.0
            if total_requests > 0:
                reliability = max(0.0, 1.0 - (total_fallback / total_requests))
            if circuit_state == "open":
                reliability *= 0.5

            return OperationalMetrics(
                circuit_state=circuit_state,
                kill_switch_active=kill_switch_active,
                kill_switch_reason=ks.reason if kill_switch_active else None,
                rate_limit_saturation_pct=round(rate_saturation * 100, 1),
                fallback_count=total_fallback,
                overall_reliability_score=round(reliability, 4),
            )

        except Exception as e:
            logger.warning("operational_metrics_failed", error=str(e))
            return OperationalMetrics(
                circuit_state="unknown",
                kill_switch_active=False,
                rate_limit_saturation_pct=0.0,
                fallback_count=0,
                overall_reliability_score=0.0,
            )


ai_operationalization = AIOperationalizationService()
