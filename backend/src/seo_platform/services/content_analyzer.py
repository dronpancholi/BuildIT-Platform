"""
SEO Platform — Website Content Analyzer
==========================================
Scrapes and analyzes website content for outreach context.
Used by the outreach engine to generate contextual, personalized emails.
"""

from __future__ import annotations

import re
from typing import Any

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


class WebsiteContentAnalyzer:

    async def analyze(self, domain: str) -> dict[str, Any]:
        """
        Scrape a website and extract content intelligence for outreach.
        Returns structured data about the site's content, tone, and focus.
        """
        result = {
            "domain": domain,
            "site_title": "",
            "site_description": "",
            "recent_articles": [],
            "topical_focus": [],
            "content_tone": "professional",
            "publishing_frequency": "unknown",
            "author_names": [],
            "success": False,
        }

        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(f"https://{domain}", headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                })
                if resp.status_code != 200:
                    return result

                html = resp.text
                result["success"] = True

                # Extract title
                title_match = re.search(r"<title>(.*?)</title>", html, re.DOTALL)
                if title_match:
                    result["site_title"] = title_match.group(1).strip()

                # Extract meta description
                desc_match = re.search(
                    r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']',
                    html,
                )
                if desc_match:
                    result["site_description"] = desc_match.group(1).strip()

                # Extract H1s as topical indicators
                h1s = re.findall(r"<h1[^>]*>(.*?)</h1>", html, re.DOTALL)
                result["topical_focus"] = [re.sub(r"<[^>]+>", "", h).strip() for h in h1s if h.strip()][:5]

                # Extract article links (patterns like /blog/, /article/, /post/)
                article_links = re.findall(
                    r'<a[^>]*href=["\'](/(?:blog|article|post|news|insights|resources)/[^"\'<>]+)["\'][^>]*>([^<]+)</a>',
                    html,
                )
                result["recent_articles"] = [
                    {"title": title.strip(), "url": url}
                    for url, title in article_links[:8]
                    if title.strip()
                ]

                # Extract author-like patterns (byline indicators)
                authors = re.findall(
                    r'(?:by|author|written\s+by)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
                    html[:5000],
                )
                result["author_names"] = list(set(authors))[:3]

                # Simple tone detection
                text_lower = html.lower()
                if any(w in text_lower for w in ["tutorial", "guide", "how to", "learn"]):
                    result["content_tone"] = "educational"
                elif any(w in text_lower for w in ["buy", "shop", "pricing", "sale"]):
                    result["content_tone"] = "commercial"
                elif any(w in text_lower for w in ["news", "breaking", "latest", "update"]):
                    result["content_tone"] = "journalistic"

        except Exception as e:
            logger.debug("content_analyzer_failed", domain=domain, error=str(e))

        return result


website_analyzer = WebsiteContentAnalyzer()
