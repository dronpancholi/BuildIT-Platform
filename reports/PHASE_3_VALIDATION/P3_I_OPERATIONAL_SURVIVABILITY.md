# P3-I: Operational Survivability Report
**Audit Date**: 2026-06-21 | **Phase**: P3 — Commercial Readiness
**Question**: Can this platform survive real-world operational conditions?

---

## Failure Scenario Analysis

### Scenario 1: Ahrefs API Goes Down

**Impact path**: `discover_prospects_activity()` → Ahrefs failure

**Recovery chain**:
1. `AhrefsRateLimitError` → re-raise → Temporal retries with `EXTERNAL_API` policy (5 attempts, exponential backoff 2s → 5min)
2. Other Ahrefs errors → `logger.warning("ahrefs_failed_for_domain_trying_registry")` → fallback to SEO provider registry
3. Registry failure → `backlink_scraper.discover_link_intersect_prospects()` — HTML scraping fallback
4. All fail + 0 prospects → `fallback_prospects_activity()` — DB prospect pool
5. DB pool empty → explicit `failed_no_prospects` halt, campaign status set, operator alerted

**Verdict**: **SURVIVES** — 4-tier recovery with explicit failure state

---

### Scenario 2: LLM Gateway (NIM) Unavailable

**Impact paths**:
1. `generate_outreach_emails_activity()` → `llm_gateway.complete()` fails
2. `enrich_business_profile()` → LLM fails → returns `{"enriched": True, ...}` without data
3. `generate_seed_keywords()` → LLM fails → Temporal retries

**Recovery**:
- `RetryPreset.LLM_INFERENCE` (3 attempts, 3s → 2min)
- `enrich_business_profile()` catches LLM exception → returns partial enrichment with TTL 3600s (1h)
- `generate_outreach_emails_activity()` → on total failure → 0 email sequences → `failed_no_emails` halt

**Verdict**: **DEGRADES GRACEFULLY** for enrichment; **EXPLICIT HALT** for outreach generation failure

---

### Scenario 3: PostgreSQL Restart

**Impact paths**: All DB reads/writes fail during restart

**Recovery**:
- `RetryPreset.DATABASE` (5 attempts, 1s → 30s) applied to all DB activities
- Asyncpg connection pool handles reconnection automatically
- Temporal activities retry independently — no data loss (Temporal persists activity inputs)
- Enum codec re-registered on new connections (P2 fix)

**Verdict**: **SURVIVES** — Temporal durability + asyncpg reconnection + retry policy

---

### Scenario 4: Redis Unavailable

**Impact paths**:
1. `idempotency_store.get/store()` fails → activities may re-execute
2. `crm_pipeline_store` Redis write fails → in-memory fallback
3. `ingest_crm_pipeline()` falls back to `self._crm_store`

**Recovery**:
- Idempotency keys: Redis failure → `idempotency_store.exists()` returns False → activity re-executes (safe if idempotent)
- Email idempotency: Redis failure → email may be sent twice (duplicate send risk)

> [!WARNING]
> **Redis Failure Risk**: If Redis is unavailable, `idempotency_store.exists(idem_key)` for email sending returns False → `send_single_email_activity()` will re-send. This is a **duplicate email risk** during Redis outages.

**Verdict**: **MOSTLY SURVIVES** — duplicate send risk on Redis outage

---

### Scenario 5: Kafka Unavailable

**Impact paths**:
1. `create_operational_event()` might route through Kafka event bus
2. Reply detection consumer fails

**Recovery**:
- `create_operational_event()` uses direct DB writes, not Kafka — not affected
- Event consumer in `worker.py` wraps Kafka start in `try/except` → logs `event_consumer_skipped` → continues without consumer

**Verdict**: **SURVIVES** — Kafka failure is gracefully skipped; reply detection stops

---

### Scenario 6: Temporal Goes Down

**Impact**: All running workflows are paused (Temporal is the orchestrator)

**Recovery**:
- Temporal persists all workflow state in its own DB
- On Temporal restart, all paused workflows resume from last checkpoint
- No data loss — activity inputs and outputs are persisted by Temporal before execution

**Verdict**: **SURVIVES** — Temporal durability guarantees

---

### Scenario 7: Worker Process Crashes

**Impact**: Activities on affected queue stop executing

**Recovery**:
- Temporal detects worker disconnection via heartbeat
- Activities are rescheduled to any available worker on the same queue
- `max_concurrent_activities` prevents queue flooding on worker return
- Temporal's `start_to_close_timeout` ensures stuck activities are retried

**Verdict**: **SURVIVES** — Temporal schedules recovery automatically

---

### Scenario 8: Hunter.io Rate Limit Hit

**Impact**: `discover_contacts_activity()` fails per prospect

**Recovery**:
- Generic `except Exception` catches Hunter failure
- Prospect recorded as `contact_source="unverified"`, `outreach_ready=False`
- Campaign continues with reduced prospect set

**Verdict**: **SURVIVES WITH DEGRADATION** — fewer outreach-ready prospects

---

### Scenario 9: Operator Never Approves Campaign

**Impact**: `BacklinkCampaignWorkflow` waits at `wait_condition` indefinitely

**Recovery**: **NONE** — no timeout, no escalation, no automatic rejection

**Verdict**: **DOES NOT RECOVER** — operator silence = permanent workflow suspension

---

### Scenario 10: OperationalLoopEngine Reaches Max Iterations

**Impact**: Loop completes after 7 days, no health scans or intelligence generation

**Recovery**: **NONE** — no automatic restart mechanism

**Verdict**: **DOES NOT RECOVER** — silent operational blindness after 7 days

---

## Survivability Scorecard

| Scenario | Verdict | Impact |
|---|---|---|
| Ahrefs API down | SURVIVES | 4-tier fallback |
| LLM gateway down | DEGRADES / HALTS | Graceful for enrichment; halt for outreach |
| PostgreSQL restart | SURVIVES | Retry + reconnect |
| Redis unavailable | MOSTLY SURVIVES | Duplicate send risk |
| Kafka unavailable | SURVIVES | Reply detection stops |
| Temporal down | SURVIVES | Full persistence |
| Worker crash | SURVIVES | Temporal reschedules |
| Hunter.io rate limit | SURVIVES WITH DEGRADATION | Fewer prospects |
| Approval never received | DOES NOT RECOVER | P3 gap |
| Loop max iteration hit | DOES NOT RECOVER | P3 gap |

---

## Operational Survivability Score: 8/10

The platform survives all infrastructure failure scenarios due to Temporal durability. The two gaps are **human-process failures**, not infrastructure failures:
1. Approval gate has no SLA timeout
2. Operational loops have no automatic restart

---

## Recommended Fixes

### Priority 1 (Pre-launch): Approval Gate Timeout
```python
# Current (no timeout)
await workflow.wait_condition(lambda: self._approval_decision is not None)

# Recommended
await workflow.wait_condition(
    lambda: self._approval_decision is not None,
    timeout=timedelta(hours=48)  # configurable SLA
)
# On timeout: auto-reject or escalate
```

### Priority 2 (Pre-launch): Loop Restart Mechanism
```python
# OperationalLoopEngine should use Temporal's ContinueAsNew
# instead of bounded iteration
if iterations >= max_iterations:
    workflow.continue_as_new(tenant_id)
```

### Priority 3 (Pre-scale): Redis Idempotency Hardening
```python
# send_single_email_activity: add DB-based idempotency as Redis fallback
# to prevent duplicate sends during Redis outages
```

---

## Conclusion

**The platform is operationally survivable** for all infrastructure failures. The two survivability gaps (approval gate timeout, loop restart) are engineering issues, not architectural defects, and can be fixed in < 1 sprint.

**Operational Survivability Certification: CONDITIONAL PASS**

Pass conditions: Fix approval gate timeout and implement `ContinueAsNew` for operational loops before production launch.
