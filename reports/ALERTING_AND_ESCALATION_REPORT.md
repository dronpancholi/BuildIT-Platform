# Alerting & Escalation Report — Phase 2.1

**Phase:** 2.1 — Production Operations & Observability
**Date:** 2026-06-05
**Verdict:** ❌ **CRITICAL FAILURE — The alerting system is defined but never fires.**

> "How will operators know something is broken?"
>
> **Currently: They won't. Not from any automated source.**

---

## 1. Executive Summary

The platform has a fully-designed in-process alerting engine (`core/alerting.py`, 290 lines) with severity levels, escalation rules, 7 alert rules, an HTTP API, and an in-memory alert store. **The engine runs.** The escalation loop ticks every check_interval. The alert rules are loaded.

**No alert has ever been raised.** The `_run_cycle` method only calls `_check_escalations()` — it does NOT call any rule evaluation, condition check, or `raise_alert()`. The 7 defined rules sit in `ALERT_RULES` and are never consulted.

In addition, there is **no external notification** — no Slack, PagerDuty, email, SMS, or webhook. Even if alerts were raised, no one would be told.

In addition, Prometheus has **0 alert rules configured** at the infrastructure level. No "Postgres is down" alert, no "Redis memory pressure" alert, no "Kafka consumer lag" alert.

In addition, there is **no on-call schedule, no escalation policy, and no PagerDuty/Slack integration** anywhere in the codebase.

---

## 2. The In-Process Alerting Engine

### 2.1. What exists

`backend/src/seo_platform/core/alerting.py:290` defines:

- `class Severity(str, Enum)` — `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`
- `class AlertStatus(str, Enum)` — `FIRING`, `ACKNOWLEDGED`, `RESOLVED`, `ESCALATED`
- `class Alert` — dataclass with id, type, severity, title, message, source, status, timestamps
- `class AlertManager` — singleton with `start()`, `stop()`, `raise_alert()`, `acknowledge()`, `resolve()`, `get_active_alerts()`, `get_alert_summary()`

`main.py:177-181` starts the engine on app boot:

```python
try:
    from seo_platform.core.alerting import alert_manager
    await alert_manager.start()
    logger.info("alert_manager_started")
except Exception as e:
    logger.warning("alert_manager_start_failed", error=str(e))
```

Verified at boot:

```
$ grep alert_manager /tmp/uvicorn_p201.log
[info] alert_manager_started   [seo_platform.core.alerting]
[info] alert_manager_started   [seo_platform.main]
```

### 2.2. The 7 rules

`ALERT_RULES: dict[str, dict[str, Any]]` defines:

| Rule | Severity | Condition | Resolution hint |
|---|---|---|---|
| `high_error_rate` | HIGH | `error_rate > 0.05` | Check deployments, review logs |
| `database_unavailable` | CRITICAL | `not database_ok` | Restart DB, check pool, verify creds |
| `queue_backlog` | HIGH | `queue_depth > 1000` | Scale workers, check health |
| `slow_api` | MEDIUM | `p95_latency_ms > 500` | Review slow endpoints, add caching |
| `automation_failures` | HIGH | `automation_failure_rate > 0.1` | Check rule configs, fix failures |
| `approval_backlog` | MEDIUM | `pending_approvals > 50` | Assign reviewers |
| `sla_breach` | CRITICAL | `sla_breaches > 0` | Investigate breach |

### 2.3. Escalation policy

```python
ESCALATION_DELAYS = {
    Severity.CRITICAL: [60, 300, 900],      # 1min, 5min, 15min
    Severity.HIGH:     [300, 900, 3600],     # 5min, 15min, 1hr
    Severity.MEDIUM:   [1800, 7200],         # 30min, 2hr
    Severity.LOW:      [7200],                # 2hr
}
```

### 2.4. **CRITICAL BUG: The rules are never evaluated**

`alerting.py:130-150` — the `_run_cycle`:

```python
async def _run_cycle(self):
    while self._running:
        try:
            self._check_escalations()
        except Exception as e:
            logger.error("alert_cycle_error", error=str(e))
        await asyncio.sleep(self._check_interval)
```

`_check_escalations()` walks the `self._alerts` dict and escalates existing alerts based on age. **It never evaluates `ALERT_RULES` against current metrics.** It never calls `raise_alert()`. It never reads from Prometheus, the DB, or any health endpoint.

To raise an alert, **code must explicitly call `alert_manager.raise_alert(...)`**. Searching the codebase:

```
$ grep -rn "alert_manager\.raise\|AlertManager().raise\|raise_alert(" backend/src/seo_platform/ --include="*.py"
(no results)
```

**No call site exists.** The 7 rules are decorative.

### 2.5. Verified: zero alerts ever

```
$ curl http://localhost:8000/api/v1/alerts
{"success":true,"data":{"total":0,"alerts":[]}}

$ curl http://localhost:8000/api/v1/alerts/summary
{"success":true,"data":{}}

$ grep -iE "alert_fired|alert_raised|alert_escalated" /tmp/uvicorn_p201.log
(no results)
```

The system has never raised, escalated, or resolved an alert in the entire history of the running process.

---

## 3. Prometheus Alert Rules

### 3.1. Inventory

```
$ curl http://localhost:9090/api/v1/rules
{"data":{"groups":[]}}
```

**Zero rule groups. Zero rules. Zero alerts.** The Prometheus instance is configured to scrape but not to alert on anything.

`prometheus.yml:21` has no `rule_files:` directive. There is no `*.rules.yml` file in the repository.

`find /Users/dronpancholi/Developer/Project\ 31A -name "*.rules.yml" 2>/dev/null` returns no results.

### 3.2. Required rules (not present)

| Alert | Expression | For | Severity |
|---|---|---|---|
| PostgresDown | `up{job="postgres"} == 0` | 1m | critical |
| RedisDown | `up{job="redis"} == 0` | 1m | critical |
| TemporalDown | `up{job="temporal"} == 0` | 1m | critical |
| KafkaDown | `up{job="kafka"} == 0` | 1m | critical |
| MinIODown | `up{job="minio"} == 0` | 1m | high |
| HighErrorRate | `rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05` | 5m | high |
| HighP95Latency | `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1` | 5m | medium |
| DBPoolExhausted | `db_connection_pool_pct > 80` | 2m | high |
| DiskSpaceLow | `(node_filesystem_avail_bytes / node_filesystem_size_bytes) < 0.1` | 5m | high |
| WorkflowFailureRate | `rate(temporal_workflow_failed_total[10m]) > 0.1` | 5m | high |

None of these exist.

---

## 4. External Notification

### 4.1. Integrations

| Channel | Present? | Notes |
|---|---|---|
| Slack | ❌ No | No Slack SDK, no webhook URL config |
| PagerDuty | ❌ No | No PagerDuty SDK |
| Opsgenie | ❌ No | No Opsgenie SDK |
| Email (SMTP) | ⚠️ Partial | `mailhog` is for test capture, not production |
| SMS | ❌ No | No Twilio/etc |
| Webhook | ❌ No | No generic webhook caller |
| Pushover / Telegram / Discord | ❌ No | |
| Dead-man's switch | ❌ No | (Heartbeat not implemented) |

Even if the alerting engine fired, the alert would only be visible at `GET /api/v1/alerts`. No external actor is watching that endpoint.

### 4.2. Alertmanager

Alertmanager is **not deployed** in the docker-compose stack. The `infrastructure/docker/` directory contains no `alertmanager/` folder, no `alertmanager.yml`, no Docker image reference.

---

## 5. Severity Classification (proposed, current reality)

| Severity | Current behavior | What SHOULD happen |
|---|---|---|
| **CRITICAL** | Page on-call, SMS, phone call | **No action** — alert never fires |
| **HIGH** | Slack #ops-alerts, PagerDuty | **No action** — alert never fires |
| **MEDIUM** | Slack #ops, dashboard badge | **No action** — alert never fires |
| **LOW** | Log entry, dashboard tile | **No action** — alert never fires |

The classification is defined in code but unused.

---

## 6. Failure Mode Analysis: "What would be missed?"

| Failure | Detected? | Who finds out? |
|---|---|---|
| PostgreSQL hard crash | ❌ No alert | User (5xx responses) or on-call (next health check from outside) |
| Redis hard crash | ❌ No alert | User (rate limiter stops working) |
| Temporal container dies | ❌ No alert | User (workflow start fails) |
| Kafka broker down | ❌ No alert | User (events don't propagate) |
| MinIO disk full | ❌ No alert | User (upload fails) |
| Worker process dies | ❌ No alert | The next time a workflow is queued (it sits indefinitely) |
| Backend process OOM | ❌ No alert | Load balancer / external monitor |
| API p99 > 10s | ❌ No alert | User complaints |
| DB connection pool exhausted | ❌ No alert | 5xx storm |
| LLM provider quota exhausted | ❌ No alert | Generation silently fails with mock fallback |
| LLM provider returns 401 | ❌ No alert (caught + logged) | Until someone checks logs |
| NIM slow > 30s | ❌ No alert | User waits |
| Workflow runs > 1 hour | ❌ No alert | Operator notices ad-hoc |
| External API (DataForSEO) returns 429 | ❌ No alert | Quota burns out |
| Disk > 90% full | ❌ No alert | Until DB write fails |
| Memory > 90% | ❌ No alert | Until OOM kill |

**Every line of this table is a failure that would NOT generate an automated page.** Discovery depends on (a) users complaining, (b) an external monitor like Pingdom/UptimeRobot, or (c) a human happening to look at the dashboard.

---

## 7. MTTD and MTTR Estimate

Given the alerting gap:

| Metric | Current | Industry target |
|---|---|---|
| MTTD (mean time to detect) | **Hours-to-days** for most failures; seconds-to-minutes only when the failure manifests as visible errors in the user-facing UI | Minutes for critical, hours for medium |
| MTTR (mean time to recover) | **Tied to human discovery**; can be unbounded if no one is watching | Hours for critical, days for medium |

The current state is "incident response happens when someone gets paged by a customer." That is **not a production operations posture**.

---

## 8. Recommended Alert Set (minimum viable for production)

| Alert | Source | Severity | Action |
|---|---|---|---|
| PostgresDown | Prometheus `up{job="postgres"}==0` for 1m | critical | Page on-call |
| PostgresPoolSaturated | Prometheus `db_connection_pool_pct>90` for 2m | high | Slack #ops-alerts |
| RedisDown | `up{job="redis"}==0` for 1m | critical | Page on-call |
| RedisMemoryHigh | `redis_memory_used_bytes / redis_max_memory_bytes > 0.9` for 5m | high | Slack |
| TemporalDown | `up{job="temporal"}==0` for 1m | critical | Page on-call |
| KafkaBrokerDown | `up{job="kafka"}==0` for 1m | critical | Page on-call |
| KafkaConsumerLag | `kafka_consumer_lag{group="workflow-workers"} > 1000` for 5m | high | Slack |
| MinIODown | `up{job="minio"}==0` for 1m | high | Slack |
| APIHighErrorRate | `rate(http_requests_total{status=~"5.."}[5m]) > 0.05` for 5m | high | Slack |
| APIHighP95Latency | `histogram_quantile(0.95, ...) > 2` for 5m | medium | Slack |
| WorkerDown | `sum(up{job=~"worker-.*"}) < 6` for 2m | critical | Page on-call |
| DiskSpaceLow | `node_filesystem_avail_bytes < 5GB` for 5m | high | Slack |
| ExternalAPIQuota | `external_api_quota_remaining < 100` for 5m | high | Slack |
| WorkflowBacklog | `temporal_workflow_started_total - temporal_workflow_completed_total > 100` for 10m | high | Slack |

15 alerts is the minimum. Currently: **0**.

---

## 9. Score

| Category | Weight | Score | Notes |
|---|---|---|---|
| In-process alerting engine | 25% | 40/100 | Code exists, framework works, but rule evaluation is not wired |
| Prometheus alert rules | 25% | 0/100 | Zero rules configured |
| External notification | 20% | 0/100 | No Slack/PagerDuty/email/webhook |
| On-call / escalation policy | 15% | 0/100 | No schedule, no policy |
| Dead-man's switch | 10% | 0/100 | No heartbeat |
| End-to-end test of alerting | 5% | 0/100 | No alert has ever fired |

**Overall: 10/100** — One step above "production unsafe". A fire alarm that doesn't connect to the sprinkler.

---

## 10. Findings

| ID | Finding | Severity |
|---|---|---|
| ALERT-001 | `AlertManager._run_cycle` only calls `_check_escalations`; rules are never evaluated | **P0** |
| ALERT-002 | No call site ever invokes `alert_manager.raise_alert()` | **P0** |
| ALERT-003 | Prometheus has 0 alert rules | **P0** |
| ALERT-004 | No external notification (Slack, PagerDuty, email, SMS, webhook) | **P0** |
| ALERT-005 | No Alertmanager deployment | **P0** |
| ALERT-006 | No on-call schedule | **P1** |
| ALERT-007 | No dead-man's switch (heartbeat) | **P2** |
| ALERT-008 | No runbook linking alert → investigation steps | **P1** |

---

**Status:** ❌ CRITICAL. The system cannot raise an alert and has no way to notify anyone. Every production operations audit question of the form "Who gets alerted?" is currently answered: **no one**.
