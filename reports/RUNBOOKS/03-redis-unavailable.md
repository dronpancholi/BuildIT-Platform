# Runbook — Redis Unavailable

**Severity:** HIGH
**Alert rule:** `redis_unavailable`
**Detection:** `/health/components.redis.status == "unhealthy"`
**SLO target:** Recovery <3 min

---

## Symptoms

- Rate limiter stops enforcing (clients may exceed quota)
- Kill switches reset to "off" — **safety hazard if a kill switch was active**
- Idempotency store loses state — in-flight operations may double-execute
- Real-time SSE connections drop
- `/api/v1/distributed/redis-recovery` shows `recovery_needed: true`

## Detection

| Detector | Fires when |
|----------|------------|
| `redis_unavailable` | `health.components.redis.status != healthy/degraded` |
| `RedisDown` (Prometheus) | `up{job="redis"} == 0` for 1m |

## Triage (30 sec)

```bash
# 1. Is the container running?
docker ps | grep seo-redis
# If not running → start it (Recovery step 1).

# 2. Is it responsive?
docker exec seo-redis redis-cli ping
# Expected: PONG

# 3. Memory pressure?
docker exec seo-redis redis-cli info memory | grep -E "used_memory_human|maxmemory_human"
# If used_memory near maxmemory → eviction happening.
```

## Recovery

### Step 1: Start Redis if stopped

```bash
docker start seo-redis
# Or via watchdog (auto): the platform's ServiceWatchdog polls every 60s
# and restarts stopped containers automatically.
```

### Step 2: Wait for AOF to replay

```bash
# Check status
docker exec seo-redis redis-cli ping
# May take 10-30s if AOF is large
```

### Step 3: Recover kill switches (CRITICAL)

```bash
# Force the platform to re-validate Redis state and restore kill switches
curl -s -X POST http://localhost:8000/api/v1/distributed/recover-redis | jq .
# Expected: {"success": true, "data": {"recovery_needed": false, ...}}
```

### Step 4: Verify

```bash
curl -s http://localhost:8000/api/v1/health | jq '.components.redis'
# Expected: {"status": "healthy", ...}
```

## Validation

- [ ] `redis-cli ping` returns PONG
- [ ] `/api/v1/health` shows `redis: healthy`
- [ ] Kill switches are restored (check via `GET /api/v1/incident/kill-switches`)
- [ ] Idempotency store integrity is true

## Safety Notes

**Kill switches reset to OFF after Redis restart.** If any kill switch was active for safety reasons (e.g., circuit breaker, abuse prevention), verify they are correctly restored. If not, manually re-activate them via the platform's kill-switch API.

## Escalation

- If Redis keeps crashing → check `docker logs seo-redis | tail -50` for OOM or other errors
- If AOF is corrupted → `docker exec seo-redis redis-check-aof --fix /data/appendonly.aof` (data loss possible)
- If persistent state loss → page engineering lead
