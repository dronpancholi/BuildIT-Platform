"""
SEO Platform — Trafilatura Content Extractor Client
======================================================
Extracts clean content, markdown, author names, and metadata from HTML.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TrafilaturaResult(BaseModel):
    title: str | None = None
    author: str | None = None
    date: str | None = None
    markdown_content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class TrafilaturaClient:
    """
    Wrapper for Trafilatura library to perform clean text extraction.
    """

    @staticmethod
    async def extract(html_content: str, url: str = "") -> TrafilaturaResult:
        try:
            import trafilatura

            extracted_text = trafilatura.extract(
                html_content,
                url=url,
                output_format="markdown",
                include_comments=False,
                include_tables=True,
                no_fallback=False,
            )

            metadata_dict = trafilatura.extract_metadata(html_content, default_url=url)

            title = metadata_dict.title if metadata_dict else None
            author = metadata_dict.author if metadata_dict else None
            date = metadata_dict.date if metadata_dict else None

            return TrafilaturaResult(
                title=title,
                author=author,
                date=date,
                markdown_content=extracted_text or "",
                metadata=metadata_dict.__dict__ if metadata_dict else {},
            )
        except ImportError:
            logger.warning("trafilatura_not_installed")
            raise RuntimeError("Trafilatura library not installed.")
        except Exception as e:
            logger.error("trafilatura_extraction_failed", error=str(e))
            raise RuntimeError(f"Trafilatura parsing failed: {e}")
