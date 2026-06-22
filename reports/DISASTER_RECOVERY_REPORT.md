# Disaster Recovery Report — Phase 2.1

**Phase:** 2.1 — Production Operations & Observability
**Date:** 2026-06-05
**Verdict:** ❌ **CRITICAL — 0 of 6 scenarios have a tested recovery procedure; "global DR" endpoint returns hardcoded mocks.**

> "What happens if PostgreSQL dies?"
>
> "We lose everything. We have no backup. We have no replica. We have no failover."

---

## 1. Executive Summary

The platform has a single point of failure for every critical component. There is:

- No PostgreSQL replica (read replica, hot standby, or streaming replication)
- No Redis replica (master-replica, Sentinel, or Cluster)
- No Kafka multi-broker (single broker, replication factor 1)
- No MinIO replication (single instance, no `mc mirror` to secondary)
- No Temporal cluster (single auto-setup instance)
- No Qdrant replica
- No multi-region deployment (the `global-infra` endpoint returns 4 hardcoded region deployments that do not exist)

The platform's disaster recovery posture is: **restart and pray**.

There IS a `/api/v1/global-infra/disaster-recovery` endpoint. It returns:

```json
[
  {"region": "us-east-1", "dr_status": "configured", "rpo_seconds": 60, "rto_seconds": 300, "last_dr_test": "2026-04-15T14:00:00Z", "dr_readiness": 100},
  {"region": "us-west-2", "dr_status": "configured", "rpo_seconds": 60, "rto_seconds": 300, "last_dr_test": "2026-04-10T10:00:00Z", "dr_readiness": 100},
  {"region": "eu-west-1",    "dr_status": "configured", "rpo_seconds": 120, "rto_seconds": 600, "last_dr_test": "2026-03-20T09:00:00Z", "dr_readiness": 100},
  {"region": "eu-central-1",  "dr_status": "degraded",   "rpo_seconds": 120, "rto_seconds": 600, "last_dr_test": "2026-03-20T09:00:00Z", "dr_readiness": 60}
]
```

This data is **synthesized** by `services/global_infrastructure.py:get_all_region_deployments()`. It returns hardcoded `RegionDeployment` instances. The `last_dr_test` dates are static. The `rpo_seconds: 60` claim is false — there is no replication, no offsite backup, no failover to another region.

A new engineer looking at this endpoint would believe the platform has multi-region DR with 60-second RPO. It does not.

---

## 2. Scenario-by-Scenario Analysis

### Scenario A: PostgreSQL unavailable

**Trigger:** `brew services stop postgresql@16` (host) or filesystem corruption.

**Detection time:** 0–60 seconds (next health check from external monitor). The internal `/api/v1/health` would return `postgresql: unhealthy` on its next call, but **no alert fires** (Phase 2.1 Alerting Report).

**User-visible impact:**
- All API requests that touch the DB fail with 500.
- Frontend shows "Internal Server Error" on every page.
- Workflows that try to schedule themselves fail.
- Workflows already running fail their next activity that needs DB.
- Temporal continues to operate (it has its own DB session) but the application layer is dead.

**Data loss risk:** None if the data is intact on disk. Total if disk is corrupted.

**Recovery process:**
1. Restart PostgreSQL: `brew services start postgresql@16` (or `pg_ctl start`).
2. Verify: `psql -h localhost -U seo_platform -d seo_platform -c 'SELECT 1'`.
3. Restart backend (to clear any bad connection pool state).
4. Restart all 6 worker processes.
5. Total manual effort: ~5 minutes if everything goes right.

**Recovery time:** 5–10 minutes (RTO), 0 data loss (RPO=0) if the DB is intact.

**Required manual intervention:** Yes. There is no automatic restart of backend/workers.

**Tested?** No. The `recover-postgres` endpoint returns 500 (verified in Phase 2.1 Incident Response Audit).

---

### Scenario B: Temporal unavailable

**Trigger:** `docker stop seo-temporal` (network, OOM, crash).

**Detection time:** 0–60 seconds. `/api/v1/health` returns `temporal: degraded`.

**User-visible impact:**
- Cannot start new workflows (any operation that calls `temporal.start_workflow` fails).
- Already-running workflows continue (they're already in Temporal's memory or history).
- The "operational loop" (autonomous discovery, health scans) stops because it uses Temporal.
- The 6 worker processes become pollerless — they connect to Temporal on startup, but new workflow starts are blocked.

**Data loss risk:** Workflows in-flight are preserved by Temporal's history. No application data loss. **But** the operational loop and any new campaign launches are dead.

**Recovery process:**
1. `docker start seo-temporal` (the container is configured with `restart: unless-stopped`).
2. The `seo-platform-dev` namespace is auto-recreated by `ensure_namespace()` in the backend (Phase 2.0.1 fix).
3. Workers should reconnect (they retry on each poll).
4. Manual verification: `curl http://localhost:8000/api/v1/health` should show `temporal: healthy`.
5. If workers don't reconnect: kill + restart all 6.

**Recovery time:** 2–5 minutes if auto-restart works; 5–15 minutes if not.

**Required manual intervention:** Maybe. Depends on whether the container is configured to auto-restart. The current container was created with `--restart unless-stopped` — so if the host stays up, restart is automatic. If the host dies too, full manual recovery.

**Tested?** Yes — verified in Phase 2.0.1 that the workflow executes end-to-end after Temporal restart. The `recover-temporal` endpoint works (verified in Phase 2.1 Incident Response Audit).

---

### Scenario C: Redis unavailable

**Trigger:** `docker stop seo-redis` (network, OOM, crash).

**Detection time:** 0–60 seconds.

**User-visible impact:**
- Rate limiter stops working (it uses Redis for in-memory token bucket per process, so it might actually still work briefly).
- Kill switches reset to "off" (Redis stores them). If a kill switch was active, it will silently deactivate. This could be dangerous.
- Idempotency store loses state. In-flight operations may double-execute.
- Real-time SSE state lost. Clients may need to reconnect.
- Caching (if any) loses warm data.

**Data loss risk:** Operational state only (kill switches, idempotency keys). No application data.

**Recovery process:**
1. `docker start seo-redis`. Container has `restart: unless-stopped`.
2. Run `POST /api/v1/distributed/recover-redis` to:
   - Restore kill switches (from code defaults? From a stored snapshot?)
   - Validate idempotency store integrity
   - Clear stale connections
3. Verify health endpoint shows `redis: healthy`.

**Recovery time:** 1–3 minutes if auto-restart works.

**Required manual intervention:** Minimal if `recover-redis` works (verified). But there's no guarantee the kill switch state is correctly restored — it depends on whether `recover_redis_state()` reads from a persistence layer (the code shows it does, but no test exists).

**Tested?** No end-to-end kill-switch-restoration test.

---

### Scenario D: Kafka unavailable

**Trigger:** `docker stop seo-kafka` (network, OOM, crash).

**Detection time:** 0–60 seconds.

**User-visible impact:**
- The 4 worker Kafka consumers (`EventConsumer` in `worker.py`) lose connection.
- Events published to Kafka topics are NOT consumed: `approval_request_decided`, `workflow_campaign_started`, `workflow_campaign_completed`, `seo_keyword_research_completed`.
- The `/api/v1/incident/diagnostics` `event_bus` component will degrade.
- The system can still produce events, but no one consumes them. The topics fill up (7-day retention = ~3 days of buffer).

**Data loss risk:** Events older than 7 days in Kafka that weren't consumed. For the platform's typical event rates, this is effectively zero.

**Recovery process:**
1. `docker start seo-kafka`. Container has `restart: unless-stopped`. Zookeeper must also be up.
2. Workers reconnect to Kafka (they have a consumer group, the broker reassigns partitions).
3. Run `POST /api/v1/distributed/recover-kafka?consumer_group=workflow-workers` to validate partition health and rebalance.
4. Verify event flow by publishing a test event and checking consumption.

**Recovery time:** 2–5 minutes.

**Required manual intervention:** Maybe. Workers reconnect automatically; `recover-kafka` is optional but recommended.

**Tested?** `recover-kafka` was not tested in this audit (it requires a `consumer_group` parameter and may not work as advertised).

---

### Scenario E: MinIO unavailable

**Trigger:** `docker stop seo-minio` (network, OOM, disk full).

**Detection time:** 0–60 seconds (next /health check).

**User-visible impact:**
- All S3 API calls (upload, download, presigned URL) fail.
- Operations that depend on storage (report generation, asset upload) fail.
- **But** the storage adapter has bounded timeouts (2s connect, 5s read) and a circuit breaker (Phase 2.0.1). So requests fail fast (not hang).
- After 5 consecutive failures, the circuit opens for 30 seconds, then probes.

**Data loss risk:** None on a transient outage. Total if MinIO disk is lost and there's no backup (Phase 2.1 Backup Report confirms no backup).

**Recovery process:**
1. `docker start seo-minio`. Container has `restart: unless-stopped`.
2. Storage circuit closes on next successful call.
3. Backend automatically retries.

**Recovery time:** 1–2 minutes.

**Required manual intervention:** None. The bounded timeouts + circuit breaker are correctly implemented (Phase 2.0.1 P2-2).

**Tested?** Yes — Phase 2.0.1 verified that the MinIO adapter has proper timeouts and a round-trip upload succeeded.

---

### Scenario F: Entire server unavailable

**Trigger:** Host reboot, hardware failure, datacenter outage.

**Detection time:** 0–5 minutes (external monitor like Pingdom).

**Impact:** Everything. Backend dead, all workers dead, PostgreSQL dead, all docker containers dead.

**Recovery process (assuming host is recoverable):**
1. Host boots up.
2. PostgreSQL service auto-starts (homebrew's `brew services` has a launchd plist that auto-starts on boot).
3. **Backend does NOT auto-start.** No launchd plist. No systemd. No pm2. No `docker-compose up` is run.
4. **Workers do NOT auto-start.** They are `nohup` background processes that die with the parent shell.
5. **Docker containers auto-restart** if the docker daemon is configured to (depends on host). The `restart: unless-stopped` policy in compose should bring them back.
6. Operator logs in, manually starts backend (`uvicorn ...`), then 6 workers.

**Recovery time:**
- 5–10 minutes if operator is awake and follows the (unwritten) restart procedure.
- Hours to days if no one is available or if the procedure is unknown.

**Required manual intervention:** Critical. Without the manual restart, the platform is half-up (containers up, app dead).

**Tested?** No reboot test has ever been performed.

---

## 3. The "Global DR" Endpoint — Fabricated Data

`/api/v1/global-infra/disaster-recovery` claims:

```json
{
  "region": "us-east-1",
  "dr_status": "configured",
  "rpo_seconds": 60,
  "rto_seconds": 300,
  "last_dr_test": "2026-04-15T14:00:00Z",
  "dr_readiness": 100
}
```

This is **hardcoded** in `services/global_infrastructure.py:65-78`:

```python
RegionDeployment(
    region="us-east-1",
    status="active",
    service_instances=[
        {"name": "api", "version": "v2.0.3", "healthy": True},
        ...
    ],
    health_score=98.5,
    latency_ms=12.0,
    ...
)
```

There is no `us-east-1`. There is no `v2.0.3`. The `last_dr_test` of `2026-04-15T14:00:00Z` is a static string. The `dr_readiness: 100` is a constant.

A new engineer looking at the response would believe:
- The platform runs in 4 regions (it runs in 1)
- The platform has failover to a backup region (it doesn't)
- The last DR test was successful (there has never been a test)

This is **dangerous misinformation in production** — the data is presented as authoritative but is fabricated.

---

## 4. Summary Table

| Scenario | RTO (estimate) | RPO (estimate) | Tested? | Required manual intervention | Risk |
|---|---|---|---|---|---|
| A: PostgreSQL down | 5–10 min | 0 (if disk intact) | ❌ | Yes | High (single point of failure, no replica) |
| B: Temporal down | 2–5 min | 0 | ✅ Partial (Phase 2.0.1) | Maybe | Medium (namespace auto-provision works) |
| C: Redis down | 1–3 min | Some operational state lost | ❌ | Minimal | Medium (kill switch state may not restore) |
| D: Kafka down | 2–5 min | Up to 7 days of events | ❌ | Maybe | Low (events are regenerable from workflow history) |
| E: MinIO down | 1–2 min | Total if disk lost (no backup) | ✅ Partial (Phase 2.0.1) | None | Low for transient, Critical for disk loss |
| F: Entire server | 5–10 min (if operator) | All non-git state | ❌ | Critical | High (no process supervisor) |

---

## 5. Worst-Case Estimate

If a single disk failure occurs on the host (the only place where data is stored):
- 36 MB of application data: **LOST**
- 9.6 MB of Temporal history: **LOST**
- 14.2 MB of Redis state: **LOST**
- 364 K of MinIO assets: **LOST**
- 724 K of Kafka events: **LOST**
- 3.2 MB of Qdrant vectors: **LOST**
- 78 MB of Prometheus TSDB: **LOST**

**No part of the platform is recoverable** because there is no backup, no replica, no offsite copy.

The only recoverable artifacts are:
- Git-tracked code (frontend, backend, migrations, infrastructure)
- Container images (re-pullable from Docker Hub)
- Configuration templates (`.env.example`)

Time to rebuild from scratch: 2–5 days of engineering (assuming `.env` and `DEPLOYMENT_RUNBOOK.md` are intact).

---

## 6. Score

| Category | Weight | Score | Notes |
|---|---|---|---|
| Single-component recovery | 25% | 50/100 | MinIO works, Temporal works, but Postgres/Redis/Kafka have unverified recovery |
| Multi-component recovery | 20% | 20/100 | No replicas, no failover |
| Full-server recovery | 20% | 0/100 | No process supervisor; manual restart required for backend+workers |
| Backup-and-restore | 20% | 5/100 | Script exists, not run, not verified |
| DR drill / game day | 10% | 0/100 | Never performed |
| DR documentation accuracy | 5% | 0/100 | `global-infra` returns hardcoded false data |

**Overall: 18/100** — Far below "operationally acceptable." The platform cannot survive a real disaster.

---

## 7. Findings

| ID | Finding | Severity |
|---|---|---|
| DR-001 | No PostgreSQL replica or streaming replication | **P0** |
| DR-002 | No Redis replica or Sentinel | **P0** |
| DR-003 | No Kafka multi-broker (replication factor 1) | **P0** |
| DR-004 | No MinIO replication or erasure coding | **P0** |
| DR-005 | No process supervisor — backend/workers don't restart on host reboot | **P0** |
| DR-006 | `/api/v1/global-infra/disaster-recovery` returns hardcoded fake data | **P0** (misinformation) |
| DR-007 | No off-host backup destination | **P0** |
| DR-008 | `recover-postgres` endpoint returns 500 | **P0** |
| DR-009 | Kill switch state may not restore on Redis recovery | **P1** |
| DR-010 | No DR drill / chaos game day ever performed | **P1** |
| DR-011 | RTO for "entire server" is 5–10 min ONLY if operator is awake and knows the procedure | **P0** |

---

**Status:** ❌ CRITICAL. A single disk failure or host crash would result in total data loss and a 1-7 day rebuild. The "DR endpoints" that look reassuring are returning fabricated data.
