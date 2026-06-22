"""
SEO Platform — Citation Automation API
========================================
Endpoints for semi-automated browser-based form filling.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from seo_platform.core.auth import CurrentUser, get_current_user, get_validated_tenant_id
from seo_platform.core.database import get_session
from seo_platform.core.logging import get_logger
from seo_platform.models.citation_v2 import CitationProject, CitationSite, CitationSubmissionV2
from seo_platform.schemas import APIResponse

logger = get_logger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------
class AutoFillRequest(BaseModel):
    """Request to auto-fill a form for a submission."""
    take_screenshot: bool = Field(True, description="Capture screenshots before/after")


class AutoFillResponse(BaseModel):
    """Response from auto-fill operation."""
    filled_fields: list[str] = Field(default_factory=list)
    unfilled_fields: list[str] = Field(default_factory=list)
    screenshot_before: str | None = Field(None, description="Base64 encoded screenshot")
    screenshot_after: str | None = Field(None, description="Base64 encoded screenshot")
    page_url: str = ""
    listing_url: str | None = None


class SubmitRequest(BaseModel):
    """Request to submit a filled form."""
    pass


class SubmitResponse(BaseModel):
    """Response from form submission."""
    submitted: bool
    result_url: str | None = None
    error: str | None = None


class CheckExistenceResponse(BaseModel):
    """Response from listing existence check."""
    exists: bool
    listing_url: str | None = None
    details: str = ""


class BatchRunRequest(BaseModel):
    """Request to run batch automation."""
    submission_ids: list[uuid.UUID]
    delay_seconds: float = Field(30.0, ge=5, le=300, description="Delay between submissions")
    auto_submit: bool = Field(False, description="Auto-submit after filling")


class BatchRunResponse(BaseModel):
    """Response from batch automation."""
    total: int
    succeeded: int
    failed: int
    duration_ms: int


class FormMappingResponse(BaseModel):
    """Site form mapping info."""
    site_name: str
    slug: str
    has_mapping: bool
    fields: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# POST /citations/automation/auto-fill — Auto-fill a submission form
# ---------------------------------------------------------------------------
@router.post(
    "/submissions/{submission_id}/auto-fill",
    response_model=APIResponse[AutoFillResponse],
)
async def auto_fill_submission(
    submission_id: uuid.UUID,
    request: AutoFillRequest,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[AutoFillResponse]:
    """Launch browser, navigate to site, and auto-fill the form."""
    from seo_platform.services.citation_automation import get_automation_service
    from seo_platform.services.citation_automation import SubmissionTask

    async with get_session() as session:
        # Get submission
        result = await session.execute(
            select(CitationSubmissionV2).where(
                CitationSubmissionV2.id == submission_id,
                CitationSubmissionV2.tenant_id == tenant_id,
            )
        )
        submission = result.scalar_one_or_none()
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        # Get project
        proj_result = await session.execute(
            select(CitationProject).where(
                CitationProject.id == submission.project_id,
                CitationProject.tenant_id == tenant_id,
            )
        )
        project = proj_result.scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Get site
        site_result = await session.execute(
            select(CitationSite).where(CitationSite.id == submission.site_id)
        )
        site = site_result.scalar_one_or_none()

    # Build project data dict
    project_data = {
        "business_name": project.business_name,
        "phone": project.phone or "",
        "email": project.email or "",
        "website": project.website_url or "",
        "address": project.address or "",
        "city": project.city or "",
        "state": project.state or "",
        "postal_code": project.postal_code or "",
        "country": project.country or "Australia",
        "description": project.description or "",
        "category": project.category or "",
    }

    # Build task
    task = SubmissionTask(
        submission_id=submission_id,
        project_id=project.id,
        tenant_id=tenant_id,
        site_url=site.url if site else "",
        submission_url=site.submission_url if site else None,
        site_name=site.name if site else "Unknown",
        site_slug=_get_site_slug(site.name) if site else None,
        project_data=project_data,
    )

    # Run automation
    service = get_automation_service()
    auto_result = await service.run_single_submission(task, auto_submit=False)

    # Build response
    import base64
    response = AutoFillResponse(
        filled_fields=auto_result.filled_fields,
        unfilled_fields=auto_result.unfilled_fields,
        screenshot_before=base64.b64encode(auto_result.screenshot_before).decode() if auto_result.screenshot_before else None,
        screenshot_after=base64.b64encode(auto_result.screenshot_after).decode() if auto_result.screenshot_after else None,
        page_url=auto_result.page_url,
        listing_url=auto_result.listing_url,
    )

    if not auto_result.success and auto_result.error:
        raise HTTPException(status_code=400, detail=auto_result.error)

    return APIResponse(data=response)


# ---------------------------------------------------------------------------
# POST /citations/automation/submit — Submit a filled form
# ---------------------------------------------------------------------------
@router.post(
    "/submissions/{submission_id}/submit-form",
    response_model=APIResponse[SubmitResponse],
)
async def submit_filled_form(
    submission_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[SubmitResponse]:
    """Submit the currently filled form (requires operator action)."""
    # In semi-auto mode, this is triggered by the operator clicking "Submit"
    # The browser session is managed client-side or via WebSocket
    return APIResponse(data=SubmitResponse(
        submitted=False,
        error="Submit requires active browser session. Use auto-fill with auto_submit=true.",
    ))


# ---------------------------------------------------------------------------
# POST /citations/automation/check-existence — Check for existing listing
# ---------------------------------------------------------------------------
@router.post(
    "/submissions/{submission_id}/check-existence",
    response_model=APIResponse[CheckExistenceResponse],
)
async def check_listing_existence(
    submission_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[CheckExistenceResponse]:
    """Check if a business listing already exists on the target site."""
    from seo_platform.services.citation_automation import get_automation_service
    from seo_platform.services.citation_automation import SubmissionTask

    async with get_session() as session:
        result = await session.execute(
            select(CitationSubmissionV2).where(
                CitationSubmissionV2.id == submission_id,
                CitationSubmissionV2.tenant_id == tenant_id,
            )
        )
        submission = result.scalar_one_or_none()
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        proj_result = await session.execute(
            select(CitationProject).where(
                CitationProject.id == submission.project_id,
                CitationProject.tenant_id == tenant_id,
            )
        )
        project = proj_result.scalar_one_or_none()

        site_result = await session.execute(
            select(CitationSite).where(CitationSite.id == submission.site_id)
        )
        site = site_result.scalar_one_or_none()

    if not project or not site:
        raise HTTPException(status_code=404, detail="Project or site not found")

    # Navigate to site and search
    from seo_platform.services.browser_manager import get_browser_manager
    browser_manager = get_browser_manager()

    try:
        async with browser_manager.browser_session() as (browser, context, page):
            target_url = site.submission_url or site.url
            await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)

            service = get_automation_service()
            existence = await service.check_listing_exists(
                page,
                project.business_name,
                project.city,
            )

            return APIResponse(data=CheckExistenceResponse(**existence))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Check failed: {e}")


# ---------------------------------------------------------------------------
# POST /citations/automation/batch — Run batch automation
# ---------------------------------------------------------------------------
@router.post(
    "/batch",
    response_model=APIResponse[BatchRunResponse],
)
async def run_batch_automation(
    request: BatchRunRequest,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[BatchRunResponse]:
    """Run batch automation for multiple submissions."""
    from seo_platform.services.citation_automation import get_automation_service, SubmissionTask

    tasks = []

    async with get_session() as session:
        for sub_id in request.submission_ids:
            result = await session.execute(
                select(CitationSubmissionV2).where(
                    CitationSubmissionV2.id == sub_id,
                    CitationSubmissionV2.tenant_id == tenant_id,
                )
            )
            submission = result.scalar_one_or_none()
            if not submission:
                continue

            proj_result = await session.execute(
                select(CitationProject).where(
                    CitationProject.id == submission.project_id,
                )
            )
            project = proj_result.scalar_one_or_none()

            site_result = await session.execute(
                select(CitationSite).where(CitationSite.id == submission.site_id)
            )
            site = site_result.scalar_one_or_none()

            if not project or not site:
                continue

            project_data = {
                "business_name": project.business_name,
                "phone": project.phone or "",
                "email": project.email or "",
                "website": project.website_url or "",
                "address": project.address or "",
                "city": project.city or "",
                "state": project.state or "",
                "postal_code": project.postal_code or "",
                "country": project.country or "Australia",
                "description": project.description or "",
                "category": project.category or "",
            }

            tasks.append(SubmissionTask(
                submission_id=sub_id,
                project_id=project.id,
                tenant_id=tenant_id,
                site_url=site.url,
                submission_url=site.submission_url,
                site_name=site.name,
                site_slug=_get_site_slug(site.name),
                project_data=project_data,
            ))

    if not tasks:
        raise HTTPException(status_code=400, detail="No valid submissions found")

    service = get_automation_service()
    batch_result = await service.run_batch(
        tasks,
        delay_seconds=request.delay_seconds,
        auto_submit=request.auto_submit,
    )

    return APIResponse(data=BatchRunResponse(
        total=batch_result.total,
        succeeded=batch_result.succeeded,
        failed=batch_result.failed,
        duration_ms=batch_result.duration_ms,
    ))


# ---------------------------------------------------------------------------
# GET /citations/automation/form-mappings — List available form mappings
# ---------------------------------------------------------------------------
@router.get(
    "/form-mappings",
    response_model=APIResponse[list[FormMappingResponse]],
)
async def list_form_mappings(
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[list[FormMappingResponse]]:
    """List all available site form mappings."""
    from seo_platform.services.form_filler import FormFiller

    filler = FormFiller()
    mappings = []

    for slug, config in filler._mappings.items():
        mappings.append(FormMappingResponse(
            site_name=config.get("name", slug),
            slug=slug,
            has_mapping=bool(config.get("fields")),
            fields=list(config.get("fields", {}).keys()),
        ))

    return APIResponse(data=mappings)


# ---------------------------------------------------------------------------
# GET /citations/automation/form-mapping/{slug} — Get specific mapping
# ---------------------------------------------------------------------------
@router.get(
    "/form-mapping/{slug}",
    response_model=APIResponse[dict[str, Any]],
)
async def get_form_mapping(
    slug: str,
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[dict[str, Any]]:
    """Get the form mapping for a specific site."""
    from seo_platform.services.form_filler import FormFiller

    filler = FormFiller()
    mapping = filler.get_site_mapping(slug)

    if not mapping:
        raise HTTPException(status_code=404, detail=f"No mapping found for '{slug}'")

    return APIResponse(data=mapping)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _get_site_slug(site_name: str) -> str | None:
    """Convert a site name to a slug for form mapping lookup."""
    if not site_name:
        return None

    slug = site_name.lower().strip()
    slug = slug.replace(" ", "_")
    slug = slug.replace("-", "_")
    slug = slug.replace(".", "")
    slug = slug.replace(",", "")
    slug = slug.replace("(", "").replace(")", "")

    # Common name normalizations
    normalizations = {
        "hotfrog_australia": "hotfrog_australia",
        "yellow_pages_australia": "yellow_pages_au",
        "true_local": "truelocal",
        "start_local": "start_local",
        "australian_business_directory": "australian_business_directory",
        "cylex_australia": "cylex_australia",
        "business_australia": "business_australia",
        "google_business_profile": "google_business",
        "bing_places": "bing_places",
        "facebook_business": "facebook_business",
    }

    return normalizations.get(slug, slug)
