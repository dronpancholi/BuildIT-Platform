"""
SEO Platform — Form Filler
===========================
Generic form filling engine with fuzzy field matching.
Maps project data to form inputs using labels, names, placeholders, and selectors.
"""

from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from playwright.async_api import Page

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)

# Path to form mappings
FORM_MAPPINGS_PATH = Path(__file__).parent.parent.parent.parent / "data" / "form_mappings.json"

# Default field mapping keywords (used when no site-specific mapping exists)
DEFAULT_FIELD_KEYWORDS: dict[str, list[str]] = {
    "business_name": [
        "business name", "company name", "organization name",
        "listing name", "trading name", "abn name", "name",
    ],
    "phone": [
        "phone", "telephone", "tel", "mobile", "contact number",
        "phone number", "cell", "fax",
    ],
    "email": [
        "email", "e-mail", "contact email", "business email",
        "email address", "work email",
    ],
    "website": [
        "website", "url", "website url", "web address",
        "site url", "homepage",
    ],
    "address": [
        "address", "street address", "location", "business address",
        "street", "address line 1", "address line 2", "address 1",
    ],
    "city": [
        "city", "suburb", "town", "locality", "neighborhood",
    ],
    "state": [
        "state", "province", "region", "territory",
    ],
    "postal_code": [
        "postal code", "zip", "zip code", "postcode", "postal",
    ],
    "country": [
        "country", "country code", "nation",
    ],
    "description": [
        "description", "about", "business description",
        "listing description", "about us", "bio", "summary",
    ],
    "category": [
        "category", "categories", "business type", "industry",
        "type of business", "sector",
    ],
    "hours": [
        "hours", "opening hours", "business hours",
        "working hours", "trade hours",
    ],
    "logo": [
        "logo", "business logo", "company logo",
        "image", "photo", "upload",
    ],
}


class FormFiller:
    """
    Generic form filling engine.

    Maps project data fields to form inputs using:
    1. Site-specific selectors from form_mappings.json
    2. Field label matching (case-insensitive, fuzzy)
    3. Input name/type matching
    4. Placeholder text matching
    """

    def __init__(self):
        self._mappings: dict[str, Any] = {}
        self._load_mappings()

    def _load_mappings(self) -> None:
        """Load site-specific form mappings from JSON."""
        try:
            if FORM_MAPPINGS_PATH.exists():
                with open(FORM_MAPPINGS_PATH) as f:
                    self._mappings = json.load(f)
                logger.info("form_mappings_loaded", count=len(self._mappings))
            else:
                logger.warning("form_mappings_not_found", path=str(FORM_MAPPINGS_PATH))
        except Exception as e:
            logger.error("form_mappings_load_failed", error=str(e))

    def get_site_mapping(self, site_slug: str) -> dict[str, Any] | None:
        """Get site-specific form mapping."""
        return self._mappings.get(site_slug)

    def _normalize(self, text: str) -> str:
        """Normalize text for comparison."""
        return re.sub(r"[^a-z0-9]", "", text.lower().strip())

    def _similarity(self, a: str, b: str) -> float:
        """Calculate similarity between two strings."""
        return SequenceMatcher(None, self._normalize(a), self._normalize(b)).ratio()

    async def _find_field_by_label(
        self, page: Page, field_name: str, keywords: list[str]
    ) -> Any | None:
        """Find a form field by its label text."""
        # Try finding label elements
        labels = await page.query_selector_all("label")
        for label in labels:
            text = await label.inner_text()
            for keyword in keywords:
                if self._similarity(text, keyword) > 0.6:
                    # Find the associated input
                    for_attr = await label.get_attribute("for")
                    if for_attr:
                        field = await page.query_selector(f"#{for_attr}")
                        if field:
                            return field
                    # Try finding input inside label
                    field = await label.query_selector("input, textarea, select")
                    if field:
                        return field
        return None

    async def _find_field_by_attributes(
        self, page: Page, field_name: str, keywords: list[str]
    ) -> Any | None:
        """Find a form field by name, id, or placeholder attributes."""
        # Try by name attribute
        for keyword in keywords:
            selectors = [
                f"input[name*='{keyword}']",
                f"input[id*='{keyword}']",
                f"input[placeholder*='{keyword}']",
                f"textarea[name*='{keyword}']",
                f"textarea[id*='{keyword}']",
                f"textarea[placeholder*='{keyword}']",
                f"select[name*='{keyword}']",
                f"select[id*='{keyword}']",
            ]
            for selector in selectors:
                field = await page.query_selector(selector)
                if field:
                    return field
        return None

    async def _find_field_by_type(
        self, page: Page, field_name: str
    ) -> Any | None:
        """Find a form field by input type."""
        type_map = {
            "phone": "tel",
            "email": "email",
            "website": "url",
            "postal_code": "text",
        }
        input_type = type_map.get(field_name)
        if input_type:
            field = await page.query_selector(f"input[type='{input_type}']")
            if field:
                return field
        return None

    async def _find_field(
        self, page: Page, field_name: str
    ) -> Any | None:
        """Find a form field using multiple strategies."""
        keywords = DEFAULT_FIELD_KEYWORDS.get(field_name, [field_name])

        # Strategy 1: Find by label
        field = await self._find_field_by_label(page, field_name, keywords)
        if field:
            return field

        # Strategy 2: Find by attributes
        field = await self._find_field_by_attributes(page, field_name, keywords)
        if field:
            return field

        # Strategy 3: Find by input type
        field = await self._find_field_by_type(page, field_name)
        if field:
            return field

        return None

    async def _fill_field(self, page: Page, field: Any, value: str) -> bool:
        """Fill a single form field with a value."""
        try:
            tag = await field.evaluate("el => el.tagName.toLowerCase()")
            input_type = await field.get_attribute("type") or ""
            field_class = await field.get_attribute("class") or ""

            # Skip hidden fields
            if input_type == "hidden":
                return False

            # Handle select elements
            if tag == "select":
                # Try to find matching option
                options = await field.query_selector_all("option")
                for option in options:
                    option_text = await option.inner_text()
                    option_value = await option.get_attribute("value") or ""
                    if (self._similarity(option_text, value) > 0.6 or
                            value.lower() in option_text.lower()):
                        await field.select_option(value=option_value)
                        return True
                # Try first option if no match
                return False

            # Handle file inputs (for logo uploads)
            if input_type == "file":
                # Can't fill file inputs directly
                return False

            # Handle checkboxes and radios
            if input_type == "checkbox":
                if value.lower() in ("true", "yes", "1", "on"):
                    is_checked = await field.is_checked()
                    if not is_checked:
                        await field.check()
                return True

            # Handle text areas and inputs
            await field.click()
            await field.fill("")
            await field.type(value, delay=50)
            return True

        except Exception as e:
            logger.warning("fill_field_failed", error=str(e))
            return False

    async def fill_form(
        self,
        page: Page,
        project_data: dict[str, Any],
        site_slug: str | None = None,
    ) -> dict[str, Any]:
        """
        Fill all visible form fields with project data.

        Args:
            page: Playwright page object
            project_data: Project data dict with business info
            site_slug: Optional site-specific mapping key

        Returns:
            Dict with filled_fields, unfilled_fields, screenshots
        """
        filled_fields = []
        unfilled_fields = []

        # Check for site-specific mapping
        site_mapping = self.get_site_mapping(site_slug) if site_slug else None

        if site_mapping and "fields" in site_mapping:
            # Use site-specific selectors
            for field_name, field_config in site_mapping["fields"].items():
                value = project_data.get(field_name)
                if not value:
                    unfilled_fields.append(field_name)
                    continue

                selector = field_config.get("selector")
                if selector:
                    try:
                        field = await page.query_selector(selector)
                        if field:
                            success = await self._fill_field(page, field, str(value))
                            if success:
                                filled_fields.append(field_name)
                            else:
                                unfilled_fields.append(field_name)
                        else:
                            unfilled_fields.append(field_name)
                    except Exception:
                        unfilled_fields.append(field_name)
                else:
                    unfilled_fields.append(field_name)
        else:
            # Use generic fuzzy matching
            for field_name, value in project_data.items():
                if not value or field_name in ("id", "tenant_id", "client_id", "status", "created_at", "updated_at"):
                    continue

                field = await self._find_field(page, field_name)
                if field:
                    success = await self._fill_field(page, field, str(value))
                    if success:
                        filled_fields.append(field_name)
                    else:
                        unfilled_fields.append(field_name)
                else:
                    unfilled_fields.append(field_name)

        return {
            "filled_fields": filled_fields,
            "unfilled_fields": unfilled_fields,
        }

    async def find_submit_button(self, page: Page) -> Any | None:
        """Find the submit button on the page."""
        selectors = [
            "button[type='submit']",
            "input[type='submit']",
            "button:has-text('Submit')",
            "button:has-text('Register')",
            "button:has-text('Sign Up')",
            "button:has-text('Create')",
            "button:has-text('Save')",
            "button:has-text('Add')",
            "button:has-text('List')",
            "button:has-text('Claim')",
            "a:has-text('Submit')",
            "a:has-text('Register')",
        ]
        for selector in selectors:
            try:
                button = await page.query_selector(selector)
                if button and await button.is_visible():
                    return button
            except Exception:
                continue
        return None

    async def search_existing_listing(self, page: Page, business_name: str, location: str) -> str | None:
        """
        Search for an existing listing on the site.

        Returns the listing URL if found, None otherwise.
        """
        # Look for search inputs
        search_selectors = [
            "input[type='search']",
            "input[name='q']",
            "input[name='search']",
            "input[name='query']",
            "input[placeholder*='search']",
            "input[placeholder*='Search']",
            "input[id*='search']",
        ]

        for selector in search_selectors:
            search_input = await page.query_selector(selector)
            if search_input:
                try:
                    await search_input.click()
                    await search_input.fill(f"{business_name} {location}")
                    await page.keyboard.press("Enter")
                    await page.wait_for_timeout(3000)

                    # Check for results
                    results = await page.query_selector_all("a[href*='business'], a[href*='listing'], .result-item, .search-result")
                    if results:
                        first_result = results[0]
                        href = await first_result.get_attribute("href")
                        if href:
                            return href
                except Exception:
                    continue

        return None
