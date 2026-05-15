"""
SEO Platform — Contact Extraction Engine
===========================================
Resilient contact extraction with multiple page crawling and regex extraction.
"""

import re
from typing import Any

from playwright.async_api import Page

from seo_platform.core.logging import get_logger
from seo_platform.services.scraping.base import BaseScraper

logger = get_logger(__name__)


class ContactExtractionEngine(BaseScraper):
    """
    Hardened contact extraction with:
    - Multiple page crawling (home, contact, about)
    - Resilient email regex
    - Phone number extraction
    - Social profile detection
    - Confidence scoring
    """

    EMAIL_REGEX = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    PHONE_REGEX = r'(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}'

    CONTACT_PAGE_PATTERNS = [
        "contact", "contact-us", "contactus", "about", "about-us",
        "aboutus", "team", "people", "staff", "directory",
    ]

    def __init__(self):
        super().__init__(service_name="contact_extractor")

    async def extract_contacts(self, domain: str) -> dict[str, Any]:
        """
        Crawls the domain to find contact info with confidence scoring.
        """
        url = f"https://{domain}" if not domain.startswith("http") else domain

        all_emails = set()
        all_phones = set()
        social_profiles = []
        pages_visited = []

        async def extract_from_page(page: Page, page_url: str) -> None:
            """Extract emails, phones from a single page."""
            try:
                content = await page.content()

                emails = set(re.findall(self.EMAIL_REGEX, content))
                filtered_emails = {e for e in emails if not any(x in e.lower() for x in ['example', 'test', 'noreply', 'no-reply'])}
                all_emails.update(filtered_emails)

                phones = set(re.findall(self.PHONE_REGEX, content))
                all_phones.update(phones)

                social_selectors = ["a[href*='linkedin.com']", "a[href*='twitter.com']", "a[href*='facebook.com']"]
                for selector in social_selectors:
                    links = await page.query_selector_all(selector)
                    for link in links:
                        href = await link.get_attribute("href")
                        if href:
                            social_profiles.append(href)

                pages_visited.append(page_url)

            except Exception as e:
                logger.warning("page_extraction_failed", url=page_url, error=str(e))

        async def parse_homepage(page: Page) -> dict[str, Any]:
            """Extract from homepage first."""
            await extract_from_page(page, url)

            contact_links = []
            for pattern in self.CONTACT_PAGE_PATTERNS:
                try:
                    links = await page.query_selector_all(f"a[href*='{pattern}']")
                    for link in links:
                        href = await link.get_attribute("href")
                        if href:
                            if href.startswith("/"):
                                contact_links.append(f"{url.rstrip('/')}{href}")
                            elif href.startswith("http"):
                                contact_links.append(href)
                except:
                    continue

            for contact_url in contact_links[:3]:
                try:
                    await page.goto(contact_url, wait_until="domcontentloaded", timeout=15000)
                    await extract_from_page(page, contact_url)
                except Exception as e:
                    logger.debug("contact_page_failed", url=contact_url, error=str(e))

            return {
                "emails": list(all_emails),
                "phones": list(all_phones),
                "social": social_profiles,
                "pages_visited": pages_visited,
                "confidence": min(1.0, len(all_emails) * 0.3 + len(social_profiles) * 0.2),
            }

        result = await self.execute_task(url, parse_homepage, max_retries=2)
        logger.info("contacts_extracted", domain=domain, emails=len(result.get("emails", [])), phones=len(result.get("phones", [])))
        return result


contact_extractor = ContactExtractionEngine()
