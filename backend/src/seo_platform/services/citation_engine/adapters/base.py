"""
SEO Platform — Citation Engine Adapters
=========================================
Plugin architecture for deterministic directory submissions.
"""

import uuid
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from seo_platform.models.citation import BusinessProfile


class AdapterStatus(BaseModel):
    is_healthy: bool
    error_message: str | None = None
    rate_limit_remaining: int | None = None

class DirectoryAdapter(ABC):
    """
    Deterministic contract for all directory submissions.
    Ensures that whether it's YellowPages or Yelp, the orchestrator
    interacts with a uniform interface.
    """

    @property
    @abstractmethod
    def adapter_name(self) -> str:
        """e.g., 'yellowpages', 'justdial'"""
        pass

    @property
    @abstractmethod
    def requires_browser_automation(self) -> bool:
        """True if Playwright is required, False if API-driven."""
        pass

    @abstractmethod
    async def check_health(self) -> AdapterStatus:
        """Verifies if the platform is currently accessible and accepting submissions."""
        pass

    @abstractmethod
    async def format_payload(self, profile: BusinessProfile) -> dict[str, Any]:
        """Maps canonical BusinessProfile to the directory's specific schema/fields."""
        pass

    @abstractmethod
    async def execute_submission(self, payload: dict[str, Any], tenant_id: uuid.UUID) -> str:
        """
        Executes the submission (via API or Playwright).
        Returns the live URL or a tracking ID.
        Raises specific retryable/non-retryable exceptions.
        """
        pass

    @abstractmethod
    async def verify_listing(self, url: str) -> str:
        """
        Scrapes or queries the live listing to verify it exists and matches NAP.
        Returns VerificationState value.
        """
        pass
