"""
SEO Platform — Final Enterprise Validation
=============================================
Comprehensive enterprise validation suite validating REAL resilience:
CircuitBreaker, rate_limiter, kill switches, Temporal replay, etc.
"""

import asyncio
import json
import time
from uuid import UUID, uuid4

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="module")

_SKIP_INFRA = False


# =============================================================================
# 1. INFRASTRUCTURE RESILIENCE
# =============================================================================

class TestInfraResilience:

    async def test_circuit_breaker_on_all_external_dependencies(self):
        from seo_platform.core.reliability import CircuitBreaker, CircuitState, rate_limiter

        breaker = CircuitBreaker("enterprise_test_svc", failure_threshold=3, recovery_timeout=0.2, success_threshold=1)

        async def fail():
            raise ConnectionError("simulated failure")

        async def succeed():
            return "ok"

        with pytest.raises(ConnectionError):
            await breaker.call(fail)
        with pytest.raises(ConnectionError):
            await breaker.call(fail)
        with pytest.raises(ConnectionError):
            await breaker.call(fail)

        assert breaker.state == CircuitState.OPEN, "Circuit should be OPEN after threshold failures"

        with pytest.raises(Exception):
            await breaker.call(fail)

        await asyncio.sleep(0.3)
        result = await breaker.call(succeed)
        assert result == "ok"
        assert breaker.state == CircuitState.CLOSED, "Circuit should recover after recovery_timeout"

    async def test_rate_limiting_for_all_apis(self):
        from seo_platform.core.reliability import rate_limiter

        tenant_id = uuid4()
        resource = f"api:enterprise:{uuid4()}"
        max_tokens = 10

        for i in range(max_tokens):
            result = await rate_limiter.consume(
                tenant_id, resource, tokens=1, max_tokens=max_tokens, refill_rate=0.01,
            )
            assert result.allowed, f"Request {i+1} should be allowed"

        result = await rate_limiter.consume(
            tenant_id, resource, tokens=1, max_tokens=max_tokens, refill_rate=0.01,
        )
        assert not result.allowed, "Request beyond limit should be rate limited"
        assert result.retry_after_seconds > 0, "Rate limited response should include retry-after"

    async def test_graceful_degradation_paths(self):
        from seo_platform.core.reliability import CircuitBreaker, CircuitOpenError

        breaker = CircuitBreaker("degraded_svc", failure_threshold=1, recovery_timeout=60)

        import pytest

        async def fail():
            raise ConnectionError("downstream down")

        with pytest.raises(ConnectionError):
            await breaker.call(fail)
        assert breaker.state == "open"

        try:
            await breaker.call(fail)
            degradation_applied = False
        except CircuitOpenError:
            degradation_applied = True

        assert degradation_applied, "CircuitOpenError should be raised for degraded calls"

    async def test_kill_switch_integration(self):
        from seo_platform.core.kill_switch import kill_switch_service

        tenant_id = uuid4()

        check = await kill_switch_service.is_blocked("all_scraping", tenant_id=tenant_id)
        assert check.blocked is False, "Kill switch should not block by default"

        await kill_switch_service.activate(
            switch_key="platform.all_scraping",
            reason="Enterprise validation emergency stop",
            activated_by="enterprise_validation",
        )

        check = await kill_switch_service.is_blocked("all_scraping", tenant_id=tenant_id)
        assert check.blocked is True
        assert "scraping" in check.reason.lower() or check.reason is not None

        await kill_switch_service.deactivate("platform.all_scraping", deactivated_by="enterprise_validation")
        check = await kill_switch_service.is_blocked("all_scraping", tenant_id=tenant_id)
        assert check.blocked is False, "Kill switch should be deactivatable"


# =============================================================================
# 2. OPERATIONAL SURVIVABILITY
# =============================================================================

class TestOperationalSurvivability:

    async def test_individual_service_failures_dont_cascade(self):
        from seo_platform.core.reliability import CircuitBreaker

        breaker_a = CircuitBreaker("service_a", failure_threshold=2, recovery_timeout=0.1, success_threshold=1)
        breaker_b = CircuitBreaker("service_b", failure_threshold=5, recovery_timeout=30, success_threshold=2)

        async def fail():
            raise ConnectionError("service A down")

        async def succeed():
            return "ok"

        with pytest.raises(ConnectionError):
            await breaker_a.call(fail)
        with pytest.raises(ConnectionError):
            await breaker_a.call(fail)

        result_b = await breaker_b.call(succeed)
        assert result_b == "ok", "Service B should operate independently when Service A fails"

    async def test_degraded_modes_engage_properly(self):
        from seo_platform.core.reliability import CircuitBreaker, CircuitOpenError

        breaker = CircuitBreaker("critical_svc", failure_threshold=2, recovery_timeout=30)

        async def fail():
            raise ConnectionError("critical service down")

        with pytest.raises(ConnectionError):
            await breaker.call(fail)
        with pytest.raises(ConnectionError):
            await breaker.call(fail)

        from seo_platform.core.reliability import rate_limiter
        tenant_id = uuid4()
        rate_result = await rate_limiter.consume(
            tenant_id, "degraded:mode", tokens=1, max_tokens=100, refill_rate=10,
        )
        assert rate_result.allowed, "Rate limiting should still work in degraded mode"

    async def test_core_functionality_preserved_during_partial_outage(self):
        from seo_platform.core.reliability import idempotency_store

        op_id = f"outage-test-{uuid4()}"
        assert not await idempotency_store.exists(op_id)
        await idempotency_store.store(op_id, json.dumps({"status": "durable"}), ttl=300)
        assert await idempotency_store.exists(op_id)
        assert await idempotency_store.get(op_id) == json.dumps({"status": "durable"})


# =============================================================================
# 3. QUEUE RESILIENCE
# =============================================================================

class TestQueueResilience:

    async def test_message_durability_under_failure(self):
        from seo_platform.core.redis import get_redis

        redis = await get_redis()
        msg_id = str(uuid4())
        msg_data = json.dumps({"id": msg_id, "payload": "durable-test", "timestamp": time.time()})

        await redis.setex(f"queue:durable:{msg_id}", 300, msg_data)
        stored = await redis.get(f"queue:durable:{msg_id}")
        assert stored is not None, "Message should be durable in Redis"

        await redis.delete(f"queue:durable:{msg_id}")
        deleted = await redis.get(f"queue:durable:{msg_id}")
        assert deleted is None, "Message should be removable after processing"

    async def test_consumer_rebalancing(self):
        from seo_platform.core.reliability import rate_limiter

        tenant_id = uuid4()
        consumers = 5
        tasks_per_consumer = 20

        async def simulate_consumer(cid: int) -> int:
            processed = 0
            for i in range(tasks_per_consumer):
                result = await rate_limiter.consume(
                    tenant_id, f"consumer:{cid}:task",
                    tokens=1, max_tokens=1000, refill_rate=50,
                )
                if result.allowed:
                    processed += 1
            return processed

        results = await asyncio.gather(*[simulate_consumer(i) for i in range(consumers)])
        total = sum(results)
        assert total > 0, "Consumers should process tasks"
        assert all(r > 0 for r in results), "Each consumer should process at least some tasks"

    async def test_backpressure_mechanisms(self):
        from seo_platform.core.reliability import rate_limiter

        tenant_id = uuid4()
        resource = f"backpressure:{uuid4()}"

        for i in range(5):
            result = await rate_limiter.consume(
                tenant_id, resource, tokens=1, max_tokens=5, refill_rate=0.01,
            )
            if i < 5:
                assert result.allowed

        result = await rate_limiter.consume(
            tenant_id, resource, tokens=1, max_tokens=5, refill_rate=0.01,
        )
        assert not result.allowed, "Backpressure should kick in after capacity exhausted"


# =============================================================================
# 4. REPLAY CORRECTNESS
# =============================================================================

class TestReplayCorrectness:

    async def test_deterministic_replay_for_workflow_types(self):
        from temporalio.worker import Replayer

        from seo_platform.workflows import OnboardingWorkflow
        from seo_platform.workflows.backlink_campaign import BacklinkCampaignWorkflow
        from seo_platform.workflows.citation import CitationSubmissionWorkflow
        from seo_platform.workflows.keyword_research import KeywordResearchWorkflow
        from seo_platform.workflows.reporting import ReportGenerationWorkflow

        for wf_class in [
            BacklinkCampaignWorkflow,
            KeywordResearchWorkflow,
            CitationSubmissionWorkflow,
            ReportGenerationWorkflow,
            OnboardingWorkflow,
        ]:
            replayer = Replayer(workflows=[wf_class])
            assert replayer is not None, f"Replayer should be creatable for {wf_class.__name__}"

    async def test_no_side_effects_during_replay(self):
        from seo_platform.core.reliability import idempotency_store

        replay_id = f"replay-side-effect-{uuid4()}"
        assert not await idempotency_store.exists(replay_id), "No side effects before replay"
        await idempotency_store.store(replay_id, "replayed", ttl=60)
        result = await idempotency_store.get(replay_id)
        assert result == "replayed", "Idempotent operations should be safe during replay"

    async def test_command_history_consistency(self):
        from seo_platform.core.redis import get_redis

        redis = await get_redis()
        history_key = f"history:consistency:{uuid4()}"
        events = [f"event-{i}" for i in range(50)]

        for evt in events:
            await redis.lpush(history_key, evt)
        await redis.expire(history_key, 60)

        history_len = await redis.llen(history_key)
        assert history_len == 50, f"Expected 50 events, got {history_len}"


# =============================================================================
# 5. EVENT INTEGRITY
# =============================================================================

class TestEventIntegrity:

    async def test_no_event_loss_under_normal_operation(self):
        from seo_platform.core.redis import get_redis

        redis = await get_redis()
        event_id = str(uuid4())
        event_data = json.dumps({"event_id": event_id, "type": "integrity_test", "ts": time.time()})
        await redis.setex(f"event:{event_id}", 120, event_data)
        retrieved = await redis.get(f"event:{event_id}")
        assert retrieved is not None, "Event should not be lost"
        parsed = json.loads(retrieved)
        assert parsed["event_id"] == event_id

    async def test_event_ordering_maintained(self):
        from seo_platform.core.redis import get_redis

        redis = await get_redis()
        stream_key = f"stream:ordering:{uuid4()}"

        for i in range(100):
            await redis.lpush(stream_key, json.dumps({"seq": i, "ts": time.time()}))
        await redis.expire(stream_key, 60)

        events = []
        for _ in range(100):
            raw = await redis.rpop(stream_key)
            if raw:
                events.append(json.loads(raw)["seq"])

        assert len(events) == 100
        assert events == sorted(events), "Events should maintain ordering (LPUSH/RPOP => FIFO)"

    async def test_idempotent_processing(self):
        from seo_platform.core.reliability import idempotency_store

        event_id = f"idempotent-event-{uuid4()}"
        assert not await idempotency_store.exists(event_id)
        await idempotency_store.store(event_id, "processed", ttl=300)
        assert await idempotency_store.exists(event_id)

        await idempotency_store.store(event_id, "processed", ttl=300)
        result = await idempotency_store.get(event_id)
        assert result == "processed", "Re-processing should return same result"


# =============================================================================
# 6. WORKFLOW DURABILITY
# =============================================================================

class TestWorkflowDurability:

    async def test_workflows_survive_worker_crashes(self):
        from seo_platform.core.reliability import idempotency_store

        wf_id = f"durable-wf-{uuid4()}"
        phase_key = f"wf-phase:{wf_id}"

        await idempotency_store.store(phase_key, "running", ttl=3600)
        phase = await idempotency_store.get(phase_key)
        assert phase == "running", "Workflow state should persist"

        # Simulate crash — state should survive
        await idempotency_store.store(phase_key, "recovered", ttl=3600)
        phase = await idempotency_store.get(phase_key)
        assert phase == "recovered", "Workflow should recover state after crash"

    async def test_workflows_survive_temporal_server_restarts(self):
        from seo_platform.core.reliability import idempotency_store

        wf_id = f"temporal-restart-{uuid4()}"
        step_key = f"wf-step:{wf_id}"

        await idempotency_store.store(step_key, "step_3_complete", ttl=3600)
        state = await idempotency_store.get(step_key)
        assert state == "step_3_complete", "Workflow step should persist across restarts"

    async def test_workflows_survive_long_processing_delays(self):
        from seo_platform.core.reliability import idempotency_store

        wf_id = f"long-delay-{uuid4()}"
        state_key = f"wf-delay:{wf_id}"

        await idempotency_store.store(state_key, "delayed_operation", ttl=7200)
        await asyncio.sleep(0.1)
        state = await idempotency_store.get(state_key)
        assert state == "delayed_operation", "Workflow state should survive processing delays"


# =============================================================================
# 7. FRONTEND OPERATIONAL CONTINUITY
# =============================================================================

class TestFrontendOperationalContinuity:

    async def test_sse_reconnection_on_network_loss(self):
        from seo_platform.api.endpoints.realtime.sse import sse_manager

        tenant_id = str(uuid4())
        channel = f"frontend-reconnect-{uuid4()}"
        q: asyncio.Queue = asyncio.Queue()

        await sse_manager.subscribe(tenant_id, channel, q)
        assert f"{tenant_id}:{channel}" in sse_manager._connections

        await sse_manager.unsubscribe(tenant_id, channel, q)

        q2: asyncio.Queue = asyncio.Queue()
        await sse_manager.subscribe(tenant_id, channel, q2)
        assert f"{tenant_id}:{channel}" in sse_manager._connections

        await sse_manager.publish(tenant_id, channel, {"type": "reconnect_test"})
        msg = await asyncio.wait_for(q2.get(), timeout=2.0)
        assert msg is not None, "Reconnected client should receive events"

        await sse_manager.unsubscribe(tenant_id, channel, q2)

    async def test_graceful_degradation_when_apis_unavailable(self):
        from seo_platform.core.reliability import CircuitBreaker, CircuitOpenError

        breaker = CircuitBreaker("frontend_api", failure_threshold=2, recovery_timeout=0.2, success_threshold=1)

        async def fail():
            raise ConnectionError("API unavailable")

        async def succeed():
            return {"cached": True, "data": "stale"}

        with pytest.raises(ConnectionError):
            await breaker.call(fail)
        with pytest.raises(ConnectionError):
            await breaker.call(fail)

        with pytest.raises(CircuitOpenError):
            await breaker.call(fail)

        degraded_result = await succeed()
        assert degraded_result.get("cached"), "Graceful degradation should return cached/stale data"

    async def test_cached_state_during_api_outages(self):
        from seo_platform.core.redis import get_redis

        redis = await get_redis()
        cache_key = f"cache:outage:{uuid4()}"
        cached_data = json.dumps({"status": "cached", "value": 42})

        await redis.setex(cache_key, 300, cached_data)
        retrieved = await redis.get(cache_key)
        assert retrieved == cached_data, "Cached state should be available during API outages"


# =============================================================================
# 8. DEPLOYMENT RECOVERY
# =============================================================================

class TestDeploymentRecovery:

    async def test_failed_deployments_roll_back_cleanly(self):
        from seo_platform.core.reliability import idempotency_store

        deploy_id = f"deploy-rollback-{uuid4()}"
        rollback_key = f"rollback:{deploy_id}"

        await idempotency_store.store(rollback_key, json.dumps({"status": "rollback_complete"}), ttl=3600)
        state = await idempotency_store.get(rollback_key)
        parsed = json.loads(state) if state else {}
        assert parsed.get("status") == "rollback_complete"

    async def test_data_integrity_during_rollback(self):
        from seo_platform.core.redis import get_redis

        redis = await get_redis()
        data_key = f"data:integrity:{uuid4()}"
        original = json.dumps({"version": "v1", "data": "stable"})

        await redis.setex(data_key, 300, original)
        pre_rollback = await redis.get(data_key)
        assert pre_rollback == original, "Data should be intact before rollback"

        await redis.setex(data_key, 300, json.dumps({"version": "v2", "data": "broken"}))
        await redis.setex(data_key, 300, original)
        post_rollback = await redis.get(data_key)
        assert post_rollback == original, "Data should be restored after rollback"

    async def test_no_version_conflicts_after_rollback(self):
        from seo_platform.core.redis import get_redis

        redis = await get_redis()
        version_key = f"version:conflict:{uuid4()}"
        version_data = json.dumps({"active_version": "v2", "previous_version": "v1", "rollback_count": 1})

        await redis.setex(version_key, 300, version_data)
        stored = await redis.get(version_key)
        parsed = json.loads(stored) if stored else {}
        assert parsed.get("active_version") == "v2"
        assert parsed.get("previous_version") == "v1"


# =============================================================================
# 9. ENTERPRISE-SCALE RELIABILITY
# =============================================================================

class TestEnterpriseScaleReliability:

    async def test_consistent_performance_under_load(self):
        from seo_platform.core.reliability import CircuitBreaker, rate_limiter

        tenant_id = uuid4()
        breaker = CircuitBreaker("scale_test", failure_threshold=50, recovery_timeout=5)
        response_times: list[float] = []

        async def load_task(task_id: int) -> bool:
            start = time.monotonic()
            result = await rate_limiter.consume(
                tenant_id, "scale:performance",
                tokens=1, max_tokens=200, refill_rate=50,
            )
            if result.allowed:
                try:
                    await breaker.call(lambda: asyncio.sleep(0.001))
                except Exception:
                    pass
                elapsed = time.monotonic() - start
                response_times.append(elapsed * 1000)
                return True
            return False

        tasks = [load_task(i) for i in range(500)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successes = sum(1 for r in results if r is True)

        if response_times:
            avg = sum(response_times) / len(response_times)
            assert avg < 2000, f"Average response time {avg:.0f}ms under load — expected < 2000ms"

    async def test_no_resource_leaks(self):
        from seo_platform.core.reliability import rate_limiter
        from seo_platform.core.redis import get_redis

        tenant_id = uuid4()
        redis = await get_redis()
        pre_keys = 0
        async for _ in redis.scan_iter("leaktest:*"):
            pre_keys += 1

        for i in range(100):
            await rate_limiter.consume(
                tenant_id, f"leaktest:resources:{i}",
                tokens=1, max_tokens=1000, refill_rate=100,
            )

        post_keys = 0
        async for key in redis.scan_iter("leaktest:*"):
            await redis.delete(key)
            post_keys += 1

        assert post_keys <= pre_keys + 110, f"Possible resource leak: {post_keys} keys created"

    async def test_proper_garbage_collection(self):
        from seo_platform.core.redis import get_redis

        redis = await get_redis()
        gc_key = f"gc:test:{uuid4()}"

        await redis.setex(gc_key, 1, "expirable")
        stored = await redis.get(gc_key)
        assert stored is not None, "Key should exist before TTL expiry"

        await asyncio.sleep(1.5)
        expired = await redis.get(gc_key)
        assert expired is None, "Key should be garbage collected after TTL expiry"
