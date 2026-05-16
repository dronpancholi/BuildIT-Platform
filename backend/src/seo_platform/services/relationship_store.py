"""
SEO Platform — Prospect Relationship Store
===========================================
Tracks relationship history, warmth, and interaction quality
with each prospect domain. Enables contextual follow-ups
and relationship-driven backlinking.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


class ProspectRelationship:
    """Represents the full relationship state with a prospect domain."""

    def __init__(self, domain: str, tenant_id: UUID):
        self.domain = domain
        self.tenant_id = tenant_id
        self.interaction_count = 0
        self.warmth_score = 0.0  # 0.0 (cold) → 1.0 (warm partnership)
        self.last_contact_at: datetime | None = None
        self.first_contact_at: datetime | None = None
        self.last_email_subject: str = ""
        self.last_email_body: str = ""
        self.last_response: str = ""
        self.response_quality: float = 0.0
        self.prior_references: list[str] = []
        self.outcome: str = "new"  # new → contacted → responded → positive → acquired
        self.notes: list[str] = []

    @property
    def is_warm(self) -> bool:
        return self.warmth_score > 0.5

    @property
    def days_since_last_contact(self) -> float:
        if self.last_contact_at is None:
            return 999.0
        delta = datetime.now(timezone.utc) - self.last_contact_at
        return delta.total_seconds() / 86400

    def record_outreach(self, subject: str, body: str) -> None:
        now = datetime.now(timezone.utc)
        if self.first_contact_at is None:
            self.first_contact_at = now
        self.last_contact_at = now
        self.last_email_subject = subject
        self.last_email_body = body
        self.interaction_count += 1
        if self.outcome == "new":
            self.outcome = "contacted"

    def record_response(self, response_text: str) -> None:
        self.last_response = response_text
        self.response_quality = self._assess_response_quality(response_text)
        self.warmth_score = min(1.0, self.warmth_score + self.response_quality * 0.3)
        if self.response_quality > 0.5:
            self.outcome = "positive"
        else:
            self.outcome = "responded"
        self.prior_references.append(response_text[:200])

    def _assess_response_quality(self, text: str) -> float:
        positive = ["interested", "great", "yes", "sure", "let's", "love to", "happy to",
                     "sounds good", "tell me more", "thanks", "thank you", "appreciate"]
        negative = ["not interested", "no", "unsubscribe", "stop", "leave me alone",
                     "not now", "busy", "don't"]
        text_lower = text.lower()
        pos_count = sum(1 for w in positive if w in text_lower)
        neg_count = sum(1 for w in negative if w in text_lower)
        if pos_count + neg_count == 0:
            return 0.5
        return pos_count / (pos_count + neg_count)

    def get_warmth_label(self) -> str:
        if self.warmth_score >= 0.7:
            return "hot"
        elif self.warmth_score >= 0.4:
            return "warm"
        elif self.warmth_score >= 0.1:
            return "lukewarm"
        return "cold"

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "tenant_id": str(self.tenant_id),
            "interaction_count": self.interaction_count,
            "warmth_score": self.warmth_score,
            "warmth_label": self.get_warmth_label(),
            "outcome": self.outcome,
            "last_contact_at": self.last_contact_at.isoformat() if self.last_contact_at else None,
            "first_contact_at": self.first_contact_at.isoformat() if self.first_contact_at else None,
            "response_quality": self.response_quality,
            "notes": self.notes,
        }


class RelationshipStore:
    """In-memory store of prospect relationships, keyed by domain."""

    def __init__(self):
        self._relationships: dict[str, "ProspectRelationship"] = {}

    def get_or_create(self, domain: str, tenant_id: UUID) -> ProspectRelationship:
        key = f"{tenant_id}:{domain}"
        if key not in self._relationships:
            self._relationships[key] = ProspectRelationship(domain, tenant_id)
        return self._relationships[key]

    def get(self, domain: str, tenant_id: UUID) -> ProspectRelationship | None:
        return self._relationships.get(f"{tenant_id}:{domain}")

    def get_warm_domains(self, tenant_id: UUID, min_warmth: float = 0.4) -> list[ProspectRelationship]:
        return [
            rel for rel in self._relationships.values()
            if rel.tenant_id == tenant_id and rel.warmth_score >= min_warmth
        ]

    def get_outreach_history(self, domain: str, tenant_id: UUID) -> str:
        rel = self.get(domain, tenant_id)
        if not rel or rel.interaction_count == 0:
            return ""
        lines = [
            f"Relationship: {rel.get_warmth_label()} (score: {rel.warmth_score:.2f})",
            f"Previous interactions: {rel.interaction_count}",
            f"Outcome: {rel.outcome}",
            f"Days since last contact: {rel.days_since_last_contact:.0f}",
        ]
        if rel.last_email_subject:
            lines.append(f"Last email subject: {rel.last_email_subject}")
        if rel.last_response:
            lines.append(f"Last response: {rel.last_response[:200]}")
        return "\n".join(lines)

    def to_dict(self, tenant_id: UUID) -> list[dict[str, Any]]:
        return [
            rel.to_dict()
            for rel in self._relationships.values()
            if rel.tenant_id == tenant_id
        ]


# Singleton
relationship_store = RelationshipStore()
