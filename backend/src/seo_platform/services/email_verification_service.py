"""
SEO Platform — Email Verification Service
==========================================
Orchestrates the full email verification workflow:
wait → read inbox → extract link → click → confirm.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

from seo_platform.core.logging import get_logger
from seo_platform.services.email_reader import EmailReader, VerificationEmail
from seo_platform.services.verification_link_clicker import ClickResult, VerificationLinkClicker

logger = get_logger(__name__)

# Path to email patterns
EMAIL_PATTERNS_PATH = Path(__file__).parent.parent.parent.parent / "data" / "email_patterns.json"


@dataclass
class VerificationResult:
    """Result of an email verification attempt."""
    success: bool
    status: str  # "verified", "failed", "timeout", "no_email", "error"
    email_found: bool = False
    link_clicked: bool = False
    link_url: str | None = None
    confirmation_text: str | None = None
    error_text: str | None = None
    verification_time_seconds: float = 0
    screenshot: bytes | None = None
    redirect_chain: list[str] = field(default_factory=list)
    emails_checked: int = 0


class EmailVerificationService:
    """
    Orchestrates the full email verification workflow.

    Workflow:
    1. After form submission, mark submission as 'awaiting_verification'
    2. Poll submission email inbox every 30 seconds
    3. When verification email arrives, extract link
    4. Click the link using Playwright
    5. Detect confirmation or error
    6. Update submission status accordingly
    """

    def __init__(self):
        self._patterns: dict[str, Any] = {}
        self._link_clicker = VerificationLinkClicker()
        self._load_patterns()

    def _load_patterns(self) -> None:
        """Load email patterns from JSON."""
        try:
            if EMAIL_PATTERNS_PATH.exists():
                with open(EMAIL_PATTERNS_PATH) as f:
                    self._patterns = json.load(f)
                logger.info("email_patterns_loaded", count=len(self._patterns))
        except Exception as e:
            logger.error("email_patterns_load_failed", error=str(e))

    def get_site_pattern(self, site_domain: str) -> dict[str, Any] | None:
        """Get email pattern for a specific site domain."""
        # Try exact match first
        if site_domain in self._patterns:
            return self._patterns[site_domain]

        # Try partial match
        for domain, pattern in self._patterns.items():
            if domain in site_domain or site_domain in domain:
                return pattern

        return None

    def _get_imap_credentials(
        self,
        submission_email: str,
        submission_password: str,
    ) -> EmailReader | None:
        """Create EmailReader from project credentials."""
        if not submission_email or not submission_password:
            return None

        # Determine IMAP provider from email domain
        domain = submission_email.split("@")[-1].lower()
        provider_map = {
            "gmail.com": "gmail",
            "googlemail.com": "gmail",
            "outlook.com": "outlook",
            "hotmail.com": "outlook",
            "live.com": "outlook",
            "yahoo.com": "yahoo",
        }
        provider = provider_map.get(domain, "custom")

        if provider == "custom":
            # For custom providers, we'd need IMAP host from config
            # For now, try common patterns
            imap_host = f"mail.{domain}"
            return EmailReader(
                imap_host=imap_host,
                email_address=submission_email,
                password=submission_password,
            )

        return EmailReader.from_provider(
            provider=provider,
            email_address=submission_email,
            password=submission_password,
        )

    async def check_and_process_verification(
        self,
        submission_email: str | None,
        submission_password: str | None,
        site_domain: str,
        after_timestamp: datetime | None = None,
    ) -> VerificationResult:
        """
        One-shot check: read inbox, find verification email, click link.

        Args:
            submission_email: Email address to check
            submission_password: Password for IMAP access
            site_domain: Domain of the site that sent verification
            after_timestamp: Only look for emails after this time

        Returns:
            VerificationResult with all details
        """
        start_time = datetime.now(UTC)

        # Get email reader
        reader = self._get_imap_credentials(submission_email, submission_password)
        if not reader:
            return VerificationResult(
                success=False,
                status="error",
                error_text="No email credentials configured",
            )

        try:
            # Connect to IMAP
            if not reader.connect():
                return VerificationResult(
                    success=False,
                    status="error",
                    error_text="Failed to connect to email server",
                )

            # Get site-specific patterns
            site_pattern = self.get_site_pattern(site_domain)
            sender_domains = [site_domain]
            subject_patterns = ["verify", "confirm", "activation"]

            if site_pattern:
                sender_domains = site_pattern.get("verification_sender", [site_domain])
                # Extract domain from email addresses
                sender_domains = [
                    d.split("@")[-1] if "@" in d else d
                    for d in sender_domains
                ]
                subject_patterns = site_pattern.get("subject_patterns", subject_patterns)

            # Search for verification emails
            if after_timestamp is None:
                after_timestamp = datetime.now(UTC) - timedelta(minutes=30)

            verification_emails = reader.search_verification_emails(
                sender_domains=sender_domains,
                subject_patterns=subject_patterns,
                after_timestamp=after_timestamp,
            )

            if not verification_emails:
                return VerificationResult(
                    success=False,
                    status="no_email",
                    email_found=False,
                    error_text="No verification email found in inbox",
                )

            # Use the most recent verification email
            ve = verification_emails[0]
            link = ve.links[0] if ve.links else None

            if not link:
                return VerificationResult(
                    success=False,
                    status="no_email",
                    email_found=True,
                    error_text="Verification email found but no links extracted",
                )

            # Click the verification link
            click_result = await self._link_clicker.click_verification_link(link)

            duration = (datetime.now(UTC) - start_time).total_seconds()

            return VerificationResult(
                success=click_result.success,
                status="verified" if click_result.success else "failed",
                email_found=True,
                link_clicked=True,
                link_url=link,
                confirmation_text=click_result.confirmation_text,
                error_text=click_result.error_text,
                verification_time_seconds=duration,
                screenshot=click_result.screenshot,
                redirect_chain=click_result.redirect_chain,
                emails_checked=len(verification_emails),
            )

        except Exception as e:
            duration = (datetime.now(UTC) - start_time).total_seconds()
            return VerificationResult(
                success=False,
                status="error",
                error_text=str(e),
                verification_time_seconds=duration,
            )
        finally:
            reader.disconnect()

    async def verify_email_for_submission(
        self,
        submission_email: str | None,
        submission_password: str | None,
        site_domain: str,
        max_wait_seconds: int = 300,
        poll_interval_seconds: int = 30,
    ) -> VerificationResult:
        """
        Main entry point with polling. Runs async with timeout.

        Polls the inbox every poll_interval_seconds until:
        - Verification email found and clicked (success)
        - max_wait_seconds exceeded (timeout)
        - Error occurs

        Args:
            submission_email: Email address to check
            submission_password: Password for IMAP access
            site_domain: Domain of the site that sent verification
            max_wait_seconds: Maximum time to wait (default 5 min)
            poll_interval_seconds: Time between polls (default 30s)

        Returns:
            VerificationResult
        """
        start_time = datetime.now(UTC)
        check_after = datetime.now(UTC) - timedelta(seconds=10)  # Look back 10s

        logger.info(
            "verification_polling_started",
            site_domain=site_domain,
            max_wait=max_wait_seconds,
            interval=poll_interval_seconds,
        )

        attempts = 0
        while True:
            attempts += 1
            elapsed = (datetime.now(UTC) - start_time).total_seconds()

            if elapsed >= max_wait_seconds:
                logger.info(
                    "verification_timeout",
                    elapsed=elapsed,
                    attempts=attempts,
                )
                return VerificationResult(
                    success=False,
                    status="timeout",
                    error_text=f"Verification timed out after {max_wait_seconds}s",
                    verification_time_seconds=elapsed,
                    emails_checked=attempts,
                )

            logger.info(
                "verification_poll_attempt",
                attempt=attempts,
                elapsed=elapsed,
            )

            result = await self.check_and_process_verification(
                submission_email=submission_email,
                submission_password=submission_password,
                site_domain=site_domain,
                after_timestamp=check_after,
            )

            if result.success:
                return result

            if result.status == "error":
                return result

            # Wait before next poll
            await asyncio.sleep(poll_interval_seconds)

    async def click_manual_link(
        self,
        link_url: str,
    ) -> ClickResult:
        """Manually trigger link clicking (for operator override)."""
        return await self._link_clicker.click_verification_link(link_url)

    def check_inbox_preview(
        self,
        submission_email: str | None,
        submission_password: str | None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get inbox preview for UI display."""
        reader = self._get_imap_credentials(submission_email, submission_password)
        if not reader:
            return []

        try:
            if not reader.connect():
                return []
            return reader.check_inbox_preview(limit=limit)
        finally:
            reader.disconnect()


# Singleton instance
_verification_service: EmailVerificationService | None = None


def get_verification_service() -> EmailVerificationService:
    """Get or create the singleton EmailVerificationService."""
    global _verification_service
    if _verification_service is None:
        _verification_service = EmailVerificationService()
    return _verification_service
