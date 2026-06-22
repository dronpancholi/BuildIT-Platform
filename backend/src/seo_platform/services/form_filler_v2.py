"""
SEO Platform — Multilingual Form Filler (v2)
=============================================
Extended form filler with multi-language field detection.
When filling forms on non-English sites, tries translated field labels
in addition to English before falling back to fuzzy matching.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)

# Path to translations file
TRANSLATIONS_PATH = Path(__file__).parent.parent.parent.parent / "data" / "form_field_translations.json"

# Standard project field names that map to form fields
STANDARD_FIELDS = {
    "business_name",
    "phone",
    "email",
    "address",
    "city",
    "state",
    "postal_code",
    "description",
    "hours",
    "website",
    "logo",
    "category",
    "image",
    "facebook",
    "twitter",
    "linkedin",
    "instagram",
    "youtube",
    "contact_person",
    "founded",
    "employees",
    "price_range",
}


class MultilingualFormFiller:
    """
    Extended form filler with multi-language field detection.

    Strategy:
    1. Detect site language from citation_sites.language field
    2. Load translation map for that language
    3. For each project field, try:
       a. English label match (original logic)
       b. Translated label match
       c. Fuzzy match (last resort)
    4. Return filled/unfilled breakdown with language info
    """

    def __init__(self):
        self.translations = self._load_translations()
        self._lang_cache: dict[str, dict[str, list[str]]] = {}

    def _load_translations(self) -> dict[str, dict[str, list[str]]]:
        """Load all translation mappings from JSON."""
        try:
            if TRANSLATIONS_PATH.exists():
                with open(TRANSLATIONS_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load translations: {e}")
        return {}

    def get_translation_map(self, site_language: str) -> dict[str, list[str]]:
        """Get the translation map for a specific target language."""
        if site_language in self._lang_cache:
            return self._lang_cache[site_language]

        key = f"en_to_{site_language}"
        result = self.translations.get(key, {})
        self._lang_cache[site_language] = result
        return result

    def get_supported_languages(self) -> list[str]:
        """List of languages with translation data."""
        return [
            key.replace("en_to_", "")
            for key in self.translations.keys()
            if key.startswith("en_to_")
        ]

    def get_all_labels_for_field(
        self,
        field_name: str,
        site_language: str = "en",
    ) -> list[str]:
        """
        Get all possible labels for a field in the target language.
        Includes English labels as fallback.
        """
        labels = []

        # Get translated labels
        if site_language != "en":
            translation_map = self.get_translation_map(site_language)
            translated = translation_map.get(field_name, [])
            labels.extend(translated)

        # Add common English variants as fallback
        english_variants = self._get_english_variants(field_name)
        labels.extend(english_variants)

        return labels

    def _get_english_variants(self, field_name: str) -> list[str]:
        """Get common English variants for a field name."""
        variants = {
            "business_name": ["Business Name", "Company Name", "Name", "Organization"],
            "phone": ["Phone", "Telephone", "Phone Number", "Tel", "Contact Number"],
            "email": ["Email", "E-mail", "Email Address", "Contact Email"],
            "address": ["Address", "Street Address", "Business Address", "Location"],
            "city": ["City", "Town", "Municipality"],
            "state": ["State", "Province", "Region", "County"],
            "postal_code": ["Postal Code", "ZIP Code", "Postcode", "Zip"],
            "description": ["Description", "About", "About Us", "Business Description"],
            "hours": ["Hours", "Business Hours", "Opening Hours", "Operating Hours"],
            "website": ["Website", "URL", "Web Address", "Site"],
            "logo": ["Logo", "Business Logo", "Company Logo"],
            "category": ["Category", "Business Type", "Industry", "Sector"],
            "image": ["Image", "Photo", "Picture", "Business Photo"],
            "facebook": ["Facebook", "Facebook URL", "Facebook Page"],
            "twitter": ["Twitter", "Twitter URL", "Twitter Handle"],
            "linkedin": ["LinkedIn", "LinkedIn URL", "LinkedIn Page"],
            "instagram": ["Instagram", "Instagram URL", "Instagram Handle"],
            "youtube": ["YouTube", "YouTube URL", "YouTube Channel"],
            "contact_person": ["Contact Person", "Contact Name", "Representative"],
            "founded": ["Founded", "Year Founded", "Established"],
            "employees": ["Employees", "Number of Employees", "Staff Size"],
            "price_range": ["Price Range", "Price Level", "Price Category"],
        }
        return variants.get(field_name, [field_name.replace("_", " ").title()])

    async def analyze_form_fields(
        self,
        page: Any,  # Playwright Page object
        site_language: str = "en",
    ) -> dict[str, Any]:
        """
        Analyze all form fields on the page and map them to project fields.
        Returns a mapping of project_field -> form_selector.
        """
        from difflib import SequenceMatcher

        # Get all input/textarea/select elements
        fields_info = await page.evaluate("""
            () => {
                const fields = [];
                const elements = document.querySelectorAll('input, textarea, select');
                elements.forEach(el => {
                    const labels = [];
                    // Check associated label
                    if (el.id) {
                        const label = document.querySelector(`label[for="${el.id}"]`);
                        if (label) labels.push(label.textContent.trim());
                    }
                    // Check parent label
                    const parentLabel = el.closest('label');
                    if (parentLabel) labels.push(parentLabel.textContent.trim());
                    // Check aria-label
                    if (el.getAttribute('aria-label')) labels.push(el.getAttribute('aria-label'));
                    // Check placeholder
                    if (el.placeholder) labels.push(el.placeholder);
                    // Check name attribute
                    if (el.name) labels.push(el.name);
                    // Check id
                    if (el.id) labels.push(el.id);

                    fields.push({
                        tag: el.tagName.toLowerCase(),
                        type: el.type || '',
                        name: el.name || '',
                        id: el.id || '',
                        placeholder: el.placeholder || '',
                        ariaLabel: el.getAttribute('aria-label') || '',
                        labels: labels.filter(l => l && l.length > 0),
                        selector: el.id ? '#' + el.id : (el.name ? `[name="${el.name}"]` : null)
                    });
                });
                return fields;
            }
        """)

        # Map project fields to form fields
        all_labels = {}
        for field_name in STANDARD_FIELDS:
            all_labels[field_name] = self.get_all_labels_for_field(field_name, site_language)

        field_mapping = {}
        for field_name, target_labels in all_labels.items():
            best_match = None
            best_score = 0.0

            for form_field in fields_info:
                if not form_field.get("selector"):
                    continue

                form_labels = [l.lower() for l in form_field.get("labels", [])]
                if not form_labels:
                    # Try name/id/placeholder as fallback
                    form_labels = [
                        l.lower()
                        for l in [
                            form_field.get("name", ""),
                            form_field.get("id", ""),
                            form_field.get("placeholder", ""),
                            form_field.get("ariaLabel", ""),
                        ]
                        if l
                    ]

                for target_label in target_labels:
                    target_lower = target_label.lower()
                    for form_label in form_labels:
                        # Exact match
                        if target_lower == form_label:
                            best_match = form_field["selector"]
                            best_score = 1.0
                            break

                        # Containment match
                        if target_lower in form_label or form_label in target_lower:
                            score = 0.8
                            if score > best_score:
                                best_match = form_field["selector"]
                                best_score = score

                        # Fuzzy match
                        ratio = SequenceMatcher(None, target_lower, form_label).ratio()
                        if ratio > 0.6 and ratio > best_score:
                            best_match = form_field["selector"]
                            best_score = ratio

                    if best_score >= 1.0:
                        break
                if best_score >= 1.0:
                    break

            if best_match and best_score >= 0.6:
                field_mapping[field_name] = {
                    "selector": best_match,
                    "confidence": best_score,
                    "method": "exact" if best_score >= 1.0 else "fuzzy",
                }

        return {
            "language": site_language,
            "total_fields_found": len(fields_info),
            "mapped_fields": field_mapping,
            "mapped_count": len(field_mapping),
            "unmapped_fields": [f for f in STANDARD_FIELDS if f not in field_mapping],
        }

    async def fill_form_multilingual(
        self,
        page: Any,
        project_data: dict[str, Any],
        site_language: str = "en",
    ) -> dict[str, Any]:
        """
        Fill form using language-appropriate field mappings.

        Returns filled/unfilled breakdown with language info.
        """
        results = {
            "language": site_language,
            "filled_fields": [],
            "unfilled_fields": [],
            "translations_used": [],
            "fallback_fuzzy_used": [],
            "total_attempted": 0,
        }

        # Analyze form fields first
        analysis = await self.analyze_form_fields(page, site_language)
        field_mapping = analysis.get("mapped_fields", {})

        for field_name, field_value in project_data.items():
            if not field_value or field_name not in STANDARD_FIELDS:
                continue

            results["total_attempted"] += 1

            mapping = field_mapping.get(field_name)
            if not mapping:
                results["unfilled_fields"].append(field_name)
                continue

            selector = mapping["selector"]
            confidence = mapping["confidence"]
            method = mapping["method"]

            try:
                # Try to fill the field
                filled = await self._fill_field(page, selector, str(field_value))
                if filled:
                    results["filled_fields"].append(field_name)
                    if site_language != "en" and method == "exact":
                        results["translations_used"].append(field_name)
                    if method == "fuzzy":
                        results["fallback_fuzzy_used"].append(field_name)
                else:
                    results["unfilled_fields"].append(field_name)
            except Exception as e:
                logger.warning(f"Failed to fill field {field_name}: {e}")
                results["unfilled_fields"].append(field_name)

        return results

    async def _fill_field(self, page: Any, selector: str, value: str) -> bool:
        """Fill a single form field by selector."""
        try:
            element = await page.query_selector(selector)
            if not element:
                return False

            # Check element type
            tag = await element.evaluate("el => el.tagName.toLowerCase()")
            input_type = await element.evaluate("el => el.type || ''")

            if tag == "select":
                # Handle select dropdowns
                await page.select_option(selector, label=value)
            elif input_type in ("checkbox", "radio"):
                # Handle checkboxes/radio buttons
                is_checked = await element.evaluate("el => el.checked")
                if not is_checked:
                    await element.click()
            else:
                # Handle text inputs, textareas
                await element.fill(value)

            return True
        except Exception as e:
            logger.debug(f"Failed to fill field {selector}: {e}")
            return False
