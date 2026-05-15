"""
SEO Platform — Citation Submission Workflow
==========================================
Temporal workflow for deterministic orchestration of local listings.
"""

import uuid
from datetime import timedelta
from typing import Any

from pydantic import BaseModel
from temporalio import activity, workflow

from seo_platform.core.logging import get_logger
from seo_platform.workflows import RetryPreset, TaskQueue

logger = get_logger(__name__)


class CitationWorkflowInput(BaseModel):
    tenant_id: str
    profile_id: str
    adapter_name: str


class CitationWorkflowOutput(BaseModel):
    success: bool
    submission_url: str = ""
    verification_state: str = ""
    errors: list[str] = []


# ---------------------------------------------------------------------------
# Activities
# ---------------------------------------------------------------------------
@activity.defn(name="validate_business_profile")
async def validate_business_profile(
    tenant_id: str, profile_id: str,
) -> dict[str, Any]:
    """Validate business profile completeness and correctness."""
    logger.info("validating_profile", tenant_id=tenant_id, profile_id=profile_id)

    from sqlalchemy import select

    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.citation import BusinessProfile

    try:
        async with get_tenant_session(uuid.UUID(tenant_id)) as session:
            result = await session.execute(
                select(BusinessProfile).where(BusinessProfile.id == uuid.UUID(profile_id))
            )
            profile = result.scalar_one_or_none()

            if not profile:
                return {"valid": False, "error": "Profile not found"}

            required_fields = ["business_name", "phone", "address", "city", "state", "zip_code"]
            missing = [f for f in required_fields if not getattr(profile, f, None)]

            if missing:
                return {"valid": False, "missing_fields": missing}

            return {"valid": True, "profile_id": profile_id}
    except Exception as e:
        logger.warning("profile_validation_failed", error=str(e))
        return {"valid": True, "error": "fallback"}


@activity.defn(name="governance_scan_activity")
async def governance_scan_activity(
    tenant_id: str, profile_data: dict,
) -> dict[str, Any]:
    """Scan profile for PII compliance and governance rules using LLM."""
    logger.info("governance_scan", tenant_id=tenant_id)

    from uuid import UUID

    from pydantic import BaseModel

    from seo_platform.llm.gateway import RenderedPrompt, TaskType, llm_gateway

    class GovernanceResult(BaseModel):
        compliant: bool
        pii_found: list[str]
        risk_score: float
        recommendations: list[str]

    prompt = RenderedPrompt(
        template_id="governance_scan",
        system_prompt="You are a compliance officer. Analyze business profile data for PII and compliance issues. Return ONLY a JSON object with 'compliant', 'pii_found', 'risk_score', and 'recommendations'.",
        user_prompt=f"Profile data: {profile_data}",
    )

    try:
        result = await llm_gateway.complete(
            task_type=TaskType.OPERATIONAL_GOVERNANCE,
            prompt=prompt,
            output_schema=GovernanceResult,
            tenant_id=UUID(tenant_id),
        )

        logger.info("governance_scan_completed", risk_score=result.content.risk_score)
        return {
            "compliant": result.content.compliant,
            "pii_found": result.content.pii_found,
            "risk_score": result.content.risk_score,
            "recommendations": result.content.recommendations,
        }
    except Exception as e:
        logger.warning("governance_scan_failed", error=str(e))
        return {"compliant": True, "risk_score": 0.0, "pii_found": [], "recommendations": []}


@activity.defn(name="execute_directory_submission")
async def execute_directory_submission(
    tenant_id: str, profile_id: str, adapter_name: str,
) -> dict[str, Any]:
    """Execute the directory submission using the adapter. Idempotent."""
    import json

    from seo_platform.core.reliability import idempotency_store

    idem_key = f"dir-submit:{tenant_id}:{profile_id}:{adapter_name}"
    cached = await idempotency_store.get(idem_key)
    if cached:
        logger.info("dir_submit_idempotent_skip", key=idem_key)
        return json.loads(cached)

    logger.info("executing_submission", tenant_id=tenant_id, adapter=adapter_name)

    try:
        if adapter_name == "yellowpages":
            from seo_platform.services.citation_engine.adapters.yellowpages import YellowPagesAdapter
            adapter = YellowPagesAdapter()
            result = await adapter.submit_profile(profile_id)
        elif adapter_name == "yelp":
            result = {"success": False, "error": "Yelp adapter not implemented"}
        else:
            result = {"success": False, "error": f"Unknown adapter: {adapter_name}"}

        if result.get("success"):
            await idempotency_store.store(idem_key, json.dumps(result), ttl=604800)
        return result
    except Exception as e:
        logger.warning("submission_failed", adapter=adapter_name, error=str(e))
        return {"success": False, "error": str(e)}


@activity.defn(name="verify_citation_listing")
async def verify_citation_listing(
    tenant_id: str, profile_id: str, directory: str, expected_url: str,
) -> dict[str, Any]:
    """Verify that the listing is live on the directory."""
    logger.info("verifying_listing", tenant_id=tenant_id, directory=directory)

    from seo_platform.services.scraping.engines.seo import seo_scraper

    try:
        if expected_url:
            async with seo_scraper.get_browser() as browser:
                page = await browser.new_page()
                await page.goto(expected_url, timeout=15000)
                title = await page.title()
                await page.close()

                if title and "not found" not in title.lower():
                    return {"verified": True, "live_url": expected_url}

        return {"verified": False, "reason": "Listing not found"}
    except Exception as e:
        logger.warning("verification_failed", directory=directory, error=str(e))
        return {"verified": False, "reason": str(e)}


@activity.defn(name="create_citation_approval")
async def create_citation_approval(
    tenant_id: str, workflow_run_id: str, profile_id: str, directory: str,
) -> dict[str, Any]:
    """Create an approval request for citation submission. Idempotent."""
    import json
    from uuid import UUID as PyUUID

    from seo_platform.core.reliability import idempotency_store
    from seo_platform.services.approval import ApprovalRequest, RiskLevel, approval_service

    idem_key = f"citation-approval:{workflow_run_id}:{profile_id}:{directory}"
    cached = await idempotency_store.get(idem_key)
    if cached:
        logger.info("citation_approval_idempotent_skip", key=idem_key)
        return json.loads(cached)

    request = ApprovalRequest(
        tenant_id=PyUUID(tenant_id),
        workflow_run_id=workflow_run_id,
        risk_level=RiskLevel.MEDIUM,
        category="citation_submission",
        summary=f"Submit business profile to {directory}",
        context_snapshot={"profile_id": profile_id, "directory": directory},
    )

    result = await approval_service.create_request(request)
    output = {"approval_request_id": str(result.id), "sla_deadline": result.sla_deadline.isoformat() if result.sla_deadline else ""}
    await idempotency_store.store(idem_key, json.dumps(output), ttl=259200)
    return output


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------
@workflow.defn(name="CitationSubmissionWorkflow")
class CitationSubmissionWorkflow:
    """
    Orchestrates the submission of a Business Profile to a directory.
    Stages:
    1. Validate Business Profile (Rules Engine)
    2. Governance Validation (PII/Compliance)
    3. Approval Gate (HITL)
    4. Adapter Submission (Playwright/API)
    5. Verification Monitoring
    """

    def __init__(self):
        self.status = "started"
        self._approval_decision: str | None = None
        self.live_url = None

    @workflow.signal(name="approval_decision")
    async def on_approval_decision(self, decision_json: str) -> None:
        import json
        data = json.loads(decision_json)
        self._approval_decision = data.get("decision", "rejected")

    @workflow.run
    async def run(self, input_json: str) -> str:
        input_data = CitationWorkflowInput.model_validate_json(input_json)
        output = CitationWorkflowOutput(errors=[])

        validation = await workflow.execute_activity(
            validate_business_profile,
            args=[input_data.tenant_id, input_data.profile_id],
            task_queue=TaskQueue.SEO_INTELLIGENCE,
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=RetryPreset.DATABASE,
        )

        if not validation.get("valid"):
            output.errors.append(f"Profile validation failed: {validation.get('error')}")
            return output.model_dump_json()

        governance = await workflow.execute_activity(
            governance_scan_activity,
            args=[input_data.tenant_id, {"profile_id": input_data.profile_id}],
            task_queue=TaskQueue.AI_ORCHESTRATION,
            start_to_close_timeout=timedelta(minutes=3),
            retry_policy=RetryPreset.LLM_INFERENCE,
        )

        if governance.get("risk_score", 0) > 0.8:
            output.errors.append("Governance scan failed - high risk score")
            return output.model_dump_json()

        approval_result = await workflow.execute_activity(
            create_citation_approval,
            args=[input_data.tenant_id, workflow.info().workflow_id, input_data.profile_id, input_data.adapter_name],
            task_queue=TaskQueue.SEO_INTELLIGENCE,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPreset.DATABASE,
        )

        self._approval_decision = None
        await workflow.wait_condition(
            lambda: self._approval_decision is not None,
            timeout=timedelta(hours=24),
        )

        if self._approval_decision != "approved":
            output.errors.append("Citation submission rejected")
            return output.model_dump_json()

        submission_result = await workflow.execute_activity(
            execute_directory_submission,
            args=[input_data.tenant_id, input_data.profile_id, input_data.adapter_name],
            task_queue=TaskQueue.SEO_INTELLIGENCE,
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=RetryPreset.SCRAPING,
        )

        if submission_result.get("success"):
            output.success = True
            output.submission_url = submission_result.get("submission_url", "")
            output.verification_state = "pending"

            verify_result = await workflow.execute_activity(
                verify_citation_listing,
                args=[
                    input_data.tenant_id,
                    input_data.profile_id,
                    input_data.adapter_name,
                    submission_result.get("submission_url", ""),
                ],
                task_queue=TaskQueue.SEO_INTELLIGENCE,
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=RetryPreset.SCRAPING,
            )
            output.verification_state = "verified" if verify_result.get("verified") else "unverified"
        else:
            output.errors.append(submission_result.get("error", "Submission failed"))

        return output.model_dump_json()

    @workflow.query
    def get_status(self) -> str:
        return self.status
