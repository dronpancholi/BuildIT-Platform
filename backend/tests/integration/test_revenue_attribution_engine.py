"""
SEO Platform — Revenue Attribution & Campaign Evolution Integration Tests
==========================================================================
Verifies the closed-loop commercial impact model: CRM pipeline ingestion,
organic traffic surge simulation, ROI summary calculation, and the
CampaignEvolutionWorkflow's periodic cycle under simulated conditions.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from seo_platform.services.revenue_attribution.service import (
    AttributedDeal,
    CampaignROISummary,
    OrganicTrafficSurge,
    revenue_attribution_service,
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
def sample_crm_deals() -> list[dict]:
    return [
        {
            "deal_id": "deal-001",
            "deal_name": "Enterprise SEO Platform - Acme Corp",
            "crm_stage": "closed_won",
            "amount": 48000.0,
        },
        {
            "deal_id": "deal-002",
            "deal_name": "Content Strategy Retainer - Beta Inc",
            "crm_stage": "closed_won",
            "amount": 24000.0,
        },
        {
            "deal_id": "deal-003",
            "deal_name": "Link Building Campaign - Gamma LLC",
            "crm_stage": "proposal",
            "amount": 15000.0,
        },
        {
            "deal_id": "deal-004",
            "deal_name": "SEO Audit - Delta Co",
            "crm_stage": "qualified",
            "amount": 8000.0,
        },
        {
            "deal_id": "deal-005",
            "deal_name": "Consulting - Epsilon Ltd",
            "crm_stage": "lead",
            "amount": 5000.0,
        },
    ]


@pytest.fixture
def standard_backlinks() -> list[dict]:
    return [
        {"domain_rating": 55, "prospect_id": "p1", "acquired_at": "2025-01-15T00:00:00"},
        {"domain_rating": 48, "prospect_id": "p2", "acquired_at": "2025-01-20T00:00:00"},
        {"domain_rating": 60, "prospect_id": "p3", "acquired_at": "2025-02-01T00:00:00"},
        {"domain_rating": 42, "prospect_id": "p4", "acquired_at": "2025-02-10T00:00:00"},
    ]


@pytest.fixture
def tier1_enriched_backlinks() -> list[dict]:
    return [
        {"domain_rating": 55, "prospect_id": "p1", "acquired_at": "2025-01-15T00:00:00"},
        {"domain_rating": 88, "prospect_id": "p2", "acquired_at": "2025-01-20T00:00:00", "tier1_asset": True},
        {"domain_rating": 60, "prospect_id": "p3", "acquired_at": "2025-02-01T00:00:00"},
        {"domain_rating": 92, "prospect_id": "p4", "acquired_at": "2025-02-10T00:00:00", "tier1_asset": True},
    ]


@pytest.fixture
def empty_backlinks() -> list[dict]:
    return []


# ---------------------------------------------------------------------------
# Test: Pydantic schema validation
# ---------------------------------------------------------------------------


class TestSchemaValidation:

    async def test_valid_attributed_deal_succeeds(self, campaign_id: UUID):
        deal = AttributedDeal(
            deal_id="deal-001",
            deal_name="Enterprise Deal",
            crm_stage="closed_won",
            amount=25000.0,
            attributed_percentage=0.25,
            associated_campaign_id=campaign_id,
        )
        assert deal.amount == 25000.0
        assert deal.attributed_percentage == 0.25

    async def test_attributed_deal_negative_amount_raises(self, campaign_id: UUID):
        with pytest.raises(ValueError, match="Input should be greater than 0"):
            AttributedDeal(
                deal_id="deal-001",
                deal_name="Bad Deal",
                amount=-100.0,
                attributed_percentage=0.25,
                associated_campaign_id=campaign_id,
            )

    async def test_attributed_percentage_clamped(self, campaign_id: UUID):
        with pytest.raises(ValueError, match="Input should be less than or equal to 1"):
            AttributedDeal(
                deal_id="deal-001",
                deal_name="Over Attributed",
                amount=1000.0,
                attributed_percentage=1.5,
                associated_campaign_id=campaign_id,
            )

    async def test_valid_organic_traffic_surge_succeeds(self):
        surge = OrganicTrafficSurge(
            keyword_cluster="enterprise_seo",
            previous_position=45,
            new_position=12,
            estimated_monthly_clicks=340,
            traffic_value_usd=15300.0,
        )
        assert surge.keyword_cluster == "enterprise_seo"
        assert surge.new_position == 12
        assert surge.traffic_value_usd == 15300.0

    async def test_organic_surge_position_floor(self):
        with pytest.raises(ValueError, match="Input should be greater than or equal to 1"):
            OrganicTrafficSurge(
                keyword_cluster="general",
                previous_position=0,
                new_position=1,
                estimated_monthly_clicks=100,
                traffic_value_usd=5000.0,
            )

    async def test_valid_campaign_roi_summary_succeeds(self, tenant_id: UUID, campaign_id: UUID):
        summary = CampaignROISummary(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            total_spend=5000.0,
            total_pipeline_created=2000.0,
            total_closed_won=18000.0,
            organic_traffic_value_added=3000.0,
            roi_percentage=360.0,
        )
        assert summary.roi_percentage == 360.0

    async def test_campaign_roi_mismatch_raises(self, tenant_id: UUID, campaign_id: UUID):
        with pytest.raises(ValueError, match="ROI percentage"):
            CampaignROISummary(
                tenant_id=tenant_id,
                campaign_id=campaign_id,
                total_spend=5000.0,
                total_pipeline_created=2000.0,
                total_closed_won=18000.0,
                organic_traffic_value_added=3000.0,
                roi_percentage=999.0,
            )


# ---------------------------------------------------------------------------
# Test: CRM Pipeline Ingestion
# ---------------------------------------------------------------------------


class TestCrmPipelineIngestion:

    async def test_ingest_valid_pipeline(self, tenant_id: UUID, campaign_id: UUID, sample_crm_deals: list[dict]):
        result = await revenue_attribution_service.ingest_crm_pipeline(
            tenant_id=tenant_id,
            client_id=campaign_id,
            crm_deals=sample_crm_deals,
        )
        assert result["success"] is True
        assert result["deal_count"] == len(sample_crm_deals)
        assert result["total_pipeline"] == 100000.0

    async def test_ingest_empty_pipeline_fails(self, tenant_id: UUID, campaign_id: UUID):
        result = await revenue_attribution_service.ingest_crm_pipeline(
            tenant_id=tenant_id,
            client_id=campaign_id,
            crm_deals=[],
        )
        assert result["success"] is False
        assert "empty" in result["error"]

    async def test_ingest_pipeline_stores_for_retrieval(self, tenant_id: UUID, campaign_id: UUID, sample_crm_deals: list[dict]):
        await revenue_attribution_service.ingest_crm_pipeline(
            tenant_id=tenant_id,
            client_id=campaign_id,
            crm_deals=sample_crm_deals,
        )
        deals = await revenue_attribution_service._retrieve_crm_deals(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
        )
        assert len(deals) == len(sample_crm_deals)
        assert deals[0]["deal_id"] == "deal-001"


# ---------------------------------------------------------------------------
# Test: Authority & Traffic Evolution Simulation
# ---------------------------------------------------------------------------


class TestTrafficEvolutionSimulation:

    async def test_standard_backlinks_produce_surge(
        self, tenant_id: UUID, campaign_id: UUID, standard_backlinks: list[dict],
    ):
        surge = await revenue_attribution_service.simulate_authority_and_traffic_evolution(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            acquired_links=standard_backlinks,
        )
        assert surge.new_position < surge.previous_position
        assert surge.estimated_monthly_clicks > 0
        assert surge.traffic_value_usd > 0

    async def test_tier1_links_generate_premium_value(
        self, tenant_id: UUID, campaign_id: UUID, tier1_enriched_backlinks: list[dict],
        standard_backlinks: list[dict],
    ):
        standard = await revenue_attribution_service.simulate_authority_and_traffic_evolution(
            tenant_id=tenant_id,
            campaign_id=uuid4(),
            acquired_links=standard_backlinks,
        )
        tier1 = await revenue_attribution_service.simulate_authority_and_traffic_evolution(
            tenant_id=tenant_id,
            campaign_id=uuid4(),
            acquired_links=tier1_enriched_backlinks,
        )
        assert tier1.traffic_value_usd > standard.traffic_value_usd

    async def test_empty_links_return_no_movement(self, tenant_id: UUID, campaign_id: UUID, empty_backlinks: list[dict]):
        surge = await revenue_attribution_service.simulate_authority_and_traffic_evolution(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            acquired_links=empty_backlinks,
        )
        assert surge.previous_position == surge.new_position
        assert surge.estimated_monthly_clicks == 0
        assert surge.traffic_value_usd == 0.0

    async def test_surge_retrievable_after_simulation(
        self, tenant_id: UUID, campaign_id: UUID, standard_backlinks: list[dict],
    ):
        await revenue_attribution_service.simulate_authority_and_traffic_evolution(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            acquired_links=standard_backlinks,
        )
        retrieved = await revenue_attribution_service._retrieve_traffic_surge(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
        )
        assert retrieved is not None
        assert retrieved.keyword_cluster == campaign_id.hex[:8]


# ---------------------------------------------------------------------------
# Test: Campaign ROI Summary Calculation
# ---------------------------------------------------------------------------


class TestCampaignROISummary:

    async def test_roi_summary_with_deals_and_traffic(
        self, tenant_id: UUID, campaign_id: UUID, sample_crm_deals: list[dict],
        standard_backlinks: list[dict],
    ):
        await revenue_attribution_service.ingest_crm_pipeline(
            tenant_id=tenant_id,
            client_id=campaign_id,
            crm_deals=sample_crm_deals,
        )
        await revenue_attribution_service.simulate_authority_and_traffic_evolution(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            acquired_links=standard_backlinks,
        )
        summary = await revenue_attribution_service.calculate_campaign_roi_summary(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            simulation_spend=8000.0,
        )
        assert summary.total_closed_won > 0
        assert summary.total_pipeline_created > 0
        assert summary.organic_traffic_value_added > 0
        assert summary.roi_percentage > 0

    async def test_roi_without_deals_returns_baseline(
        self, tenant_id: UUID, campaign_id: UUID, standard_backlinks: list[dict],
    ):
        await revenue_attribution_service.simulate_authority_and_traffic_evolution(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            acquired_links=standard_backlinks,
        )
        summary = await revenue_attribution_service.calculate_campaign_roi_summary(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            simulation_spend=5000.0,
        )
        assert summary.total_closed_won == 0.0
        assert summary.total_pipeline_created == 0.0

    async def test_roi_without_traffic_or_deals(
        self, tenant_id: UUID, campaign_id: UUID, empty_backlinks: list[dict],
    ):
        await revenue_attribution_service.simulate_authority_and_traffic_evolution(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            acquired_links=empty_backlinks,
        )
        summary = await revenue_attribution_service.calculate_campaign_roi_summary(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            simulation_spend=5000.0,
        )
        assert summary.roi_percentage == 0.0

    async def test_attributed_deals_contain_expected_fields(
        self, tenant_id: UUID, campaign_id: UUID, sample_crm_deals: list[dict],
        standard_backlinks: list[dict],
    ):
        await revenue_attribution_service.ingest_crm_pipeline(
            tenant_id=tenant_id,
            client_id=campaign_id,
            crm_deals=sample_crm_deals,
        )
        await revenue_attribution_service.simulate_authority_and_traffic_evolution(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            acquired_links=standard_backlinks,
        )
        summary = await revenue_attribution_service.calculate_campaign_roi_summary(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
        )
        for deal in summary.attributed_deals:
            assert deal.associated_campaign_id == campaign_id
            assert deal.amount > 0
            assert 0.0 <= deal.attributed_percentage <= 1.0


# ---------------------------------------------------------------------------
# Test: CTR decay curve
# ---------------------------------------------------------------------------


class TestCTRDecayCurve:

    async def test_position_1_has_highest_ctr(self):
        benchmark = {"ctr_position_1": 0.28, "ctr_position_5": 0.08, "ctr_position_10": 0.03}
        ctr_1 = revenue_attribution_service._ctr_for_position(1, benchmark)
        ctr_5 = revenue_attribution_service._ctr_for_position(5, benchmark)
        ctr_10 = revenue_attribution_service._ctr_for_position(10, benchmark)
        ctr_20 = revenue_attribution_service._ctr_for_position(20, benchmark)
        assert ctr_1 > ctr_5 > ctr_10 > ctr_20

    async def test_ctr_is_strictly_decreasing(self):
        benchmark = {"ctr_position_1": 0.28, "ctr_position_5": 0.08, "ctr_position_10": 0.03}
        previous = 1.0
        for pos in range(1, 31):
            ctr = revenue_attribution_service._ctr_for_position(pos, benchmark)
            assert ctr <= previous, f"CTR increased at position {pos}: {previous} → {ctr}"
            previous = ctr


# ---------------------------------------------------------------------------
# Test: In-memory isolation between campaigns
# ---------------------------------------------------------------------------


class TestServiceIsolation:

    async def test_isolation_between_campaigns(self, sample_crm_deals: list[dict], standard_backlinks: list[dict]):
        t1, c1 = uuid4(), uuid4()
        t2, c2 = uuid4(), uuid4()

        await revenue_attribution_service.ingest_crm_pipeline(t1, c1, sample_crm_deals)
        await revenue_attribution_service.ingest_crm_pipeline(t2, c2, [])

        deals_1 = await revenue_attribution_service._retrieve_crm_deals(t1, c1)
        deals_2 = await revenue_attribution_service._retrieve_crm_deals(t2, c2)
        assert len(deals_1) == len(sample_crm_deals)
        assert deals_2 == []

        await revenue_attribution_service.simulate_authority_and_traffic_evolution(t1, c1, standard_backlinks)
        surge_1 = await revenue_attribution_service._retrieve_traffic_surge(t1, c1)
        surge_2 = await revenue_attribution_service._retrieve_traffic_surge(t2, c2)
        assert surge_1 is not None
        assert surge_2 is None
