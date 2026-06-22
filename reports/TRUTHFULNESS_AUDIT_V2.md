# 9. TRUTHFULNESS_AUDIT_V2.md
**Phase 11 — Truthfulness Audit**
**Date:** 2026-06-14

## Fakes Found (Severity: CRITICAL)

### F1: Simulated Link Intersect Matrix
- **File:** `services/scraping/engines/backlinks.py` lines 129-162
- **What it does:** When Ahrefs fails, generates fake domain names:
  ```python
  simulated_authorities = [
      (f"{niche_slug}insights.com", 78, 0.92, ["editorial", "news"]),
      (f"{niche_slug}journal.org", 82, 0.95, ["research", "academic"]),
  ]
  ```
- **Impact:** Operator receives non-existent domains as "prospects"
- **Trust:** ZERO — these domains don't exist
- **Fix:** Return empty list with clear error, never generate fake domains

### F2: Hardcoded Domain Health
- **File:** `services/deliverability/engine.py` lines 31-44
- **What it does:** Returns `reputation_score=0.98` for EVERY domain
- **Impact:** Operator thinks all domains have excellent health
- **Trust:** ZERO — fabricated metric
- **Fix:** Return "not checked" or actually check domain health

### F3: Fake Forecast Data
- **File:** `services/forecasting.py` lines 108, 149, 184, 213
- **What it does:** When no historical data exists, fabricates data:
  ```python
  values = [50000.0] * 6  # Fake revenue
  values = [75.0] * 6     # Fake health
  ```
- **Impact:** Operator sees forecasts based on invented numbers
- **Trust:** ZERO — linear regression on fake data
- **Fix:** Return "insufficient data" instead of fabricating

### F4: Hardcoded Keyword Volumes
- **File:** `workflows/__init__.py` line 317
- **What it does:** Returns keywords with fake metrics:
  ```python
  return [{"keyword": f"{s} strategy", "volume": 1200, "difficulty": 0.45}]
  ```
- **Impact:** Operator sees fabricated search volume and difficulty
- **Trust:** ZERO — numbers are invented
- **Fix:** Return keywords without volume/difficulty, or mark as "estimated"

### F5: Hardcoded `demo@buildit.local`
- **File:** `api/endpoints/campaigns.py` line 837
- **What it does:** Uses demo email address in outreach threads
- **Impact:** Emails would be sent from a non-existent address
- **Trust:** LOW — looks unprofessional
- **Fix:** Use configured sender email

## Fakes Found (Severity: MODERATE)

### F6: Copilot Branding
- **File:** `services/copilot.py`
- **What it does:** Keyword matching presented as "AI Copilot"
- **Impact:** Operator expects conversational AI, gets SQL search
- **Fix:** Relabel as "Quick Query" or integrate real LLM

### F7: AI Recommendations Branding
- **File:** `services/ai_recommendations.py`
- **What it does:** Threshold rules presented as "AI Recommendations"
- **Impact:** Operator expects intelligent suggestions, gets if/else logic
- **Fix:** Relabel as "Smart Alerts" or integrate real LLM

### F8: Campaign Agent Branding
- **File:** `services/campaign_agent.py`
- **What it does:** Status checks presented as "Autonomous Agent"
- **Impact:** Operator expects autonomous decision-making, gets status polling
- **Fix:** Either implement LLM reasoning or remove "Agent" branding

### F9: Maintainability Scores
- **File:** `services/maintainability_dominance.py`
- **What it does:** Hardcoded scores (0.78, 0.55, 0.15) for every analysis
- **Impact:** Operator thinks system has been analyzed, gets static numbers
- **Fix:** Either compute real scores or remove the feature

### F10: Spam Heuristic
- **File:** `services/deliverability/engine.py` lines 46-64
- **What it does:** Naive word-matching labeled "for demo purposes"
- **Impact:** Operator trusts spam scoring, gets toy implementation
- **Fix:** Integrate real spam checker or clearly label as "basic"

## Things That Are Truthful

| Feature | Truthful? | Evidence |
|---------|-----------|----------|
| Client CRUD | ✅ YES | Real DB operations |
| Campaign CRUD | ✅ YES | Real DB operations |
| Citation Submission | ✅ YES | Real Playwright execution |
| Email Sending | ✅ YES | Real provider APIs (when configured) |
| Audit Logger | ⚠️ PARTIAL | Code exists but not capturing |
| Approval Workflow | ✅ YES | Real Temporal signal integration |
| Prospect Discovery (HackerTarget) | ✅ YES | Real public API |
| Prospect Discovery (Scrapling) | ✅ YES | Real web scraping |
| Ahrefs Client | ✅ YES | Real API calls (when key configured) |
| Hunter.io Client | ✅ YES | Real API calls (when key configured) |

## Operator Trust Assessment

**Can an operator trust this platform?**

| Area | Trust Level | Reason |
|------|-------------|--------|
| Data entry (CRUD) | HIGH | Real DB operations |
| Prospect discovery | LOW | Fake fallback exists |
| Email generation | LOW | Template fallback labeled as "AI" |
| Domain authority | LOW | Heuristic, not real measurement |
| Recommendations | LOW | Rules, not AI |
| Forecasting | ZERO | Fabricated data |
| Audit trail | LOW | Not capturing |
| Campaign execution | ZERO | Temporal not running |

## Verdict: TRUSTWORTHINESS = LOW

The platform has a fundamental truthfulness problem:
1. Multiple systems present fake/heuristic data as real AI output
2. The most critical fake (simulated link intersect) generates non-existent domains
3. Forecasting fabricates historical data
4. "AI" branding is misleading for 5 out of 8 systems

**An operator cannot fully trust the outputs of this platform.**
