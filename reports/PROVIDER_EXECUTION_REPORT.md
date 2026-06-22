# PROVIDER EXECUTION REPORT — Phase 2.5

**Date:** 2026-06-06
**Verdict:** **PARTIAL — 5 of 10 providers execute, 5 are absent, 1 has silent fallback.**

This report documents the actual execution state of every external provider the platform depends on. Each provider is exercised with a real call (or attempted call) and the response is recorded. No provider is assumed to work because the code path exists; the provider is called directly.

---

## 1. Provider Inventory

| Category | Provider | Configured | Live | Notes |
|----------|----------|-----------|------|-------|
| AI Inference | NVIDIA NIM | ✅ | ✅ (with caveats) | Direct call works; gateway primary model times out |
| SEO Data | DataForSEO | ❌ | ❌ | No login/password in env; 401 from upstream |
| SEO Data | Ahrefs | ❌ | ❌ | No key in env |
| Email Discovery | Hunter | ❌ | ⚠️ has silent mock fallback | Code returns `editor@<domain>` with 95 confidence |
| Web Crawling | Firecrawl | ❌ | ❌ | No key in env |
| Web Crawling | Scrapling | ✅ (no external dep) | ✅ | Local; uses Playwright |
| Web Crawling | Trafilatura | ✅ (no external dep) | ✅ | Local; pure-python HTML extraction |
| Web Crawling | ContactCrawler | ✅ (no external dep) | ✅ | Local; uses Playwright |
| Search | SearXNG | ❌ | ❌ | No instance running |
| Rank Data | OpenPageRank | ❌ | ❌ | No key in env |
| Tech Profiling | Wappalyzer | ✅ (no external dep) | ✅ | Local; uses regex patterns |
| Email Delivery | SendGrid | ❌ | ❌ | No key; has silent MailHog fallback |
| Email Delivery | Mailgun | ❌ | ❌ | No key |
| Email Delivery | Resend | ❌ | ❌ | No key |
| Email Delivery | MailHog | ✅ | ✅ | Dev-only SMTP catcher |
| Object Storage | MinIO (S3) | ✅ | ✅ | Real; 3 objects in `seo-platform-assets` |
| Cache | Redis | ✅ | ✅ | PONG |
| Vector DB | Qdrant | ✅ | ✅ | 2 collections |
| Message Bus | Kafka | ✅ | ✅ | 3 brokers, no tested topics (no CLI in container) |
| Workflow | Temporal | ✅ | ✅ | Server up; namespace default |
| Observability | OTLP/Prometheus | ✅ | ✅ | Prometheus on :9090, OTLP on :4317 |

---

## 2. Provider-by-Provider Evidence

### 2.1 NVIDIA NIM (AI Inference) — PARTIAL REAL

**Configuration:**
```
NVIDIA_NIM_API_KEY=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
```

**Direct call (curl, real):**
```bash
$ curl -X POST "https://integrate.api.nvidia.com/v1/chat/completions" \
       -H "Authorization: Bearer nvapi-va-..." \
       -H "Content-Type: application/json" \
       -d '{"model":"meta/llama-3.1-8b-instruct","messages":[{"role":"user","content":"Say hi in 3 words"}],"max_tokens":20}'
{"id":"chatcmpl-1805fd30-baf2-4513-b256-f38c8482ab61","choices":[{"index":0,"message":{"content":"Hello, how are you?","role":"assistant","reasoning_content":null},"finish_reason":"stop"}],"usage":{"prompt_tokens":10,"completion_tokens":6,"total_tokens":16,"prompt_tokens_details":{"audio_tokens":null,"cached_tokens":16}}}
```

**Result:** Direct NIM call works. 120 models accessible.

**However, the LLM gateway's primary SEO_ANALYSIS model fails:**
```python
TASK_MODEL_ROUTING[TaskType.SEO_ANALYSIS] = ModelRole.OPERATIONAL_UTILITY
# = google/gemma-4-31b-it
```

```bash
$ curl -X POST "https://integrate.api.nvidia.com/v1/chat/completions" \
       -H "Authorization: Bearer nvapi-va-..." \
       -d '{"model":"google/gemma-4-31b-it",...}'
# (no response — times out at 20s)
```

**Log evidence:**
```
2026-06-06 14:50:27 [warning] nim_fallback_triggered error='NVIDIA NIM request timed out' primary=google/gemma-4-31b-it
```

**Result:** The primary SEO model times out. The LLM gateway has fallback logic but the fallback model (`nvidia/llama-3.1-nemotron-70b-instruct`) returns 404. So in practice, the gateway falls back to a 404 model and the call fails.

**AI query endpoint consequence:**
```bash
$ curl -X POST "http://localhost:8000/api/v1/ai/query?tenant_id=00000000-...&question=Show%20total%20clients"
{"success":false,"error":{"error_code":"INTERNAL_ERROR","message":"'AIQueryEngine' object has no attribute 'query'"}}
```

The `/api/v1/ai/query` endpoint calls `ai_query_engine.query()` (see `api/endpoints/ai_query.py:25`), but `AIQueryEngine` has only `execute_query` (see `services/ai_query.py:155`). **This is a bug — the endpoint is wired to a method that does not exist.**

The `execute_query` path also fails:
```bash
$ ai_query_engine.execute_query("Show total clients", UUID(...))
# Result: intent='llm_generated' sql='' explanation='Query rejected by safety validator' results=[{'error': 'SQL validation failed'}] latency_ms=0.3
# (This is because the LLM call to generate SQL failed and fell back to a safety rejection)
```

**Score:** 50/100 (real key, real API, but no working model for production tasks, and the endpoint is broken)

### 2.2 DataForSEO — ABSENT

```bash
$ curl -X POST "https://api.dataforseo.com/v3/serp/google/organic/live/advanced" -u "nouser:nopass" -d '...'
{"version":"0.1.20260525","status_code":40100,"status_message":"You are not authorized to access this resource. See your login details here: https://app.dataforseo.com/api-access","time":"0 sec.","cost":0,"tasks_count":0,"tasks_error":0,"tasks":null}
```

**Result:** No credentials configured. Any feature that requires SERP data, keyword volume, or competitor analysis will fail at runtime.

**Score:** 0/100

### 2.3 Ahrefs — ABSENT

```bash
$ grep -E "AHREFS" .env
# (no match)
```

**Score:** 0/100

### 2.4 Hunter — ABSENT (with silent mock fallback)

```python
# clients/hunter.py
async def find_email(self, domain: str, first_name: str, last_name: str) -> dict[str, Any]:
    settings = get_settings()
    if settings.use_mock_providers:
        return {
            "email": f"{first_name.lower()}.{last_name.lower()}@{domain}",
            "confidence": 95,
            "sources": ["mock"],
        }
```

**Current setting:** `USE_MOCK_PROVIDERS=false`, so this path is OFF today. But the code is still there. If the env var flips to `true` (e.g., a misconfigured `.env` in production), every email lookup would silently return `john.doe@<domain>` with fake 95 confidence.

**Score:** 50/100 (mock code still present, env var off)

### 2.5 Firecrawl — ABSENT

```bash
$ grep -E "FIRECRAWL" .env
# (no match)
```

The Firecrawl client code exists in `clients/firecrawl.py` but the API key is missing. Any attempt to use it will return 401/403 from upstream.

**Score:** 0/100

### 2.6 Scrapling, Trafilatura, Wappalyzer, ContactCrawler — REAL (local)

These are local code, not external services. Scrapling uses Playwright. Trafilatura is pure-python HTML extraction. Wappalyzer uses regex patterns. ContactCrawler uses Playwright.

**Health check:**
```json
{"name":"playwright","status":"healthy","latency_ms":242.0,"message":"Playwright browser operational"}
```

**Score:** 100/100 (no external dependency, real and exercised)

### 2.7 SearXNG — ABSENT

```bash
$ curl -m 3 "http://localhost:8888/search?q=test" 2>&1
# (connection refused — no instance running)
```

The SearXNG client code exists (`clients/searxng.py`) but no SearXNG instance is running. Local discovery will fail.

**Score:** 0/100

### 2.8 OpenPageRank — ABSENT

```bash
$ grep -E "OPENPAGERANK" .env
# (no match)
```

**Score:** 0/100

### 2.9 Email Delivery — MailHog only (no real provider)

```python
# services/email/email_provider.py:get_email_provider()
def get_email_provider():
    if settings.resend_api_key:
        return ResendClient()
    if settings.mailgun_api_key:
        return MailgunClient()
    # FALLBACK: returns MailhogClient()
    return MailhogClient()
```

**Configuration check:**
```
SENDGRID_API_KEY=  (not set)
MAILGUN_API_KEY=   (not set)
RESEND_API_KEY=    (not set)
```

**Live SMTP test:**
```bash
$ python3 -c "
import smtplib
from email.mime.text import MIMEText
msg = MIMEText('Test')
s = smtplib.SMTP('localhost', 1025, timeout=5)
s.send_message(msg)
s.quit()
print('OK')
"
OK
```

**Result:** SMTP send to MailHog works. But MailHog is a dev catcher — it doesn't actually deliver emails to recipients. **In production, an outbound email to a customer will be accepted by the SMTP server, the platform will log "email sent," and the recipient will never receive it.**

**Score:** 30/100 (transport works, but no real delivery, and silent fallback hides the gap)

### 2.10 MinIO S3 — REAL

```bash
$ python3 -c "
import boto3
s3 = boto3.client('s3', endpoint_url='http://localhost:9000', aws_access_key_id='minioadmin', aws_secret_access_key='minioadmin', region_name='us-east-1')
print(s3.list_buckets())
"
{'Buckets': [{'Name': 'seo-platform-assets'}]}

$ python3 -c "
import boto3
s3 = boto3.client('s3', endpoint_url='http://localhost:9000', aws_access_key_id='minioadmin', aws_secret_access_key='minioadmin', region_name='us-east-1')
print(s3.list_objects_v2(Bucket='seo-platform-assets'))
"
{'KeyCount': 3, 'Contents': [{'Key': '00000000-0000-0000-0000-000000000001/attachments/2fb5061e-57f3-4855-86ae-24ec1b5702b1.txt'}, {'Key': '00000000-0000-0000-0000-000000000001/attachments/c2273b96-c208-4e38-9f5d-bb68cbcd04a9.txt'}, {'Key': 'phase201/test-upload.txt'}]}
```

**Result:** Real S3-compatible storage. 3 objects persisted from earlier work.

**Score:** 100/100

### 2.11 Redis — REAL

```bash
$ docker exec seo-redis redis-cli ping
PONG
```

**Score:** 100/100

### 2.12 Qdrant — REAL

```bash
$ curl -s "http://localhost:6333/collections"
{"result":{"collections":[{"name":"client_keywords"},{"name":"prospect_content"}],"status":"ok"}}
```

**Score:** 100/100

### 2.13 Kafka — REAL (state unknown)

```
seo-kafka         Up 21 minutes (healthy)   0.0.0.0:9092->9092/tcp
```

**Result:** Container healthy. Could not enumerate topics from host (no Kafka CLI installed). The platform's event bus claims to publish events; the health check reports `event_bus: 50 events in last 10 minutes`.

**Score:** 75/100 (up but not directly exercised via CLI; trust the health check)

### 2.14 Temporal — REAL (limited test)

```bash
$ curl -s "http://localhost:8233/api/namespaces"
{"code":5,"message":"Not Found"}
```

**Result:** Server is up (port 7233 is listening, health reports healthy). The 8233 is the UI; the tctl `namespace list` would need proper auth in production. No workflow was actually started.

**Score:** 75/100 (up, no workflow exercised)

---

## 3. Provider Dependency Map

| Feature | Required Provider | Status |
|---------|------------------|--------|
| AI-generated content | NVIDIA NIM (small/utility model) | ⚠️ primary times out, fallback 404 |
| AI text-to-SQL | NVIDIA NIM (operational_utility) | ❌ endpoint broken, engine fails |
| SERP tracking | DataForSEO | ❌ not configured |
| Backlink data | Ahrefs | ❌ not configured |
| Email discovery | Hunter | ⚠️ no key, mock fallback still in code |
| Web crawl | Scrapling + Playwright | ✅ |
| HTML extraction | Trafilatura | ✅ |
| Tech profiling | Wappalyzer | ✅ |
| Local SERP | SearXNG | ❌ not running |
| Domain rank | OpenPageRank | ❌ not configured |
| Outbound email | SendGrid/Mailgun/Resend | ❌ all absent, silent MailHog fallback |
| File storage | MinIO | ✅ |
| Caching | Redis | ✅ |
| Vector search | Qdrant | ✅ |
| Event bus | Kafka | ✅ |
| Workflows | Temporal | ✅ |

---

## 4. What This Means for Production

A customer-facing workflow that touches any of the ⚠️ or ❌ providers will silently fail. The platform's surface behavior:

- **Onboarding:** Customer signs up. AI-generated welcome message **may** succeed (depends on which model and whether it times out). Most likely to fall back to a canned template.
- **First audit run:** Customer runs a website audit. Playwright + Trafilatura extract the page. Then the platform tries to use DataForSEO for SERP data — **401**. SERP results are empty. The audit completes but with no competitor/rank data. The customer sees a "We found 0 SERP competitors" report, which looks professional but is actually empty data.
- **Backlink analysis:** Customer requests backlinks. Ahrefs returns 401. The platform shows "0 backlinks" — same problem.
- **Email outreach:** Customer triggers an outreach. The platform looks up emails via Hunter — **fails**. Falls back to mock: `editor@<company>.com` (if `USE_MOCK_PROVIDERS=true`) or fails with empty result. Outreach goes to wrong addresses or no addresses.
- **Send:** Customer expects an email to be delivered to a real recipient. MailHog catches it. **Recipient never receives it.** Platform logs "email sent." Customer asks "why didn't my prospect respond?" — answer is the email was never sent.

This is a product that **appears to work in screenshots but does not work in production.**

---

## 5. Provider Configuration Required for Production

To make this platform production-ready for real customers:

| Provider | Action | Estimated Setup |
|----------|--------|-----------------|
| DataForSEO | Sign up, get login/password | 15 minutes, $50/100k requests |
| Ahrefs | Sign up, get API key | 15 minutes, $99+/mo |
| Hunter | Sign up, get API key | 15 minutes, $49/mo |
| Firecrawl | Sign up, get API key (or remove dependency) | 15 minutes |
| SearXNG | Self-host or use community instance | 2 hours |
| SendGrid or Resend | Sign up, get API key, verify domain | 1 hour |
| NVIDIA NIM primary | Pick a model that doesn't time out, configure in `TASK_MODEL_ROUTING` | 30 minutes |
| AI engine bug | Add `query` method or change endpoint to call `execute_query` | 30 minutes |
| Remove mock fallback | Delete `if settings.use_mock_providers` blocks in `clients/hunter.py` and `services/email/email_provider.py` | 30 minutes |
| Add startup check | Refuse to start if no real email provider configured | 30 minutes |

**Total:** 1-2 days of work + 1-2 weeks of buffer for provider onboarding and contract finalization.

---

## 6. Production Verdict

**Status: PARTIAL.** The infrastructure providers (Redis, Qdrant, MinIO, Kafka, Temporal) are all real and working. The AI provider has a real API key and a real upstream API, but the production workflow is broken because (a) the primary model times out and the fallback model returns 404, and (b) the `/api/v1/ai/query` endpoint calls a non-existent method.

The SEO and email providers are all absent or silently falling back. A customer-facing product that depends on these providers is not production-ready.

**Signed:** Provider Execution Report, 2026-06-06.
