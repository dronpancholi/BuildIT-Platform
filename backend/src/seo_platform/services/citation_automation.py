"""
SEO Platform — Citation Automation Service
============================================
Orchestrates semi-automated citation submissions using Playwright.
Handles the full workflow: navigate → search → fill → submit → capture.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from playwright.async_api import Page

from seo_platform.core.logging import get_logger
from seo_platform.services.browser_manager import AutomationResult, BrowserManager, get_browser_manager
from seo_platform.services.form_filler import FormFiller

logger = get_logger(__name__)


@dataclass
class SubmissionTask:
    """A single submission task to process."""
    submission_id: UUID
    project_id: UUID
    tenant_id: UUID
    site_url: str
    submission_url: str | None
    site_name: str
    site_slug: str | None
    project_data: dict[str, Any]


@dataclass
class BatchResult:
    """Result of a batch automation run."""
    total: int
    succeeded: int
    failed: int
    results: list[AutomationResult] = field(default_factory=list)
    duration_ms: int = 0


class CitationAutomationService:
    """
    Orchestrates the full citation automation workflow.

    Workflow:
    1. Get submission from queue
    2. Launch browser
    3. Navigate to submission URL
    4. Check if listing exists (search)
    5. If not exists, navigate to add listing form
    6. Fill form using FormFiller
    7. Pause for operator review (semi-auto)
    8. Submit on operator command
    9. Capture result URL
    10. Update submission status
    """

    def __init__(self):
        self._browser_manager = get_browser_manager()
        self._form_filler = FormFiller()

    async def check_listing_exists(
        self,
        page: Page,
        business_name: str,
        city: str | None = None,
    ) -> dict[str, Any]:
        """
        Check if a business listing already exists on the site.

        Returns:
            {"exists": bool, "listing_url": str | None, "details": str}
        """
        location = city or ""
        listing_url = await self._form_filler.search_existing_listing(
            page, business_name, location
        )

        if listing_url:
            return {
                "exists": True,
                "listing_url": listing_url,
                "details": f"Found existing listing at {listing_url}",
            }

        return {
            "exists": False,
            "listing_url": None,
            "details": "No existing listing found",
        }

    async def auto_fill_form(
        self,
        page: Page,
        project_data: dict[str, Any],
        site_slug: str | None = None,
    ) -> dict[str, Any]:
        """
        Auto-fill the form on the current page.

        Returns:
            {
                "filled_fields": [...],
                "unfilled_fields": [...],
                "screenshot_before": bytes,
                "screenshot_after": bytes,
            }
        """
        # Take screenshot before filling
        screenshot_before = await self._browser_manager.take_screenshot(page)

        # Fill the form
        result = await self._form_filler.fill_form(page, project_data, site_slug)

        # Take screenshot after filling
        screenshot_after = await self._browser_manager.take_screenshot(page)

        return {
            "filled_fields": result["filled_fields"],
            "unfilled_fields": result["unfilled_fields"],
            "screenshot_before": screenshot_before,
            "screenshot_after": screenshot_after,
        }

    async def submit_form(self, page: Page) -> dict[str, Any]:
        """
        Submit the form on the current page.

        Returns:
            {"submitted": bool, "result_url": str | None, "error": str | None}
        """
        try:
            submit_button = await self._form_filler.find_submit_button(page)
            if not submit_button:
                return {
                    "submitted": False,
                    "result_url": None,
                    "error": "Submit button not found",
                }

            # Click submit
            await submit_button.click()

            # Wait for navigation
            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                await page.wait_for_timeout(5000)

            # Capture the result URL
            result_url = page.url

            return {
                "submitted": True,
                "result_url": result_url,
                "error": None,
            }

        except Exception as e:
            return {
                "submitted": False,
                "result_url": None,
                "error": str(e),
            }

    async def run_single_submission(
        self,
        task: SubmissionTask,
        auto_submit: bool = False,
    ) -> AutomationResult:
        """
        Execute a single submission with browser automation.

        Args:
            task: The submission task to process
            auto_submit: If True, auto-submit after filling. If False, pause for review.

        Returns:
            AutomationResult with all details
        """
        start_time = time.time()
        result = AutomationResult(success=False)

        try:
            async with self._browser_manager.browser_session() as (browser, context, page):
                # Determine the URL to navigate to
                target_url = task.submission_url or task.site_url

                if not target_url:
                    result.error = "No submission URL available"
                    return result

                logger.info(
                    "automation_navigating",
                    submission_id=str(task.submission_id),
                    url=target_url,
                )

                # Navigate to the site
                try:
                    await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
                except Exception as e:
                    result.error = f"Navigation failed: {e}"
                    return result

                result.page_url = page.url
                result.screenshot_before = await self._browser_manager.take_screenshot(page)

                # Check if listing already exists
                existence = await self.check_listing_exists(
                    page,
                    task.project_data.get("business_name", ""),
                    task.project_data.get("city"),
                )

                if existence["exists"]:
                    result.listing_url = existence["listing_url"]
                    result.error = existence["details"]
                    result.screenshot_after = await self._browser_manager.take_screenshot(page)
                    return result

                # Auto-fill the form
                fill_result = await self.auto_fill_form(
                    page,
                    task.project_data,
                    task.site_slug,
                )

                result.filled_fields = fill_result["filled_fields"]
                result.unfilled_fields = fill_result["unfilled_fields"]
                result.screenshot_after = fill_result["screenshot_after"]

                # Auto-submit if requested
                if auto_submit:
                    submit_result = await self.submit_form(page)
                    if submit_result["submitted"]:
                        result.listing_url = submit_result["result_url"]
                        result.success = True
                    else:
                        result.error = submit_result["error"]
                else:
                    # Semi-auto: form is filled, waiting for operator to submit
                    result.success = True

                result.duration_ms = int((time.time() - start_time) * 1000)

                logger.info(
                    "automation_complete",
                    submission_id=str(task.submission_id),
                    success=result.success,
                    filled=len(result.filled_fields),
                    unfilled=len(result.unfilled_fields),
                    duration_ms=result.duration_ms,
                )

                return result

        except Exception as e:
            result.error = f"Automation failed: {e}"
            result.duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                "automation_error",
                submission_id=str(task.submission_id),
                error=str(e),
            )
            return result

    async def run_batch(
        self,
        tasks: list[SubmissionTask],
        delay_seconds: float = 30.0,
        auto_submit: bool = False,
    ) -> BatchResult:
        """
        Run multiple submissions with delays between each.

        Args:
            tasks: List of submission tasks
            delay_seconds: Delay between submissions (rate limiting)
            auto_submit: If True, auto-submit each form

        Returns:
            BatchResult with aggregate stats
        """
        start_time = time.time()
        batch_result = BatchResult(
            total=len(tasks),
            succeeded=0,
            failed=0,
        )

        for i, task in enumerate(tasks):
            logger.info(
                "batch_progress",
                current=i + 1,
                total=len(tasks),
                submission_id=str(task.submission_id),
            )

            result = await self.run_single_submission(task, auto_submit)
            batch_result.results.append(result)

            if result.success:
                batch_result.succeeded += 1
            else:
                batch_result.failed += 1

            # Rate limiting delay between submissions
            if i < len(tasks) - 1:
                await asyncio.sleep(delay_seconds)

        batch_result.duration_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "batch_complete",
            total=batch_result.total,
            succeeded=batch_result.succeeded,
            failed=batch_result.failed,
            duration_ms=batch_result.duration_ms,
        )

        return batch_result

    async def cleanup(self) -> None:
        """Clean up browser resources."""
        await self._browser_manager.cleanup_stale_browsers()


# Singleton instance
_automation_service: CitationAutomationService | None = None


def get_automation_service() -> CitationAutomationService:
    """Get or create the singleton CitationAutomationService."""
    global _automation_service
    if _automation_service is None:
        _automation_service = CitationAutomationService()
    return _automation_service
