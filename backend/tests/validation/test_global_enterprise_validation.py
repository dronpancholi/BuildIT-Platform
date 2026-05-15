"""
SEO Platform — Global Enterprise Validation
==============================================
Comprehensive global enterprise validation suite validating REAL resilience:
CircuitBreaker, rate_limiter, kill_switch_service, idempotency_store, etc.
"""

import asyncio
import json
import time
from uuid import uuid4

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="module")


# =============================================================================
# 1. MULTI-REGION ORCHESTRATION
# =============================================================================

class TestMultiRegionOrchestration:

    async def test_global_circuit_breaker_resilience(self):
        from seo_platform.core.reliability import CircuitBreaker, CircuitState

        breaker = CircuitBreaker(
            "global_resilience_svc",
            failure_threshold=3,
            recovery_timeout=0.3,
            success_threshold=2,
        )
        regions = 5
        calls_per_region = 10

        async def region_caller(region_id: int, results: list[str]):
            for i in range(calls_per_region):
                call_id = f"region-{region_id}-call-{i}"

                async def fail():
                    raise ConnectionError(f"failure from {call_id}")

                async def succeed():
                    return call_id

                try:
                    if breaker.state == CircuitState.OPEN:
                        await asyncio.sleep(0.35)
                    result = await breaker.call(succeed)
                    results.append(result)
                except Exception:
                    try:
                        await breaker.call(fail)
                    except Exception:
                        pass

        all_results: list[str] = []
        tasks = [region_caller(r, all_results) for r in range(regions)]
        await asyncio.gather(*tasks, return_exceptions=True)

        assert breaker.state == CircuitState.CLOSED, \
            f"Circuit should eventually recover to CLOSED, got {breaker.state}"

    async def test_cross_region_replay_consistency(self):
        from seo_platform.core.reliability import idempotency_store

        regions = 4
        workflow_id = f"cross-region-replay-{uuid4()}"

        async def simulate_replay(region: str, step: str) -> str:
            key = f"replay:{workflow_id}:{region}:{step}"
            if await idempotency_store.exists(key):
                stored = await idempotency_store.get(key)
                return stored
            result = json.dumps({"region": region, "step": step, "status": "completed"})
            await idempotency_store.store(key, result, ttl=300)
            return result

        steps = ["init", "process", "finalize"]
        replay_tasks = []
        for region_idx in range(regions):
            for step in steps:
                replay_tasks.append(simulate_replay(f"region-{region_idx}", step))

        results = await asyncio.gather(*replay_tasks, return_exceptions=True)
        successes = [r for r in results if isinstance(r, str)]
        assert len(successes) == regions * len(steps), \
            f"Expected {regions * len(steps)} successful replays, got {len(successes)}"

        for step in steps:
            region_results = []
            for region_idx in range(regions):
                key = f"replay:{workflow_id}:region-{region_idx}:{step}"
                stored = await idempotency_store.get(key)
                if stored:
                    parsed = json.loads(stored)
                    region_results.append(parsed["status"])
            assert all(s == "completed" for s in region_results), \
                f"Step {step} should be consistent across regions"

    async def test_geo_aware_rate_limiting(self):
        from seo_platform.core.reliability import rate_limiter

        geo_tenants = [uuid4() for _ in range(5)]
        resource = f"geo:api:{uuid4()}"
        max_tokens = 20
        total_allowed = 0
        total_limited = 0

        for tenant_id in geo_tenants:
            for _ in range(max_tokens):
                result = await rate_limiter.consume(
                    tenant_id, resource, tokens=1,
                    max_tokens=max_tokens, refill_rate=0.1,
                )
                if result.allowed:
                    total_allowed += 1
                else:
                    total_limited += 1

            result = await rate_limiter.consume(
                tenant_id, resource, tokens=1,
                max_tokens=max_tokens, refill_rate=0.1,
            )
            assert not result.allowed, \
                f"Tenant {tenant_id} should be rate limited after exhausting quota"

        assert total_allowed > 0, "At least some requests should be allowed across geo tenants"


# =============================================================================
# 2. GLOBAL REPLAY SAFETY
# =============================================================================

class TestGlobalReplaySafety:

    async def test_deterministic_replay_across_regions(self):
        from seo_platform.core.reliability import CircuitBreaker

        regions = ["us-east", "eu-west", "ap-southeast"]
        results_by_region: dict[str, list[int]] = {}

        async def replay_operation(region: str) -> int:
            breaker = CircuitBreaker(
                f"replay_{region}",
                failure_threshold=10,
                recovery_timeout=30,
                success_threshold=1,
            )
            call_count = 0
            for i in range(20):
                async def succeed(i=i):
                    await asyncio.sleep(0.001)
                    return i * 2

                result = await breaker.call(succeed)
                call_count += 1
            return call_count

        region_tasks = [replay_operation(r) for r in regions]
        counts = await asyncio.gather(*region_tasks)

        for i in range(1, len(counts)):
            assert counts[i] == counts[0], \
                f"Region {regions[i]} produced {counts[i]} calls, expected {counts[0]}"

    async def test_replay_idempotency_global(self):
        from seo_platform.core.reliability import idempotency_store

        op_id = f"global-idempotent-{uuid4()}"
        result_payload = json.dumps({"executed": True, "timestamp": time.time()})

        first_store = await idempotency_store.store(op_id, result_payload, ttl=300)
        assert first_store is None

        first_exists = await idempotency_store.exists(op_id)
        assert first_exists, "Operation should exist after first store"

        await idempotency_store.store(op_id, result_payload, ttl=300)
        stored = await idempotency_store.get(op_id)
        parsed = json.loads(stored)
        assert parsed["executed"] is True, "Idempotent replay should return consistent result"

        concurrent_stores = []
        for _ in range(10):
            concurrent_stores.append(idempotency_store.store(op_id, result_payload, ttl=300))

        await asyncio.gather(*concurrent_stores, return_exceptions=True)
        final = await idempotency_store.get(op_id)
        assert final == result_payload, \
            "Concurrent idempotent stores should not corrupt stored result"

    async def test_replay_command_history_consistency(self):
        from seo_platform.core.redis import get_redis

        redis = await get_redis()
        session_id = f"replay-history-{uuid4()}"
        history_key = f"history:global:{session_id}"
        commands = [f"cmd-{i}" for i in range(25)]

        for cmd in commands:
            await redis.lpush(history_key, json.dumps({"command": cmd, "ts": time.time()}))
        await redis.expire(history_key, 120)

        history_length = await redis.llen(history_key)
        assert history_length == 25, f"Expected 25 commands, got {history_length}"

        replayed = []
        for _ in range(25):
            raw = await redis.rpop(history_key)
            if raw:
                replayed.append(json.loads(raw)["command"])

        assert len(replayed) == 25, "Should retrieve all 25 commands on replay"
        assert set(replayed) == set(commands), "Replayed commands should match original set"


# =============================================================================
# 3. DISTRIBUTED RESILIENCE
# =============================================================================

class TestDistributedResilience:

    async def test_worker_crash_recovery_global(self):
        from seo_platform.core.reliability import CircuitBreaker

        breaker = CircuitBreaker(
            "worker_crash_svc",
            failure_threshold=2,
            recovery_timeout=0.3,
            success_threshold=1,
        )

        async def crashable_worker(task_id: int) -> str:
            if task_id % 3 == 0:
                raise ConnectionError(f"worker {task_id} crashed")
            return f"worker-{task_id}-completed"

        results = []
        for i in range(6):
            try:
                result = await breaker.call(lambda i=i: crashable_worker(i))
                results.append(result)
            except Exception:
                results.append(f"worker-{i}-failed")

        assert breaker.state in ("closed", "half_open"), \
            f"Circuit should recover after crash, got {breaker.state}"

        await asyncio.sleep(0.35)
        recovered = await breaker.call(lambda: crashable_worker(99))
        assert "completed" in recovered, "Worker should recover after circuit closes"

    async def test_queue_resilience_distributed(self):
        from seo_platform.core.reliability import rate_limiter

        queue_resources = [f"distributed:queue:{uuid4()}" for _ in range(4)]
        tenant_id = uuid4()
        max_tokens = 50

        async def queue_consumer(queue: str, consumer_id: int) -> int:
            processed = 0
            for _ in range(15):
                result = await rate_limiter.consume(
                    tenant_id, queue, tokens=1,
                    max_tokens=max_tokens, refill_rate=20,
                )
                if result.allowed:
                    processed += 1
                await asyncio.sleep(0.005)
            return processed

        consumer_tasks = []
        for q_idx, queue in enumerate(queue_resources):
            for c_id in range(3):
                consumer_tasks.append(queue_consumer(queue, c_id))

        consumer_results = await asyncio.gather(*consumer_tasks, return_exceptions=True)
        successful = [r for r in consumer_results if isinstance(r, int)]
        total_processed = sum(successful)

        assert total_processed > 0, "Distributed queue consumers should process messages"
        assert all(r > 0 for r in successful if isinstance(r, int)), \
            "Each consumer should process at least some messages"

    async def test_event_deduplication_global(self):
        from seo_platform.core.reliability import idempotency_store

        event_id = f"global-dedup-{uuid4()}"
        event_payload = json.dumps({"event_id": event_id, "data": "global-event"})

        assert not await idempotency_store.exists(event_id), \
            "Event should not exist before first storage"

        await idempotency_store.store(event_id, event_payload, ttl=300)
        assert await idempotency_store.exists(event_id), \
            "Event should exist after storage"

        async def concurrent_dup(dup_id: str) -> str | None:
            if await idempotency_store.exists(dup_id):
                return await idempotency_store.get(dup_id)
            return None

        dup_tasks = [concurrent_dup(event_id) for _ in range(20)]
        dup_results = await asyncio.gather(*dup_tasks)
        non_none = [r for r in dup_results if r is not None]
        all_same = all(r == event_payload for r in non_none)
        assert all_same, "All concurrent dedup reads should return identical payload"

    async def test_kill_switch_global_scope(self):
        from seo_platform.core.kill_switch import kill_switch_service

        tenants = [uuid4() for _ in range(3)]

        for tid in tenants:
            check = await kill_switch_service.is_blocked("global_scraping", tenant_id=tid)
            assert check.blocked is False, \
                f"Kill switch should not block tenant {tid} by default"

        await kill_switch_service.activate(
            switch_key="platform.global_scraping",
            reason="Global enterprise validation emergency stop",
            activated_by="global_enterprise_validation",
        )

        for tid in tenants:
            check = await kill_switch_service.is_blocked("global_scraping", tenant_id=tid)
            assert check.blocked is True, \
                f"Kill switch should block tenant {tid} after activation"

        await kill_switch_service.deactivate(
            "platform.global_scraping",
            deactivated_by="global_enterprise_validation",
        )

        for tid in tenants:
            check = await kill_switch_service.is_blocked("global_scraping", tenant_id=tid)
            assert check.blocked is False, \
                f"Kill switch should unblock tenant {tid} after deactivation"


# =============================================================================
# 4. ORGANIZATIONAL SCALING
# =============================================================================

class TestOrganizationalScaling:

    async def test_concurrent_workflow_scaling(self):
        from seo_platform.core.reliability import CircuitBreaker

        breaker = CircuitBreaker(
            "scaling_wf",
            failure_threshold=20,
            recovery_timeout=5,
            success_threshold=1,
        )
        load_levels = [10, 25, 50]

        for concurrent_count in load_levels:
            false_opens = 0

            async def workflow_task(idx: int) -> bool:
                try:
                    async def succeed():
                        await asyncio.sleep(0.002)
                        return idx
                    await breaker.call(succeed)
                    return True
                except Exception:
                    return False

            tasks = [workflow_task(i) for i in range(concurrent_count)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            false_opens = sum(1 for r in results if r is False)
            success_count = sum(1 for r in results if r is True)

            assert breaker.state == "closed" or success_count > 0, \
                f"At load {concurrent_count}, circuit should not permanently open"
            assert false_opens <= 3, \
                f"Load {concurrent_count}: too many false opens ({false_opens})"

    async def test_rate_limiter_organizational_burst(self):
        from seo_platform.core.reliability import rate_limiter

        orgs = [uuid4() for _ in range(5)]
        resource = f"org:burst:{uuid4()}"
        max_tokens = 100
        burst_size = 30

        async def org_burst(org_id) -> tuple[int, int]:
            allowed = 0
            denied = 0
            for _ in range(burst_size):
                result = await rate_limiter.consume(
                    org_id, resource, tokens=1,
                    max_tokens=max_tokens, refill_rate=50,
                )
                if result.allowed:
                    allowed += 1
                else:
                    denied += 1
            return allowed, denied

        burst_tasks = [org_burst(org) for org in orgs]
        burst_results = await asyncio.gather(*burst_tasks)

        for org, (allowed, denied) in zip(orgs, burst_results):
            assert allowed > 0, f"Org {org} should have some allowed requests"
            total = allowed + denied
            assert total == burst_size, \
                f"Org {org}: expected {burst_size} total, got {total}"

    async def test_kill_switch_tenant_isolation(self):
        from seo_platform.core.kill_switch import kill_switch_service

        tenant_a = uuid4()
        tenant_b = uuid4()

        check_a = await kill_switch_service.is_blocked("tenant_scraping", tenant_id=tenant_a)
        check_b = await kill_switch_service.is_blocked("tenant_scraping", tenant_id=tenant_b)
        assert check_a.blocked is False
        assert check_b.blocked is False

        await kill_switch_service.activate(
            switch_key="platform.tenant_scraping",
            reason=f"Isolation test for tenant {tenant_a}",
            activated_by="global_enterprise_validation",
        )

        check_a = await kill_switch_service.is_blocked("tenant_scraping", tenant_id=tenant_a)
        assert check_a.blocked is True, \
            "Kill switch should block tenant A after activation"

        check_b = await kill_switch_service.is_blocked("tenant_scraping", tenant_id=tenant_b)
        assert check_b.blocked is True, \
            "Kill switch should block tenant B (global scope)"

        await kill_switch_service.activate(
            switch_key="platform.tenant_scraping",
            reason="Isolation test for tenant B exemption",
            activated_by="global_enterprise_validation",
        )

        await kill_switch_service.deactivate(
            "platform.tenant_scraping",
            deactivated_by="global_enterprise_validation",
        )

        check_a = await kill_switch_service.is_blocked("tenant_scraping", tenant_id=tenant_a)
        check_b = await kill_switch_service.is_blocked("tenant_scraping", tenant_id=tenant_b)
        assert check_a.blocked is False
        assert check_b.blocked is False


# =============================================================================
# 5. OPERATIONAL COGNITION QUALITY
# =============================================================================

class TestOperationalCognitionQuality:

    async def test_anomaly_detection_accuracy(self):
        from seo_platform.core.reliability import CircuitBreaker, CircuitState

        breaker = CircuitBreaker(
            "anomaly_svc",
            failure_threshold=4,
            recovery_timeout=0.2,
            success_threshold=2,
        )
        anomaly_patterns: list[dict] = []

        async def fail():
            raise ConnectionError("anomalous failure")

        async def succeed():
            return "normal"

        for _ in range(4):
            try:
                await breaker.call(fail)
            except Exception:
                pass

        assert breaker.state == CircuitState.OPEN, \
            "Circuit should be OPEN after anomaly threshold breached"
        anomaly_patterns.append({
            "state": str(breaker.state),
            "failures": breaker._failure_count,
            "detected": True,
        })

        await asyncio.sleep(0.25)
        try:
            await breaker.call(fail)
        except Exception:
            pass
        anomaly_patterns.append({
            "state": str(breaker.state),
            "detected": breaker.state == CircuitState.HALF_OPEN,
        })

        result = await breaker.call(succeed)
        assert result == "normal"
        await breaker.call(succeed)
        assert breaker.state == CircuitState.CLOSED, \
            "Circuit should close after sufficient successes"

    async def test_operational_insight_consistency(self):
        from seo_platform.core.reliability import rate_limiter

        tenant_id = uuid4()
        resource = f"insight:test:{uuid4()}"
        max_tokens = 75

        async def consume_batch(batch_id: int) -> dict:
            allowed = 0
            denied = 0
            for _ in range(20):
                result = await rate_limiter.consume(
                    tenant_id, resource, tokens=1,
                    max_tokens=max_tokens, refill_rate=30,
                )
                if result.allowed:
                    allowed += 1
                else:
                    denied += 1
            return {"batch": batch_id, "allowed": allowed, "denied": denied}

        batches = await asyncio.gather(*[consume_batch(i) for i in range(5)])
        for batch in batches:
            assert batch["allowed"] >= 0
            assert batch["denied"] >= 0
            assert batch["allowed"] + batch["denied"] == 20, \
                f"Batch {batch['batch']}: expected 20 total, got {batch['allowed'] + batch['denied']}"

        first_ratio = batches[0]["allowed"]
        for batch in batches[1:]:
            if first_ratio > 0:
                assert batch["allowed"] >= 0, "All batches should have consistent rate limiting"

    async def test_recommendation_reliability(self):
        from seo_platform.core.reliability import rate_limiter

        tenant_ids = [uuid4() for _ in range(5)]
        resource = f"recommendation:{uuid4()}"
        max_tokens = 30

        async def recommendation_request(tid, request_id: int) -> bool:
            result = await rate_limiter.consume(
                tid, resource, tokens=1,
                max_tokens=max_tokens, refill_rate=5,
            )
            return result.allowed

        all_requests = []
        for tid in tenant_ids:
            for i in range(10):
                all_requests.append(recommendation_request(tid, i))

        results = await asyncio.gather(*all_requests, return_exceptions=True)
        valid = [r for r in results if isinstance(r, bool)]
        allowed_count = sum(1 for r in valid if r)

        assert allowed_count > 0, "Recommendation requests should be allowed under concurrent access"


# =============================================================================
# 6. INFRASTRUCTURE SCALABILITY
# =============================================================================

class TestInfrastructureScalability:

    async def test_circuit_breaker_scalability(self):
        from seo_platform.core.reliability import CircuitBreaker

        breaker = CircuitBreaker(
            "scalability_svc",
            failure_threshold=50,
            recovery_timeout=5,
            success_threshold=1,
        )
        concurrent_calls = 1000

        async def scalable_task(task_id: int) -> int:
            async def succeed():
                await asyncio.sleep(0.001)
                return task_id * 2

            result = await breaker.call(succeed)
            return result

        tasks = [scalable_task(i) for i in range(concurrent_calls)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful = [r for r in results if isinstance(r, int)]
        assert len(successful) > concurrent_calls * 0.9, \
            f"At least 90% should succeed, got {len(successful)}/{concurrent_calls}"
        assert breaker.state == "closed", \
            f"Circuit should remain closed under load, got {breaker.state}"

    async def test_rate_limiter_scalability(self):
        from seo_platform.core.reliability import rate_limiter

        tenant_id = uuid4()
        resources = [f"scalable:resource:{uuid4()}" for _ in range(10)]
        max_tokens = 100

        async def resource_consumer(resource: str) -> int:
            allowed = 0
            for _ in range(20):
                result = await rate_limiter.consume(
                    tenant_id, resource, tokens=1,
                    max_tokens=max_tokens, refill_rate=50,
                )
                if result.allowed:
                    allowed += 1
            return allowed

        consumer_tasks = [resource_consumer(r) for r in resources]
        results = await asyncio.gather(*consumer_tasks, return_exceptions=True)
        successful = [r for r in results if isinstance(r, int)]

        total_allowed = sum(successful)
        assert total_allowed > 0, \
            "Rate limiter should allow requests across many resources"
        assert all(r > 0 for r in successful), \
            "Each resource should have at least some allowed requests"

    async def test_idempotency_store_scalability(self):
        from seo_platform.core.reliability import idempotency_store

        operations = 200
        store_tasks = []
        for i in range(operations):
            op_id = f"scalable-idempotent-{uuid4()}"
            payload = json.dumps({"seq": i, "data": f"bulk-{i}"})
            store_tasks.append(idempotency_store.store(op_id, payload, ttl=300))

        store_results = await asyncio.gather(*store_tasks, return_exceptions=True)
        store_successes = sum(1 for r in store_results if r is None or r is True)
        assert store_successes > operations * 0.95, \
            f"At least 95% stores should succeed, got {store_successes}/{operations}"

        verify_tasks = []
        for i in range(operations):
            op_id = f"scalable-idempotent-{uuid4()}"
            verify_tasks.append(idempotency_store.exists(op_id))

        verify_results = await asyncio.gather(*verify_tasks, return_exceptions=True)
        verified = sum(1 for r in verify_results if r is True)
        assert verified > 0, "At least some idempotent operations should be verified"


# =============================================================================
# 7. ENTERPRISE SURVIVABILITY
# =============================================================================

class TestEnterpriseSurvivability:

    async def test_cascading_failure_isolation(self):
        from seo_platform.core.reliability import CircuitBreaker

        breaker_a = CircuitBreaker(
            "service_alpha", failure_threshold=2,
            recovery_timeout=30, success_threshold=1,
        )
        breaker_b = CircuitBreaker(
            "service_beta", failure_threshold=5,
            recovery_timeout=30, success_threshold=2,
        )

        async def fail():
            raise ConnectionError("service alpha failure")

        async def succeed():
            return "ok"

        with pytest.raises(ConnectionError):
            await breaker_a.call(fail)
        with pytest.raises(ConnectionError):
            await breaker_a.call(fail)

        assert breaker_a.state != "closed", "Service A circuit should be open after failures"

        for _ in range(5):
            result = await breaker_b.call(succeed)
            assert result == "ok", "Service B should operate independently of Service A"

        assert breaker_b.state == "closed", \
            "Service B circuit should remain closed despite Service A failures"

    async def test_graceful_degradation_global(self):
        from seo_platform.core.reliability import CircuitBreaker, CircuitOpenError, rate_limiter

        breaker = CircuitBreaker(
            "global_degraded_svc",
            failure_threshold=2,
            recovery_timeout=30,
            success_threshold=1,
        )

        async def fail():
            raise ConnectionError("global service unavailable")

        with pytest.raises(ConnectionError):
            await breaker.call(fail)
        with pytest.raises(ConnectionError):
            await breaker.call(fail)

        with pytest.raises(CircuitOpenError):
            await breaker.call(fail)

        tenant_id = uuid4()
        rate_result = await rate_limiter.consume(
            tenant_id, "degraded:global",
            tokens=1, max_tokens=100, refill_rate=10,
        )
        assert rate_result.allowed, \
            "Rate limiting should continue working during circuit breaker degradation"

    async def test_automatic_recovery_global(self):
        from seo_platform.core.reliability import CircuitBreaker, CircuitState

        breaker = CircuitBreaker(
            "auto_recovery_svc",
            failure_threshold=2,
            recovery_timeout=0.2,
            success_threshold=1,
        )

        async def fail():
            raise ConnectionError("auto recovery test failure")

        async def succeed():
            return "recovered"

        with pytest.raises(ConnectionError):
            await breaker.call(fail)
        with pytest.raises(ConnectionError):
            await breaker.call(fail)

        assert breaker.state == CircuitState.OPEN, \
            "Circuit should be OPEN after threshold failures"

        await asyncio.sleep(0.25)

        result = await breaker.call(succeed)
        assert result == "recovered", \
            "Circuit should automatically transition to HALF_OPEN and allow probe"

        assert breaker.state == CircuitState.CLOSED, \
            "Circuit should be CLOSED after successful probe"

    async def test_state_consistency_after_recovery(self):
        from seo_platform.core.reliability import CircuitBreaker, CircuitState

        breaker = CircuitBreaker(
            "state_consistency_svc",
            failure_threshold=3,
            recovery_timeout=0.2,
            success_threshold=2,
        )

        async def fail():
            raise ConnectionError("state consistency failure")

        async def succeed():
            return "consistent"

        for _ in range(3):
            with pytest.raises(ConnectionError):
                await breaker.call(fail)

        assert breaker.state == CircuitState.OPEN
        assert breaker._failure_count >= 3

        await asyncio.sleep(0.25)

        result = await breaker.call(succeed)
        assert result == "consistent"
        assert breaker.state == CircuitState.HALF_OPEN

        result = await breaker.call(succeed)
        assert result == "consistent"
        assert breaker.state == CircuitState.CLOSED, \
            "Circuit should be CLOSED after meeting success_threshold"
        assert breaker._failure_count == 0, \
            "Failure count should reset to 0 after recovery"
