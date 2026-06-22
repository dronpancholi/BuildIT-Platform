"""
SEO Platform — Contact Page Crawler
======================================
Scans common resource paths for contact details, author bios, and social links.
"""

from __future__ import annotations

import re
from typing import Any

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)

CONTACT_PATHS = [
    "/about/",
    "/about",
    "/contact/",
    "/contact",
    "/team/",
    "/team",
    "/about-us/",
    "/about-us",
    "/authors/",
    "/contributors/",
]


class ContactCrawler:
    """
    Crawls common resource paths to extract contact details and social links.
    """

    EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    SOCIAL_DOMAINS = {
        "linkedin.com": "linkedin",
        "twitter.com": "twitter",
        "x.com": "x",
        "github.com": "github",
        "facebook.com": "facebook",
        "youtube.com": "youtube",
        "instagram.com": "instagram",
    }

    def __init__(self, timeout: int = 15) -> None:
        self.timeout = timeout

    async def extract_contacts(self, domain: str) -> dict[str, Any]:
        """
        Scans known resource paths on the domain and returns:
          - email addresses found
          - social media profile URLs
          - a brief author bio snippet
          - which pages were reachable
        """
        from seo_platform.clients.scrapling import ScraplingClient

        client = ScraplingClient(timeout=self.timeout)

        emails: set[str] = set()
        social_links: dict[str, str] = {}
        reachable_pages: list[str] = []
        author_bio = ""

        for path in CONTACT_PATHS:
            try:
                url = f"https://{domain}{path}"
                res = await client.fetch(url)
                if res.status_code != 200:
                    continue
                reachable_pages.append(path)

                found_emails = self.EMAIL_RE.findall(res.text_content + res.html_content)
                for e in found_emails:
                    if not e.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg")):
                        emails.add(e.lower())

                for link in res.outbound_links:
                    for social_domain, social_name in self.SOCIAL_DOMAINS.items():
                        if social_domain in link and social_name not in social_links:
                            social_links[social_name] = link

                if not author_bio and len(res.text_content) > 50:
                    bio_start = res.text_content[:2000]
                    if bio_start:
                        sentences = bio_start.split(".")[:3]
                        author_bio = ". ".join(s.strip() for s in sentences if s.strip()) + "."

                if len(reachable_pages) >= 3 and emails:
                    break
            except Exception:
                continue

        return {
            "domain": domain,
            "emails": list(emails),
            "social_links": social_links,
            "reachable_pages": reachable_pages,
            "author_bio": author_bio,
        }
