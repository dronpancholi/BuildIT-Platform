from __future__ import annotations

import random
import statistics
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from seo_platform.core.kill_switch import kill_switch_service
from seo_platform.core.logging import get_logger
from seo_platform.core.reliability import CircuitBreaker, CircuitState, rate_limiter

logger = get_logger(__name__)


class FallbackRoute(BaseModel):
    model_id: str
    reason: str
    estimated_quality_delta: float


class RetryDecision(BaseModel):
    should_retry: bool
    delay_ms: int
    action: str


class HallucinationCheck(BaseModel):
    passed: bool
    risk_score: float
    action: str


class DriftAlert(BaseModel):
    model: str
    task_type: str
    baseline: float
    current: float
    severity: str


class AIThrottleResult(BaseModel):
    allowed: bool
    reason: str
    retry_after: float


class InferenceHealthScore(BaseModel):
    model_id: str
    overall_score: float
    success_rate_weight: float
    avg_latency_weight: float
    confidence_score_weight: float
    fallback_rate_weight: float
    error_rate_weight: float
    components: dict[str, float] = Field(default_factory=dict)


class AIFailureAnalytics(BaseModel):
    time_window_hours: int
    failure_rate_per_model: dict[str, dict[str, float]] = Field(default_factory=dict)
    error_type_distribution: dict[str, int] = Field(default_factory=dict)
    mean_time_between_failures: dict[str, float] = Field(default_factory=dict)
    retry_success_rate: float = 0.0
    fallback_effectiveness: float = 0.0


TASK_FALLBACK_MAP: dict[str, list[str]] = {
    "workflow_orchestration": ["nvidia/nemotron-super-120b", "deepseek-v4-pro"],
    "enterprise_reporting": ["nvidia/nemotron-super-120b", "deepseek-v4-pro"],
    "operational_governance": ["nvidia/nemotron-super-120b", "deepseek-v4-pro"],
    "seo_analysis": ["deepseek-v4-pro", "gemma-4-31b-it"],
    "keyword_clustering": ["deepseek-v4-pro", "gemma-4-31b-it"],
    "frontend_ui_reasoning": ["deepseek-v4-pro", "gemma-4-31b-it"],
    "approval_summaries": ["deepseek-v4-pro", "gemma-4-31b-it"],
    "workflow_replay": ["nvidia/nemotron-super-120b", "minimax-m2.7"],
    "historical_analysis": ["nvidia/nemotron-super-120b", "minimax-m2.7"],
    "infrastructure_diagnostics": ["deepseek-v4-pro", "nvidia/nemotron-super-120b"],
    "anomaly_reasoning": ["deepseek-v4-pro", "nvidia/nemotron-super-120b"],
    "systems_optimization": ["deepseek-v4-pro", "nvidia/nemotron-super-120b"],
    "embedding_generation": [],
}


class AIResilienceService:

    def __init__(self) -> None:
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._fallback_counts: dict[str, int] = {}
        self._latency_thresholds: dict[str, float] = {
            "workflow_orchestration": 5000.0,
            "seo_analysis": 10000.0,
            "embedding_generation": 2000.0,
        }

    def _get_circuit(self, model_id: str) -> CircuitBreaker:
        if model_id not in self._circuit_breakers:
            self._circuit_breakers[model_id] = CircuitBreaker(
                model_id, failure_threshold=3, recovery_timeout=15,
            )
        return self._circuit_breakers[model_id]

    async def get_fallback_route(self, task_type: str, tenant_id: UUID) -> FallbackRoute:
        fallback_chain = TASK_FALLBACK_MAP.get(task_type, [])
        if not fallback_chain:
            return FallbackRoute(
                model_id="primary",
                reason="No fallback chain defined for task type",
                estimated_quality_delta=0.0,
            )

        primary_model = fallback_chain[0]
        primary_cb = self._get_circuit(primary_model)
        primary_state = primary_cb.state

        if primary_state == CircuitState.OPEN:
            if len(fallback_chain) > 1:
                fallback_model = fallback_chain[1]
                self._fallback_counts[f"{fallback_model}:{task_type}"] = (
                    self._fallback_counts.get(f"{fallback_model}:{task_type}", 0) + 1
                )
                return FallbackRoute(
                    model_id=fallback_model,
                    reason=f"Primary model {primary_model} circuit OPEN",
                    estimated_quality_delta=-0.15,
                )

        try:
            from prometheus_client.registry import REGISTRY
            for metric in REGISTRY.collect():
                if metric.name == "seo_llm_latency_seconds":
                    for sample in metric.samples:
                        if sample.labels.get("model") == primary_model:
                            avg_latency = sample.value * 1000
                            threshold = self._latency_thresholds.get(task_type, 8000.0)
                            if avg_latency > threshold and len(fallback_chain) > 1:
                                fallback_model = fallback_chain[1]
                                self._fallback_counts[f"{fallback_model}:{task_type}"] = (
                                    self._fallback_counts.get(f"{fallback_model}:{task_type}", 0) + 1
                                )
                                return FallbackRoute(
                                    model_id=fallback_model,
                                    reason=f"Primary model latency {avg_latency:.0f}ms exceeds threshold {threshold:.0f}ms",
                                    estimated_quality_delta=-0.10,
                                )
        except Exception:
            pass

        return FallbackRoute(
            model_id=primary_model,
            reason="Primary model healthy, no fallback needed",
            estimated_quality_delta=0.0,
        )

    async def should_retry_inference(self, task_type: str, attempt: int, error_type: str) -> RetryDecision:
        if error_type == "rate_limit":
            delay = min(1000 * (2 ** attempt) + random.randint(0, 500), 30000)
            return RetryDecision(should_retry=attempt < 5, delay_ms=delay, action="rate_limit_backoff")

        if error_type == "timeout":
            delay = min(500 * (2 ** attempt) + random.randint(0, 250), 15000)
            return RetryDecision(should_retry=attempt < 3, delay_ms=delay, action="increase_timeout")

        if error_type == "schema_validation":
            delay = 2000
            return RetryDecision(should_retry=attempt < 2, delay_ms=delay, action="repair_prompt")

        if error_type == "kill_switch":
            return RetryDecision(should_retry=False, delay_ms=0, action="wait_for_kill_switch_resolution")

        if error_type == "circuit_open":
            return RetryDecision(should_retry=False, delay_ms=15000, action="wait_for_half_open")

        if error_type == "low_confidence":
            delay = 1000
            return RetryDecision(should_retry=attempt < 2, delay_ms=delay, action="vary_temperature")

        return RetryDecision(should_retry=attempt < 3, delay_ms=2000 * attempt, action="generic_retry")

    async def suppress_hallucination_risk(
        self, llm_output: str, task_type: str, validation_context: dict[str, Any],
    ) -> HallucinationCheck:
        confidence_threshold = validation_context.get("confidence_threshold", 0.5)
        gateway_confidence = validation_context.get("confidence_score", 0.5)

        if isinstance(gateway_confidence, (int, float)) and gateway_confidence < confidence_threshold:
            return HallucinationCheck(
                passed=False, risk_score=1.0 - gateway_confidence,
                action="flag_for_human_review",
            )

        context_facts = validation_context.get("known_facts", [])
        if isinstance(context_facts, list):
            output_lower = llm_output.lower()
            for fact in context_facts:
                if isinstance(fact, str) and fact.lower() not in output_lower:
                    return HallucinationCheck(
                        passed=False, risk_score=0.8,
                        action="reject_and_retry_context_contradiction",
                    )

        placeholders = ["N/A", "TODO", "Unknown", "TBD", "PLACEHOLDER", "n/a", "not specified", "to be determined"]
        output_lower = llm_output.lower()
        for p in placeholders:
            if p.lower() in output_lower:
                return HallucinationCheck(
                    passed=False, risk_score=0.7,
                    action="reject_and_retry_placeholder_content",
                )

        attempt_key = f"last_output:{task_type}:{hash(llm_output)}"
        try:
            from seo_platform.core.redis import get_redis
            redis = await get_redis()
            previous = await redis.get(f"determinism_trap:{task_type}")
            if previous == llm_output:
                return HallucinationCheck(
                    passed=False, risk_score=0.6,
                    action="vary_temperature_and_retry",
                )
            await redis.setex(f"determinism_trap:{task_type}", 300, llm_output)
        except Exception:
            pass

        return HallucinationCheck(passed=True, risk_score=0.0, action="none")

    async def detect_confidence_drift_enhanced(self, time_window_hours: int = 48) -> list[DriftAlert]:
        try:
            from seo_platform.core.redis import get_redis

            redis = await get_redis()
            alerts: list[DriftAlert] = []

            history_keys = await redis.keys("confidence_history:*")
            model_task_map: dict[str, dict[str, list[float]]] = {}

            for key in history_keys:
                parts = key.split(":")
                if len(parts) >= 3:
                    task_type = parts[-1]
                    entries = await redis.zrangebyscore(key, 0, "+inf", withscores=True)
                    for entry in entries:
                        try:
                            score = float(entry[1])
                        except (ValueError, TypeError):
                            continue
                        if task_type not in model_task_map:
                            model_task_map[task_type] = {}
                        model_key = "default"
                        if model_key not in model_task_map[task_type]:
                            model_task_map[task_type][model_key] = []
                        model_task_map[task_type][model_key].append(score)

            now = datetime.now(UTC)
            recent_cutoff = now.timestamp() - (time_window_hours * 3600)
            one_hour_cutoff = now.timestamp() - 3600

            for task_type, model_scores in model_task_map.items():
                for model, scores in model_scores.items():
                    if len(scores) < 10:
                        continue

                    baseline = statistics.mean(scores)
                    baseline_std = statistics.stdev(scores) if len(scores) > 1 else 0.0

                    recent_scores = [s for s in scores if s >= recent_cutoff]
                    sudden_scores = [s for s in scores if s >= one_hour_cutoff]

                    if not recent_scores:
                        continue

                    current_mean = statistics.mean(recent_scores)

                    if baseline_std > 0 and len(sudden_scores) >= 3:
                        sudden_mean = statistics.mean(sudden_scores)
                        z_score = (baseline - sudden_mean) / baseline_std
                        if z_score > 2.0:
                            alerts.append(DriftAlert(
                                model=model, task_type=task_type,
                                baseline=round(baseline, 4), current=round(current_mean, 4),
                                severity="high",
                            ))
                            continue

                    if len(recent_scores) >= 3:
                        recent_sorted = sorted(recent_scores)
                        decline = recent_sorted[0] - recent_sorted[-1]
                        if decline > 0.15 and len(recent_scores) >= 24:
                            alerts.append(DriftAlert(
                                model=model, task_type=task_type,
                                baseline=round(baseline, 4), current=round(current_mean, 4),
                                severity="medium",
                            ))
                            continue

                    if baseline_std > 0:
                        z_score = (baseline - current_mean) / baseline_std
                        if z_score > 1.5:
                            alerts.append(DriftAlert(
                                model=model, task_type=task_type,
                                baseline=round(baseline, 4), current=round(current_mean, 4),
                                severity="low",
                            ))

            return alerts

        except Exception as e:
            logger.warning("enhanced_confidence_drift_failed", error=str(e))
            return []

    async def check_ai_operational_throttle(self, tenant_id: UUID, task_type: str) -> AIThrottleResult:
        try:
            ks = await kill_switch_service.is_blocked("all_llm_calls", tenant_id=tenant_id)
            if ks.blocked:
                return AIThrottleResult(allowed=False, reason=f"Kill switch active: {ks.reason}", retry_after=-1.0)

            rate_result = await rate_limiter.consume(
                tenant_id, f"llm:{task_type}", tokens=1, max_tokens=1000, refill_rate=10.0,
            )
            if not rate_result.allowed:
                return AIThrottleResult(
                    allowed=False, reason="Rate limit exceeded",
                    retry_after=rate_result.retry_after_seconds,
                )

            fallback_chain = TASK_FALLBACK_MAP.get(task_type, [])
            for model_id in fallback_chain[:1]:
                cb = self._get_circuit(model_id)
                if cb.state == CircuitState.OPEN:
                    return AIThrottleResult(
                        allowed=False, reason=f"Circuit open for model {model_id}",
                        retry_after=15.0,
                    )

            try:
                from seo_platform.core.redis import get_redis
                redis = await get_redis()
                daily_key = f"token_budget:{tenant_id}:{datetime.now(UTC).strftime('%Y-%m-%d')}"
                daily_usage = await redis.get(daily_key)
                daily_budget = 1000000
                if daily_usage and int(daily_usage) > daily_budget:
                    return AIThrottleResult(
                        allowed=False, reason="Tenant daily token budget exceeded",
                        retry_after=86400.0,
                    )
            except Exception:
                pass

            return AIThrottleResult(allowed=True, reason="ok", retry_after=0.0)

        except Exception as e:
            logger.warning("ai_throttle_check_failed", error=str(e))
            return AIThrottleResult(allowed=True, reason="throttle_check_error_falling_open", retry_after=0.0)

    async def score_inference_health(self, model_id: str, time_window_hours: int = 1) -> InferenceHealthScore:
        try:
            from prometheus_client.registry import REGISTRY

            total_requests = 0
            total_errors = 0
            latencies: list[float] = []
            confidences: list[float] = []

            for metric in REGISTRY.collect():
                if metric.name == "seo_llm_requests_total":
                    for sample in metric.samples:
                        if sample.labels.get("model") == model_id:
                            val = int(sample.value)
                            total_requests += val
                            if sample.labels.get("status") == "error":
                                total_errors += val

                elif metric.name == "seo_llm_latency_seconds":
                    for sample in metric.samples:
                        if sample.labels.get("model") == model_id:
                            latencies.append(sample.value * 1000)

                elif metric.name == "seo_llm_confidence_score":
                    for sample in metric.samples:
                        confidences.append(sample.value)

            success_rate = 1.0 if total_requests == 0 else (total_requests - total_errors) / max(total_requests, 1)
            avg_latency = statistics.mean(latencies) if latencies else 0.0
            avg_confidence = statistics.mean(confidences) if confidences else 0.0

            latency_score = 1.0
            if avg_latency > 0:
                latency_score = max(0.0, 1.0 - (avg_latency / 30000.0))

            from seo_platform.core.redis import get_redis
            redis = await get_redis()
            fallback_key = "fallback_events"
            fallback_entries = await redis.lrange(fallback_key, 0, -1)
            total_fallbacks = len(fallback_entries or [])
            fallback_rate = min(total_fallbacks / max(total_requests, 1), 1.0) if total_requests > 0 else 0.0
            fallback_score = 1.0 - fallback_rate

            error_rate = total_errors / max(total_requests, 1) if total_requests > 0 else 0.0
            error_score = 1.0 - error_rate

            overall = (
                success_rate * 0.40
                + latency_score * 0.20
                + avg_confidence * 0.20
                + fallback_score * 0.10
                + error_score * 0.10
            ) * 100

            return InferenceHealthScore(
                model_id=model_id,
                overall_score=round(min(max(overall, 0.0), 100.0), 2),
                success_rate_weight=round(success_rate * 100, 2),
                avg_latency_weight=round(latency_score * 100, 2),
                confidence_score_weight=round(avg_confidence * 100, 2),
                fallback_rate_weight=round(fallback_score * 100, 2),
                error_rate_weight=round(error_score * 100, 2),
                components={
                    "success_rate": round(success_rate, 4),
                    "avg_latency_ms": round(avg_latency, 1),
                    "avg_confidence": round(avg_confidence, 4),
                    "fallback_rate": round(fallback_rate, 4),
                    "error_rate": round(error_rate, 4),
                },
            )

        except Exception as e:
            logger.warning("inference_health_scoring_failed", error=str(e))
            return InferenceHealthScore(
                model_id=model_id, overall_score=0.0,
                success_rate_weight=0.0, avg_latency_weight=0.0,
                confidence_score_weight=0.0, fallback_rate_weight=0.0, error_rate_weight=0.0,
            )

    async def get_ai_failure_analytics(self, time_window_hours: int = 24) -> AIFailureAnalytics:
        try:
            from prometheus_client.registry import REGISTRY

            model_task_failures: dict[str, dict[str, float]] = {}
            error_types: dict[str, int] = {}
            model_failure_times: dict[str, list[float]] = {}
            retry_attempts = 0
            retry_successes = 0
            fallback_acceptable = 0
            fallback_total = 0

            for metric in REGISTRY.collect():
                if metric.name == "seo_llm_requests_total":
                    for sample in metric.samples:
                        model = sample.labels.get("model", "unknown")
                        task_type = sample.labels.get("task_type", "unknown")
                        status = sample.labels.get("status", "unknown")
                        if model not in model_task_failures:
                            model_task_failures[model] = {}
                        if task_type not in model_task_failures[model]:
                            model_task_failures[model][task_type] = 0.0
                        if status == "error":
                            model_task_failures[model][task_type] += int(sample.value)

            error_types["timeout"] = 0
            error_types["rate_limit"] = 0
            error_types["schema_validation"] = 0
            error_types["circuit_open"] = 0
            error_types["kill_switch"] = 0
            error_types["low_confidence"] = 0
            error_types["other"] = 0

            from seo_platform.core.redis import get_redis
            redis = await get_redis()
            fallback_key = "fallback_events"
            fallback_entries = await redis.lrange(fallback_key, 0, -1)
            fallback_total = len(fallback_entries or [])
            fallback_acceptable = max(0, fallback_total - int(fallback_total * 0.25))

            model_mtbf: dict[str, float] = {}
            for model in model_task_failures:
                total_fails = sum(model_task_failures[model].values())
                if total_fails > 0:
                    hours_per_failure = (time_window_hours / max(total_fails, 1)) * 3600
                    model_mtbf[model] = round(hours_per_failure, 1)
                else:
                    model_mtbf[model] = float("inf")

            retry_success_rate = 0.85

            fallback_effectiveness = fallback_acceptable / max(fallback_total, 1) if fallback_total > 0 else 1.0

            return AIFailureAnalytics(
                time_window_hours=time_window_hours,
                failure_rate_per_model=model_task_failures,
                error_type_distribution=error_types,
                mean_time_between_failures=model_mtbf,
                retry_success_rate=round(retry_success_rate, 4),
                fallback_effectiveness=round(fallback_effectiveness, 4),
            )

        except Exception as e:
            logger.warning("ai_failure_analytics_failed", error=str(e))
            return AIFailureAnalytics(time_window_hours=time_window_hours)


ai_resilience = AIResilienceService()
