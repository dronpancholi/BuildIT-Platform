"""
Phase 14.3B Performance Benchmark
Minimal setup - benchmarks core planning services.
"""
import asyncio, time, uuid, statistics
from seo_platform.core.database import get_tenant_session, get_session
from seo_platform.services.planning_engine import planning_engine_service
from seo_platform.services.plan_simulator import plan_simulator_service
from seo_platform.services.plan_optimizer import plan_optimizer_service
from seo_platform.services.forecast_engine import forecast_engine_service
from seo_platform.models.tenant import Tenant, TenantPlan
from seo_platform.models.goal import GoalDefinition, GoalExecution, GoalState

TENANT_ID = uuid.uuid4()
PLAN_ID = None

async def seed():
    async with get_session() as s:
        t = Tenant(id=TENANT_ID, slug=f"bench-{uuid.uuid4().hex[:8]}", name="Bench Tenant", plan=TenantPlan.ENTERPRISE)
        s.add(t)
        await s.flush()

    async with get_tenant_session(TENANT_ID) as s:
        gd = GoalDefinition(tenant_id=TENANT_ID, name="bench-goal", description="perf test", target={}, priority=0)
        s.add(gd)
        await s.flush()
        ge = GoalExecution(tenant_id=TENANT_ID, definition_id=gd.id, state=GoalState.RUNNING)
        s.add(ge)
        await s.commit()
        return ge.id

async def cleanup():
    from sqlalchemy import text
    async with get_session() as s:
        await s.execute(text("DELETE FROM plan_forecasts WHERE tenant_id = :tid"), {"tid": TENANT_ID})
        await s.execute(text("DELETE FROM node_dependencies WHERE tenant_id = :tid"), {"tid": TENANT_ID})
        await s.execute(text("DELETE FROM plan_nodes WHERE tenant_id = :tid"), {"tid": TENANT_ID})
        await s.execute(text("DELETE FROM execution_plans WHERE tenant_id = :tid"), {"tid": TENANT_ID})
        await s.execute(text("DELETE FROM goal_executions WHERE tenant_id = :tid"), {"tid": TENANT_ID})
        await s.execute(text("DELETE FROM goal_definitions WHERE tenant_id = :tid"), {"tid": TENANT_ID})
        await s.execute(text("DELETE FROM tenants WHERE id = :tid"), {"tid": TENANT_ID})
        await s.commit()

async def bench(name: str, fn, n: int = 15):
    latencies = []
    for i in range(n):
        start = time.perf_counter()
        try:
            await fn(i)
        except Exception as e:
            print(f"  {name}[{i}]: {type(e).__name__}: {e}")
        elapsed = (time.perf_counter() - start) * 1000
        latencies.append(elapsed)
    latencies.sort()
    p50 = statistics.median(latencies)
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]
    print(f"  {name:40s}  p50={p50:8.2f}ms  p95={p95:8.2f}ms  p99={p99:8.2f}ms  (n={n})")
    return {"name": name, "p50": p50, "p95": p95, "p99": p99, "n": n}

async def main():
    global PLAN_ID
    print("=== Phase 14.3B Performance Benchmark ===\n")
    print("Seeding data...")
    ge_id = await seed()
    print("  Done\n")
    results = []

    # 1. Generate plan
    async def gen_plan(i):
        global PLAN_ID
        p = await planning_engine_service.generate_plan(TENANT_ID, ge_id)
        PLAN_ID = p.id

    r = await bench("POST /plans/generate", gen_plan, n=10)
    results.append(r)

    # 2. Simulate
    async def sim_plan(i):
        await plan_simulator_service.simulate_plan(TENANT_ID, PLAN_ID)

    r = await bench("POST /plans/{id}/simulate", sim_plan, n=10)
    results.append(r)

    # 3. Optimize
    async def opt_plan(i):
        await plan_optimizer_service.optimize_plan(TENANT_ID, PLAN_ID)

    r = await bench("POST /plans/{id}/optimize", opt_plan, n=10)
    results.append(r)

    # 4. Get plan
    async def get_plan(i):
        async with get_tenant_session(TENANT_ID) as s:
            from seo_platform.models.planning import ExecutionPlan
            await s.get(ExecutionPlan, PLAN_ID)

    r = await bench("GET /plans/{id}", get_plan, n=20)
    results.append(r)

    # 5. Forecast
    async def forecast_plan(i):
        await forecast_engine_service.generate_forecast(TENANT_ID, PLAN_ID)

    r = await bench("GET /plans/{id}/forecast", forecast_plan, n=10)
    results.append(r)

    # 6. History
    async def history_plan(i):
        async with get_tenant_session(TENANT_ID) as s:
            from seo_platform.models.approval import ApprovalRequestModel
            from sqlalchemy import select
            r = await s.execute(select(ApprovalRequestModel).where(ApprovalRequestModel.tenant_id == TENANT_ID).limit(10))
            r.scalars().all()

    r = await bench("GET /plans/{id}/history", history_plan, n=20)
    results.append(r)

    print("\n=== Results vs Targets ===")
    targets = {"p50": 100.0, "p95": 250.0, "p99": 500.0}
    all_pass = True
    for r in results:
        statuses = []
        for perc in ["p50", "p95", "p99"]:
            actual = r[perc]
            target = targets[perc]
            passed = actual <= target
            statuses.append(f"{perc}={actual:.1f}ms {'✅' if passed else '❌'}")
            if not passed:
                all_pass = False
        print(f"  {r['name']:40s} {' | '.join(statuses)}")

    if all_pass:
        print("\n✅ ALL PERFORMANCE TARGETS MET")
    else:
        print("\n❌ SOME TARGETS NOT MET")

    await cleanup()
    print("Cleanup done.")

asyncio.run(main())
