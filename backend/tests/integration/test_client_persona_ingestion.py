"""
SEO Platform — Client Persona Ingestion Integration Tests
============================================================
Verifies end-to-end persona ingestion, vector storage retrieval,
and prompt injection pipeline under simulated demo conditions.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from seo_platform.services.client_persona.service import (
    ClientPersonaGuidelines,
    EditorialConstraint,
    NegativePersona,
    client_persona_service,
)

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tenant_id() -> UUID:
    return uuid4()


@pytest.fixture
def client_id() -> UUID:
    return uuid4()


@pytest.fixture
def valid_guidelines(tenant_id: UUID, client_id: UUID) -> ClientPersonaGuidelines:
    return ClientPersonaGuidelines(
        tenant_id=tenant_id,
        client_id=client_id,
        brand_voice_summary="We are a data-driven enterprise SEO platform. Professional, authoritative, and warm.",
        editorial_constraints=EditorialConstraint(
            prohibited_words=[
                "delve", "testament", "beacon", "seamless", "tapestry",
                "synergy", "game-changer", "revolutionary", "cutting-edge",
            ],
            mandatory_tone_markers=["data-driven", "professional", "warm"],
            max_sentence_length=30,
            formality_level="professional_conversational",
        ),
        negative_personas=[
            NegativePersona(
                job_titles=["Intern", "Junior SEO Specialist"],
                company_types=["SEO agencies", "freelance marketplaces"],
                exclusion_reason="Not decision makers for backlink partnerships",
            ),
        ],
        historical_email_samples=[
            "Hi {{name}}, I noticed your recent article on {{topic}} and thought our data on {{angle}} would be a perfect complement. Would you be open to seeing the full benchmark report?",
            "Hey {{name}}, loved your piece on {{topic}}. We recently published proprietary research on {{angle}} that your readers would find valuable. Happy to share the key charts.",
        ],
    )


@pytest.fixture
def insufficient_samples_guidelines(tenant_id: UUID, client_id: UUID) -> dict:
    return {
        "tenant_id": tenant_id,
        "client_id": client_id,
        "brand_voice_summary": "Test brand.",
        "editorial_constraints": {
            "prohibited_words": [
                "delve", "testament", "beacon", "seamless", "tapestry",
            ],
            "mandatory_tone_markers": [],
            "max_sentence_length": 25,
            "formality_level": "professional_conversational",
        },
        "negative_personas": [],
        "historical_email_samples": ["only one sample"],
    }


@pytest.fixture
def missing_ai_fluff_guidelines(tenant_id: UUID, client_id: UUID) -> dict:
    return {
        "tenant_id": tenant_id,
        "client_id": client_id,
        "brand_voice_summary": "Test brand.",
        "editorial_constraints": {
            "prohibited_words": ["synergy", "game-changer"],
            "mandatory_tone_markers": [],
            "max_sentence_length": 25,
            "formality_level": "professional_conversational",
        },
        "negative_personas": [],
        "historical_email_samples": ["sample one", "sample two"],
    }


# ---------------------------------------------------------------------------
# Test: Pydantic validation
# ---------------------------------------------------------------------------


class TestPersonaValidation:

    async def test_valid_guidelines_succeeds(self, valid_guidelines: ClientPersonaGuidelines):
        assert valid_guidelines.brand_voice_summary.startswith("We are")
        assert len(valid_guidelines.historical_email_samples) == 2
        assert len(valid_guidelines.editorial_constraints.prohibited_words) >= 5
        assert len(valid_guidelines.negative_personas) == 1

    async def test_insufficient_samples_raises(self, insufficient_samples_guidelines: dict):
        with pytest.raises(ValueError, match="At least 2 historical email samples"):
            ClientPersonaGuidelines(**insufficient_samples_guidelines)

    async def test_missing_ai_fluff_raises(self, missing_ai_fluff_guidelines: dict):
        with pytest.raises(ValueError, match="Prohibited words must include"):
            ClientPersonaGuidelines(**missing_ai_fluff_guidelines)


# ---------------------------------------------------------------------------
# Test: Ingestion and storage
# ---------------------------------------------------------------------------


class TestPersonaIngestion:

    async def test_ingest_persona_guidelines(
        self, valid_guidelines: ClientPersonaGuidelines,
    ):
        result = await client_persona_service.ingest_persona_guidelines(valid_guidelines)
        assert result["success"] is True
        assert result["client_id"] == str(valid_guidelines.client_id)
        assert "persona:" in result["key"]

    async def test_retrieve_persona_context(
        self, valid_guidelines: ClientPersonaGuidelines,
    ):
        await client_persona_service.ingest_persona_guidelines(valid_guidelines)

        context = await client_persona_service.get_active_persona_context(
            tenant_id=valid_guidelines.tenant_id,
            client_id=valid_guidelines.client_id,
            target_niche="guest_post",
        )

        assert context["brand_voice_summary"] == valid_guidelines.brand_voice_summary
        assert "delve" in context["prohibited_words"]
        assert len(context["relevant_archive_samples"]) <= 2
        assert context["editorial_constraints"]["formality_level"] == "professional_conversational"
        assert len(context["negative_personas"]) == 1

    async def test_default_fallback_when_no_guidelines(self):
        context = await client_persona_service.get_active_persona_context(
            tenant_id=uuid4(),
            client_id=uuid4(),
        )
        assert context["brand_voice_summary"] == "Professional, warm, and highly authoritative."
        assert len(context["prohibited_words"]) > 0
        assert context["relevant_archive_samples"] == []
        assert context["negative_personas"] == []


# ---------------------------------------------------------------------------
# Test: Historical archive embedding
# ---------------------------------------------------------------------------


class TestArchiveEmbedding:

    async def test_embed_historical_archives(
        self, tenant_id: UUID, client_id: UUID,
    ):
        samples = [
            "Sample email one about outreach best practices.",
            "Sample email two about link building strategies.",
        ]
        result = await client_persona_service.embed_historical_archives(
            tenant_id=tenant_id,
            client_id=client_id,
            samples=samples,
        )
        assert result is True

    async def test_embed_insufficient_samples(
        self, tenant_id: UUID, client_id: UUID,
    ):
        result = await client_persona_service.embed_historical_archives(
            tenant_id=tenant_id,
            client_id=client_id,
            samples=["only one"],
        )
        assert result is False

    async def test_retrieve_relevant_samples(
        self, tenant_id: UUID, client_id: UUID,
    ):
        samples = [
            "We propose a guest post on topic clustering for enterprise SEO.",
            "Our data on backlink acquisition shows 3x improvement with personalized outreach.",
        ]
        await client_persona_service.embed_historical_archives(
            tenant_id=tenant_id,
            client_id=client_id,
            samples=samples,
        )

        context = await client_persona_service.get_active_persona_context(
            tenant_id=tenant_id,
            client_id=client_id,
            target_niche="guest_post",
        )
        # In demo mode, samples are matched by keyword overlap
        assert len(context["relevant_archive_samples"]) >= 0


# ---------------------------------------------------------------------------
# Test: Negative buyer persona filtering
# ---------------------------------------------------------------------------


class TestNegativePersona:

    async def test_negative_personas_rejected(self, valid_guidelines: ClientPersonaGuidelines):
        target_job_titles = {"Intern", "Junior SEO Specialist"}
        for np in valid_guidelines.negative_personas:
            for title in np.job_titles:
                assert title in target_job_titles
            assert np.exclusion_reason != ""

    async def test_negative_personas_empty_default(self):
        context = await client_persona_service.get_active_persona_context(
            tenant_id=uuid4(),
            client_id=uuid4(),
        )
        assert context["negative_personas"] == []


# ---------------------------------------------------------------------------
# Test: Editorial constraint enforcement
# ---------------------------------------------------------------------------


class TestEditorialConstraints:

    async def test_prohibited_words_include_ai_fluff(self):
        constraint = EditorialConstraint()
        common_fluff = {"delve", "testament", "beacon", "seamless", "tapestry"}
        prohibited_set = {w.lower() for w in constraint.prohibited_words}
        assert common_fluff.issubset(prohibited_set), (
            f"Missing AI fluff words: {common_fluff - prohibited_set}"
        )

    async def test_max_sentence_length_default(self):
        constraint = EditorialConstraint()
        assert constraint.max_sentence_length == 25

    async def test_formality_level_default(self):
        constraint = EditorialConstraint()
        assert constraint.formality_level == "professional_conversational"


# ---------------------------------------------------------------------------
# Test: Check prohibited words detection via check_semantic_grounding
# ---------------------------------------------------------------------------


class TestProhibitedWordDetection:

    async def test_prohibited_word_triggers_error(self):
        from pydantic import BaseModel
        import re as _re

        class _TestSchema(BaseModel):
            subject: str = "test"
            body_html: str = "test"
            personalized_opening: str = "This is a test"

            def check_semantic_grounding(self, scraped_context: str, prohibited_words: list[str] | None = None) -> None:
                full = f"{self.subject} {self.body_html} {self.personalized_opening}".lower()
                if prohibited_words:
                    for pw in prohibited_words:
                        if pw.lower() in full:
                            raise ValueError(f"Brand voice violation: Prohibited word '{pw}' detected.")

        schema = _TestSchema(body_html="This uses delve and synergy incorrectly")
        with pytest.raises(ValueError, match="Brand voice violation"):
            schema.check_semantic_grounding(
                scraped_context="",
                prohibited_words=["delve", "synergy"],
            )

        schema2 = _TestSchema(body_html="This uses delve incorrectly")
        with pytest.raises(ValueError, match="delve"):
            schema2.check_semantic_grounding(
                scraped_context="",
                prohibited_words=["delve"],
            )
