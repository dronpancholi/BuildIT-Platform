"""
SEO Platform — Citation Verification API
==========================================
Endpoints for email verification automation.
"""

from __future__ import annotations

import base64
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
class VerifyEmailRequest(BaseModel):
    """Request to trigger email verification."""
    max_wait_seconds: int = Field(300, ge=30, le=600, description="Max wait time in seconds")
    poll_interval_seconds: int = Field(30, ge=10, le=120, description="Poll interval in seconds")


class VerifyEmailResponse(BaseModel):
    """Response from email verification."""
    success: bool
    status: str
    email_found: bool = False
    link_clicked: bool = False
    link_url: str | None = None
    confirmation_text: str | None = None
    error_text: str | None = None
    verification_time_seconds: float = 0
    screenshot: str | None = Field(None, description="Base64 encoded screenshot")
    redirect_chain: list[str] = Field(default_factory=list)


class CheckEmailRequest(BaseModel):
    """Request to check inbox (one-shot)."""
    pass


class CheckEmailResponse(BaseModel):
    """Response from inbox check."""
    email_found: bool
    links: list[str] = Field(default_factory=list)
    email_subject: str | None = None
    email_from: str | None = None
    email_date: str | None = None


class ClickLinkRequest(BaseModel):
    """Request to manually click a verification link."""
    link_url: str


class ClickLinkResponse(BaseModel):
    """Response from link clicking."""
    success: bool
    confirmation_text: str | None = None
    error_text: str | None = None
    final_url: str = ""
    redirect_chain: list[str] = Field(default_factory=list)
    screenshot: str | None = None


class InboxPreviewResponse(BaseModel):
    """Inbox preview for UI display."""
    emails: list[dict[str, Any]] = Field(default_factory=list)


class EmailPatternResponse(BaseModel):
    """Email pattern for a site."""
    site_name: str
    domain: str
    verification_sender: list[str]
    subject_patterns: list[str]
    wait_time_seconds: int


# ---------------------------------------------------------------------------
# POST /citations/verification/submissions/{id}/verify-email
# ---------------------------------------------------------------------------
@router.post(
    "/submissions/{submission_id}/verify-email",
    response_model=APIResponse[VerifyEmailResponse],
)
async def verify_email(
    submission_id: uuid.UUID,
    request: VerifyEmailRequest,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[VerifyEmailResponse]:
    """Trigger email verification for a submission with polling."""
    from seo_platform.services.email_verification_service import get_verification_service

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

        # Get project for email credentials
        proj_result = await session.execute(
            select(CitationProject).where(
                CitationProject.id == submission.project_id,
                CitationProject.tenant_id == tenant_id,
            )
        )
        project = proj_result.scalar_one_or_none()

        # Get site for domain
        site_result = await session.execute(
            select(CitationSite).where(CitationSite.id == submission.site_id)
        )
        site = site_result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=400, detail="Project not found")

    if not project.submission_email or not project.submission_password:
        raise HTTPException(
            status_code=400,
            detail="No email credentials configured. Set submission_email and submission_password on the project.",
        )

    site_domain = ""
    if site and site.url:
        from urllib.parse import urlparse
        site_domain = urlparse(site.url).netloc

    service = get_verification_service()

    # Decrypt password
    from seo_platform.core.encryption import encryption_service
    password = encryption_service.decrypt(project.submission_password)

    verify_result = await service.verify_email_for_submission(
        submission_email=project.submission_email,
        submission_password=password,
        site_domain=site_domain,
        max_wait_seconds=request.max_wait_seconds,
        poll_interval_seconds=request.poll_interval_seconds,
    )

    # Build response
    response = VerifyEmailResponse(
        success=verify_result.success,
        status=verify_result.status,
        email_found=verify_result.email_found,
        link_clicked=verify_result.link_clicked,
        link_url=verify_result.link_url,
        confirmation_text=verify_result.confirmation_text,
        error_text=verify_result.error_text,
        verification_time_seconds=verify_result.verification_time_seconds,
        screenshot=base64.b64encode(verify_result.screenshot).decode() if verify_result.screenshot else None,
        redirect_chain=verify_result.redirect_chain,
    )

    # Update submission status if verified
    if verify_result.success:
        async with get_session() as session:
            result = await session.execute(
                select(CitationSubmissionV2).where(
                    CitationSubmissionV2.id == submission_id,
                )
            )
            sub = result.scalar_one_or_none()
            if sub:
                sub.email_verified = True
                sub.status = "pending_review"
                await session.commit()

    return APIResponse(data=response)


# ---------------------------------------------------------------------------
# POST /citations/verification/submissions/{id}/check-email
# ---------------------------------------------------------------------------
@router.post(
    "/submissions/{submission_id}/check-email",
    response_model=APIResponse[CheckEmailResponse],
)
async def check_email(
    submission_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[CheckEmailResponse]:
    """One-shot inbox check: read inbox now, don't wait."""
    from seo_platform.services.email_verification_service import get_verification_service

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
            )
        )
        project = proj_result.scalar_one_or_none()

        site_result = await session.execute(
            select(CitationSite).where(CitationSite.id == submission.site_id)
        )
        site = site_result.scalar_one_or_none()

    if not project or not project.submission_email:
        raise HTTPException(status_code=400, detail="No email credentials configured")

    site_domain = ""
    if site and site.url:
        from urllib.parse import urlparse
        site_domain = urlparse(site.url).netloc

    from seo_platform.core.encryption import encryption_service
    password = encryption_service.decrypt(project.submission_password)

    service = get_verification_service()
    check_result = await service.check_and_process_verification(
        submission_email=project.submission_email,
        submission_password=password,
        site_domain=site_domain,
    )

    return APIResponse(data=CheckEmailResponse(
        email_found=check_result.email_found,
        links=[check_result.link_url] if check_result.link_url else [],
        confirmation_text=check_result.confirmation_text,
        error_text=check_result.error_text,
    ))


# ---------------------------------------------------------------------------
# POST /citations/verification/submissions/{id}/click-verification-link
# ---------------------------------------------------------------------------
@router.post(
    "/submissions/{submission_id}/click-verification-link",
    response_model=APIResponse[ClickLinkResponse],
)
async def click_verification_link(
    submission_id: uuid.UUID,
    request: ClickLinkRequest,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[ClickLinkResponse]:
    """Manually trigger link clicking for a specific URL."""
    from seo_platform.services.email_verification_service import get_verification_service

    # Verify submission exists
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

    service = get_verification_service()
    click_result = await service.click_manual_link(request.link_url)

    response = ClickLinkResponse(
        success=click_result.success,
        confirmation_text=click_result.confirmation_text,
        error_text=click_result.error_text,
        final_url=click_result.final_url,
        redirect_chain=click_result.redirect_chain,
        screenshot=base64.b64encode(click_result.screenshot).decode() if click_result.screenshot else None,
    )

    # Update submission if verified
    if click_result.success:
        async with get_session() as session:
            result = await session.execute(
                select(CitationSubmissionV2).where(
                    CitationSubmissionV2.id == submission_id,
                )
            )
            sub = result.scalar_one_or_none()
            if sub:
                sub.email_verified = True
                sub.listing_url = click_result.final_url
                await session.commit()

    return APIResponse(data=response)


# ---------------------------------------------------------------------------
# GET /citations/verification/inbox-preview
# ---------------------------------------------------------------------------
@router.get(
    "/inbox-preview",
    response_model=APIResponse[InboxPreviewResponse],
)
async def inbox_preview(
    project_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_validated_tenant_id),
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[InboxPreviewResponse]:
    """Preview recent emails in submission inbox."""
    from seo_platform.services.email_verification_service import get_verification_service

    async with get_session() as session:
        result = await session.execute(
            select(CitationProject).where(
                CitationProject.id == project_id,
                CitationProject.tenant_id == tenant_id,
            )
        )
        project = result.scalar_one_or_none()

    if not project or not project.submission_email:
        raise HTTPException(status_code=400, detail="No email credentials configured")

    from seo_platform.core.encryption import encryption_service
    password = encryption_service.decrypt(project.submission_password)

    service = get_verification_service()
    emails = service.check_inbox_preview(
        submission_email=project.submission_email,
        submission_password=password,
        limit=10,
    )

    return APIResponse(data=InboxPreviewResponse(emails=emails))


# ---------------------------------------------------------------------------
# GET /citations/verification/email-patterns
# ---------------------------------------------------------------------------
@router.get(
    "/email-patterns",
    response_model=APIResponse[list[EmailPatternResponse]],
)
async def list_email_patterns(
    user: CurrentUser = Depends(get_current_user),
) -> APIResponse[list[EmailPatternResponse]]:
    """List all known verification email patterns."""
    from seo_platform.services.email_verification_service import get_verification_service

    service = get_verification_service()
    patterns = []

    for domain, config in service._patterns.items():
        patterns.append(EmailPatternResponse(
            site_name=config.get("name", domain),
            domain=domain,
            verification_sender=config.get("verification_sender", []),
            subject_patterns=config.get("subject_patterns", []),
            wait_time_seconds=config.get("wait_time_seconds", 60),
        ))

    return APIResponse(data=patterns)
