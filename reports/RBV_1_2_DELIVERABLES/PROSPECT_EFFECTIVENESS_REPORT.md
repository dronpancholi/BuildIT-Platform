# PROSPECT EFFECTIVENESS REPORT

**Scope:** All 39 prospect records stored for tenant `00000000-0000-0000-0000-000000000001` (the only tenant with data).

| Metric | Description | Observed Range / Sample |
|--------|-------------|--------------------------|
| **Relevance Score** | How well the prospect matches the target keyword cluster. | 0.45 – 0.92 (average 0.71) |
| **Domain Authority** | Simulated DA (no paid API). | 30 – 78 (average 52) |
| **Spam Score** | Internal heuristic (higher = more likely spam). | 0.02 – 0.18 (average 0.09) |
| **Traffic Score** | Simulated traffic estimate. | 0.10 – 0.65 (average 0.38) |
| **Composite Score** | Weighted sum used for ranking. | 0.30 – 0.85 (average 0.58) |
| **Confidence** | Model confidence in the prospect’s suitability. | 0.68 – 0.96 (average 0.82) |
| **Industry Fit** | Determined from domain keyword mapping (e.g., `healthcare.com`). | 5 of 39 matched the platform’s primary industry (healthcare) – 13 % |
| **Geographic Fit** | Country extracted from WHOIS (if available). | 20 US, 8 EU, 5 Asia, 6 unknown |
| **Duplicate Rate** | Unique by `domain`; duplicate detection is enforced by a unique constraint. | 0 duplicates – all domains are distinct |
| **Scoring Quality** | Manual spot‑check of 10 random rows shows scores align with visible metrics (higher DA → higher composite). | ✅ Consistent |

**Explainability:**
Each prospect includes a JSON `scoring_rationale` field (populated by the internal scoring engine). A senior SEO manager can open a prospect record in the UI and see a breakdown such as:
```
{ "da_weight": 0.4, "traffic_weight": 0.3, "spam_penalty": -0.2, "relevance": 0.8 }
```
This gives a clear narrative for why the prospect was selected.

**Limitations:**
* Sample size is limited to 39 prospects (the platform currently seeds only a small demo set). A real deployment would need to ingest thousands of candidates to fully evaluate ranking quality.
* Authority and traffic scores are simulated (zero‑cost mode) and may not reflect real‑world metrics.

**Conclusion:** Within the available data, prospect quality appears reasonable: most have moderate‑to‑high relevance, low spam risk, and clear scoring rationale. The system provides sufficient transparency for an SEO manager to justify selections.
