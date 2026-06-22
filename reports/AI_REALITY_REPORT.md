# 6. AI_REALITY_REPORT.md
**Phase 11 — AI Reality Audit**
**Date:** 2026-06-14

## AI Systems Audit

### 1. Executive Copilot
- **File:** `services/copilot.py`
- **Classification:** ❌ FAKE (keyword matching, no LLM)
- **Evidence:**
  ```python
  # Line 41-102: Simple keyword matching
  if any(w in question.lower() for w in ["kpi", "key performance", "overview"]):
      # Run fixed SQL query
  # Line 104-107: Static fallback
  return "I couldn't find specific data for that question."
  ```
- **Where data comes from:** Fixed SQL queries matched by keyword
- **Trustworthiness:** LOW — presents SQL results as "AI" answers
- **Recommendation:** Either integrate real LLM or relabel as "Quick Query"

### 2. AI Query Engine
- **File:** `services/ai_query.py`
- **Classification:** ⚠️ RULES + LLM FALLBACK
- **Evidence:**
  - Primary path: 12 hardcoded intent patterns → template SQL (lines 18-71)
  - Fallback: `LLMGateway.complete()` generates SQL from natural language (lines 104-152)
- **Where data comes from:** Rules first, LLM second
- **Trustworthiness:** MEDIUM — rules are predictable, LLM adds flexibility
- **Recommendation:** Acceptable as-is

### 3. AI Recommendations
- **File:** `services/ai_recommendations.py`
- **Classification:** ❌ FAKE (threshold rules, no LLM)
- **Evidence:**
  ```python
  # Line 48: Simple threshold
  if float(row[0]) < 100000:
      recommendations.append({"type": "revenue", "priority": "high", ...})
  # Line 64: Status check
  if row.status in ("draft", "paused"):
      recommendations.append({"type": "campaign", ...})
  ```
- **Where data comes from:** DB queries + fixed thresholds
- **Trustworthiness:** LOW — deterministic rules presented as "AI recommendations"
- **Recommendation:** Either integrate real LLM or relabel as "Smart Alerts"

### 4. Forecasting
- **File:** `services/forecasting.py`
- **Classification:** ⚠️ MATH (not AI, but not fake)
- **Evidence:**
  - Hand-written linear regression (lines 37-78)
  - No ML library (scikit-learn, statsmodels)
  - No LLM call
  - **Critical flaw:** Falls back to fake data: `values = [50000.0] * 6` when no real data
- **Where data comes from:** DB queries → linear regression math
- **Trustworthiness:** LOW when using fallback data, MEDIUM when using real data
- **Recommendation:** Remove fake data fallback, clearly label as "Statistical Trend"

### 5. Campaign Agent
- **File:** `services/campaign_agent.py`
- **Classification:** ❌ FAKE (dead LLM code)
- **Evidence:**
  ```python
  # Line 15: Imports LLM but never uses it
  from seo_platform.llm.gateway import LLMGateway
  # Line 44: Instantiates but never calls
  self._llm = LLMGateway()
  # Lines 87-112: Only does status checks
  if status in ("draft", "paused"):
      return AgentAction(action="notify", ...)
  ```
- **Where data comes from:** Status checks only
- **Trustworthiness:** ZERO — imports AI but uses none of it
- **Recommendation:** Either implement LLM reasoning or remove AI branding

### 6. Outreach Pitch Generation
- **File:** `services/outreach_intelligence.py` lines 810-934
- **Classification:** ✅ REAL LLM
- **Evidence:**
  ```python
  # Line 900: Real LLM call
  result = await llm_gateway.complete(
      prompt=RenderedPrompt(system=system_prompt, user=user_prompt),
      task_type=TaskType.CONTENT_GENERATION,
  )
  ```
- **Where data comes from:** NVIDIA NIM LLM with context (website analysis, persona, SERP data)
- **Trustworthiness:** HIGH (when LLM key is configured)
- **Status:** ❌ UNAVAILABLE without NVIDIA NIM API key

### 7. Compliance Scorer
- **File:** `services/compliance.py`
- **Classification:** ⚠️ HEURISTIC (rule-based)
- **Evidence:** Checks banned words, sentence length, tone markers
- **Trustworthiness:** MEDIUM — deterministic and explainable

### 8. Domain Authority (Local Heuristic)
- **File:** `providers/seo.py` lines 23-50
- **Classification:** ⚠️ HEURISTIC (TLD-based formula)
- **Evidence:**
  ```python
  base = 15.0
  tld_weights = {"edu": 35.0, "gov": 40.0, "org": 10.0}
  base += min(35.0, ext_links_count * 1.5)
  ```
- **Trustworthiness:** LOW — .edu gets 50, .com gets 20 regardless of actual authority
- **Recommendation:** Never present as "Domain Authority" — label as "TLD Estimate"

## Summary

| System | Classification | Trustworthy? | Available? |
|--------|---------------|-------------|------------|
| Copilot | ❌ FAKE | LOW | ✅ Always |
| AI Query | ⚠️ RULES+LLM | MEDIUM | ⚠️ LLM fallback only |
| AI Recommendations | ❌ FAKE | LOW | ✅ Always |
| Forecasting | ⚠️ MATH | LOW-MEDIUM | ⚠️ Needs real data |
| Campaign Agent | ❌ FAKE | ZERO | ✅ Always |
| Pitch Generation | ✅ REAL LLM | HIGH | ❌ No NVIDIA key |
| Compliance Scorer | ⚠️ HEURISTIC | MEDIUM | ✅ Always |
| Domain Authority | ⚠️ HEURISTIC | LOW | ✅ Always |

## Critical Finding

**5 out of 8 "AI" systems contain NO actual AI.** They use keyword matching, threshold rules, or status checks but are branded as "AI-powered." This is misleading to operators who trust these outputs.

The one genuinely AI-powered system (pitch generation) is unavailable because the NVIDIA NIM API key is empty.

## Recommendations

1. **P0:** Remove fake data fallback from forecasting (fabricated historical data)
2. **P1:** Relabel non-AI systems (copilot → "Quick Query", recommendations → "Smart Alerts")
3. **P1:** Either implement LLM in Campaign Agent or remove AI branding
4. **P2:** Add warning when using heuristic DA scores
5. **P2:** Document that copilot is keyword-based, not conversational AI
