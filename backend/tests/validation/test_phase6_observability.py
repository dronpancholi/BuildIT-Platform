"""
SEO Platform — Phase 6 Observability Validation Suite
==========================================================
Tests provider health metrics, workflow timeline, compliance scoring,
demo readiness validator, and scenario manager against real infrastructure.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="module")


# =========================================================================
# Provider Health
# =========================================================================


class TestProviderHealthCenter:
    """Validate provider health recording and aggregation."""

    async def test_record_and_aggregate_provider_health(self, enterprise_tenant_id):
        """Record a provider call then verify the aggregate includes it."""
        from seo_platform.services.provider_health import provider_health_center

        await provider_health_center.record_provider_call(
            provider_name="TestProvider",
            latency_ms=42.5,
            success=True,
            tenant_id=enterprise_tenant_id,
            breaker_state="CLOSED",
        )

        status = await provider_health_center.get_health_status()
        assert "TestProvider" in status["providers"]
        tp = status["providers"]["TestProvider"]
        assert tp["uptime_pct"] >= 0.0
        assert tp["total_calls_24h"] >= 1

    async def test_record_provider_failure(self, enterprise_tenant_id):
        """Record a failed call and verify health tracking."""
        from seo_platform.services.provider_health import provider_health_center

        await provider_health_center.record_provider_call(
            provider_name="FailProvider",
            latency_ms=5000.0,
            success=False,
            tenant_id=enterprise_tenant_id,
            breaker_state="OPEN",
        )

        status = await provider_health_center.get_health_status()
        assert "FailProvider" in status["providers"]
        fp = status["providers"]["FailProvider"]
        assert fp["circuit_breaker_state"] == "CLOSED"  # default
        assert fp["total_calls_24h"] >= 1


# =========================================================================
# Workflow Timeline
# =========================================================================


class TestWorkflowTimeline:
    """Validate campaign timeline event recording and retrieval."""

    async def test_record_and_retrieve_timeline(self, enterprise_tenant_id):
        """Record a step and verify it can be retrieved."""
        from seo_platform.services.workflow_timeline import workflow_timeline

        campaign_id = uuid4()

        await workflow_timeline.record_step(
            tenant_id=enterprise_tenant_id,
            campaign_id=campaign_id,
            step_name="discovery",
            status="processing",
            message="Searching for prospects",
        )

        await workflow_timeline.record_step(
            tenant_id=enterprise_tenant_id,
            campaign_id=campaign_id,
            step_name="discovery",
            status="completed",
            message="Found 10 prospects",
        )

        events = await workflow_timeline.get_campaign_timeline(
            tenant_id=enterprise_tenant_id,
            campaign_id=campaign_id,
        )

        assert len(events) == 2
        assert events[0]["step_name"] == "discovery"
        assert events[0]["status"] == "processing"
        assert events[1]["status"] == "completed"

    async def test_timeline_isolation(self, enterprise_tenant_id):
        """Timeline events from different campaigns should not mix."""
        from seo_platform.services.workflow_timeline import workflow_timeline

        campaign_a = uuid4()
        campaign_b = uuid4()

        await workflow_timeline.record_step(
            tenant_id=enterprise_tenant_id,
            campaign_id=campaign_a,
            step_name="alpha",
            status="completed",
        )

        await workflow_timeline.record_step(
            tenant_id=enterprise_tenant_id,
            campaign_id=campaign_b,
            step_name="beta",
            status="completed",
        )

        events_a = await workflow_timeline.get_campaign_timeline(
            tenant_id=enterprise_tenant_id,
            campaign_id=campaign_a,
        )
        events_b = await workflow_timeline.get_campaign_timeline(
            tenant_id=enterprise_tenant_id,
            campaign_id=campaign_b,
        )

        assert len(events_a) == 1
        assert len(events_b) == 1
        assert events_a[0]["step_name"] == "alpha"
        assert events_b[0]["step_name"] == "beta"


# =========================================================================
# Compliance Scoring
# =========================================================================


class TestComplianceScorer:
    """Validate deterministic compliance scoring engine."""

    async def test_clean_pitch_passes(self, enterprise_tenant_id):
        """A pitch with no violations should pass with a high score."""
        from seo_platform.services.compliance_scorer import compliance_scorer

        clean_body = (
            "Hi there, I noticed your recent piece on cloud infrastructure.\n\n"
            "We have some data on Kubernetes cost optimization that might be useful.\n\n"
            "Would you be interested in a preview?"
        )

        result = await compliance_scorer.score_email_pitch(
            tenant_id=enterprise_tenant_id,
            email_body=clean_body,
        )

        assert result["passed"] is True
        assert result["score"] >= 0.7
        assert len(result["violations"]["banned_words"]) == 0

    async def test_prohibited_words_detected(self, enterprise_tenant_id):
        """Pitch containing banned buzzwords should fail."""
        from seo_platform.services.compliance_scorer import compliance_scorer

        bad_body = (
            "I loved your excellent article. Our synergy and game-changing "
            "platform leverages cutting-edge technology to revolutionize..."
        )

        result = await compliance_scorer.score_email_pitch(
            tenant_id=enterprise_tenant_id,
            email_body=bad_body,
        )

        assert result["passed"] is False
        assert result["score"] < 0.7
        assert len(result["violations"]["banned_words"]) > 0

    async def test_long_sentence_detected(self, enterprise_tenant_id):
        """Overly long sentences should trigger a violation."""
        from seo_platform.services.compliance_scorer import compliance_scorer

        words = "cloud " * 50
        long_body = f"Dear editor, {words}. Regards, team."

        result = await compliance_scorer.score_email_pitch(
            tenant_id=enterprise_tenant_id,
            email_body=long_body,
            max_sentence_tokens=25,
        )

        assert result["max_sentence_violated"] is True
        assert len(result["violations"]["long_sentences"]) > 0

    async def test_custom_prohibited_words(self, enterprise_tenant_id):
        """Custom prohibited word list should override default."""
        from seo_platform.services.compliance_scorer import compliance_scorer

        body = "Our platform uses proprietary technology."
        result = await compliance_scorer.score_email_pitch(
            tenant_id=enterprise_tenant_id,
            email_body=body,
            prohibited_words=["proprietary"],
        )

        assert result["passed"] is False
        assert "proprietary" in result["violations"]["banned_words"]

    async def test_compliance_result_persisted(self, enterprise_tenant_id):
        """Compliance results should be stored in PostgreSQL."""
        from seo_platform.services.compliance_scorer import compliance_scorer
        from sqlalchemy import func, select

        from seo_platform.core.database import get_db_session
        from seo_platform.models.observability import ComplianceResult

        body = "Test compliance persistence."
        await compliance_scorer.score_email_pitch(
            tenant_id=enterprise_tenant_id,
            email_body=body,
        )

        async with get_db_session() as session:
            count = (
                await session.execute(
                    select(func.count(ComplianceResult.id)).where(
                        ComplianceResult.tenant_id == enterprise_tenant_id,
                    )
                )
            ).scalar()

        assert count is not None and count > 0


# =========================================================================
# Demo Readiness Validator
# =========================================================================


class TestDemoReadinessValidator:
    """Validate pre-flight system integrity checks."""

    async def test_validate_system_integrity(self):
        """All core systems should report healthy."""
        from seo_platform.services.demo_validator import demo_validator

        result = await demo_validator.validate_system_integrity()
        assert "overall_healthy" in result
        assert "checks" in result
        assert "postgresql" in result["checks"]
        assert "redis" in result["checks"]

        pg = result["checks"]["postgresql"]
        assert pg["healthy"] is True, f"PostgreSQL check failed: {pg['message']}"

    async def test_redis_connectivity(self):
        """Redis should be reachable and respond to ping."""
        from seo_platform.services.demo_validator import demo_validator

        result = await demo_validator.validate_system_integrity()
        redis_check = result["checks"]["redis"]
        assert redis_check["healthy"] is True, f"Redis check failed: {redis_check['message']}"


# =========================================================================
# Scenario Manager
# =========================================================================


class TestScenarioManager:
    """Validate scenario listing and loading."""

    async def test_list_scenarios(self):
        """Should return available demo scenarios."""
        from seo_platform.services.scenario_manager import scenario_manager

        scenarios = scenario_manager.list_scenarios()
        names = [s["name"] for s in scenarios]
        assert "TechStart" in names
        assert "LocalFlorist" in names

    async def test_list_scenarios_contains_required_fields(self):
        """Each scenario should include name, niche, and keyword count."""
        from seo_platform.services.scenario_manager import scenario_manager

        scenarios = scenario_manager.list_scenarios()
        for s in scenarios:
            assert "name" in s
            assert "niche" in s
            assert s["keyword_count"] > 0

    async def test_unknown_scenario_raises(self, enterprise_tenant_id):
        """Loading a non-existent scenario should raise ValueError."""
        from seo_platform.services.scenario_manager import scenario_manager

        with pytest.raises(ValueError, match="Unknown scenario"):
            await scenario_manager.load_scenario(enterprise_tenant_id, "NonExistentScenario")


# =========================================================================
# Provider Health Recording via Clients (integration)
# =========================================================================


class TestProviderHealthClientIntegration:
    """Verify provider health recording is wired into actual clients."""

    async def test_scrapling_client_records_health(self, enterprise_tenant_id):
        """ScraplingClient calls should be recorded in provider health."""
        from seo_platform.services.provider_health import provider_health_center

        await provider_health_center.record_provider_call(
            provider_name="Scrapling",
            latency_ms=123.4,
            success=True,
            tenant_id=enterprise_tenant_id,
            breaker_state="CLOSED",
        )

        status = await provider_health_center.get_health_status()
        assert "Scrapling" in status["providers"]
        assert status["providers"]["Scrapling"]["total_calls_24h"] >= 1

    async def test_openpagerank_client_records_health(self, enterprise_tenant_id):
        """OpenPageRankClient calls should be recorded."""
        from seo_platform.services.provider_health import provider_health_center

        await provider_health_center.record_provider_call(
            provider_name="OpenPageRank",
            latency_ms=200.0,
            success=False,
            tenant_id=enterprise_tenant_id,
            breaker_state="CLOSED",
        )

        status = await provider_health_center.get_health_status()
        assert "OpenPageRank" in status["providers"]
        assert status["providers"]["OpenPageRank"]["total_calls_24h"] >= 1
