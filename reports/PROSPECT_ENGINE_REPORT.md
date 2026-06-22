# 3. PROSPECT_ENGINE_REPORT.md
**Phase 11 — Prospect Discovery Reality Audit**
**Date:** 2026-06-14

## Prospect Sources Analysis

### Source 1: Ahrefs API (Primary — Temporal Workflow)
- **File:** `clients/ahrefs.py`
- **Mechanism:** Real HTTP calls to `api.ahrefs.com`
- **Status:** ❌ NO API KEY CONFIGURED
- **Evidence:** `settings.ahrefs.api_key` is empty/not set
- **Verdict:** REAL but UNAVAILABLE

### Source 2: Hunter.io (Contact Discovery)
- **File:** `clients/hunter.py`
- **Mechanism:** Real HTTP calls to `api.hunter.io`
- **Status:** ❌ NO API KEY CONFIGURED
- **Mock gating:** `use_mock_providers=True` returns fake data; currently `USE_MOCK_PROVIDERS=false` so it would fail-loud
- **Verdict:** REAL but UNAVAILABLE

### Source 3: Scrapling (Active Provider)
- **File:** `providers/seo.py` → `ScraplingSEOProvider`
- **Mechanism:** Real web scraping via Scrapling client
- **Status:** ✅ CONFIGURED (active provider)
- **Evidence:** `providers/seo.py` line 145: `ScraplingSEOProvider` is registered
- **What it actually does:**
  - `get_domain_authority()`: Calls OpenPageRank API (real), falls back to `calculate_local_authority()` (heuristic)
  - `discover_backlink_prospects()`: Uses Scrapling web scraping to find links on target pages (real)
  - `get_keyword_metrics()`: Raises `ProviderUnavailableError` (not implemented)
- **Verdict:** REAL (scraping) + HEURISTIC (DA scoring)

### Source 4: SearXNG (Available Provider)
- **File:** `providers/seo.py` → `SearXNGSEOProvider`
- **Mechanism:** Local SearXNG instance or web scraping
- **Status:** Available but not active
- **Verdict:** REAL (requires running SearXNG instance)

### Source 5: HackerTarget API (Public, No Key)
- **File:** `api/endpoints/campaigns.py` lines 995-1020
- **Mechanism:** Real HTTP GET to `api.hackertarget.com`
- **Status:** ✅ NO KEY REQUIRED
- **Evidence:** URLs like `https://api.hackertarget.com/linktracer/?q={competitor}`
- **What it returns:** Plain text list of domains
- **Verdict:** REAL

### Source 6: DNS.Google (Public, No Key)
- **File:** `api/endpoints/campaigns.py` line 1015
- **Mechanism:** Real HTTP GET to `dns.google/resolve`
- **Status:** ✅ NO KEY REQUIRED
- **Verdict:** REAL

### Source 7: SecurityTrails (Public, No Key for basic)
- **File:** `api/endpoints/campaigns.py` line 1016
- **Mechanism:** Real HTTP GET to `securitytrails.com`
- **Status:** ✅ NO KEY REQUIRED (basic endpoint)
- **Verdict:** REAL

### Source 8: Simulated Link Intersect Matrix (Fallback)
- **File:** `services/scraping/engines/backlinks.py` lines 129-162
- **Mechanism:** Generates fake domain names with fake metrics
- **Status:** ⚠️ ACTIVATED when Ahrefs fails
- **Evidence:**
  ```python
  simulated_authorities = [
      (f"{niche_slug}insights.com", 78, 0.92, ["editorial", "news"]),
      (f"{niche_slug}journal.org", 82, 0.95, ["research", "academic"]),
      ...
  ]
  ```
- **Verdict:** ❌ FAKE — generates non-existent domain names

## Domain Authority Scoring

### Real Path (when OpenPageRank works)
- Calls `https://api.openpagerank.com/api/v1/domains` with domain list
- Returns real PageRank-based authority scores
- **Status:** ✅ REAL (free API, no key needed for basic use)

### Heuristic Path (fallback)
- **File:** `providers/seo.py` lines 23-50
- **Function:** `calculate_local_authority(domain, ext_links_count)`
- **Mechanism:** TLD-based formula + name length bonus
  ```python
  base = 15.0
  tld_weights = {"edu": 35.0, "gov": 40.0, "org": 10.0, "com": 5.0}
  base += tld_weights.get(tld, 0.0)
  base += min(35.0, ext_links_count * 1.5)
  ```
- **Verdict:** ⚠️ HEURISTIC — not real authority measurement

## Deduplication
- **File:** `workflows/backlink_campaign.py` lines 169-255
- **Mechanism:** Deduplicates by domain, applies spam detection
- **Spam detection:** Uses `backlink_intelligence.detect_link_farm_and_spam()` — rule-based keyword/TLD/regex patterns
- **Verdict:** ✅ REAL (rule-based but functional)

## Enrichment
- **File:** `workflows/backlink_campaign.py` lines 258-477
- **Mechanism:** Hunter.io for contact discovery, Ahrefs for domain metrics
- **Status:** Both require API keys that are not configured
- **Verdict:** ❌ UNAVAILABLE without API keys

## Summary

| Source | Type | Real? | Available? |
|--------|------|-------|------------|
| Ahrefs API | External API | ✅ REAL | ❌ No key |
| Hunter.io | External API | ✅ REAL | ❌ No key |
| Scrapling | Web scraping | ✅ REAL | ✅ Active |
| SearXNG | Search aggregator | ✅ REAL | ⚠️ Needs instance |
| HackerTarget | Public API | ✅ REAL | ✅ No key needed |
| DNS.Google | Public API | ✅ REAL | ✅ No key needed |
| SecurityTrails | Public API | ✅ REAL | ✅ No key needed |
| Simulated Matrix | Fake generator | ❌ FAKE | ⚠️ Fallback |
| OpenPageRank | Public API | ✅ REAL | ✅ No key needed |
| Local DA Heuristic | Formula | ⚠️ HEURISTIC | ✅ Always |

## Verdict: ⚠️ PARTIAL

Prospect discovery can work via Scrapling + HackerTarget + DNS.Google (all free, no keys needed). But:
1. Domain authority falls back to TLD-based heuristic (not real authority)
2. Contact discovery requires Hunter.io key (not configured)
3. When all providers fail, the system generates FAKE domain names (simulated link intersect matrix)
4. The simulated fallback is the most dangerous fake in the codebase

**Operator can get prospects, but cannot trust the authority scores or contact information.**
