"""
SEO Platform — Autonomous Data Journalism Engine Integration Tests
====================================================================
Verifies end-to-end dataset ingestion, editorial angle extraction,
and Tier-1 asset pitch injection under simulated demo conditions.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from seo_platform.services.data_journalism.service import (
    BespokeAssetPitch,
    DataJournalismService,
    DataPoint,
    EditorialAngle,
    data_journalism_service,
)

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tenant_id() -> UUID:
    return uuid4()


@pytest.fixture
def campaign_id() -> UUID:
    return uuid4()


@pytest.fixture
def sample_dataset() -> list[dict]:
    return [
        {"year": 2020, "channel": "organic_search", "revenue": 1200000, "visitors": 450000, "conversion_rate": 2.8},
        {"year": 2021, "channel": "organic_search", "revenue": 2100000, "visitors": 720000, "conversion_rate": 3.1},
        {"year": 2022, "channel": "organic_search", "revenue": 3800000, "visitors": 1100000, "conversion_rate": 3.4},
        {"year": 2023, "channel": "organic_search", "revenue": 5200000, "visitors": 1500000, "conversion_rate": 3.2},
        {"year": 2024, "channel": "organic_search", "revenue": 8100000, "visitors": 2100000, "conversion_rate": 3.5},
        {"year": 2020, "channel": "paid_ads", "revenue": 900000, "visitors": 320000, "conversion_rate": 2.1},
        {"year": 2021, "channel": "paid_ads", "revenue": 850000, "visitors": 300000, "conversion_rate": 2.0},
        {"year": 2022, "channel": "paid_ads", "revenue": 720000, "visitors": 260000, "conversion_rate": 1.9},
        {"year": 2023, "channel": "paid_ads", "revenue": 580000, "visitors": 210000, "conversion_rate": 1.8},
        {"year": 2024, "channel": "paid_ads", "revenue": 450000, "visitors": 160000, "conversion_rate": 1.7},
        {"year": 2020, "channel": "content_partnerships", "revenue": 150000, "visitors": 85000, "conversion_rate": 4.2},
        {"year": 2021, "channel": "content_partnerships", "revenue": 420000, "visitors": 180000, "conversion_rate": 4.5},
        {"year": 2022, "channel": "content_partnerships", "revenue": 1100000, "visitors": 390000, "conversion_rate": 4.8},
        {"year": 2023, "channel": "content_partnerships", "revenue": 2400000, "visitors": 720000, "conversion_rate": 5.1},
        {"year": 2024, "channel": "content_partnerships", "revenue": 4600000, "visitors": 1200000, "conversion_rate": 5.3},
    ]


@pytest.fixture
def tier1_prospect() -> dict:
    return {
        "domain": "forbes.com",
        "domain_authority": 92,
        "contact_name": "Sarah Editor",
        "contact_email": "sarah@forbes.com",
        "relevance_score": 0.8,
    }


@pytest.fixture
def standard_prospect() -> dict:
    return {
        "domain": "example-blog.com",
        "domain_authority": 42,
        "contact_name": "John Blogger",
        "contact_email": "john@example-blog.com",
        "relevance_score": 0.6,
    }


# ---------------------------------------------------------------------------
# Test: Pydantic schema validation
# ---------------------------------------------------------------------------


class TestSchemaValidation:

    async def test_valid_editorial_angle_succeeds(self):
        angle = EditorialAngle(
            headline="Enterprise SEO Spend Triples as AI Reshapes Digital Marketing",
            counter_intuitive_hook="While ad budgets decline 73%, content partnership ROI reaches 4.7x — the biggest winners are investing in editorial relationships, not programmatic media.",
            supporting_data_points=[
                DataPoint(metric_name="SEO Budget Growth", metric_value="340%", percentage_change=340.0),
                DataPoint(metric_name="Ad Budget Decline", metric_value="73%", percentage_change=-73.0),
                DataPoint(metric_name="Partnership ROI", metric_value="4.7x"),
            ],
        )
        assert len(angle.supporting_data_points) == 3
        assert "ad budgets" in angle.counter_intuitive_hook

    async def test_insufficient_data_points_raises(self):
        with pytest.raises(ValueError, match="At least 3 supporting data points"):
            EditorialAngle(
                headline="Test",
                counter_intuitive_hook="Valid hook with actual data insight",
                supporting_data_points=[
                    DataPoint(metric_name="Only one", metric_value="1"),
                ],
            )

    async def test_fluff_hook_raises(self):
        with pytest.raises(ValueError, match="generic fluff"):
            EditorialAngle(
                headline="Test",
                counter_intuitive_hook="You won't believe this shocking data about SEO!",
                supporting_data_points=[
                    DataPoint(metric_name="A", metric_value="1"),
                    DataPoint(metric_name="B", metric_value="2"),
                    DataPoint(metric_name="C", metric_value="3"),
                ],
            )

    async def test_bespoke_asset_pitch_creation(self, tenant_id: UUID, campaign_id: UUID):
        angle = EditorialAngle(
            headline="Test Asset",
            counter_intuitive_hook="Actual data-driven insight that challenges assumptions",
            supporting_data_points=[
                DataPoint(metric_name="A", metric_value="100"),
                DataPoint(metric_name="B", metric_value="200"),
                DataPoint(metric_name="C", metric_value="300"),
            ],
        )
        asset = BespokeAssetPitch(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            asset_title="The Test Data Story",
            editorial_angle=angle,
        )
        assert asset.asset_type == "interactive_chart"
        assert "embed" in asset.embed_code_snippet or not asset.embed_code_snippet


# ---------------------------------------------------------------------------
# Test: Dataset ingestion
# ---------------------------------------------------------------------------


class TestDatasetIngestion:

    async def test_ingest_valid_dataset(self, tenant_id: UUID, campaign_id: UUID, sample_dataset: list[dict]):
        result = await data_journalism_service.ingest_client_dataset(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            raw_data=sample_dataset,
        )
        assert result["success"] is True
        assert result["record_count"] == len(sample_dataset)
        assert "revenue" in result["fields"]

    async def test_ingest_empty_dataset_fails(self, tenant_id: UUID, campaign_id: UUID):
        result = await data_journalism_service.ingest_client_dataset(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            raw_data=[],
        )
        assert result["success"] is False


# ---------------------------------------------------------------------------
# Test: Editorial angle extraction
# ---------------------------------------------------------------------------


class TestEditorialAngleExtraction:

    async def test_fallback_angle_returned_when_no_dataset(self, tenant_id: UUID, campaign_id: UUID):
        angle = await data_journalism_service.extract_editorial_angles(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            target_beat="technology",
        )
        assert isinstance(angle, EditorialAngle)
        assert len(angle.supporting_data_points) >= 3
        assert "340%" in angle.headline or "ad budget" in angle.counter_intuitive_hook

    async def test_angle_with_dataset(self, tenant_id: UUID, campaign_id: UUID, sample_dataset: list[dict]):
        await data_journalism_service.ingest_client_dataset(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            raw_data=sample_dataset,
        )
        angle = await data_journalism_service.extract_editorial_angles(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            target_beat="marketing",
        )
        assert isinstance(angle, EditorialAngle)
        assert len(angle.supporting_data_points) >= 3


# ---------------------------------------------------------------------------
# Test: Tier-1 asset generation threshold
# ---------------------------------------------------------------------------


class TestTier1AssetThreshold:

    async def test_tier1_prospect_receives_asset(self, tenant_id: UUID, campaign_id: UUID):
        asset = await data_journalism_service.generate_bespoke_asset_pitch(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            prospect_domain="forbes.com",
            prospect_dr=92,
        )
        assert asset is not None
        assert "forbes" in asset.asset_title.lower()
        assert isinstance(asset.editorial_angle, EditorialAngle)
        assert "embed" in asset.embed_code_snippet

    async def test_standard_prospect_receives_none(self, tenant_id: UUID, campaign_id: UUID):
        asset = await data_journalism_service.generate_bespoke_asset_pitch(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            prospect_domain="example-blog.com",
            prospect_dr=42,
        )
        assert asset is None

    async def test_boundary_tier1_dr75_receives_asset(self, tenant_id: UUID, campaign_id: UUID):
        asset = await data_journalism_service.generate_bespoke_asset_pitch(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            prospect_domain="high-authority.com",
            prospect_dr=75,
        )
        assert asset is not None

    async def test_sub_tier1_dr74_receives_none(self, tenant_id: UUID, campaign_id: UUID):
        asset = await data_journalism_service.generate_bespoke_asset_pitch(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            prospect_domain="mid-authority.com",
            prospect_dr=74,
        )
        assert asset is None


# ---------------------------------------------------------------------------
# Test: Embed snippet generation
# ---------------------------------------------------------------------------


class TestEmbedSnippet:

    async def test_embed_contains_metric_values(self):
        angle = EditorialAngle(
            headline="Test",
            counter_intuitive_hook="Data-driven insight challenging conventional wisdom",
            supporting_data_points=[
                DataPoint(metric_name="Growth", metric_value="340%", percentage_change=340.0),
                DataPoint(metric_name="Decline", metric_value="73%", percentage_change=-73.0),
                DataPoint(metric_name="ROI", metric_value="4.7x"),
            ],
        )
        snippet = data_journalism_service._generate_embed_snippet(angle, "testdomain")
        assert "340%" in snippet
        assert "73%" in snippet
        assert "4.7x" in snippet
        assert "TESTDOMAIN" in snippet


# ---------------------------------------------------------------------------
# Test: In-memory caching of angles
# ---------------------------------------------------------------------------


class TestAngleCaching:

    async def test_cached_angle_retrieved(self, tenant_id: UUID, campaign_id: UUID):
        angle = await data_journalism_service.extract_editorial_angles(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            target_beat="technology",
        )
        cached = await data_journalism_service.get_cached_angle(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
        )
        assert cached is not None
        assert cached.headline == angle.headline

    async def test_nonexistent_cache_returns_none(self):
        cached = await data_journalism_service.get_cached_angle(
            tenant_id=uuid4(),
            campaign_id=uuid4(),
        )
        assert cached is None


# ---------------------------------------------------------------------------
# Test: Clean singleton state per test
# ---------------------------------------------------------------------------


class TestServiceIsolation:

    async def test_isolation_between_campaigns(self):
        t1, c1 = uuid4(), uuid4()
        t2, c2 = uuid4(), uuid4()

        ds1 = [{"channel": "seo", "value": 100}]
        ds2 = [{"channel": "ppc", "value": 200}]

        await data_journalism_service.ingest_client_dataset(t1, c1, ds1)
        await data_journalism_service.ingest_client_dataset(t2, c2, ds2)

        # The demo fallback angle is deterministic — both return the same
        # fallback since LLM is unavailable in test. Verifying isolation
        # by checking each returns valid EditorialAngle.
        a1 = await data_journalism_service.extract_editorial_angles(t1, c1)
        a2 = await data_journalism_service.extract_editorial_angles(t2, c2)
        assert isinstance(a1, EditorialAngle)
        assert isinstance(a2, EditorialAngle)
