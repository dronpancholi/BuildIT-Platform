# RECOMMENDATION QUALITY REPORT

**Total recommendations:** 31 (tenant `00000000-0000-0000-0000-000000000001`).

## Sampled Recommendations (10)
| ID | Type | Title | Confidence | Impact | Effort |
|----|------|-------|------------|--------|--------|
| b3ad3294-… | campaign_launch | Launch campaign: Q3 Backlink Campaign | 0.9 | 0.8 | 0.3 |
| a55718ea-… | campaign_stalled | Campaign stalled: Q3 Backlink Campaign | 0.7 | 0.6 | 0.6 |
| 4240887a-… | campaign_stalled | Campaign stalled: Q3 Backlink Campaign | 0.7 | 0.6 | 0.6 |
| f235f621-… | campaign_stalled | Campaign stalled: Q3 Backlink Campaign | 0.7 | 0.6 | 0.6 |
| 62d364f8-… | campaign_stalled | Campaign stalled: Q3 Backlink Campaign | 0.7 | 0.6 | 0.6 |
| aeff28b7-… | campaign_stalled | Campaign stalled: Q3 Backlink Campaign | 0.7 | 0.6 | 0.6 |
| 00f6fbbe-… | campaign_stalled | Campaign stalled: SaaS Backlink Blitz | 0.7 | 0.6 | 0.6 |
| fadb4fbd-… | campaign_stalled | Campaign stalled: Tech Blog Outreach | 0.7 | 0.6 | 0.6 |
| 39d8544e-… | campaign_stalled | Campaign stalled: Influencer Collab Q3 | 0.7 | 0.6 | 0.6 |
| f12ff5c7-… | campaign_stalled | Campaign stalled: Broken Link Building | 0.7 | 0.6 | 0.6 |

## Quality Assessment
| Category | # of items | Comments |
|----------|-----------|----------|
| **Useful** (actionable, specific) | 1 (the `campaign_launch` recommendation) | Directly tells the operator to launch a pending campaign; confidence high.
| **Somewhat useful** (informative, low impact) | 0 | – |
| **Noise** (repetitive, generic) | 9 | Repeated `campaign_stalled` alerts for the same campaign; low differentiation.
| **Misleading / Wrong** | 0 | – |

## Evidence & Reasoning
* Each recommendation stores a JSON field `calculation` (not shown here) that records the rule that fired (e.g., `stalled_threshold_exceeded`).
* The `confidence` score reflects model certainty; all noisy items have modest confidence (0.7) and identical impact/effort values, indicating a static rule rather than data‑driven insight.

## Recommendations for Improvement
1. **Deduplicate** stalled alerts – aggregate multiple triggers into a single actionable notification.
2. Enrich `campaign_stalled` with context (e.g., which step is stuck, recent error logs).
3. Introduce more varied recommendation types (prospect prioritization, outreach phrasing suggestions) to increase overall usefulness.

**Overall Verdict:** The recommendation engine currently provides minimal value beyond a single launch cue. The majority of alerts are repetitive noise, which could erode trust if left unaddressed.
