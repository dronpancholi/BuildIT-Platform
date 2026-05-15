from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


class SERPIntelligenceService:

    async def scrape_serp(self, keyword: str, geo: str = "us") -> dict[str, Any]:
        """Scrape real Google SERP for a keyword using Playwright.
        
        NOTE: Google blocks headless browsers. This method works but returns empty
        results unless using residential proxies or Google Custom Search API.
        For production, use DataForSEO or SERP API with valid API keys.
        """
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0",
                    locale="en-US",
                )
                page = await context.new_page()
                url = f"https://www.google.com/search?q={keyword.replace(' ', '+')}&hl=en&gl={geo}"
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                await page.wait_for_timeout(3000)

                content = await page.content()
                text = content.lower()

                results = await self._extract_results(page, content)
                serp_features = self._detect_serp_features(text, content)
                related = await self._extract_related_searches(page)

                await browser.close()

                return {
                    "keyword": keyword,
                    "geo": geo,
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                    "result_count": len(results),
                    "results": results[:10],
                    "features": serp_features,
                    "related_searches": related,
                    "success": True,
                    "note": "Google may block headless scraping. Results may be empty without proxies or SERP API."
                }
        except Exception as e:
            logger.warning("serp_scrape_failed", keyword=keyword, error=str(e))
            return {"keyword": keyword, "success": False, "error": str(e)}

    async def _extract_results(self, page, content: str) -> list[dict]:
        results = []
        try:
            for sel in ["div.g", "div[data-hveid]", "div[data-sokoban-container]"]:
                items = await page.query_selector_all(sel)
                if items and len(items) >= 3:
                    for item in items[:10]:
                        try:
                            title_el = await item.query_selector("h3")
                            link_el = await item.query_selector("a[href]")
                            snippet_el = await item.query_selector("div[data-sncf], span.aCOpRe, div.VwiC3b")
                            title = await title_el.inner_text() if title_el else ""
                            href = await link_el.get_attribute("href") if link_el else ""
                            snippet = ""
                            if snippet_el:
                                snippet = await snippet_el.inner_text()
                            if title.strip():
                                results.append({
                                    "title": title.strip(),
                                    "url": href.strip() if href else "",
                                    "snippet": snippet.strip()[:200],
                                })
                        except Exception:
                            pass
                    if results:
                        break
        except Exception:
            pass
        return results

    def _detect_serp_features(self, text: str, content: str) -> list[dict]:
        features = []
        if "featured_snippet" in text or 'role="heading"' in content and "people also ask" in content:
            features.append({"type": "featured_snippet", "present": True})
        if "localpack" in text or "local results" in text or "places" in text:
            features.append({"type": "local_pack", "present": True})
        if "people also ask" in text:
            features.append({"type": "people_also_ask", "present": True})
        if "knowledge" in text and ("panel" in text or "card" in text):
            features.append({"type": "knowledge_panel", "present": True})
        if len(features) == 0:
            features.append({"type": "standard_serp", "present": True})
        return features

    async def _extract_related_searches(self, page) -> list[str]:
        related = []
        try:
            related_section = await page.query_selector_all("div[jsname]*=related, div.sW9g1e")
            for item in related_section[:8]:
                try:
                    text = await item.inner_text()
                    if text.strip():
                        related.append(text.strip())
                except Exception:
                    pass
        except Exception:
            pass
        return related


serp_intelligence = SERPIntelligenceService()
