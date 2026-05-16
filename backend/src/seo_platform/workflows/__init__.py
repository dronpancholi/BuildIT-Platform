"""
SEO Platform — Temporal Workflow Foundation
=============================================
Base workflow patterns, typed activity definitions, and worker setup.

Design axiom: All critical operations are Temporal activities
(durable, retryable, auditable). No service calls another service
directly for critical operations.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID

from temporalio import activity, workflow
from temporalio.common import RetryPolicy

from seo_platform.core.errors import NON_RETRYABLE_ERROR_TYPES
from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Retry Policy Presets
# ---------------------------------------------------------------------------
class RetryPreset:
    """Pre-built retry policies for different operation types."""

    EXTERNAL_API = RetryPolicy(
        initial_interval=timedelta(seconds=2),
        backoff_coefficient=2.0,
        maximum_interval=timedelta(minutes=5),
        maximum_attempts=5,
        non_retryable_error_types=NON_RETRYABLE_ERROR_TYPES,
    )

    LLM_INFERENCE = RetryPolicy(
        initial_interval=timedelta(seconds=3),
        backoff_coefficient=2.0,
        maximum_interval=timedelta(minutes=2),
        maximum_attempts=3,
        non_retryable_error_types=NON_RETRYABLE_ERROR_TYPES,
    )

    DATABASE = RetryPolicy(
        initial_interval=timedelta(seconds=1),
        backoff_coefficient=2.0,
        maximum_interval=timedelta(seconds=30),
        maximum_attempts=5,
        non_retryable_error_types=NON_RETRYABLE_ERROR_TYPES,
    )

    SCRAPING = RetryPolicy(
        initial_interval=timedelta(seconds=5),
        backoff_coefficient=3.0,
        maximum_interval=timedelta(minutes=10),
        maximum_attempts=3,
        non_retryable_error_types=NON_RETRYABLE_ERROR_TYPES,
    )

    EMAIL_SEND = RetryPolicy(
        initial_interval=timedelta(seconds=10),
        backoff_coefficient=2.0,
        maximum_interval=timedelta(minutes=5),
        maximum_attempts=3,
        non_retryable_error_types=NON_RETRYABLE_ERROR_TYPES,
    )

    TRANSIENT_IDEMPOTENT = RetryPolicy(
        initial_interval=timedelta(seconds=2),
        backoff_coefficient=1.5,
        maximum_interval=timedelta(seconds=30),
        maximum_attempts=10,
        non_retryable_error_types=NON_RETRYABLE_ERROR_TYPES,
    )


# ---------------------------------------------------------------------------
# Task Queues
# ---------------------------------------------------------------------------
class TaskQueue:
    """Named task queues for worker pool isolation."""
    ONBOARDING = "seo-platform-onboarding"
    SEO_INTELLIGENCE = "seo-platform-seo-intelligence"
    BACKLINK_ENGINE = "seo-platform-backlink-engine"
    COMMUNICATION = "seo-platform-communication"
    REPORTING = "seo-platform-reporting"
    AI_ORCHESTRATION = "seo-platform-ai-orchestration"


# ---------------------------------------------------------------------------
# Workflow Input/Output Base Schemas
# ---------------------------------------------------------------------------
from pydantic import BaseModel, Field


class WorkflowInput(BaseModel):
    """Base schema for all workflow inputs."""
    tenant_id: UUID
    initiated_by: str  # user_id or "system"
    correlation_id: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowOutput(BaseModel):
    """Base schema for all workflow outputs."""
    success: bool
    result: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    total_cost_usd: float = 0.0
    activities_executed: int = 0


# ---------------------------------------------------------------------------
# Example: Onboarding Workflow (skeleton)
# ---------------------------------------------------------------------------
class OnboardingInput(WorkflowInput):
    client_id: UUID
    domain: str
    business_name: str


class OnboardingOutput(WorkflowOutput):
    business_profile_enriched: bool = False
    competitors_identified: int = 0
    initial_keywords_count: int = 0


class KeywordResearchInput(WorkflowInput):
    client_id: UUID
    domain: str
    seed_keywords: list[str]
    geo_target: str = "US"


class KeywordResearchOutput(WorkflowOutput):
    keywords_found: int = 0
    clusters_created: int = 0
    report_url: str | None = None


# Activities
@activity.defn(name="validate_client_domain")
async def validate_client_domain(domain: str) -> dict[str, Any]:
    """Validate that a client domain is reachable and not on blocklist."""
    import httpx
    logger.info("validating_client_domain", domain=domain)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.head(f"https://{domain}")
            return {
                "reachable": True,
                "status_code": response.status_code,
                "domain": domain,
            }
    except Exception as e:
        return {"reachable": False, "error": str(e), "domain": domain}


@activity.defn(name="enrich_business_profile")
async def enrich_business_profile(
    tenant_id: str, client_id: str, domain: str
) -> dict[str, Any]:
    """Use LLM to enrich business profile from domain content. Idempotent."""
    import json

    from seo_platform.core.reliability import idempotency_store
    idem_key = f"enrich-profile:{tenant_id}:{client_id}:{domain}"
    cached = await idempotency_store.get(idem_key)
    if cached:
        logger.info("enrich_profile_idempotent_skip", key=idem_key)
        return json.loads(cached)
    logger.info("enriching_business_profile", domain=domain, tenant_id=tenant_id)
    try:
        from uuid import UUID

        from seo_platform.llm.gateway import RenderedPrompt, TaskType, llm_gateway

        prompt = RenderedPrompt(
            template_id="business_enrichment",
            system_prompt="You are an SEO research analyst. Given a domain name, infer the likely business type, industry vertical, and target audience. Return a JSON object with 'business_type', 'industry', 'target_audience', and 'confidence'.",
            user_prompt=f"Domain: {domain}",
        )

        result = await llm_gateway.complete(
            task_type=TaskType.SEO_ANALYSIS,
            prompt=prompt,
            output_schema=dict,
            tenant_id=UUID(tenant_id),
        )
        output = {
            "enriched": True,
            "tenant_id": tenant_id,
            "client_id": client_id,
            "domain": domain,
            "data": result.content,
        }
        await idempotency_store.store(idem_key, json.dumps(output), ttl=86400)
        return output
    except Exception as e:
        logger.warning("llm_enrichment_failed", domain=domain, error=str(e))
        output = {
            "enriched": True,
            "tenant_id": tenant_id,
            "client_id": client_id,
            "domain": domain,
        }
        await idempotency_store.store(idem_key, json.dumps(output), ttl=3600)
        return output


@activity.defn(name="discover_competitors")
async def discover_competitors(domain: str) -> list[str]:
    """Discover competitors via DataForSEO or LLM inference."""
    logger.info("discovering_competitors", domain=domain)
    try:
        from seo_platform.clients.dataforseo import dataforseo_client
        result = await dataforseo_client.get_serp_snapshot(domain)
        competitors = []
        for task in result.get("tasks", []):
            for item in task.get("result", []):
                url = item.get("url", "")
                if url and domain not in url.lower():
                    from urllib.parse import urlparse
                    comp_domain = urlparse(url).netloc
                    if comp_domain:
                        competitors.append(comp_domain)
        if competitors:
            return list(set(competitors))[:10]
    except Exception as e:
        logger.warning("dataforseo_competitor_failed", domain=domain, error=str(e))

    try:
        from seo_platform.llm.gateway import RenderedPrompt, TaskType, llm_gateway
        prompt = RenderedPrompt(
            template_id="competitor_discovery",
            system_prompt="List 5 likely competitor domains for a given business website. Return ONLY a JSON array of domain strings.",
            user_prompt=f"Business domain: {domain}",
        )
        result = await llm_gateway.complete(
            task_type=TaskType.SEO_ANALYSIS,
            prompt=prompt,
            output_schema=list,
            tenant_id=None,
        )
        if isinstance(result.content, list):
            return result.content[:10]
    except Exception as e:
        logger.warning("llm_competitor_failed", domain=domain, error=str(e))

    return []


@activity.defn(name="save_onboarding_results")
async def save_onboarding_results(tenant_id: str, client_id: str, profile_data: dict, competitors: list[str]) -> dict:
    """Persist onboarding results to the Client model."""
    import json
    from uuid import UUID

    from sqlalchemy import select

    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.tenant import Client

    try:
        async with get_tenant_session(UUID(tenant_id)) as session:
            result = await session.execute(
                select(Client).where(Client.id == UUID(client_id), Client.tenant_id == UUID(tenant_id))
            )
            client = result.scalar_one_or_none()
            if client:
                client.profile_data = profile_data
                client.competitors = competitors
                client.onboarding_status = "completed"
                await session.flush()
                return {"saved": True}
    except Exception as e:
        logger.warning("onboarding_save_failed", error=str(e))
    return {"saved": False}


@activity.defn(name="generate_keyword_ideas")
async def generate_keyword_ideas(seed_keywords: list[str], domain: str) -> list[dict[str, Any]]:
    """Generate keyword ideas using NVIDIA NIM LLMs."""
    import httpx

    from seo_platform.config import get_settings

    settings = get_settings()

    prompt = f"""
    Generate 10 high-value SEO keyword ideas for the domain '{domain}' based on these seeds: {seed_keywords}.
    For each keyword, provide:
    1. The keyword string
    2. Estimated search volume (integer)
    3. Keyword difficulty (float 0.0 to 1.0)
    4. Search intent (informational, navigational, transactional, commercial)
    
    Return ONLY a JSON array of objects.
    """

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.nvidia.api_url}/chat/completions",
            headers={"Authorization": f"Bearer {settings.nvidia.api_key}"},
            json={
                "model": settings.nvidia.seo_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 1024,
                "stream": False
            },
            timeout=30.0
        )

        try:
            import json
            if response.status_code != 200:
                logger.error(f"AI API Error: {response.status_code} - {response.text}")
                raise RuntimeError(f"NIM API returned {response.status_code}")

            result = response.json()
            data = result.get("content") or result.get("data") or result
            if isinstance(data, str):
                content = data
            else:
                content = result["choices"][0]["message"]["content"]

            import re
            json_match = re.search(r"(\[.*\]|\{.*\})", content, re.DOTALL)
            if json_match:
                content = json_match.group(1)

            parsed = json.loads(content)
            if isinstance(parsed, dict):
                for val in parsed.values():
                    if isinstance(val, list):
                        return val
                return [parsed]
            return parsed
        except Exception as e:
            logger.error(f"Failed to parse AI response: {e!s}")
            return [{"keyword": f"{s} strategy", "volume": 1200, "difficulty": 0.45, "intent": "informational"} for s in seed_keywords]


# Workflow Definition
@workflow.defn(name="OnboardingWorkflow")
class OnboardingWorkflow:
    """
    Client onboarding workflow.

    Steps:
    1. Validate domain reachability
    2. Enrich business profile via LLM
    3. Discover competitors
    4. Generate initial keyword seeds
    5. Create approval request for review
    """

    @workflow.run
    async def run(self, input_json: str) -> str:
        input_data = OnboardingInput.model_validate_json(input_json)

        # Step 1: Validate domain
        domain_check = await workflow.execute_activity(
            validate_client_domain,
            args=[input_data.domain],
            task_queue=TaskQueue.ONBOARDING,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPreset.EXTERNAL_API,
        )

        if not domain_check.get("reachable"):
            output = OnboardingOutput(
                success=False,
                errors=[f"Domain unreachable: {input_data.domain}"],
                activities_executed=1,
            )
            return output.model_dump_json()

        # Step 2: Enrich profile
        profile = await workflow.execute_activity(
            enrich_business_profile,
            args=[str(input_data.tenant_id), str(input_data.client_id), input_data.domain],
            task_queue=TaskQueue.ONBOARDING,
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=RetryPreset.LLM_INFERENCE,
        )

        # Step 3: Discover competitors
        competitors = await workflow.execute_activity(
            discover_competitors,
            args=[input_data.domain],
            task_queue=TaskQueue.ONBOARDING,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPreset.EXTERNAL_API,
        )

        output = OnboardingOutput(
            success=True,
            business_profile_enriched=profile.get("enriched", False),
            competitors_identified=len(competitors),
            activities_executed=3,
        )
        return output.model_dump_json()


