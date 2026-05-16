"""
SEO Platform — Website Content Analyzer
==========================================
Deep website content scraper using Firecrawl AI.
Extracts site metadata, topical focus, recent articles, and author info.
Upserts scraped content into Qdrant vector store for topical relevance matching.
"""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


class WebsiteContentAnalyzer:

    async def analyze(
        self,
        domain: str,
        tenant_id: UUID | None = None,
    ) -> dict[str, Any]:
        """
        Deep scrape a website using Firecrawl and extract content intelligence.

        Args:
            domain: Domain to analyze (e.g. example.com)
            tenant_id: Optional tenant UUID for Qdrant vector storage

        Returns:
            dict with site_title, site_description, topical_focus,
            recent_articles, markdown_body, success flag, and metadata.
        """
        from seo_platform.clients.firecrawl import firecrawl_client

        result = {
            "domain": domain,
            "site_title": "",
            "site_description": "",
            "recent_articles": [],
            "topical_focus": [],
            "author_names": [],
            "markdown_body": "",
            "content_tone": "professional",
            "success": False,
        }

        scrape = await firecrawl_client.scrape_url(f"https://{domain}")

        if not scrape.success:
            logger.debug("content_analyzer_firecrawl_failed", domain=domain, error=scrape.error)
            return result

        result["success"] = True
        result["markdown_body"] = scrape.markdown

        # Extract metadata from Firecrawl result
        meta = scrape.metadata
        result["site_title"] = meta.get("title", "") or meta.get("og:title", "")
        result["site_description"] = (
            meta.get("description", "")
            or meta.get("og:description", "")
            or meta.get("meta:description", "")
        )

        # Parse markdown for topical focus (H1/H2 headers)
        if scrape.markdown:
            headers = re.findall(r"^#{1,2}\s+(.+)$", scrape.markdown, re.MULTILINE)
            result["topical_focus"] = [h.strip() for h in headers if h.strip()][:8]

            # Extract markdown links as potential articles
            links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", scrape.markdown)
            result["recent_articles"] = [
                {"title": title.strip(), "url": url}
                for title, url in links[:12]
                if title.strip() and not url.startswith("#")
            ]

            # Extract author patterns from markdown
            authors = re.findall(
                r"(?:by|author|written\s+by)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
                scrape.markdown[:5000],
            )
            result["author_names"] = list(set(authors))[:3]

            # Tone detection from markdown
            text_lower = scrape.markdown.lower()
            if any(w in text_lower for w in ["tutorial", "guide", "how to", "learn"]):
                result["content_tone"] = "educational"
            elif any(w in text_lower for w in ["buy", "shop", "pricing", "sale"]):
                result["content_tone"] = "commercial"
            elif any(w in text_lower for w in ["news", "breaking", "latest", "update"]):
                result["content_tone"] = "journalistic"

        # Upsert into Qdrant for topical relevance matching
        if tenant_id and scrape.markdown:
            try:
                from seo_platform.services.vector_store import qdrant_vector_store
                await qdrant_vector_store.upsert_prospect_content(
                    tenant_id=tenant_id,
                    domain=domain,
                    markdown_content=scrape.markdown,
                    metadata={
                        "site_title": result["site_title"],
                        "success": True,
                    },
                )
            except Exception as e:
                logger.debug("qdrant_upsert_skipped", domain=domain, error=str(e))

        return result


website_analyzer = WebsiteContentAnalyzer()
