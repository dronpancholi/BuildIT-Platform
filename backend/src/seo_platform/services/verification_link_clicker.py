"""
SEO Platform — Verification Link Clicker
==========================================
Playwright-based link clicker with confirmation detection.
Navigates to verification URLs and determines success/failure.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from playwright.async_api import Page

from seo_platform.core.logging import get_logger
from seo_platform.services.browser_manager import BrowserManager, get_browser_manager

logger = get_logger(__name__)

# Common confirmation page indicators
CONFIRMATION_KEYWORDS = [
    "verified",
    "confirmed",
    "success",
    "thank you",
    "thank you for",
    "successfully confirmed",
    "email confirmed",
    "account verified",
    "listing verified",
    "registration complete",
    "welcome",
    "activation successful",
    "your email has been",
    "your account has been",
    "verification complete",
    "you're all set",
    "all done",
    "getting started",
]

# Common error page indicators
ERROR_KEYWORDS = [
    "error",
    "failed",
    "invalid",
    "expired",
    "not found",
    "already verified",
    "already confirmed",
    "token expired",
    "link expired",
    "link invalid",
    "verification failed",
    "something went wrong",
    "oops",
    "try again",
    "unauthorized",
    "access denied",
]

# Default confirmation text patterns for success detection
DEFAULT_CONFIRMATION_PATTERNS = [
    "thank you",
    "verified",
    "confirmed",
    "success",
    "welcome",
    "complete",
]


@dataclass
class ClickResult:
    """Result of clicking a verification link."""
    success: bool
    confirmation_text: str | None = None
    error_text: str | None = None
    redirect_chain: list[str] = field(default_factory=list)
    final_url: str = ""
    screenshot: bytes | None = None
    duration_ms: int = 0


class VerificationLinkClicker:
    """
    Clicks verification links and confirms success.

    Handles:
    - Multiple redirect chains
    - Confirmation page detection
    - Error page detection
    - Screenshot capture
    - Timeout handling
    """

    def __init__(self, browser_manager: BrowserManager | None = None):
        self._browser_manager = browser_manager or get_browser_manager()

    async def click_verification_link(
        self,
        url: str,
        confirmation_patterns: list[str] | None = None,
        timeout_ms: int = 30000,
    ) -> ClickResult:
        """
        Navigate to verification URL and determine result.

        Args:
            url: The verification URL to click
            confirmation_patterns: Custom patterns to detect confirmation page
            timeout_ms: Timeout for page load

        Returns:
            ClickResult with success status and details
        """
        start_time = time.time()
        result = ClickResult(success=False)

        try:
            async with self._browser_manager.browser_session() as (browser, context, page):
                # Track redirect chain
                redirect_chain = [url]

                def on_response(response):
                    if response.url != redirect_chain[-1]:
                        redirect_chain.append(response.url)

                page.on("response", on_response)

                # Navigate to verification URL
                try:
                    await page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=timeout_ms,
                    )
                except Exception as e:
                    result.error_text = f"Navigation failed: {e}"
                    result.screenshot = await self._browser_manager.take_screenshot(page)
                    return result

                # Wait a bit for any JavaScript redirects
                try:
                    await page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass

                result.redirect_chain = redirect_chain
                result.final_url = page.url

                # Get page content
                page_text = await page.inner_text("body")
                page_text_lower = page_text.lower()

                # Take screenshot
                result.screenshot = await self._browser_manager.take_screenshot(page)

                # Check for confirmation
                patterns = confirmation_patterns or DEFAULT_CONFIRMATION_PATTERNS
                confirmation_found = self._detect_confirmation(page_text_lower, patterns)

                if confirmation_found:
                    result.success = True
                    result.confirmation_text = confirmation_found
                    logger.info(
                        "verification_confirmed",
                        url=url,
                        confirmation=confirmation_found,
                    )
                    return result

                # Check for errors
                error_found = self._detect_error(page_text_lower)
                if error_found:
                    result.error_text = error_found
                    logger.warning(
                        "verification_error_detected",
                        url=url,
                        error=error_found,
                    )
                    return result

                # If no clear confirmation or error, check URL patterns
                if self._url_indicates_success(page.url, url):
                    result.success = True
                    result.confirmation_text = "Redirected to success page"
                    return result

                # Ambiguous - might need manual review
                result.error_text = "Could not determine verification status"
                return result

        except Exception as e:
            result.error_text = f"Verification failed: {e}"
            logger.error("verification_click_failed", url=url, error=str(e))
            return result
        finally:
            result.duration_ms = int((time.time() - start_time) * 1000)

    def _detect_confirmation(self, page_text: str, patterns: list[str]) -> str | None:
        """Detect confirmation text on the page."""
        for pattern in patterns:
            if pattern.lower() in page_text:
                # Extract surrounding context
                idx = page_text.lower().find(pattern.lower())
                start = max(0, idx - 50)
                end = min(len(page_text), idx + len(pattern) + 100)
                context = page_text[start:end].strip()
                return context[:200]  # Limit length
        return None

    def _detect_error(self, page_text: str) -> str | None:
        """Detect error text on the page."""
        for keyword in ERROR_KEYWORDS:
            if keyword.lower() in page_text:
                idx = page_text.lower().find(keyword.lower())
                start = max(0, idx - 50)
                end = min(len(page_text), idx + len(keyword) + 100)
                context = page_text[start:end].strip()
                return context[:200]
        return None

    def _url_indicates_success(self, current_url: str, original_url: str) -> bool:
        """Check if URL redirect indicates success."""
        success_patterns = [
            "/dashboard",
            "/success",
            "/welcome",
            "/confirmed",
            "/verified",
            "/account",
            "/profile",
            "/listing",
        ]
        current_lower = current_url.lower()
        return any(pattern in current_lower for pattern in success_patterns)

    async def click_multiple_links(
        self,
        urls: list[str],
        delay_ms: int = 2000,
    ) -> list[ClickResult]:
        """Click multiple verification links (for A/B testing)."""
        results = []
        for url in urls:
            result = await self.click_verification_link(url)
            results.append(result)
            if result.success:
                break  # Stop on first success
            await self._browser_manager._playwright.async_api.sleep(delay_ms / 1000)
        return results
