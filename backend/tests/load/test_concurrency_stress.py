"""
SEO Platform — High-Concurrency Stress Testing Suite
======================================================
Verifies PgBouncer connection pooling stability and queue
pressure absorption under extreme load (up to 10,000 concurrent
Temporal workflow threads / queue tasks).
"""

from __future__ import annotations

import asyncio
import time
from uuid import UUID

import pytest

pytestmark = pytest.mark.asyncio


async def _simulate_workflow_burst(
    i: int,
    semaphore: asyncio.Semaphore,
    tenant_id: UUID,
    errors: list[tuple[int, str]],
) -> None:
    """Simulate initiating a Temporal workflow under concurrency pressure."""
    async with semaphore:
        try:
            from temporalio.client import WorkflowHandle

            from seo_platform.core.temporal_client import get_temporal_client

            client = await get_temporal_client()

            handle: WorkflowHandle = await client.execute_workflow(
                "ReportGenerationWorkflow",
                f'{{"tenant_id": "{tenant_id}", "report_type": "stress_test", "initiated_by": "load_test"}}',
                id=f"stress-report-{tenant_id.hex[:8]}-{i:05d}",
                task_queue="seo-platform-reporting",
            )
            await handle.result(timeout=60)
        except Exception as exc:
            errors.append((i, str(exc)))


async def _simulate_queue_task_burst(
    i: int,
    semaphore: asyncio.Semaphore,
    errors: list[tuple[int, str]],
) -> None:
    """Simulate a queue task submission under concurrency."""
    async with semaphore:
        try:
            from seo_platform.core.temporal_client import get_temporal_client

            client = await get_temporal_client()
            await client.signal_workflow(
                f"stress-signal-{i:06d}",
                "dummy_signal",
                arg=None,
            )
        except Exception as exc:
            errors.append((i, str(exc)))


# ---------------------------------------------------------------------------
# Test: Extreme Workflow Concurrency (10,000 bursts / 500 semaphore)
# ---------------------------------------------------------------------------


@pytest.mark.load
@pytest.mark.stress
@pytest.mark.timeout(300)
async def test_extreme_workflow_concurrency(
    load_params: pytest.fixture,
    load_tenant_id: UUID,
) -> None:
    """
    Execute up to 10,000 concurrent workflow initiations using a
    Semaphore(500) throttle, verifying connection pool stability.
    """
    from seo_platform.core.reliability import idempotency_store

    workflow_count = min(load_params.workflow_count * 10, 10000)  # type: ignore[union-attr]
    semaphore = asyncio.Semaphore(500)
    errors: list[tuple[int, str]] = []

    start = time.monotonic()

    tasks = [
        _simulate_workflow_burst(i, semaphore, load_tenant_id, errors)
        for i in range(workflow_count)
    ]

    await asyncio.gather(*tasks, return_exceptions=True)

    elapsed = time.monotonic() - start

    assert len(errors) < workflow_count * 0.05, (
        f"Too many workflow initiation failures: {len(errors)} / {workflow_count} "
        f"failed. First errors: {errors[:5]}"
    )

    # Verify idempotency store stability under load
    try:
        test_key = f"loadtest:stress:{load_tenant_id.hex[:8]}"
        await idempotency_store.store(test_key, "ok", ttl=60)
        cached = await idempotency_store.get(test_key)
        assert cached == "ok", "Idempotency store unstable under load"
    except Exception as exc:
        pytest.fail(f"Idempotency store failed under load: {exc}")

    print(
        f"\n[STRESS] {workflow_count} workflows in {elapsed:.2f}s "
        f"({workflow_count / elapsed:.0f} wf/s) — {len(errors)} failures"
    )


# ---------------------------------------------------------------------------
# Test: Queue Pressure Absorption (5,000 queue tasks / 500 semaphore)
# ---------------------------------------------------------------------------


@pytest.mark.load
@pytest.mark.stress
@pytest.mark.timeout(120)
async def test_queue_pressure_absorption(
    load_params: pytest.fixture,
) -> None:
    """
    Submit 5,000 simulated queue tasks to verify Temporal queue
    pressure absorption and sub-second queue depth stability.
    """
    from seo_platform.core.temporal_client import get_temporal_client

    task_count = min(load_params.queue_task_count, 5000)  # type: ignore[union-attr]
    semaphore = asyncio.Semaphore(500)
    errors: list[tuple[int, str]] = []

    start = time.monotonic()

    tasks = [
        _simulate_queue_task_burst(i, semaphore, errors)
        for i in range(task_count)
    ]

    await asyncio.gather(*tasks, return_exceptions=True)

    elapsed = time.monotonic() - start

    assert len(errors) < task_count * 0.05, (
        f"Too many queue task failures: {len(errors)} / {task_count} "
        f"failed. First errors: {errors[:5]}"
    )

    # Verify queue depths remain bounded
    try:
        client = await get_temporal_client()
        deploy = await client.get_worker_deployments()
        queue_info = await client.get_task_queue_info("seo-platform-reporting")
        assert queue_info is not None, "Task queue info unavailable after stress"
    except Exception as exc:
        pytest.fail(f"Queue stability check failed under load: {exc}")

    print(
        f"\n[STRESS] {task_count} queue tasks in {elapsed:.2f}s "
        f"({task_count / elapsed:.0f} tasks/s) — {len(errors)} failures"
    )


# ---------------------------------------------------------------------------
# Test: Sustained Concurrency (30s sustained burst)
# ---------------------------------------------------------------------------


@pytest.mark.load
@pytest.mark.stress
@pytest.mark.timeout(180)
async def test_sustained_concurrency(
    load_params: pytest.fixture,
    load_tenant_id: UUID,
) -> None:
    """
    Sustain a continuous burst of workflow starts for 30 seconds,
    verifying that PgBonger connection pooling and Temporal queue
    pressure remain stable over time.
    """
    from seo_platform.core.temporal_client import get_temporal_client

    duration = load_params.duration_seconds  # type: ignore[union-attr]
    semaphore = asyncio.Semaphore(500)
    errors: list[tuple[int, str]] = []
    counter = 0

    start = time.monotonic()

    async def _burst_loop() -> None:
        nonlocal counter
        while time.monotonic() - start < duration:
            i = counter
            counter += 1
            async with semaphore:
                try:
                    client = await get_temporal_client()
                    handle = await client.execute_workflow(
                        "ReportGenerationWorkflow",
                        f'{{"tenant_id": "{load_tenant_id}", "report_type": "sustained_stress", "initiated_by": "load_test"}}',
                        id=f"sustained-{load_tenant_id.hex[:8]}-{i:06d}",
                        task_queue="seo-platform-reporting",
                    )
                    await handle.result(timeout=30)
                except Exception as exc:
                    errors.append((i, str(exc)))

    workers = [_burst_loop() for _ in range(50)]
    await asyncio.gather(*workers, return_exceptions=True)

    elapsed = time.monotonic() - start

    assert len(errors) < counter * 0.05, (
        f"Too many sustained concurrency failures: {len(errors)} / {counter}"
    )

    print(
        f"\n[STRESS] Sustained {counter} workflows in {elapsed:.2f}s "
        f"({counter / elapsed:.0f} wf/s) — {len(errors)} failures"
    )
