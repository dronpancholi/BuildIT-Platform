# BuildIT — Provider Provisioning Checklist

> **Purpose:** Step-by-step guide to closing the **GAP-001** open item from
> Phase 1.4 and promoting the deployment from
> **CONDITIONALLY CERTIFIED → REAL WORLD CERTIFIED**.
>
> **Current state:** 0/4 paid providers configured. The platform runs
> honestly — no fabrication, no mock data returns — but external paid
> capabilities are disabled and `/api/v1/health` reports
> `external_apis: degraded` with the message
> `"No external SEO APIs configured. Set DATAFORSEO_LOGIN/PASSWORD, AHREFS_API_KEY, HUNTER_API_KEY"`.
>
> **Time to complete:** ~30 minutes if you have the API keys ready;
> 1–3 days if you need to sign up for the providers first.
>
> **Owner:** Whoever has the budget authority for SaaS subscriptions.

---

## Table of Contents

1. [Current Provider Matrix](#1-current-provider-matrix)
2. [Pre-Flight Checklist](#2-pre-flight-checklist)
3. [Provider 1: DataForSEO](#3-provider-1-dataforseo)
4. [Provider 2: Ahrefs](#4-provider-2-ahrefs)
5. [Provider 3: Hunter](#5-provider-3-hunter)
6. [Provider 4: SendGrid (or Postmark) — Email](#6-provider-4-sendgrid-or-postmark--email)
7. [Internal Services (no action needed)](#7-internal-services-no-action-needed)
8. [Final Verification: Promote to REAL WORLD CERTIFIED](#8-final-verification-promote-to-real-world-certified)
9. [Rollback: Disabling a Provider](#9-rollback-disabling-a-provider)

---

## 1. Current Provider Matrix

Snapshot from `/tmp/phase_1_4_evidence/provider_certification_matrix.json`:

| # | Provider | Kind | Status | Env vars | What it powers |
|---|----------|------|--------|----------|---------------|
| 1 | **DataForSEO** | external_paid | BLOCKED | `DATAFORSEO_LOGIN`, `DATAFORSEO_PASSWORD` | Keyword research, SERP data, search volume |
| 2 | **Ahrefs** | external_paid | BLOCKED | `AHREFS_API_KEY` | Backlink analysis, domain rating, competitor research |
| 3 | **Hunter** | external_paid | BLOCKED | `HUNTER_API_KEY` | Email discovery (find contact emails for prospects) |
| 4 | **SendGrid** | external_paid (email) | BLOCKED | `SENDGRID_API_KEY` | Transactional + outreach email delivery |
| 5 | Mailhog | internal | READY | — | Local SMTP capture (dev only) |
| 6 | Scrapling | internal | READY | — | Browser-like HTTP fetcher with stealth |
| 7 | SearXNG | internal_self_hosted | NOT-RUNNING | — | Meta-search engine (drop-in for SERP queries) |
| 8 | OpenPageRank | external_free_tier | READY | — | Domain/page authority (no key needed) |
| 9 | Trafilatura | internal | READY | — | Boilerplate extraction from HTML |

**To promote to REAL WORLD CERTIFIED you must close providers 1, 2, 3, and 4.** Providers 5–9 require no action; SearXNG is a separate deployment (see §7.3).

---

## 2. Pre-Flight Checklist

Before you start:

- [ ] You have a credit card on file (or a pre-paid balance) with each provider
- [ ] You have a 1Password / Vault entry ready to store each new key
- [ ] You have SSH access to the production host
- [ ] You can edit `.env.production` (or the secrets manager config) on the production host
- [ ] You can restart the backend (`docker compose restart backend` or equivalent)
- [ ] The smoke test passes *before* you start (`./scripts/deploy_smoke_test.sh` exits 0)
- [ ] You have read `DEPLOYMENT_RUNBOOK.md` §4 (the 12-step deploy) and §7 (rollback)

**Order of operations:** sign up for all four providers in parallel (they don't depend on each other), then apply the keys in a single coordinated change with a smoke test at the end.

---

## 3. Provider 1: DataForSEO

### 3.1 What It Powers

- Keyword research (search volume, keyword difficulty, CPC)
- SERP feature analysis
- Competitor domain data
- On-page SEO checks (limited)

### 3.2 Sign Up

1. Go to https://dataforseo.com
2. Click **Sign Up** (top right)
3. Create a Business or Individual account
4. Add a payment method (credit card, wire for enterprise)
5. **Wait for email confirmation** — this can take 1–24 hours

### 3.3 Generate Credentials

1. Log in to https://app.dataforseo.com
2. Navigate to **API Access** (left sidebar)
3. Your **login** is shown at the top of the page (e.g., `john.doe@example.com`)
4. Your **password** is the same as your account password. **You can also create API-only credentials** under **API Access → API Keys** if you want a non-password credential.
5. Test the credential in the DataForSEO dashboard using their built-in playground (should return a real response, not an error).

### 3.4 Configure in BuildIT

Add to `.env.production` (or your secrets manager):

```bash
DATAFORSEO_LOGIN=<your-login-email>
DATAFORSEO_PASSWORD=<your-api-password>
```

### 3.5 Verify (do this AFTER restarting the backend — see §8)

```bash
# Single-shot test from the host
docker compose -f infrastructure/docker/docker-compose.yml \
               -f infrastructure/docker/docker-compose.prod.yml \
               exec backend python -c "
import asyncio
from seo_platform.clients.dataforseo import DataForSEOClient

async def main():
    c = DataForSEOClient()
    try:
        result = await c.get_search_volume(['seo platform'])
        print('OK:', result)
    finally:
        await c.close()

asyncio.run(main())
"
```

**Expected output:** a JSON object with `search_volume: <number>` for the
keyword `seo platform` (around 10000–50000 depending on month).

**If it fails:** check (1) credentials are correct, (2) account is verified
and has balance, (3) outbound HTTPS to `api.dataforseo.com:443` is allowed.

### 3.6 Cost Guardrails

DataForSEO charges per API call. The default scraper is set to 3 retries
(`SCRAPER_RETRY_ATTEMPTS=3`). To avoid surprise bills, set rate limits:

```bash
# In .env.production (custom — not yet shipped in default config)
DATAFORSEO_RATE_LIMIT_PER_MINUTE=60
```

Tracked as a P1; if not set, the rate is effectively unbounded.

---

## 4. Provider 2: Ahrefs

### 4.1 What It Powers

- Backlink analysis (who links to a domain)
- Domain Rating / URL Rating
- Referring domains
- Anchor text distribution
- Competitor research

### 4.2 Sign Up

1. Go to https://ahrefs.com
2. Click **Start your free trial** (or **Subscribe** if you have an account)
3. **Choose at least the "Lite" plan** — the API is gated behind a paid subscription. (Lite is $29/month as of 2026; check current pricing.)
4. **Wait for account activation** (usually instant for credit-card signups)

### 4.3 Generate Credentials

1. Log in to https://ahrefs.com
2. Click your avatar (top right) → **Settings**
3. Go to **API** (left sidebar)
4. Click **Generate API token**
5. **Copy the token immediately** — Ahrefs only shows it once
6. Test the token:
   ```bash
   curl -H "Authorization: Bearer <token>" \
        "https://api.ahrefs.com/v3/site-explorer/overview?target=ahrefs.com&date=2026-01-01"
   ```
   **Expected:** a JSON object with `"metrics"` field.

### 4.4 Configure in BuildIT

```bash
AHREFS_API_KEY=<your-token>
```

### 4.5 Verify (after restart)

```bash
docker compose ... exec backend python -c "
import asyncio
from seo_platform.clients.ahrefs import AhrefsClient

async def main():
    c = AhrefsClient()
    result = await c.get_domain_rating('ahrefs.com')
    print('DR:', result)
    await c.close()

asyncio.run(main())
"
```

**Expected output:** `DomainRatingResult(domain='ahrefs.com', rating=90–100, ...)` — Ahrefs' own DR should be 90+.

### 4.6 Cost Guardrails

Ahrefs charges per API row. The default backlink discovery can be expensive
(it walks the full backlink graph). The discover endpoint already caps results
to a configurable limit. Set a budget alarm in the Ahrefs dashboard and a
monthly spend cap if available.

---

## 5. Provider 3: Hunter

### 5.1 What It Powers

- Email discovery: given a domain and a person's name, find their email
- Email verification: confirm a found email is deliverable
- Domain search: list all emails Hunter knows about for a domain

### 5.2 Sign Up

1. Go to https://hunter.io
2. Sign up for a paid plan (Free tier exists but has hard limits; **you need at least "Starter"** = $49/month for production use)
3. Verify your email

### 5.3 Generate Credentials

1. Log in to https://hunter.io
2. Click your avatar → **API**
3. Your **API key** is shown on the API page
4. Test:
   ```bash
   curl "https://api.hunter.io/v2/account?api_key=<key>"
   ```
   **Expected:** JSON with `data.plan` showing your plan name and `data.requests` quota.

### 5.4 Configure in BuildIT

```bash
HUNTER_API_KEY=<your-key>
```

### 5.5 Verify (after restart)

```bash
docker compose ... exec backend python -c "
import asyncio
from seo_platform.clients.hunter import HunterClient

async def main():
    c = HunterClient()
    result = await c.find_email(domain='stripe.com', first_name='Patrick', last_name='Collison')
    print('email:', result)
    await c.close()

asyncio.run(main())
"
```

**Expected output:** an email like `patrick@stripe.com` with a confidence score 70–95.

### 5.6 Cost Guardrails

Hunter charges per search and per verification. The BuildIT backlink engine
uses Hunter for both discovery and verification. Set a monthly budget alert
in Hunter's dashboard.

**Note on the existing mock gate:** `backend/src/seo_platform/clients/hunter.py`
lines 75, 118, 153 contain a `USE_MOCK_PROVIDERS` check that returns hardcoded
data. With `USE_MOCK_PROVIDERS=false` (production default), this is inert.
A P1 hardening item is to **delete the mock return paths entirely** rather
than gate them. See `DEPLOYMENT_RUNBOOK.md` §9.2.

---

## 6. Provider 4: SendGrid (or Postmark) — Email

### 6.1 What It Powers

- Outreach email delivery (cold emails to prospects)
- Transactional email (password resets, reports to clients)
- Webhook for bounce/spam reports (delivered, opened, replied)

### 6.2 Choose a Provider

- **SendGrid** — $15/month (Essentials) covers 50k emails. Best for high volume.
- **Postmark** — $15/month (500 emails free). Better deliverability reputation for transactional. Use Postmark for transactional, SendGrid for bulk outreach if you split.

For BuildIT, **either works**. SendGrid is the default; the env var name
in `.env.production` is `SENDGRID_API_KEY`. To use Postmark, swap the SMTP
host/port and use `POSTMARK_API_KEY` instead (the email provider code
auto-detects the format).

### 6.3 Sign Up — SendGrid

1. Go to https://sendgrid.com
2. Sign up for the **Essentials** plan
3. **Verify a sender domain** (this is critical; without it, all your emails go to spam):
   - Settings → Sender Authentication → Authenticate Your Domain
   - Add the DNS records SendGrid gives you to your domain's DNS
   - This takes 1–24 hours to propagate
4. **Verify a single address** (faster alternative for testing):
   - Settings → Sender Authentication → Verify a Single Sender
   - Use a real mailbox you control

### 6.4 Generate Credentials

1. Log in to https://app.sendgrid.com
2. Settings → **API Keys** (left sidebar)
3. Click **Create API Key**
4. Choose **Restricted Access** and grant at minimum:
   - `Mail Send` → Full Access
   - `Suppressions` → Read Access
5. **Copy the key immediately** — SendGrid only shows it once
6. Test:
   ```bash
   curl -X POST "https://api.sendgrid.com/v3/mail/send" \
        -H "Authorization: Bearer <key>" \
        -H "Content-Type: application/json" \
        -d '{"personalizations":[{"to":[{"email":"you@yourdomain.com"}]}],"from":{"email":"noreply@yourdomain.com"},"subject":"Test","content":[{"type":"text/plain","value":"Hello"}]}'
   ```
   **Expected:** HTTP 202 Accepted.

### 6.5 Configure in BuildIT

```bash
# For SendGrid:
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASS=<SENDGRID_API_KEY>
SENDGRID_API_KEY=<SENDGRID_API_KEY>

# OR for Postmark (alternative):
SMTP_HOST=smtp.postmarkapp.com
SMTP_PORT=2525
SMTP_USER=<POSTMARK_SERVER_TOKEN>
SMTP_PASS=<POSTMARK_SERVER_TOKEN>
POSTMARK_API_KEY=<POSTMARK_SERVER_TOKEN>
```

### 6.6 Verify (after restart)

```bash
docker compose ... exec backend python -c "
import asyncio
from seo_platform.services.email_provider import email_provider

async def main():
    result = await email_provider.send(
        to='you@yourdomain.com',
        subject='BuildIT Email Test',
        body='If you got this, SendGrid is wired correctly.'
    )
    print('sent:', result)

asyncio.run(main())
"
```

**Expected output:** `sent: <message-id>` and an email in your inbox within
30 seconds.

**If it fails with 401:** API key is wrong or revoked.
**If it fails with 403:** sender domain not verified.
**If it goes to spam:** the sender domain's SPF/DKIM records are wrong.

### 6.7 Cost Guardrails

SendGrid's pricing escalates with volume. For BuildIT's backlink outreach,
expect ~100–1000 emails per campaign per tenant. The default
`SCRAPER_RETRY_ATTEMPTS=3` does not apply to email retries; failed sends
are persisted to the `outreach_threads` table and retried by the worker.

---

## 7. Internal Services (no action needed)

These are part of the platform, not external providers. They are READY
in the current deployment.

### 7.1 Mailhog (local SMTP capture)

**What it is:** A fake SMTP server that captures outgoing emails and shows
them in a web UI at http://yourdomain:8025. **Dev only — never use in
production.**

**Current state:** if `USE_MOCK_PROVIDERS=true`, emails go to Mailhog. With
`USE_MOCK_PROVIDERS=false` (production default), the real ESP is used and
Mailhog is bypassed.

**No action required for production.**

### 7.2 Scrapling (HTTP fetcher with stealth)

**What it is:** A drop-in `requests` replacement that handles JS-rendered
pages, anti-bot detection, and retries.

**Current state:** runs in-process inside the backend container. No external
dependency.

**No action required.** To check it's working, the smoke test already hits a
provider-using endpoint (link-verification) which exercises the HTTP stack.

### 7.3 SearXNG (meta-search engine)

**What it is:** A self-hosted meta-search engine that aggregates Google,
Bing, DuckDuckGo results. Used as a fallback SERP source.

**Current state:** NOT-RUNNING. The container is not deployed in
`docker-compose.prod.yml`. The code path is in
`backend/src/seo_platform/clients/searxng.py` and is wired up, but the
SearXNG HTTP service itself needs to be deployed.

**To deploy (optional):**

```bash
# Add to infrastructure/docker/docker-compose.yml (or a new file)
searxng:
  image: searxng/searxng:latest
  container_name: seo-searxng
  ports:
    - "8080:8080"
  environment:
    - SEARXNG_SECRET=<generate-with-openssl-rand-base64-32>
  restart: unless-stopped

# Then point the client at it:
SEARXNG_BASE_URL=http://searxng:8080
```

**Not required for REAL WORLD CERTIFIED.** SearXNG is an internal fallback;
the primary SERP path uses DataForSEO.

### 7.4 OpenPageRank

**What it is:** Free-tier domain/page authority lookups. No key required.

**Current state:** READY. Calls the free API at https://www.openpagerank.com.

**Caveat:** the free tier has rate limits (~50 req/min) and accuracy is lower
than paid alternatives (Moz, Majestic, Ahrefs). For production, prefer
Ahrefs (§4) when configured.

**No action required.**

### 7.5 Trafilatura

**What it is:** A Python library for extracting article text from HTML.
No external service, runs in-process.

**No action required.**

---

## 8. Final Verification: Promote to REAL WORLD CERTIFIED

Once all four providers are configured:

### 8.1 Apply the Changes

```bash
ssh deploy@api.yourdomain.com
cd /opt/buildit

# 1. Edit .env.production (or re-render from secrets manager)
#    Add the four new keys. Save.

# 2. Restart the backend (the env vars are read at process start)
docker compose -f infrastructure/docker/docker-compose.yml \
               -f infrastructure/docker/docker-compose.prod.yml \
               up -d --force-recreate --no-deps backend

# 3. Wait for health
for i in {1..30}; do
    sleep 2
    if curl -fsS http://localhost:8000/api/v1/health >/dev/null; then
        break
    fi
done
```

### 8.2 Run the Phase 1.4 Provider Certification

```bash
# This script re-tests every provider (or set --api-url for remote)
uv run python scripts/phase_1_4_workstream_b_provider_certification.py
```

**Expected output:** 9/9 providers (or 8/9 if OpenPageRank is intentionally
skipped). The four newly-configured paid providers should show
`status: PASS` with a real API call evidence (e.g.,
`"DataForSEO: 1/1 calls succeeded, avg latency 245ms"`).

### 8.3 Run the Smoke Test

```bash
./scripts/deploy_smoke_test.sh
```

**Expected output:** all 18 assertions pass, including the
`external_apis` health check now showing `healthy` instead of `degraded`.

### 8.4 Run the Operational Health Check

```bash
./scripts/operational_health_check.sh
```

**Expected output:** every component `healthy`, including `external_apis`.
Overall status `healthy`. Exit code `0`.

### 8.5 Update the Certification Record

Open `PHASE_1_4_FINAL_CERTIFICATION.md` and add at the bottom:

```markdown
---

## Promotion to REAL WORLD CERTIFIED

**Date:** YYYY-MM-DD
**Promoter:** <your name>
**Evidence:** /tmp/phase_1_4_evidence/provider_certification_matrix.json (regenerated)
**Smoke test:** scripts/deploy_smoke_test.sh — 18/18 pass
**Health:** operational_health_check.sh — exit 0, all components healthy

All four previously-blocked providers are now configured and verified:
- DataForSEO: <DATAFORSEO_LOGIN is set, last call 2026-XX-XX HH:MM:SS>
- Ahrefs: <AHREFS_API_KEY is set, last call ...>
- Hunter: <HUNTER_API_KEY is set, last call ...>
- SendGrid: <SENDGRID_API_KEY is set, last send ...>
```

### 8.6 Tell the Team

- Post in `#deploys` (or your team's channel): "BuildIT promoted to REAL WORLD CERTIFIED at HH:MM. Phase 1.4 closed."
- Update the dashboard (if you have one) showing the certification status.
- Optional: announce to a wider audience.

---

## 9. Rollback: Disabling a Provider

If a provider key needs to be revoked (employee leaves, key leaked,
account compromised):

### 9.1 Immediate

1. **Disable the key at the provider's dashboard** (revoke / delete the
   API key) — this is faster than waiting for a config change to propagate.
2. Set the env var to empty in `.env.production`:
   ```bash
   HUNTER_API_KEY=
   ```
3. Restart the backend.
4. The smoke test's `external_apis` check will go from `healthy` back to
   `degraded` with the appropriate message. The deployment is back to
   CONDITIONALLY CERTIFIED, which is **safe and honest** — better than
   silently failing.

### 9.2 If the Provider Is Costing Too Much

1. Set the env var to empty (as above).
2. Investigate the usage logs in the provider's dashboard.
3. If intentional use, set rate limits (where supported) or per-tenant
   spend caps.

### 9.3 If You Want to Disable Without Revoking

Set the env var to empty and restart. The provider code will report
`degraded` but not crash. The BuildIT application code handles missing
provider credentials gracefully (returns explicit errors, does not
fabricate data).

---

## Appendix — Quick Verification Commands

Run these from the production host (substitute `<provider>` and `<key>`):

```bash
# DataForSEO
docker compose ... exec backend curl -s -u "<DATAFORSEO_LOGIN>:<DATAFORSEO_PASSWORD>" \
    "https://api.dataforseo.com/v3/appendix/user_data" | head -c 200
# Expected: JSON with "login": "..."

# Ahrefs
docker compose ... exec backend curl -s \
    -H "Authorization: Bearer <AHREFS_API_KEY>" \
    "https://api.ahrefs.com/v3/account" | head -c 200
# Expected: JSON with "api_units_left": <number>

# Hunter
docker compose ... exec backend curl -s \
    "https://api.hunter.io/v2/account?api_key=<HUNTER_API_KEY>" | head -c 200
# Expected: JSON with "data.plan": "..."

# SendGrid
docker compose ... exec backend curl -s -X POST \
    -H "Authorization: Bearer <SENDGRID_API_KEY>" \
    -H "Content-Type: application/json" \
    -d '{"personalizations":[{"to":[{"email":"<your-email>"}]}],"from":{"email":"<your-verified-sender>"},"subject":"BuildIT key check","content":[{"type":"text/plain","value":"ok"}]}' \
    "https://api.sendgrid.com/v3/mail/send" -w "\nHTTP %{http_code}\n"
# Expected: HTTP 202
```

If any of these fail, the provider is not correctly configured. Do **not**
declare REAL WORLD CERTIFIED until all four return 2xx.
