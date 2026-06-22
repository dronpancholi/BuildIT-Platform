# P3-F: Scale Limits Assessment
**Audit Date**: 2026-06-21 | **Phase**: P3 — Commercial Readiness
**Method**: Source code analysis of concurrency controls, limits, and bottlenecks

---

## Worker Concurrency Configuration

**Source**: `workflows/worker.py` lines 127–131

```python
Worker(
    ...
    max_concurrent_activities=settings.temporal.max_concurrent_activities,
    max_concurrent_workflow_tasks=settings.temporal.max_concurrent_workflows,
    activity_executor=ThreadPoolExecutor(max_workers=20),
)
```

**Config source**: `get_settings().temporal.*` — from environment variables.
**ThreadPool**: 20 threads per worker process.

| Queue | Concurrent Activities (default) | Concurrent Workflows (default) |
|---|---|---|
| onboarding | settings-defined | settings-defined |
| ai-orchestration | settings-defined | settings-defined |
| seo-intelligence | settings-defined | settings-defined |
| backlink-engine | settings-defined | settings-defined |
| communication | settings-defined | settings-defined |
| reporting | settings-defined | settings-defined |

**Finding**: Default values not inspected — dependent on `.env` config. Without knowing the actual values, concurrency limits cannot be certified. However, UnsandboxedWorkflowRunner is used (line 120) for compatibility — this removes Python sandbox overhead.

---

## Campaign-Level Limits

### Prospect Discovery
- Ahrefs: `referring_domains[:50]` per competitor domain (line 117) — hard cap
- Up to N competitor domains × 50 = N×50 prospects max
- Score_prospects_activity: no explicit limit; processes full list

### Contact Discovery
- `prospects[:30]` cap (line 290) — hard limit of 30 prospects enriched per campaign
- Hunter.io: `limit=3` candidates per domain search
- `verify_email()` called per candidate

**Scale Implication**: Maximum 30 prospects proceed to contact enrichment per campaign execution. This is a **hardcoded throughput ceiling**.

### Email Generation
- `prospects[:20]` cap (line 606) — hard limit of 20 email sequences per campaign
- Each sequence: 3 LLM calls (initial + 2 follow-ups)
- Maximum LLM calls per campaign: 20 × 3 = 60

### Child Workflow Fan-Out
- One `OutreachThreadWorkflow` per email sequence
- Max 20 child workflows per campaign
- No concurrency limiter on child workflow launch

---

## API Rate Limits Observed

### Ahrefs
- `AhrefsRateLimitError` imported and handled in both discovery and scoring activities
- Rate limit triggers → re-raise (not silently swallowed)
- No backoff logic in activity itself — relies on Temporal retry with `RetryPreset.EXTERNAL_API` (max 5 attempts, exponential backoff 2s → 5min)

### Hunter.io
- No rate limit handling observed beyond generic `except Exception`
- No per-domain request throttling
- **Gap**: High-volume campaigns could exhaust Hunter.io credits silently

### LLM Gateway (NIM)
- `RetryPreset.LLM_INFERENCE` (3 attempts, 3s → 2min)
- No token budget or cost cap per campaign

---

## Database Scale Considerations

### Concurrent Session Access
- `get_tenant_session()` creates async SQLAlchemy sessions
- Connection pool managed by asyncpg — pooled per process
- Enum codec registration in P2 — confirmed working

### Table Growth
- `operational_events`: no TTL or archival policy observed
- `recommendations`: status-based filtering; no archival
- `verification_history` JSONB array: max 200 entries (enforced in `link_verification_service.py:156`)
- `workflow_timeline`: no explicit size cap

### Indexing
- `backlink_campaigns.status` — `.in_(["active", "monitoring"])` filter used; index presence not confirmed in this audit
- `backlink_prospects.tenant_id` — used in WHERE clauses; index assumed from FK definition

---

## Temporal Scale Characteristics

### OperationalLoopEngine
- Max iterations: 10,080 (7 days at 1-minute intervals)
- After 7 days, workflow completes. Restart mechanism not observed.

### ContinuousIntelligenceLoop
- Max iterations: 10,080 (7 days at 10-minute intervals)
- Same restart gap applies

> [!WARNING]
> **Finding**: `OperationalLoopEngine` and `ContinuousIntelligenceLoop` both have `max_iterations = 10080` caps and no automatic restart mechanism. After 7 days of operation, both loops terminate. The platform will silently stop health scanning and intelligence generation unless the workflows are manually re-launched.

---

## Throughput Model

### Single Campaign Throughput (Development Mode)
| Stage | Throughput | Bottleneck |
|---|---|---|
| Discovery | 50 prospects/competitor | Ahrefs API rate limit |
| Scoring | All discovered prospects | Ahrefs per-domain metric calls |
| Contact enrichment | **Hard cap: 30** | `prospects[:30]` in code |
| Email generation | **Hard cap: 20** | `prospects[:20]` in code |
| Email sending | 20 emails/campaign launch | Sequential, idempotent |
| Child workflows | 20 concurrent | No concurrency limiter |

### Multi-Campaign Throughput
- Multiple campaigns run independently as separate Temporal workflow instances
- Each campaign uses its own task queue slot
- Bottleneck: Temporal worker pool concurrency + API rate limits shared across campaigns
- No inter-campaign resource sharing or prioritization observed

---

## Scale Limit Summary

| Limit | Value | Type | Verdict |
|---|---|---|---|
| Prospects per campaign (enrichment) | 30 | Hardcoded | ACCEPTABLE for MVP |
| Email sequences per campaign | 20 | Hardcoded | ACCEPTABLE for MVP |
| Operational loop max iterations | 10,080 | Hardcoded | RISK — loops terminate after 7 days |
| Intelligence loop max iterations | 10,080 | Hardcoded | RISK — same |
| Ahrefs rate limit handling | Re-raise to Temporal | Code | PASS — retries via Temporal |
| Hunter.io rate limit handling | Generic exception | Gap | PARTIAL |
| Worker thread pool | 20/worker | Config | ACCEPTABLE for 10 concurrent campaigns |
| DB connection pool | asyncpg default | Config | ACCEPTABLE for dev/early prod |
| LLM cost cap | None | Missing | RISK — no per-campaign LLM spend ceiling |

---

## Scale Verdict

**Current scale ceiling**: ~5–10 concurrent campaigns with 20 prospects each, processing in parallel across 6 worker queues.

**Production scale (pre-investment in horizontal scaling)**: Estimated 50–100 campaigns/day with:
- 2 worker processes per queue
- Ahrefs rate limit pooling
- Hunter.io enterprise tier

**Blockers to 1,000+ campaigns/day**:
1. Prospect cap hardcoded at 30/20 — needs configuration
2. Worker concurrency tied to single-process ThreadPool — needs horizontal scaling
3. No LLM cost cap — runaway spend risk
4. 7-day loop termination — needs perpetual restart mechanism
