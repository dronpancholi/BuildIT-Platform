"""
SEO Platform — NAP Consistency Engine
=======================================
Analyzes and normalizes Name, Address, and Phone data.
Detects drift, inconsistencies, and duplicates across directory listings.
"""

import re

from seo_platform.models.citation import BusinessProfile


class NAPConsistencyEngine:

    def normalize_phone(self, phone: str) -> str:
        """Normalizes to strict E.164 format."""
        if not phone:
            return ""
        digits = re.sub(r'\D', '', phone)
        if len(digits) == 10:
            return f"+1{digits}" # Defaulting US for example, would be dynamic in prod
        return f"+{digits}"

    def normalize_address(self, address: str) -> str:
        """
        Expands abbreviations (St. -> Street, Rd. -> Road) for comparison.
        In enterprise, this calls an LLM (Gemma 4 31B) or Google Maps API.
        """
        if not address:
            return ""
        addr = address.lower()
        addr = addr.replace(" st.", " street").replace(" rd.", " road").replace(" ave.", " avenue")
        return addr.strip()

    def calculate_consistency_score(self, canonical: BusinessProfile, live_data: dict[str, str]) -> float:
        """
        Scores the consistency of a live directory listing against the canonical profile.
        Returns a float between 0.0 and 1.0.
        """
        score = 1.0

        # 1. Name Check (Fuzzy match in production, exact here for simplicity)
        if canonical.business_name.lower() != live_data.get("name", "").lower():
            score -= 0.3

        # 2. Phone Check
        live_phone = self.normalize_phone(live_data.get("phone", ""))
        if canonical.phone_number != live_phone:
            score -= 0.4

        # 3. Address Check
        live_addr = self.normalize_address(live_data.get("address", ""))
        canon_addr = self.normalize_address(canonical.street_address)
        if canon_addr != live_addr:
            score -= 0.3

        return max(0.0, score)

nap_consistency_engine = NAPConsistencyEngine()
