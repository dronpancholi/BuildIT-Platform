"""
SEO Platform — Browser Manager
===============================
Playwright browser pool with anti-detection measures.
Manages browser instances, contexts, and screenshots.
"""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)

# Stealth scripts to block webdriver detection
STEALTH_SCRIPTS = [
    """
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    """,
    """
    Object.defineProperty(navigator, 'languages', {get: () => ['en-AU', 'en-US', 'en']});
    """,
    """
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5],
    });
    """,
    """
    window.chrome = { runtime: {} };
    """,
    """
    Object.defineProperty(navigator, 'permissions', {
        get: () => ({
            query: (params) => Promise.resolve({ state: 'granted' }),
        }),
    });
    """,
]

# Common browser headers to mimic real users
DEFAULT_HEADERS = {
    "Accept-Language": "en-AU,en-US;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
}


@dataclass
class BrowserPoolEntry:
    """Entry in the browser pool."""
    browser: Browser
    created_at: float
    in_use: bool = False


@dataclass
class AutomationResult:
    """Result of a browser automation operation."""
    success: bool
    page_url: str = ""
    screenshot_before: bytes | None = None
    screenshot_after: bytes | None = None
    filled_fields: list[str] = field(default_factory=list)
    unfilled_fields: list[str] = field(default_factory=list)
    error: str | None = None
    listing_url: str | None = None
    duration_ms: int = 0


class BrowserManager:
    """
    Manages Playwright browser instances with anti-detection measures.

    Features:
    - Browser pool (reuse instances for performance)
    - Stealth mode (block webdriver detection)
    - Automatic cleanup on shutdown
    - Screenshot capture
    """

    def __init__(self, max_browsers: int = 3, headless: bool = True):
        self._max_browsers = max_browsers
        self._headless = headless
        self._playwright = None
        self._pool: list[BrowserPoolEntry] = []
        self._lock = asyncio.Lock()
        self._started = False

    async def start(self) -> None:
        """Start the Playwright instance."""
        if self._started:
            return
        self._playwright = await async_playwright().start()
        self._started = True
        logger.info("browser_manager_started", max_browsers=self._max_browsers)

    async def stop(self) -> None:
        """Close all browsers and stop Playwright."""
        async with self._lock:
            for entry in self._pool:
                try:
                    await entry.browser.close()
                except Exception:
                    pass
            self._pool.clear()
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self._started = False
        logger.info("browser_manager_stopped")

    async def _create_browser(self, proxy: str | None = None) -> Browser:
        """Create a new browser instance with stealth settings."""
        if not self._started:
            await self.start()

        launch_args = {
            "headless": self._headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars",
                "--window-size=1920,1080",
                "--disable-extensions",
                "--disable-gpu",
            ],
        }

        if proxy:
            launch_args["proxy"] = {"server": proxy}

        browser = await self._playwright.chromium.launch(**launch_args)
        return browser

    async def acquire_browser(self, proxy: str | None = None) -> Browser:
        """Acquire a browser from the pool or create a new one."""
        async with self._lock:
            # Try to reuse an idle browser
            for entry in self._pool:
                if not entry.in_use and not entry.browser.is_connected():
                    # Browser is dead, remove it
                    self._pool.remove(entry)
                    continue
                if not entry.in_use:
                    entry.in_use = True
                    return entry.browser

            # Create new browser if pool not full
            if len(self._pool) < self._max_browsers:
                browser = await self._create_browser(proxy)
                self._pool.append(BrowserPoolEntry(
                    browser=browser,
                    created_at=time.time(),
                    in_use=True,
                ))
                return browser

            # Pool is full, wait for one to become available
            logger.warning("browser_pool_full", pool_size=len(self._pool))

        # Fallback: create a new browser outside the lock
        browser = await self._create_browser(proxy)
        return browser

    async def release_browser(self, browser: Browser) -> None:
        """Release a browser back to the pool."""
        async with self._lock:
            for entry in self._pool:
                if entry.browser == browser:
                    entry.in_use = False
                    return

    async def create_context(
        self,
        browser: Browser,
        viewport: dict | None = None,
        locale: str = "en-AU",
    ) -> BrowserContext:
        """Create a browser context with stealth settings."""
        context_args = {
            "viewport": viewport or {"width": 1920, "height": 1080},
            "locale": locale,
            "timezone_id": "Australia/Sydney",
            "user_agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "extra_http_headers": DEFAULT_HEADERS,
        }

        context = await browser.new_context(**context_args)

        # Add stealth scripts
        for script in STEALTH_SCRIPTS:
            await context.add_init_script(script)

        # Block webdriver detection routes
        await context.route("**/webdriver**", lambda route: route.abort())
        await context.route("**/driver**", lambda route: route.abort())

        return context

    async def take_screenshot(self, page: Page, full_page: bool = True) -> bytes:
        """Capture a screenshot of the current page."""
        try:
            screenshot = await page.screenshot(full_page=full_page, type="png")
            return screenshot
        except Exception as e:
            logger.error("screenshot_failed", error=str(e))
            return b""

    async def cleanup_stale_browsers(self) -> int:
        """Remove stale browsers from the pool."""
        removed = 0
        async with self._lock:
            stale = [
                entry for entry in self._pool
                if not entry.browser.is_connected() or (
                    not entry.in_use and time.time() - entry.created_at > 3600
                )
            ]
            for entry in stale:
                try:
                    await entry.browser.close()
                except Exception:
                    pass
                self._pool.remove(entry)
                removed += 1

        if removed > 0:
            logger.info("stale_browsers_cleaned", count=removed)
        return removed

    @asynccontextmanager
    async def browser_session(
        self,
        proxy: str | None = None,
        viewport: dict | None = None,
    ) -> AsyncIterator[tuple[Browser, BrowserContext, Page]]:
        """Context manager for a browser session with auto-cleanup."""
        browser = await self.acquire_browser(proxy)
        context = await self.create_context(browser, viewport)
        page = await context.new_page()

        try:
            yield browser, context, page
        finally:
            try:
                await page.close()
            except Exception:
                pass
            try:
                await context.close()
            except Exception:
                pass
            await self.release_browser(browser)


# Singleton instance
_browser_manager: BrowserManager | None = None


def get_browser_manager() -> BrowserManager:
    """Get or create the singleton BrowserManager."""
    global _browser_manager
    if _browser_manager is None:
        _browser_manager = BrowserManager(max_browsers=3, headless=True)
    return _browser_manager
