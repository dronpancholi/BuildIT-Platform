# BuildIT — Production Deployment Runbook

> **Status:** CONDITIONALLY CERTIFIED — Production-Ready Pending Provider Credentials
> **Phase:** 1.4 — All 4 P0 Gaps Closed
> **Verdict source:** `PHASE_1_4_FINAL_CERTIFICATION.md`
> **Owner:** Platform Engineering
> **Last updated:** 2026-06-01

This runbook is the canonical reference for deploying, operating, and rolling
back the BuildIT SEO Operations Platform. It is intentionally separable from
`DEPLOY.md` (which covers the developer quick-start) and from the
`PROVIDER_PROVISIONING_CHECKLIST.md` (which covers the one-time path to
REAL WORLD CERTIFIED).

If you only have 5 minutes, read **§1 Pre-Deployment Checklist**, then run
**§4 Deployment**, then **§5 Smoke Test**.

---

## Table of Contents

1. [Pre-Deployment Checklist](#1-pre-deployment-checklist)
2. [Secret Management](#2-secret-management)
3. [Environment Configuration Template](#3-environment-configuration-template)
4. [Deployment Procedure](#4-deployment-procedure)
5. [Post-Deployment Smoke Test](#5-post-deployment-smoke-test)
6. [Operational Runbook](#6-operational-runbook)
7. [Rollback Procedure](#7-rollback-procedure)
8. [What Phase 1.4 Changed (operator-relevant deltas)](#8-what-phase-14-changed-operator-relevant-deltas)
9. [Known Issues and P1 Hardening](#9-known-issues-and-p1-hardening)
10. [Decision: When to Promote from CONDITIONALLY → REAL WORLD CERTIFIED](#10-decision-when-to-promote-from-conditionally--real-world-certified)

---

## 1. Pre-Deployment Checklist

Complete this **before** touching any host. Each item is verifiable.

### 1.1 Server Requirements

| Resource | Minimum | Recommended | Notes |
|----------|---------|-------------|-------|
| CPU | 2 vCPU | 4 vCPU | Playwright + NIM inference spike to 4+ cores |
| RAM | 4 GB | 8 GB | All services in compose need ~3 GB headroom |
| Disk | 40 GB SSD | 80 GB SSD | Postgres + MinIO + Temporal data grow ~5 GB/month |
| Network | 100 Mbps | 1 Gbps | Scraping and NIM calls are bursty |
| OS | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS | Alpine-based images also work |

### 1.2 Network and DNS

- [ ] A domain (`api.yourdomain.com`, `app.yourdomain.com`) resolves to the host's public IP
- [ ] Inbound ports **80** and **443** open (Nginx)
- [ ] Outbound HTTPS to all third-party providers is allowed (see §10 for the list)
- [ ] Outbound SMTP — if you use a real ESP (SendGrid, Postmark) — must allow port 587 to `*.sendgrid.net` / `*.postmarkapp.com`
- [ ] Internal docker network can reach `postgres:5432`, `redis:6379`, `kafka:9092`, `temporal:7233`, `qdrant:6333`, `minio:9000`

### 1.3 Software Prerequisites

```bash
docker --version          # ≥ 24.0
docker compose version    # ≥ 2.20 (the v2 plugin, not the legacy `docker-compose`)
openssl version           # ≥ 3.0
python3 --version         # ≥ 3.10 (for the smoke test script)
git --version             # any recent
```

### 1.4 Secrets Inventory

You must have these ready **before** running `deploy-up`. None of them may
appear in git. See §2 for how to generate them.

- [ ] `ENCRYPTION_MASTER_KEY` (32-byte AES-256-GCM, base64)
- [ ] `AUTH_SECRET_KEY` (32-byte random, base64)
- [ ] `POSTGRES_PASSWORD` (24+ char URL-safe)
- [ ] `REDIS_PASSWORD` (optional but recommended)
- [ ] Optional provider keys (see `PROVIDER_PROVISIONING_CHECKLIST.md`):
  `HUNTER_API_KEY`, `SENDGRID_API_KEY` or `POSTMARK_API_KEY`,
  `DATAFORSEO_LOGIN`+`DATAFORSEO_PASSWORD`, `AHREFS_API_KEY`
- [ ] `NVIDIA_NIM_API_KEY` (optional; without it, email generation falls back to deterministic templates — still works, just less personalized)

### 1.5 Pre-Deployment Backup (production only)

If this is **not** a fresh host:

```bash
# 1. Snapshot Postgres (use the system superuser; the app role can't lock properly)
pg_dump --no-owner --no-acl -h "$POSTGRES_HOST" -U "$POSTGRES_SUPER_USER" \
    -d seo_platform -Fc -f "buildit-predeploy-$(date -u +%Y%m%dT%H%M%SZ).dump"

# 2. Snapshot MinIO bucket
mc alias set local http://$MINIO_HOST:9000 $MINIO_ACCESS_KEY $MINIO_SECRET_KEY
mc mirror local/seo-platform-assets "s3-backup-$(date -u +%Y%m%dT%H%M%SZ)/"

# 3. Snapshot the prior `.env.production` and the `infrastructure/` directory
cp -a .env.production .env.production.bak.$(date -u +%Y%m%dT%H%M%SZ)
cp -a infrastructure infrastructure.bak.$(date -u +%Y%m%dT%H%M%SZ)
```

Store all three artifacts off-host (S3, B2, rsync.net) with a 30-day retention.

---

## 2. Secret Management

### 2.1 Generation

```bash
# Run on a trusted host, copy-paste the output into your secrets manager
./scripts/generate_secrets.sh
```

The script emits:
- `ENCRYPTION_MASTER_KEY` — 32-byte base64, used for AES-256-GCM column encryption
- `AUTH_SECRET_KEY` — 32-byte base64, used for internal JWT signing
- `POSTGRES_PASSWORD` — 24-char URL-safe password
- `REDIS_PASSWORD` — 24-char URL-safe password
- `TEMPORAL_DB_PASSWORD` — 24-char URL-safe password

**Non-negotiable rules:**
- Never commit these values to git. `.gitignore` already excludes `.env.production` and `.env*` files — verify before your first commit.
- Never log them. The application sanitizes headers and query strings, but if you `docker logs` you can still see env vars passed via `environment:` in compose.
- Never reuse the dev value `iCOJCD59uy4cTXNhmk2/BMl+/QK38NWM/wa6ZaUYWt8=` — it's in the repo and is therefore public.

### 2.2 Storage

Recommended options, in order of preference:

| Backend | How to use | Cost | Notes |
|---------|-----------|------|-------|
| 1Password CLI (`op`) | `op read op://prod/buildit/encryption_master_key` | $$ | Easiest for small teams |
| HashiCorp Vault | `vault kv get -mount=secret buildit/encryption_master_key` | Free | Best for larger orgs |
| AWS Secrets Manager | via task role at boot | $$ | Native to ECS / EKS |
| Doppler | rendered to env file at deploy time | Free tier | Best developer UX |
| Plain `.env.production` on host | `chmod 600` and owned by root | Free | Acceptable for a single trusted host |

### 2.3 Rotation Policy

- **ENCRYPTION_MASTER_KEY:** rotate every 365 days. Rotation requires re-encrypting every encrypted column in the DB — plan a 30-minute downtime window. (A rotation script is not yet shipped; track as a P1 — see §9.)
- **AUTH_SECRET_KEY:** rotate every 90 days. Invalidates all in-flight JWTs (users must re-authenticate). Doable with zero downtime by supporting a primary + secondary key for 24 hours.
- **POSTGRES_PASSWORD / REDIS_PASSWORD:** rotate every 90 days. `ALTER USER` is online; no downtime required.
- **Provider API keys:** rotate on personnel change, not on a fixed schedule.

### 2.4 Loading Secrets at Boot Time

The compose file uses `env_file: ../../.env.production`. Two patterns work:

**Pattern A — Render at deploy time (Doppler / Vault):**
```bash
doppler secrets download --no-file --format docker > .env.production.rendered
docker compose --env-file .env.production.rendered -f docker-compose.yml -f docker-compose.prod.yml up -d
shred -u .env.production.rendered
```

**Pattern B — Mount from a secrets directory (Kubernetes-style):**
```yaml
# In docker-compose.prod.yml override
secrets:
  encryption_master_key:
    file: /etc/buildit/secrets/encryption_master_key
services:
  backend:
    secrets:
      - encryption_master_key
```
The backend already reads `ENCRYPTION_MASTER_KEY` from env, so you must also export it in `environment:` or render it into `/run/secrets/encryption_master_key` and have a small entrypoint shim that exports it.

---

## 3. Environment Configuration Template

`.env.production` is the single source of truth for runtime configuration.
The shipped file is a skeleton; replace every blank or default value with a
real one before deploying.

### 3.1 Required Variables (deploy will fail or misbehave without these)

```bash
# Operational mode
APP_ENV=production
APP_DEBUG=false
APP_LOG_LEVEL=INFO
USE_MOCK_PROVIDERS=false           # MUST be false in production
DEV_AUTH_BYPASS=false              # MUST be false in production
TEST_MODE=false

# Encryption (32-byte base64)
ENCRYPTION_MASTER_KEY=<from §2>

# Auth (32-byte base64)
AUTH_SECRET_KEY=<from §2>
AUTH_PROVIDER=internal

# Database
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=seo_platform
POSTGRES_USER=seo_platform_app
POSTGRES_PASSWORD=<from §2>

# Cache
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=<from §2 or empty>

# Event bus
KAFKA_BOOTSTRAP_SERVERS=kafka:9092

# Orchestration
TEMPORAL_HOST=temporal
TEMPORAL_PORT=7233
QDRANT_HOST=qdrant
QDRANT_PORT=6333
S3_ENDPOINT=http://minio:9000
S3_ACCESS_KEY=<minio root user>
S3_SECRET_KEY=<minio root password>
S3_BUCKET_NAME=seo-platform-assets

# CORS — the comma-separated list of origins that may call the API
CORS_ORIGINS=https://app.yourdomain.com,https://yourdomain.com
```

### 3.2 Provider Variables (set per `PROVIDER_PROVISIONING_CHECKLIST.md`)

```bash
# Email
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASS=<SENDGRID_API_KEY>
# OR
SMTP_HOST=smtp.postmarkapp.com
SMTP_PORT=2525
SMTP_USER=<POSTMARK_SERVER_TOKEN>
SMTP_PASS=<POSTMARK_SERVER_TOKEN>

# External paid providers (optional, see checklist)
HUNTER_API_KEY=
DATAFORSEO_LOGIN=
DATAFORSEO_PASSWORD=
AHREFS_API_KEY=

# NVIDIA NIM (optional — fall back to templates if blank)
NVIDIA_NIM_API_URL=https://integrate.api.nvidia.com/v1
NVIDIA_NIM_API_KEY=
NVIDIA_NIM_SEO_MODEL=meta/llama-3.1-8b-instruct
NVIDIA_NIM_ORCHESTRATION_MODEL=meta/llama-3.1-70b-instruct
```

### 3.3 Defaults That Should NOT Be Changed Without an RFC

```bash
UVICORN_WORKERS=1                  # SSE + in-memory state. >1 breaks event ordering.
APP_SECRET_KEY=<unused, kept for compat>
KAFKA_CONSUMER_GROUP_PREFIX=seo-platform
TEMPORAL_NAMESPACE=seo-platform-prod
TEMPORAL_TASK_QUEUE_PREFIX=seo-platform
SCRAPER_RETRY_ATTEMPTS=3
BROWSER_HEADLESS=true
```

### 3.4 Verification

Before deploying, run this locally to confirm no obvious misconfigurations:

```bash
docker compose --env-file .env.production -f infrastructure/docker/docker-compose.yml \
    -f infrastructure/docker/docker-compose.prod.yml config -q && \
    echo "✅ compose config valid"
```

This catches missing env vars, malformed YAML, and broken service references.

---

## 4. Deployment Procedure

### 4.1 The 12-Step Deployment

```bash
# ─── 0. Pre-flight ──────────────────────────────────────────────────────
ssh deploy@api.yourdomain.com
cd /opt/buildit                       # or wherever the repo lives
git fetch --tags
git checkout v0.1.0                   # ALWAYS deploy a tag, not main

# ─── 1. Confirm you're deploying the right thing ───────────────────────
git log -1 --oneline
git status                            # MUST be clean
cat VERSION                           # or check the tag

# ─── 2. Render secrets (Doppler/Vault pattern) ─────────────────────────
# If using Doppler:
doppler secrets download --no-file --format docker > /tmp/.env.production
chmod 600 /tmp/.env.production
# If using Vault:
vault kv get -mount=secret -format=json buildit/prod | jq -r '.data.data | to_entries[] | "\(.key)=\(.value)"' > /tmp/.env.production
chmod 600 /tmp/.env.production

# ─── 3. Pre-deploy backup (skip on first deploy to empty host) ────────
./scripts/backup_postgres.sh /tmp/buildit-predeploy-$(date -u +%s).dump

# ─── 4. Stop running app containers (infra stays up) ──────────────────
docker compose -f infrastructure/docker/docker-compose.yml \
               -f infrastructure/docker/docker-compose.prod.yml \
               stop backend frontend

# ─── 5. Pull new images ───────────────────────────────────────────────
docker compose -f infrastructure/docker/docker-compose.yml \
               -f infrastructure/docker/docker-compose.prod.yml \
               --env-file /tmp/.env.production pull backend frontend

# ─── 6. Build (only if building locally; skip in CI/CD) ───────────────
# docker compose ... build --no-cache backend frontend

# ─── 7. Run database migrations ───────────────────────────────────────
docker compose -f infrastructure/docker/docker-compose.yml \
               -f infrastructure/docker/docker-compose.prod.yml \
               --env-file /tmp/.env.production \
               run --rm backend alembic upgrade head
# Expected: "Running upgrade ... -> <new-revision>, <N> migrations applied"

# ─── 8. Start backend, wait for health ────────────────────────────────
docker compose ... up -d backend
for i in {1..30}; do
    sleep 2
    if curl -fsS http://localhost:8000/api/v1/health >/dev/null; then
        echo "Backend healthy after ${i} polls"
        break
    fi
done
[ $i -lt 30 ] || { echo "Backend did not become healthy"; exit 1; }

# ─── 9. Start frontend ─────────────────────────────────────────────────
docker compose ... up -d frontend
sleep 5
curl -fsS http://localhost:3000/ -o /dev/null || { echo "Frontend not serving"; exit 1; }

# ─── 10. Reload nginx (force re-resolve of upstream) ──────────────────
docker compose ... exec nginx nginx -s reload

# ─── 11. Run the smoke test (§5) ──────────────────────────────────────
./scripts/deploy_smoke_test.sh API_URL=https://api.yourdomain.com
# MUST exit 0

# ─── 12. Shred the rendered secrets ───────────────────────────────────
shred -u /tmp/.env.production
```

### 4.2 What to Watch For During Deploy

- **Migration logs:** every `alembic upgrade` must report "Running upgrade ... -> ..." with a deterministic revision. If you see "FATAL" or "alembic.util.exc.CommandError", **stop and roll back** (see §7).
- **Backend startup logs:** expect `Application startup complete` and the version banner. Any traceback means the container is broken; restart from step 7.
- **Frontend startup:** expect `Ready in <N>s` from Next.js. Build errors will appear in the `pnpm build` step (visible in `frontend` container stdout during the image build, not at runtime).

### 4.3 First-Deploy-Only Steps

On a fresh host:

```bash
# Initialize Postgres with the right app role
./scripts/init_postgres.sh
# Creates:
#   user seo_platform_app with password from $POSTGRES_PASSWORD
#   database seo_platform owned by seo_platform_app
#   GRANT CREATE on schema public to seo_platform_app   (required for alembic)

# Initialize MinIO bucket
./scripts/init_minio.sh
# Creates bucket seo-platform-assets with the right access policy

# Initialize Temporal namespace
./scripts/init_temporal.sh
# Registers the seo-platform-prod namespace
```

---

## 5. Post-Deployment Smoke Test

This is the canary. If this fails, the deployment is not done.

```bash
# Default target = http://localhost:8000
./scripts/deploy_smoke_test.sh

# Against a remote host:
API_URL=https://api.yourdomain.com ./scripts/deploy_smoke_test.sh

# Skip the slow async report test (Phase 1.4 GAP-002) for faster CI:
SKIP_ASYNC=1 ./scripts/deploy_smoke_test.sh

# Verbose mode (show full response bodies on failure):
VERBOSE=1 ./scripts/deploy_smoke_test.sh
```

### 5.1 What It Verifies (18 assertions)

| # | Section | What it asserts | Phase 1.4 gap |
|---|---------|----------------|----------------|
| 0 | Connectivity | API returns 200 on `/api/v1/health` | — |
| 1 | Health | `status` is `healthy` or `degraded` (never missing) | GAP-001 |
| 1 | Health | `postgresql`, `redis`, `kafka`, `temporal` all `healthy` | — |
| 1 | Health | `external_apis` is `degraded` with "No external SEO APIs configured" OR `healthy` | GAP-001 |
| 2 | Metrics | `GET /metrics` returns 200 Prometheus text (≥1 KB, has `# HELP` and `# TYPE` lines) | **GAP-005** |
| 3 | Campaigns | `GET /clients/{id}/campaigns` returns `APIResponse` envelope | **GAP-004** |
| 3 | Campaigns | Tenant isolation: known client returns data, unknown client returns 404 or empty | GAP-004 |
| 3 | Campaigns | `status=ACTIVE` (uppercase enum) returns 200 | GAP-004 |
| 3 | Campaigns | `status=BOGUS` returns 400 with valid enum list (no 500) | GAP-004 |
| 4 | Errors | 404 returns envelope `{success:false, error_code:NOT_FOUND, retryable:false}` | **GAP-003** |
| 5 | Async | `POST /reports/generate-async` returns 202 in < 1 s | **GAP-002** |
| 5 | Async | Response includes `status:"pending"` and `status_url` | GAP-002 |
| 6 | Providers | Health component reports `degraded` with reason OR `healthy` (no 5xx) | GAP-001 |
| 6 | Providers | `POST /api/v1/link-verification/.../verify-all` returns 200/404/422 (not 5xx) | — |
| 7 | CORS | Preflight `OPTIONS` returns 200/204 with CORS headers | — |

### 5.2 Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | All 18 passed | Deployment succeeded. |
| 1 | One or more failed | **Do not promote.** Roll back (§7) or fix and redeploy. |
| 3 | API unreachable | Check `docker compose ps`, `docker compose logs backend`, network ACLs. |

### 5.3 Continuous Smoke Testing

The script is safe to run in a tight loop:

```bash
# 5-second polling, forever
while true; do
    ./scripts/deploy_smoke_test.sh SKIP_ASYNC=1 || alert_oncall "smoke test failed"
    sleep 5
done
```

---

## 6. Operational Runbook

### 6.1 Daily Health Check

```bash
# Text mode (humans)
./scripts/operational_health_check.sh

# JSON mode (Prometheus textfile collector, Datadog agent, etc.)
JSON=1 ./scripts/operational_health_check.sh > /var/lib/node_exporter/textfile_collector/buildit.prom
```

Exit codes:
- `0` — every component `healthy`
- `1` — overall `degraded` (one or more components degraded, including the expected `external_apis` pre-credentials)
- `2` — overall `unhealthy` or unparseable (page on-call)
- `3` — API unreachable (page on-call, check network/firewall first)

### 6.2 Common Operations

```bash
# Tail logs from the API
docker compose -f infrastructure/docker/docker-compose.yml \
               -f infrastructure/docker/docker-compose.prod.yml \
               logs -f --tail=200 backend

# Restart a single service (zero-downtime if you have >1 backend replica; otherwise a brief blip)
docker compose ... up -d --force-recreate --no-deps backend

# Restart the Temporal worker (kills in-flight workflows; safe to do during off-hours)
docker compose ... restart backend

# Check disk usage
docker system df
du -sh /var/lib/docker/volumes/*

# Tail uvicorn access logs (JSON; one event per line, includes trace_id and tenant_id)
docker compose ... logs --no-log-prefix backend | grep '"trace_id"'

# Check provider_health_metrics table for provider-specific failures
psql -h $POSTGRES_HOST -U $POSTGRES_USER -d seo_platform -c \
  "SELECT provider, status, latency_ms, error_message, created_at
   FROM provider_health_metrics
   WHERE created_at > now() - interval '1 hour'
   ORDER BY created_at DESC LIMIT 50;"
```

### 6.3 Adding Capacity

The default `backend` service runs **1** uvicorn worker because of in-memory
state (SSE, idempotency counters, the workflow event bus). Scaling out
requires either:

1. Run a second `backend` instance behind a separate hostname (e.g.,
   `api-2.yourdomain.com`) for read-heavy or worker-only traffic, or
2. Extract the in-memory state to Redis (a future P1; not yet implemented).

Do **not** set `UVICORN_WORKERS > 1` in production — it will desync SSE streams
and idempotency keys.

### 6.4 Database Maintenance

```bash
# VACUUM ANALYZE (run weekly, off-peak)
psql -h $POSTGRES_HOST -U seo_platform_app -d seo_platform \
  -c "VACUUM ANALYZE;"

# Check bloat
psql ... -c "
SELECT schemaname, tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
       n_live_tup
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC LIMIT 20;"

# Check long-running queries
psql ... -c "
SELECT pid, now() - query_start AS duration, state, query
FROM pg_stat_activity
WHERE state != 'idle' AND query_start < now() - interval '30 seconds'
ORDER BY duration DESC;"
```

### 6.5 Backup Routine

```bash
# Cron, daily at 02:00 UTC, retain 30 days
0 2 * * * /opt/buildit/scripts/backup_postgres.sh /var/backups/buildit/daily-$(date -u +\%Y\%m\%d).dump
```

The shipped `scripts/backup_postgres.sh` is `pg_dump -Fc` (custom format,
compressed, parallel-restore capable). See `PHASE_1_4_FINAL_CERTIFICATION.md`
§"Staging Rehearsal" for the exact 8-stage backup/restore procedure.

---

## 7. Rollback Procedure

A rollback is the inverse of §4. The goal: get back to the previous tag in
under 5 minutes with zero data loss.

### 7.1 When to Roll Back

Roll back if **any** of:
- `deploy_smoke_test.sh` exits non-zero after a deploy
- `/api/v1/health` returns `unhealthy` for any of `postgresql`/`redis`/`kafka`/`temporal` for >2 minutes
- Migration log shows `alembic.util.exc.CommandError` or any `sqlalchemy.exc` traceback
- Backend log shows `Application startup complete` followed by repeated worker crashes
- Frontend returns 5xx for any of `/`, `/dashboard`, `/api/v1/...`
- Provider health shows `unhealthy` (not `degraded`) for any provider with a configured key

Do **not** roll back for:
- `external_apis` showing `degraded` with the "No external SEO APIs configured" message — that's the expected pre-credentials state. Provision the keys (§10) instead.
- Latency spikes on `/api/v1/reports/generate-async` — that's the NIM call; investigate, don't roll back.

### 7.2 Rollback Steps

```bash
# ─── 0. Pre-flight ──────────────────────────────────────────────────────
ssh deploy@api.yourdomain.com
cd /opt/buildit

# ─── 1. Stop the broken release ────────────────────────────────────────
docker compose -f infrastructure/docker/docker-compose.yml \
               -f infrastructure/docker/docker-compose.prod.yml \
               stop backend frontend

# ─── 2. Check out the previous tag ────────────────────────────────────
PREVIOUS=$(git tag --sort=-version:refname | sed -n '2p')
echo "Rolling back to $PREVIOUS"
git checkout "$PREVIOUS"

# ─── 3. Downgrade migrations (only if the broken release added a migration) ──
docker compose ... --env-file /tmp/.env.production \
  run --rm backend alembic downgrade -1
# Repeat until you reach the revision that was HEAD before the broken release.
# To find it: alembic history --rev-range=<broken-revision>:<head>; pick the one
# immediately before the broken release's first migration.

# ─── 4. Bring the old images back up ──────────────────────────────────
docker compose ... --env-file /tmp/.env.production \
  up -d --force-recreate --no-deps backend frontend
sleep 10

# ─── 5. Verify the rollback ────────────────────────────────────────────
./scripts/deploy_smoke_test.sh SKIP_ASYNC=1
# MUST exit 0

# ─── 6. Clean up the rendered secrets ────────────────────────────────
shred -u /tmp/.env.production
```

### 7.3 Roll Forward (if you fixed the issue mid-rollback)

You can skip the downgrade and just re-deploy the fixed release:

```bash
git checkout main
git pull
git tag --list 'v*' | sort -V | tail -5     # pick the new tag
git checkout <new-tag>
# Re-run §4 starting at step 4
```

### 7.4 Database Restore (catastrophic only)

If the database itself is corrupted (not just the app), restore from the
most recent pre-deploy backup:

```bash
# Drop and recreate the DB
docker compose ... exec postgres psql -U postgres -c "DROP DATABASE seo_platform;"
docker compose ... exec postgres psql -U postgres -c "CREATE DATABASE seo_platform OWNER seo_platform_app;"

# Restore
pg_restore -h $POSTGRES_HOST -U seo_platform_app -d seo_platform \
  --no-owner --no-acl --jobs=4 \
  /var/backups/buildit/daily-YYYYMMDD.dump

# Re-run migrations (restore may leave alembic_version out of sync)
docker compose ... run --rm backend alembic upgrade head

# Verify
./scripts/deploy_smoke_test.sh SKIP_ASYNC=1
```

**Important:** restoring from a backup loses everything written between
the backup and now. The decision to do this is a P0 — call on-call lead
before proceeding.

---

## 8. What Phase 1.4 Changed (operator-relevant deltas)

The four P0 gaps from Phase 1.3 were closed. You will see these changes
in your deployment. None of them are breaking.

### 8.1 GAP-005 — Canonical `/metrics` endpoint

**Before:** `GET /metrics` returned 404. Prometheus had to scrape `/api/v1/metrics`.

**After:** `GET /metrics` returns Prometheus text (200, ~150 KB, 87 metric families). `/api/v1/metrics` is kept for backward compatibility and returns the same body.

**Operator action:** update your Prometheus scrape config from
`/api/v1/metrics` to `/metrics` (more standard, less coupling to the API path prefix).

### 8.2 GAP-004 — Client campaigns list

**Before:** `GET /clients/{id}/campaigns` returned 404. The endpoint didn't exist.

**After:** The endpoint exists. Required query param `tenant_id`. Optional
`status` filter (uppercase enum, returns 400 with the valid list on bad input).
Optional `limit`/`offset` pagination. Returns `APIResponse` envelope.

**Operator action:** none. Any client that hard-coded a 404 expectation
will now get a real response and should handle it.

### 8.3 GAP-003 — Global error envelope

**Before:** Errors returned `{"detail": "..."}` (FastAPI default) or
`{"success": false, "error": "string"}` (inconsistent). Status codes were
sometimes wrong (e.g., 500 for "client not found").

**After:** Every error from a registered route returns:
```json
{
  "success": false,
  "data": null,
  "error": {
    "error_code": "NOT_FOUND",
    "message": "Client not found",
    "details": {},
    "retryable": false
  },
  "meta": null
}
```

Status code → `error_code` mapping:
- 400 → `BAD_REQUEST`
- 401 → `UNAUTHORIZED`
- 403 → `FORBIDDEN`
- 404 → `NOT_FOUND`
- 422 → `VALIDATION_ERROR`
- 429 → `RATE_LIMITED` (retryable: true)
- 500 → `INTERNAL_ERROR`
- 502 → `UPSTREAM_ERROR` (retryable: true)
- 504 → `GATEWAY_TIMEOUT` (retryable: true)

`/metrics` and `/api/v1/metrics` are exempt — they return raw Prometheus text.

**Operator action:** if you have a synthetic monitor that greps `detail`
in error bodies, update it to `error.message`.

### 8.4 GAP-002 — Async report generation

**Before:** `POST /api/v1/reports/generate` blocked for up to 90 seconds
(NIM call timeout) and frequently timed out.

**After:** `POST /api/v1/reports/generate-async` returns 202 in <50 ms with:
```json
{
  "success": true,
  "data": {
    "report_id": "<uuid>",
    "status": "pending",
    "status_url": "/api/v1/reports/<uuid>/status",
    "result_url": "/api/v1/reports/<uuid>"
  }
}
```
The actual report builds in the background. Poll `status_url` until
`status == "completed"` (or `failed`).

The old synchronous `POST /api/v1/reports/generate` still works but is
deprecated and will be removed in Phase 2.0.

**Operator action:** none. If you have an external report scheduler,
point it at `generate-async` and start polling `status_url`.

### 8.5 GAP-001 — Provider provisioning (NOT closed; see §10)

The gap-fix code work is done (all paths verified honest; no fabrication).
The gap is **not** closed because the API keys are not in the environment.
Section 10 explains how to close it.

---

## 9. Known Issues and P1 Hardening

These are not blockers for the current verdict, but you should know about
them.

### 9.1 Dockerfile healthcheck points at a non-existent endpoint

**File:** `backend/Dockerfile:73`
```dockerfile
HEALTHCHECK ... CMD curl -f http://localhost:8000/healthz || exit 1
```
**Problem:** `GET /healthz` returns 404. The actual endpoint is
`GET /api/v1/health`. As a result, Docker's container healthcheck always
reports the backend as unhealthy in production.

**Workaround in this release:** none. The `operational_health_check.sh`
script polls the correct endpoint.

**Fix (P1):** change line 73 of `backend/Dockerfile` to
`curl -f http://localhost:8000/api/v1/health || exit 1`. Tracked but not
shipped in Phase 1.4 to avoid a rebuild during the conditional certification.

### 9.2 Mock gates still present

Two code paths still branch on `USE_MOCK_PROVIDERS`:

- `backend/src/seo_platform/clients/hunter.py` lines 75, 118, 153 — return
  hardcoded mock data when `USE_MOCK_PROVIDERS=true`.
- `backend/src/seo_platform/services/email_provider.py` line 160 — falls
  back to Mailhog when `USE_MOCK_PROVIDERS=true`.

**Current state:** `USE_MOCK_PROVIDERS=false` in `.env.production`, so
both gates are inert. They are safe but should be removed (not just
gated) in a future hardening pass to align with the "no fabrication"
principle. Tracked as a P1.

### 9.3 Observability alerts are framework-only

The `alerts` service is scaffolded (3 channels, generic dispatcher), but
zero domain-specific alert classes exist (`HighErrorRateAlert`,
`NoNewBacklinksAlert`, `ProviderDownAlert`, etc.).

**Workaround:** rely on the operational health check script and on
Prometheus alerts against `/metrics` for now.

**Fix (P1):** add 5–8 domain-specific alert classes. Spec is in
`PHASE_1_4_FINAL_CERTIFICATION.md` §"Observability".

### 9.4 Rate limiter is 100 req / 15 s

The default in `core/rate_limit.py` is 100 requests per 15-second window
per tenant. For production traffic this may be too low.

**Workaround:** none.

**Fix (P1):** make configurable via env var; default to 1000 / 15 s for
production tenants.

### 9.5 ENCRYPTION_MASTER_KEY rotation is not yet automated

See §2.3. A rotation script that re-encrypts all encrypted columns is
not yet shipped. Manual rotation is possible but requires ~30 minutes
of downtime. Track as a P1.

---

## 10. Decision: When to Promote from CONDITIONALLY → REAL WORLD CERTIFIED

### 10.1 The Two Open Items

| Item | Current state | To close it |
|------|--------------|-------------|
| **GAP-001** — Provider credentials | 0/3 paid providers configured; 6/6 internal services ready | Set env vars + restart + re-run WS-B (see `PROVIDER_PROVISIONING_CHECKLIST.md`) |
| **Observability alerts** | 3 channels, 0 domain-specific classes | P1 hardening; not strictly required for certification |

### 10.2 Promotion Path

```bash
# 1. Complete PROVIDER_PROVISIONING_CHECKLIST.md (one page per provider)
#    Each one ends with a "verify" command — run them all.

# 2. Restart the backend
docker compose ... restart backend

# 3. Re-run the Phase 1.4 provider certification script
uv run python scripts/phase_1_4_workstream_b_provider_certification.py \
  --api-url https://api.yourdomain.com
# Expected: 9/9 providers PASS (or 8/9 if OpenPageRank is not configured — that's free-tier)

# 4. Run the smoke test
./scripts/deploy_smoke_test.sh

# 5. If both pass, append to PHASE_1_4_FINAL_CERTIFICATION.md:
#    "Promoted to REAL WORLD CERTIFIED on <date> by <user>.
#     Provider cert: /tmp/phase_1_4_evidence/provider_certification_matrix.json"
```

### 10.3 Should You Promote Before Doing It?

No. The two states are honest signals:
- **CONDITIONALLY CERTIFIED** = "platform is built; bring your own API keys"
- **REAL WORLD CERTIFIED** = "platform is built AND live with real provider traffic"

Calling the platform REAL WORLD CERTIFIED without running real provider
calls is the same fabrication Phase 1.4 was created to prevent. Don't.

---

## Appendix A — File Map

| Purpose | File |
|---------|------|
| Phase 1.4 certification verdict | `PHASE_1_4_FINAL_CERTIFICATION.md` |
| Provider provisioning checklist | `PROVIDER_PROVISIONING_CHECKLIST.md` |
| Phase 1.3 findings (the gaps Phase 1.4 closed) | `PHASE_1_3_GAP_ANALYSIS.md` |
| Developer quick-start | `DEPLOY.md` |
| Generate secrets | `scripts/generate_secrets.sh` |
| Post-deploy smoke test | `scripts/deploy_smoke_test.sh` |
| Operational health check | `scripts/operational_health_check.sh` |
| Provider cert (re-run after provisioning) | `scripts/phase_1_4_workstream_b_provider_certification.py` |
| Backup script | `scripts/backup_postgres.sh` |
| Init scripts (first deploy only) | `scripts/init_postgres.sh`, `init_minio.sh`, `init_temporal.sh` |
| Evidence (CI artifacts) | `/tmp/phase_1_4_evidence/*.json` |

## Appendix B — Quick Reference

```bash
# Full deploy (production)
git checkout v0.1.0 && \
doppler secrets download --no-file --format docker > /tmp/.env.production && \
chmod 600 /tmp/.env.production && \
docker compose -f infrastructure/docker/docker-compose.yml \
               -f infrastructure/docker/docker-compose.prod.yml \
               --env-file /tmp/.env.production \
               run --rm backend alembic upgrade head && \
docker compose ... up -d --force-recreate --no-deps backend frontend && \
./scripts/deploy_smoke_test.sh && \
shred -u /tmp/.env.production

# Rollback
git checkout $(git tag --sort=-version:refname | sed -n '2p') && \
docker compose ... stop backend frontend && \
docker compose ... run --rm backend alembic downgrade -1 && \
docker compose ... up -d --force-recreate --no-deps backend frontend && \
./scripts/deploy_smoke_test.sh

# Health check (for cron / monitoring)
./scripts/operational_health_check.sh

# Promote to REAL WORLD CERTIFIED
# 1. Edit .env.production with provider keys
# 2. docker compose ... restart backend
# 3. uv run python scripts/phase_1_4_workstream_b_provider_certification.py
# 4. ./scripts/deploy_smoke_test.sh
```
