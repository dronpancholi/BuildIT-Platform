"""
SEO Platform — Deep Client Persona & Editorial Voice Ingestion Engine
=======================================================================
Ingests, validates, and embeds client brand voice guidelines, negative
buyer personas, and historical email archives for hyper-personalized
outreach with zero generic AI footprints.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Pydantic v2 Schemas
# ---------------------------------------------------------------------------

class EditorialConstraint(BaseModel):
    """Editorial rules that govern all client-facing content."""

    prohibited_words: list[str] = Field(
        default_factory=lambda: [
            "delve", "testament", "beacon", "seamless", "tapestry",
            "synergy", "game-changer", "revolutionary", "cutting-edge",
            "state-of-the-art", "best-in-class", "thought leadership",
        ],
        description="Words/buzzwords that must NEVER appear in outreach",
    )
    mandatory_tone_markers: list[str] = Field(
        default_factory=list,
        description="Required tone characteristics (e.g. 'warm', 'direct', 'data-driven')",
    )
    max_sentence_length: int = 25
    formality_level: str = "professional_conversational"


class NegativePersona(BaseModel):
    """Description of a buyer persona to explicitly avoid targeting."""

    job_titles: list[str] = Field(default_factory=list)
    company_types: list[str] = Field(default_factory=list)
    exclusion_reason: str = ""


class ClientPersonaGuidelines(BaseModel):
    """Complete brand voice and persona guidelines for a client."""

    tenant_id: UUID
    client_id: UUID
    brand_voice_summary: str = Field(
        ...,
        description="1-3 sentence summary of the client's brand voice",
    )
    editorial_constraints: EditorialConstraint = Field(
        default_factory=EditorialConstraint,
    )
    negative_personas: list[NegativePersona] = Field(default_factory=list)
    historical_email_samples: list[str] = Field(
        default_factory=list,
        description="Past high-converting email examples for tone matching",
    )

    @model_validator(mode="after")
    def _validate_samples_and_prohibited(self) -> ClientPersonaGuidelines:
        if len(self.historical_email_samples) < 2:
            raise ValueError(
                "At least 2 historical email samples are required for tone matching. "
                f"Got {len(self.historical_email_samples)}."
            )
        common_ai_fluff = {"delve", "testament", "beacon", "seamless", "tapestry"}
        prohibited = {w.lower().strip() for w in self.editorial_constraints.prohibited_words}
        missing = common_ai_fluff - prohibited
        if missing:
            raise ValueError(
                f"Prohibited words must include common AI fluff terms: {', '.join(sorted(missing))}."
                f" Add them to editorial_constraints.prohibited_words."
            )
        return self


# ---------------------------------------------------------------------------
# Client Persona Service
# ---------------------------------------------------------------------------

class ClientPersonaService:
    """
    Ingests, validates, stores, and retrieves client persona guidelines.
    Uses a local in-memory dict as fallback for demo mode (no external
    vector DB required).
    """

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}
        self._vector_store: dict[str, list[tuple[str, str]]] = {}

    async def ingest_persona_guidelines(
        self,
        guidelines: ClientPersonaGuidelines,
    ) -> dict[str, Any]:
        """Persist the persona guidelines. Falls back to in-memory dict."""
        key = f"persona:{guidelines.tenant_id}:{guidelines.client_id}"
        data = guidelines.model_dump()
        data["_id"] = key

        try:
            from seo_platform.core.redis import get_redis
            redis = await get_redis()
            await redis.setex(key, 86400 * 90, json.dumps(data))
            logger.info("persona_guidelines_stored_redis", key=key)
        except Exception:
            self._store[key] = data
            logger.info("persona_guidelines_stored_memory", key=key)

        return {"success": True, "key": key, "client_id": str(guidelines.client_id)}

    async def embed_historical_archives(
        self,
        tenant_id: UUID,
        client_id: UUID,
        samples: list[str],
    ) -> bool:
        """Embed historical email samples into Qdrant with in-memory fallback.

        Returns True if at least 2 samples were stored.
        """
        if len(samples) < 2:
            logger.warning("insufficient_samples_for_embedding", count=len(samples))
            return False

        key = f"archives:{tenant_id}:{client_id}"

        try:
            from seo_platform.services.vector_store import qdrant_vector_store
            stored = await qdrant_vector_store.store_texts(
                collection="client_archives",
                tenant_id=tenant_id,
                texts=samples,
                metadata={"client_id": str(client_id)},
            )
            if stored:
                logger.info("archives_embedded_qdrant", key=key, count=len(samples))
                return True
        except Exception:
            pass

        self._vector_store[key] = [(s, s) for s in samples]
        logger.info("archives_embedded_memory", key=key, count=len(samples))
        return True

    async def get_active_persona_context(
        self,
        tenant_id: UUID,
        client_id: UUID,
        target_niche: str = "",
    ) -> dict[str, Any]:
        """Retrieve the active persona context for prompt injection.

        Returns a structured dict with brand_voice_summary, editorial_constraints,
        prohibited_words, negative_personas, and relevant_archive_samples.
        Falls back to a clean professional baseline if no guidelines exist.
        """
        key = f"persona:{tenant_id}:{client_id}"
        data: dict[str, Any] | None = None

        try:
            from seo_platform.core.redis import get_redis
            redis = await get_redis()
            raw = await redis.get(key)
            if raw:
                data = json.loads(raw)
        except Exception:
            pass

        if data is None:
            data = self._store.get(key)

        if data is None:
            return self._default_persona_context()

        constraints = data.get("editorial_constraints", {})
        if isinstance(constraints, dict):
            pass
        elif hasattr(constraints, "model_dump"):
            constraints = constraints.model_dump()

        prohibited = (
            constraints.get("prohibited_words")
            if isinstance(constraints, dict)
            else getattr(constraints, "prohibited_words", None)
        ) or EditorialConstraint().prohibited_words

        negative_personas_raw = data.get("negative_personas", [])

        relevant_samples = await self._retrieve_relevant_samples(
            tenant_id, client_id, target_niche,
        )

        return {
            "brand_voice_summary": data.get(
                "brand_voice_summary",
                "Professional, warm, and highly authoritative.",
            ),
            "editorial_constraints": {
                "prohibited_words": prohibited,
                "mandatory_tone_markers": (
                    constraints.get("mandatory_tone_markers", [])
                    if isinstance(constraints, dict)
                    else getattr(constraints, "mandatory_tone_markers", [])
                ),
                "max_sentence_length": (
                    constraints.get("max_sentence_length", 25)
                    if isinstance(constraints, dict)
                    else getattr(constraints, "max_sentence_length", 25)
                ),
                "formality_level": (
                    constraints.get("formality_level", "professional_conversational")
                    if isinstance(constraints, dict)
                    else getattr(constraints, "formality_level", "professional_conversational")
                ),
            },
            "prohibited_words": prohibited,
            "negative_personas": [
                {
                    "job_titles": np.get("job_titles", []),
                    "company_types": np.get("company_types", []),
                    "exclusion_reason": np.get("exclusion_reason", ""),
                }
                for np in (
                    [p.model_dump() for p in negative_personas_raw]
                    if isinstance(negative_personas_raw, list) and negative_personas_raw and hasattr(negative_personas_raw[0], "model_dump")
                    else negative_personas_raw
                )
            ],
            "relevant_archive_samples": relevant_samples,
        }

    async def _retrieve_relevant_samples(
        self,
        tenant_id: UUID,
        client_id: UUID,
        target_niche: str,
        top_k: int = 2,
    ) -> list[str]:
        """Retrieve most relevant historical email samples via Qdrant or in-memory."""
        archive_key = f"archives:{tenant_id}:{client_id}"

        try:
            from seo_platform.services.vector_store import qdrant_vector_store
            results = await qdrant_vector_store.search(
                collection="client_archives",
                tenant_id=tenant_id,
                query=target_niche or "",
                limit=top_k,
            )
            if results:
                return [r.get("text", "") for r in results if r.get("text")]
        except Exception:
            pass

        samples = self._vector_store.get(archive_key, [])
        if target_niche:
            scored = []
            for text, raw in samples:
                score = sum(1 for w in target_niche.lower().split() if w in text.lower())
                scored.append((score, raw))
            scored.sort(key=lambda x: x[0], reverse=True)
            return [s[1] for s in scored[:top_k]]

        return [s[1] for s in samples[:top_k]]

    def _default_persona_context(self) -> dict[str, Any]:
        """Return a clean professional baseline when no persona is configured."""
        return {
            "brand_voice_summary": "Professional, warm, and highly authoritative.",
            "editorial_constraints": {
                "prohibited_words": EditorialConstraint().prohibited_words,
                "mandatory_tone_markers": [],
                "max_sentence_length": 25,
                "formality_level": "professional_conversational",
            },
            "prohibited_words": EditorialConstraint().prohibited_words,
            "negative_personas": [],
            "relevant_archive_samples": [],
        }


client_persona_service = ClientPersonaService()
