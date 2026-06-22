# P3-H: Revenue Attribution Certification
**Audit Date**: 2026-06-21 | **Phase**: P3 — Commercial Readiness
**Method**: Source code inspection of `revenue_attribution/service.py`

---

## Revenue Attribution Architecture

### Service
**File**: `backend/src/seo_platform/services/revenue_attribution/service.py` (383 lines)
**Class**: `RevenueAttributionService`

### Data Models

```python
class AttributedDeal(BaseModel):
    deal_id: str
    crm_stage: CRMStage  # "lead" | "qualified" | "proposal" | "closed_won"
    amount: float
    attributed_percentage: float  # 0.0–1.0
    associated_campaign_id: UUID

class OrganicTrafficSurge(BaseModel):
    keyword_cluster: str
    previous_position: int  # 1–100
    new_position: int       # 1–100
    estimated_monthly_clicks: int
    traffic_value_usd: float

class CampaignROISummary(BaseModel):
    total_spend: float
    total_pipeline_created: float
    total_closed_won: float
    organic_traffic_value_added: float
    roi_percentage: float
    attributed_deals: list[AttributedDeal]
```

---

## ROI Calculation Verification

### Formula (Source: lines 329–330)
```python
roi_pct = ((total_value) - total_spend) / max(total_spend, 0.01) * 100
summary = CampaignROISummary(
    roi_percentage=round(max(roi_pct, 0.0), 2),
    ...
)
```

### Pydantic Validation (Source: lines 63–74)
```python
@model_validator(mode="after")
def _validate_roi_calculation(self) -> CampaignROISummary:
    raw_roi = ((self.total_closed_won + self.organic_traffic_value_added) - self.total_spend) / max(self.total_spend, 0.01) * 100
    expected_roi = max(raw_roi, 0.0)
    if abs(self.roi_percentage - expected_roi) > 0.1:
        raise ValueError(...)
```

**Verdict**: ROI formula is mathematically validated at construction time. Any caller that provides an incorrect `roi_percentage` will get a `ValueError`. This is **bulletproof** for data integrity.

---

## Attribution Logic

### CRM Attribution Weights (Source: lines 303–317)
| Stage | Attribution % | Notes |
|---|---|---|
| `closed_won` | 25% | SEO is one of 4 channels |
| `proposal` | 15% | Partial attribution for pipeline |
| `qualified` | 15% | Same as proposal |
| `lead` | 0% | Not attributed |

**Assessment**: The 25% closed-won attribution is conservative and defensible for multi-touch attribution models. Not inflated.

---

## Traffic Surge Model

### Position Improvement Model (Source: lines 218–233)
```python
position_improvement = min(link_count * 3, 20)  # cap at 20 positions
previous_position = 45  # hardcoded starting position
new_position = max(1, previous_position - position_improvement)
```

**Assessment**: `previous_position = 45` is hardcoded. For a campaign with no historical rank data, this is a reasonable default (starting from outside top 10). However, it does not reflect the actual SERP position.

### CTR Model (Source: lines 257–272)
```python
# Position 1: 28% CTR
# Position 5: 8% CTR + linear interpolation
# Position 10: 3% CTR + linear interpolation
# Position > 10: power-law decay 0.03 × (10/pos)^1.5
```

**Assessment**: CTR curve is based on industry benchmark data (Ahrefs, Sistrix studies). The power-law decay formula is mathematically sound for positions > 10.

### Authority Multiplier (Source: lines 210–216)
```python
tier1_count = sum(1 for link in acquired_links if link.get("domain_rating") >= 75 or link.get("tier1_asset", False))
authority_multiplier = 1.5 if tier1_count > 0 else 1.0
```

**Assessment**: 1.5× multiplier for Tier-1 (DR≥75) links is aggressive but plausible for high-DR editorial links.

---

## CRM Data Source

### Data Ingestion (Source: lines 153–178)
```python
async def ingest_crm_pipeline(self, tenant_id, client_id, crm_deals):
    key = f"crm:{tenant_id}:{client_id}"
    try:
        redis = await get_redis()
        await redis.setex(key, 86400 * 30, json.dumps(crm_deals))
    except Exception:
        self._crm_store[key] = crm_deals  # in-memory fallback
```

**Assessment**: CRM data must be ingested by calling this API. There is **no live integration** with HubSpot, Salesforce, or any CRM platform. The customer must push their deal pipeline via API.

---

## Revenue Attribution Completeness

| Capability | Status | Evidence |
|---|---|---|
| ROI formula | REAL | `@model_validator` enforces math |
| ROI non-negative floor | REAL | `max(roi_pct, 0.0)` |
| Attribution by CRM stage | REAL | Closed won: 25%, Pipeline: 15% |
| Traffic value calculation | MODEL | Industry CTR benchmarks, not live SERP |
| Tier-1 link premium | REAL | 1.5× multiplier for DR≥75 |
| CRM data ingestion | REAL (API push) | Redis/memory store |
| CRM API integration | MISSING | No HubSpot/Salesforce connector |
| Live SERP rank tracking | MISSING | Simulated 45→N position model |

---

## Financial Accuracy Assessment

For a campaign that:
- Acquires 10 links (avg DR 60)
- Position improvement: 10 × 3 = 30, capped at 20 → position 45 → 25
- Benchmark: "general" cluster, 5,000/mo volume, $30 CPC
- CTR position 25: `0.03 × (10/25)^1.5 ≈ 0.0076`
- Incremental clicks: 5,000 × 0.0076 = 38/mo
- Traffic value: 38 × $30 = $1,140/mo
- Annualized: ~$13,680

**Assessment**: Calculations are mathematically sound given model inputs. The accuracy depends entirely on whether `previous_position = 45` is representative of the actual keyword cluster positions. For a cold-start customer with no historical rank data, this is the best available estimate.

---

## Revenue Attribution Verdict

**Score: 7/10**

| Dimension | Score |
|---|---|
| Mathematical integrity | 10/10 |
| Attribution model fairness | 9/10 |
| CRM data freshness | 4/10 (push-only, no live integration) |
| SERP position accuracy | 3/10 (simulated, not live) |
| Traffic value accuracy | 7/10 (benchmark CTR is defensible) |

**Certification**: Revenue attribution is **mathematically valid** and **commercially defensible** as a projection model. It should not be presented as live revenue tracking without disclosing that SERP position and CRM data are model-based.

**Pre-commercial recommendation**: Add disclosure language in the ROI dashboard: "Traffic value based on industry CTR benchmarks. Integrate live SERP tracking for actual rank-based attribution."
