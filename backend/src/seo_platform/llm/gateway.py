"""
SEO Platform — Elite NIM Enterprise LLM Gateway
=================================================
Strictly structured model-agnostic inference gateway for NVIDIA NIM.

ARCHITECTURE AXIOM:
AI proposes. Deterministic systems execute. Reliability is the product.

ROUTING ARCHITECTURE:
Request -> Task Classification -> Kill Switch Check -> Governance Interceptor 
-> Rate Limiter -> Model Router -> Selected Model -> Structured Validation 
-> Governance Validation -> Confidence Scoring -> Approval Gate -> Deterministic Execution.
"""

from __future__ import annotations

import enum
import hashlib
import time
from decimal import Decimal
from typing import Any
from uuid import UUID

import httpx
import orjson
from pydantic import BaseModel, Field

from seo_platform.config import get_settings
from seo_platform.core.errors import (
    KillSwitchActiveError,
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
    OutputSchemaError,
)
from seo_platform.core.kill_switch import kill_switch_service
from seo_platform.core.logging import get_logger
from seo_platform.core.reliability import CircuitBreaker, rate_limiter

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Enums & Schemas
# ---------------------------------------------------------------------------
class ModelRole(str, enum.Enum):
    ORCHESTRATION = "orchestration"          # DeepSeek-V4-Pro
    OPERATIONAL_UTILITY = "utility"          # Gemma 4 31B IT
    LONG_CONTEXT_MEMORY = "memory"           # MiniMax M2.7
    INFRASTRUCTURE_INTELLIGENCE = "infra"    # NVIDIA-Nemotron-3-Super-120B-A12B
    EMBEDDING = "embedding"                  # nvidia/nv-embedqa-e5-v5


class TaskType(str, enum.Enum):
    """Business tasks map explicitly to elite model roles."""
    WORKFLOW_ORCHESTRATION = "workflow_orchestration"
    ENTERPRISE_REPORTING = "enterprise_reporting"
    OPERATIONAL_GOVERNANCE = "operational_governance"

    SEO_ANALYSIS = "seo_analysis"
    KEYWORD_CLUSTERING = "keyword_clustering"
    FRONTEND_UI_REASONING = "frontend_ui_reasoning"
    APPROVAL_SUMMARIES = "approval_summaries"

    WORKFLOW_REPLAY = "workflow_replay"
    HISTORICAL_ANALYSIS = "historical_analysis"

    INFRASTRUCTURE_DIAGNOSTICS = "infrastructure_diagnostics"
    ANOMALY_REASONING = "anomaly_reasoning"
    SYSTEMS_OPTIMIZATION = "systems_optimization"

    EMBEDDING_GENERATION = "embedding_generation"

    ENTERPRISE_ECOSYSTEM_ANALYSIS = "enterprise_ecosystem_analysis"
    CROSS_TENANT_ANALYTICS = "cross_tenant_analytics"


# Task → Model Role Routing Matrix
TASK_MODEL_ROUTING: dict[TaskType, ModelRole] = {
    TaskType.WORKFLOW_ORCHESTRATION: ModelRole.ORCHESTRATION,
    TaskType.ENTERPRISE_REPORTING: ModelRole.ORCHESTRATION,
    TaskType.OPERATIONAL_GOVERNANCE: ModelRole.ORCHESTRATION,

    TaskType.SEO_ANALYSIS: ModelRole.OPERATIONAL_UTILITY,
    TaskType.KEYWORD_CLUSTERING: ModelRole.OPERATIONAL_UTILITY,
    TaskType.FRONTEND_UI_REASONING: ModelRole.OPERATIONAL_UTILITY,
    TaskType.APPROVAL_SUMMARIES: ModelRole.OPERATIONAL_UTILITY,

    TaskType.WORKFLOW_REPLAY: ModelRole.LONG_CONTEXT_MEMORY,
    TaskType.HISTORICAL_ANALYSIS: ModelRole.LONG_CONTEXT_MEMORY,

    TaskType.INFRASTRUCTURE_DIAGNOSTICS: ModelRole.INFRASTRUCTURE_INTELLIGENCE,
    TaskType.ANOMALY_REASONING: ModelRole.INFRASTRUCTURE_INTELLIGENCE,
    TaskType.SYSTEMS_OPTIMIZATION: ModelRole.INFRASTRUCTURE_INTELLIGENCE,

    TaskType.EMBEDDING_GENERATION: ModelRole.EMBEDDING,

    TaskType.ENTERPRISE_ECOSYSTEM_ANALYSIS: ModelRole.ORCHESTRATION,
    TaskType.CROSS_TENANT_ANALYTICS: ModelRole.ORCHESTRATION,
}


class RenderedPrompt(BaseModel):
    """A fully rendered prompt ready for inference."""
    template_id: str
    system_prompt: str = ""
    user_prompt: str = ""
    variables: dict[str, Any] = Field(default_factory=dict)


class LLMResult(BaseModel):
    """Structured result from LLM inference."""
    content: Any  # Validated Pydantic model instance
    model_used: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0
    confidence_score: float = 0.0
    cached: bool = False
    cost_usd: Decimal = Decimal("0")


# ---------------------------------------------------------------------------
# Confidence Scorer & Governance
# ---------------------------------------------------------------------------
def compute_confidence(output: BaseModel, schema: type[BaseModel]) -> float:
    score = 1.0
    output_dict = output.model_dump()

    for field_name, field_info in schema.model_fields.items():
        value = output_dict.get(field_name)
        if not field_info.is_required() and value is None:
            score -= 0.05

    placeholders = ["N/A", "Unknown", "TBD", "TODO", "PLACEHOLDER", "n/a", "fabricated"]
    for value in _flatten_values(output_dict):
        if isinstance(value, str) and any(p in value for p in placeholders):
            score -= 0.15

    return max(0.0, min(1.0, score))


def _flatten_values(d: dict | list | Any) -> list[Any]:
    values: list[Any] = []
    if isinstance(d, dict):
        for v in d.values():
            values.extend(_flatten_values(v))
    elif isinstance(d, list):
        for item in d:
            values.extend(_flatten_values(item))
    else:
        values.append(d)
    return values


# ---------------------------------------------------------------------------
# LLM Gateway
# ---------------------------------------------------------------------------
class LLMGateway:
    """
    Elite Enterprise NIM Gateway.
    Strictly enforcing the Task -> Model routing and fallback matrix.
    """

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._circuit = CircuitBreaker("nvidia_nim", failure_threshold=3, recovery_timeout=15)
        self._cache: dict[str, LLMResult] = {}

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            settings = get_settings()
            self._client = httpx.AsyncClient(
                base_url=settings.nvidia.api_url,
                headers={
                    "Authorization": f"Bearer {settings.nvidia.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(settings.nvidia.request_timeout),
            )
        return self._client

    def _get_model_id(self, role: ModelRole) -> str:
        settings = get_settings()
        return {
            ModelRole.ORCHESTRATION: settings.nvidia.orchestration_model,
            ModelRole.OPERATIONAL_UTILITY: settings.nvidia.seo_model,
            ModelRole.LONG_CONTEXT_MEMORY: settings.nvidia.memory_model,
            ModelRole.INFRASTRUCTURE_INTELLIGENCE: settings.nvidia.infra_model,
            ModelRole.EMBEDDING: settings.nvidia.embedding_model,
        }[role]

    def _get_fallback_role(self, primary_role: ModelRole) -> ModelRole | None:
        """Mandatory Fallback Strategy"""
        strategy = {
            ModelRole.ORCHESTRATION: ModelRole.INFRASTRUCTURE_INTELLIGENCE,
            ModelRole.OPERATIONAL_UTILITY: ModelRole.ORCHESTRATION,
            ModelRole.LONG_CONTEXT_MEMORY: ModelRole.INFRASTRUCTURE_INTELLIGENCE,
            ModelRole.INFRASTRUCTURE_INTELLIGENCE: ModelRole.ORCHESTRATION,
        }
        return strategy.get(primary_role)

    def _compute_cache_key(self, model_id: str, prompt: RenderedPrompt) -> str:
        content = f"{model_id}:{prompt.system_prompt}:{prompt.user_prompt}"
        return hashlib.sha256(content.encode()).hexdigest()

    def _normalize_json_keys(self, content: str) -> str:
        """Lowercase first letter of JSON keys to match Pydantic schema."""
        import re
        return re.sub(r'"([A-Z][^"]*)"\s*:', lambda m: '"' + m.group(1)[0].lower() + m.group(1)[1:] + '":', content)

    async def complete(
        self,
        task_type: TaskType,
        prompt: RenderedPrompt,
        output_schema: type[BaseModel],
        tenant_id: UUID,
        use_cache: bool = True,
        temperature: float | None = None,
    ) -> LLMResult:
        """
        Execute deterministic pipeline.
        Kill Switch -> Route -> Fallback -> Validate -> Confidence.
        """
        # 1. Kill Switch Check
        ks = await kill_switch_service.is_blocked("all_llm_calls", tenant_id=tenant_id)
        if ks.blocked:
            raise KillSwitchActiveError(f"LLM Calls blocked by kill switch: {ks.reason}")

        # 2. Rate Limiter Check
        try:
            rate_result = await rate_limiter.consume(
                tenant_id, f"llm:{task_type.value}",
                tokens=1, max_tokens=1000, refill_rate=10.0,
            )
            if not rate_result.allowed:
                raise LLMRateLimitError(f"Rate limit exceeded for {task_type.value}")
        except LLMRateLimitError:
            raise
        except Exception:
            pass

        # 3. Inject Governance — sanitize input prompt
        from copy import deepcopy
        sanitized_prompt = deepcopy(prompt)
        try:
            from seo_platform.governance import governance_pipeline
            sanitized_text = governance_pipeline.sanitize_prospect_data({"text": sanitized_prompt.user_prompt}).get("text", sanitized_prompt.user_prompt)
            if sanitized_text != sanitized_prompt.user_prompt:
                sanitized_prompt.user_prompt = sanitized_text
                logger.warning("prompt_sanitized", task_type=task_type.value)
        except Exception:
            pass

        role = TASK_MODEL_ROUTING[task_type]
        model_id = self._get_model_id(role)
        cache_key = self._compute_cache_key(model_id, sanitized_prompt)

        if use_cache and cache_key in self._cache:
            cached = self._cache[cache_key]
            return LLMResult(**{**cached.model_dump(), "cached": True})

        settings = get_settings()
        start_time = time.monotonic()

        try:
            raw_response = await self._circuit.call(
                self._call_nim_api,
                model_id=model_id,
                prompt=sanitized_prompt,
                temperature=temperature or settings.nvidia.default_temperature,
                max_tokens=settings.nvidia.default_max_tokens,
            )
        except Exception as e:
            fallback_role = self._get_fallback_role(role)
            if fallback_role:
                logger.warning("nim_fallback_triggered", primary=model_id, error=str(e))
                fallback_model = self._get_model_id(fallback_role)
                raw_response = await self._call_nim_api(
                    model_id=fallback_model, prompt=sanitized_prompt,
                    temperature=temperature or settings.nvidia.default_temperature,
                    max_tokens=settings.nvidia.default_max_tokens,
                )
                model_id = fallback_model
            else:
                raise

        latency_ms = (time.monotonic() - start_time) * 1000
        content_text = raw_response["choices"][0]["message"]["content"]
        usage = raw_response.get("usage", {})

        # 4. Gov Evaluation on output
        try:
            from seo_platform.core.metrics import (
                governance_compliance_blocks as gov_comp_metric,
            )
            from seo_platform.core.metrics import (
                governance_injection_detections as gov_inj_metric,
            )
            from seo_platform.core.metrics import (
                governance_pii_detections as gov_pii_metric,
            )
            from seo_platform.governance import governance_pipeline
            gov_result = await governance_pipeline.evaluate(
                llm_output=content_text,
                grounded_context={"task_type": task_type.value, "tenant_id": str(tenant_id)},
                task_type=task_type.value,
                tenant_id=tenant_id,
            )
            if gov_result.pii_detections:
                for pii_type in set(gov_result.pii_detections):
                    gov_pii_metric.labels(pii_type=pii_type).inc()
            if gov_result.injection_detections:
                gov_inj_metric.labels(source="llm_output").inc(len(gov_result.injection_detections))
            if gov_result.compliance_issues:
                for issue in gov_result.compliance_issues:
                    gov_comp_metric.labels(violation_type=issue).inc()
        except Exception:
            pass

        # Validation
        try:
            content_text = self._normalize_json_keys(content_text)
            validated = output_schema.model_validate_json(content_text)
        except Exception as validation_error:
            logger.warning("nim_schema_repair", task=task_type.value)
            try:
                validated = await self._repair_and_retry(
                    model_id, prompt, output_schema, content_text, str(validation_error)
                )
            except Exception:
                raise OutputSchemaError("LLM output failed strict schema validation.")

        # Confidence Scoring
        confidence = compute_confidence(validated, output_schema)

        # 5. AI Observability
        try:
            from seo_platform.llm.observability import ai_observability
            await ai_observability.analyze_inference(
                prompt=sanitized_prompt.user_prompt,
                response=content_text,
                metadata={
                    "model": model_id,
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "latency_ms": latency_ms,
                    "tenant_id": str(tenant_id),
                    "workflow_id": sanitized_prompt.template_id,
                }
            )
        except Exception:
            pass

        result = LLMResult(
            content=validated,
            model_used=model_id,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            latency_ms=latency_ms,
            confidence_score=confidence,
        )

        if use_cache:
            self._cache[cache_key] = result

        # 6. Prometheus Metrics
        try:
            from seo_platform.core.metrics import (
                llm_confidence_score,
                llm_latency,
                llm_requests_total,
                llm_tokens_used,
            )
            llm_requests_total.labels(task_type=task_type.value, model=model_id, status="success").inc()
            llm_latency.labels(task_type=task_type.value, model=model_id).observe(latency_ms / 1000)
            if usage.get("prompt_tokens"):
                llm_tokens_used.labels(tenant_id=str(tenant_id), model=model_id, direction="input").inc(usage["prompt_tokens"])
            if usage.get("completion_tokens"):
                llm_tokens_used.labels(tenant_id=str(tenant_id), model=model_id, direction="output").inc(usage["completion_tokens"])
            llm_confidence_score.labels(task_type=task_type.value).observe(confidence)
        except Exception:
            pass

        logger.info(
            "llm_inference_complete",
            task_type=task_type.value,
            model=model_id,
            latency_ms=round(latency_ms, 1),
            confidence=round(confidence, 3),
        )

        return result

    async def _call_nim_api(self, model_id: str, prompt: RenderedPrompt,
                            temperature: float, max_tokens: int) -> dict:
        client = await self._get_client()
        messages = []
        if prompt.system_prompt:
            messages.append({"role": "system", "content": prompt.system_prompt})
        messages.append({"role": "user", "content": prompt.user_prompt})

        payload = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }

        try:
            response = await client.post("/chat/completions", json=payload)
            if response.status_code == 429:
                raise LLMRateLimitError("NVIDIA NIM rate limit exceeded")
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            raise LLMTimeoutError("NVIDIA NIM request timed out")
        except httpx.HTTPStatusError as e:
            raise LLMError(f"NIM API error: {e.response.status_code}")

    async def _repair_and_retry(self, model_id: str, original_prompt: RenderedPrompt,
                                 schema: type[BaseModel], raw_output: str, error: str) -> BaseModel:
        repair_prompt = RenderedPrompt(
            template_id="schema_repair",
            system_prompt="You are a JSON repair assistant. Return ONLY valid JSON.",
            user_prompt=(
                f"Original output: {raw_output[:2000]}\n\n"
                f"Validation error: {error}\n\n"
                f"Required schema: {orjson.dumps(schema.model_json_schema()).decode()}\n\n"
            ),
        )
        settings = get_settings()
        raw = await self._call_nim_api(model_id, repair_prompt, temperature=0.1,
                                        max_tokens=settings.nvidia.default_max_tokens)
        content = raw["choices"][0]["message"]["content"]
        return schema.model_validate_json(content)

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

llm_gateway = LLMGateway()
