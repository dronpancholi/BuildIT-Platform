"""
SEO Platform — CAPTCHA Handler Service
=======================================
Detects and handles CAPTCHA challenges.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CaptchaInfo:
    """Information about a detected CAPTCHA."""

    captcha_type: str  # 'recaptcha_v2', 'recaptcha_v3', 'hcaptcha', 'image', 'text'
    site_key: str | None = None
    url: str | None = None
    selector: str | None = None


class CaptchaHandler:
    """
    Detects and handles CAPTCHA challenges.

    Supported types:
    - reCAPTCHA v2/v3 (Google)
    - hCaptcha
    - Image challenges
    - Text challenges

    Solving options:
    - 2Captcha API (external service)
    - Anti-Captcha API (external service)
    - Manual solve (queue for human)
    - Skip (mark as failed)
    """

    # Common CAPTCHA selectors
    RECAPTCHA_SELECTORS = [
        "iframe[src*='recaptcha']",
        ".g-recaptcha",
        "#recaptcha",
        "iframe[title*='reCAPTCHA']",
    ]
    HCAPTCHA_SELECTORS = [
        "iframe[src*='hcaptcha']",
        ".h-captcha",
        "#hcaptcha",
    ]

    async def detect_captcha(self, page) -> Optional[CaptchaInfo]:
        """
        Check page for CAPTCHA challenges.

        Returns:
            CaptchaInfo or None if no CAPTCHA detected
        """
        try:
            # Check for reCAPTCHA
            for selector in self.RECAPTCHA_SELECTORS:
                element = await page.query_selector(selector)
                if element:
                    site_key = await page.evaluate(
                        """() => {
                        const el = document.querySelector('.g-recaptcha');
                        return el ? el.getAttribute('data-sitekey') : null;
                    }"""
                    )
                    return CaptchaInfo(
                        captcha_type="recaptcha_v2",
                        site_key=site_key,
                        selector=selector,
                    )

            # Check for hCaptcha
            for selector in self.HCAPTCHA_SELECTORS:
                element = await page.query_selector(selector)
                if element:
                    return CaptchaInfo(
                        captcha_type="hcaptcha",
                        selector=selector,
                    )

            # Check for image-based CAPTCHA
            image_captcha = await page.query_selector(
                "img[src*='captcha'], img[alt*='captcha'], .captcha-image"
            )
            if image_captcha:
                return CaptchaInfo(captcha_type="image")

        except Exception as e:
            logger.error("captcha_detection_error", error=str(e))

        return None

    async def solve_captcha(
        self,
        captcha_info: CaptchaInfo,
        service: str = "manual",
        api_key: str | None = None,
    ) -> Optional[str]:
        """
        Solve CAPTCHA and return token.

        Returns:
            Token string for reCAPTCHA
            or None if skipped/failed
        """
        if service == "skip":
            logger.info("captcha_skipped", captcha_type=captcha_info.captcha_type)
            return None

        if service == "manual":
            logger.info(
                "captcha_manual_required",
                captcha_type=captcha_info.captcha_type,
            )
            return None

        if service in ("2captcha", "anticaptcha") and api_key:
            logger.info(
                "captcha_solving_started",
                service=service,
                captcha_type=captcha_info.captcha_type,
            )
            # Integration with external solving service would go here
            # For now, return None to indicate not solved
            return None

        return None

    async def handle_captcha_challenge(
        self,
        page,
        max_wait_seconds: int = 120,
    ) -> bool:
        """
        Full flow: detect → solve → submit → verify.
        Returns True if CAPTCHA was handled successfully.
        """
        captcha_info = await self.detect_captcha(page)
        if not captcha_info:
            return True  # No CAPTCHA detected

        logger.info("captcha_detected", captcha_type=captcha_info.captcha_type)

        token = await self.solve_captcha(captcha_info, service="skip")
        if not token:
            return False

        # Inject token and submit
        try:
            if captcha_info.captcha_type in ("recaptcha_v2", "recaptcha_v3"):
                await page.evaluate(f"""() => {{
                document.getElementById('g-recaptcha-response').value = '{token}';
            }}""")
            return True
        except Exception as e:
            logger.error("captcha_inject_failed", error=str(e))
            return False

    def build_captcha_config(self) -> dict:
        """Get current CAPTCHA configuration."""
        return {
            "service": "manual",
            "api_key_configured": False,
            "auto_solve": False,
            "max_wait_seconds": 120,
        }


captcha_handler = CaptchaHandler()
