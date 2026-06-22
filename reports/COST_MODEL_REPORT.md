# COST_MODEL_REPORT.md — Phase 2 Final

**Date:** 2026-06-05
**Method:** Current resource measurement + cost extrapolation at 100/500/1000 tenants
**Currency:** USD/month

---

## 1. Current Resource Usage (Baseline, 1-3 tenants, 34 campaigns)

| Component | Memory | CPU | Notes |
|---|---|---|---|
| Backend (uvicorn) | 284 MB RSS | 0.1% idle | Single process |
| Workers (6 total) | ~390 MB total | 0.1% idle each | 1 per task queue |
| PostgreSQL | 16 MB shared_buffers | minimal | 42 MB DB |
| Redis | 11 MB | minimal | Cache only |
| Kafka | 1.07 GB | 79% (currently!) | Single broker, idle topics |
| Temporal | 270 MB | 2% | Shared DB |
| MinIO | 96 MB | 0% | 364 KB used |
| Qdrant | 222 MB | 0.1% | Unused in dev |
| Prometheus | 79 MB | 0% | Metrics only |
| **Total container memory** | **~2.3 GB** | | |

**Disk:** 42 MB database, 364 KB MinIO. Trivial at current scale.

**Critical observation:** **Kafka is using 79% CPU at idle.** This is a misconfiguration or runaway thread. Not cost-relevant but indicates a health issue.

---

## 2. Cost Model Assumptions

### 2.1. Per-Tenant Activity

Based on current platform behavior:
- 1 user per tenant
- 10 clients per tenant (avg)
- 3.4 campaigns per client (avg) = 34 campaigns per tenant
- 4.4 keywords per client
- 1 report per client per month = 10 reports/tenant/month
- 0.2 emails per client (currently low)

### 2.2. Cost Categories

| Category | Notes |
|---|---|
| **Compute** | Backend, workers, supporting containers |
| **Storage** | Postgres, MinIO, snapshots, logs |
| **AI / Inference** | NVIDIA NIM API calls |
| **External APIs** | DataForSEO, Ahrefs, Hunter, etc. |
| **Monitoring** | Prometheus, logs, alerts |
| **Backups** | Local + offsite (S3 / similar) |

---

## 3. Compute Costs

### 3.1. Self-Hosted (Single Mac Mini / EC2)

**Single-host cost (24/7, idle baseline):**
- Mac Mini M2: ~$600 one-time, 0 ongoing
- AWS EC2 m6i.xlarge: $0.192/hr × 730 = **$140/month**
- AWS EC2 m6i.2xlarge: $0.384/hr × 730 = **$280/month**
- Self-hosted (home/office internet + power): $30-50/month

**Current single-host fits 50-100 tenants.** To go beyond, need horizontal scaling.

### 3.2. Horizontal Scale Required

| Tenants | vCPUs needed | Memory | EC2 instance | $/month |
|---|---|---|---|---|
| 100 | 4 | 16 GB | m6i.xlarge | $140 |
| 500 | 16 | 64 GB | 4× m6i.xlarge or 1× m6i.4xlarge | $560 |
| 1000 | 32 | 128 GB | 8× m6i.xlarge or 2× m6i.4xlarge | $1,120 |

**Compute-only cost:**
- 100 tenants: $140/month
- 500 tenants: $560/month
- 1000 tenants: $1,120/month

### 3.3. Component Breakdown (per 100 tenants)

| Component | Size | Cost/month |
|---|---|---|
| Backend (uvicorn) | 4 vCPU / 8 GB | $70 |
| Workers (6 × 3 replicas) | 4 vCPU / 8 GB | $70 |
| PostgreSQL (primary) | 2 vCPU / 8 GB | $70 |
| PostgreSQL (read replica) | 2 vCPU / 8 GB | $70 |
| Redis | 1 vCPU / 2 GB | $25 |
| Kafka (3 brokers) | 6 vCPU / 12 GB | $140 |
| Temporal | 2 vCPU / 4 GB | $50 |
| MinIO (4 nodes erasure) | 4 vCPU / 8 GB | $70 |
| Qdrant | 2 vCPU / 4 GB | $50 |
| Prometheus + Grafana | 1 vCPU / 2 GB | $25 |
| **Total** | **28 vCPU / 56 GB** | **$640/month** |

**Per-tenant cost at 100 tenants: $6.40/month**

---

## 4. Storage Costs

### 4.1. Per-Tenant Storage Profile

| Data | Per Tenant | Per 100 | Per 500 | Per 1000 |
|---|---|---|---|---|
| Clients (rows) | 10 | 1,000 | 5,000 | 10,000 |
| Campaigns (rows) | 34 | 3,400 | 17,000 | 34,000 |
| Keywords (rows) | 44 | 4,400 | 22,000 | 44,000 |
| Prospects (rows) | 0.7 | 70 | 350 | 700 |
| Outreach emails (rows) | 0.2 | 20 | 100 | 200 |
| Reports (rows) | 1.0 | 100 | 500 | 1,000 |
| **Total rows per tenant** | ~90 | 9,000 | 45,000 | 90,000 |

### 4.2. Snapshot Tables (Growth-Heavy)

| Table | Current | Per 100 Tenants | Per 1000 Tenants |
|---|---|---|---|
| keyword_metric_snapshots | 49k rows / 11 MB | 1.1 MB | 11 MB (without growth) |
| Growth at 1 snapshot/keyword/day | | +440 rows/day | +44k rows/day |
| Annual growth | | 160k rows / 36 MB | 16M rows / 3.6 GB |

**Critical:** Snapshot tables will dominate storage without retention.

### 4.3. Storage Cost Estimates

| Item | Per 100 Tenants | Per 500 | Per 1000 |
|---|---|---|---|
| PostgreSQL data | 100 MB | 500 MB | 1 GB |
| PostgreSQL snapshots (90d) | 1 GB | 5 GB | 10 GB |
| MinIO reports (10/tenant/mo) | 50 MB | 250 MB | 500 MB |
| MinIO backups (12 months) | 600 MB | 3 GB | 6 GB |
| Offsite backup (S3 Standard) | $0.023/GB × 6 GB = $0.14 | $0.69 | $1.38 |
| **Total storage** | **~2 GB** | **~10 GB** | **~20 GB** |

**Storage cost (S3):**
- 100 tenants: $0.14/month
- 500 tenants: $0.69/month
- 1000 tenants: $1.38/month

Storage is the cheapest cost. Compute dominates.

---

## 5. AI / Inference Costs (NVIDIA NIM)

### 5.1. Per-Call Cost

NVIDIA NIM pricing (illustrative — actual depends on model):
- deepseek-v4-pro (orchestration): ~$0.0014/1k input tokens, $0.0028/1k output
- gemma-4-31b-it (SEO model): ~$0.0005/1k input, $0.001/1k output
- minimax-m2.7 (memory): ~$0.0003/1k input, $0.0006/1k output
- nemotron-3 (infra): ~$0.001/1k input, $0.002/1k output

### 5.2. Per-Tenant AI Usage

Based on workflow triggers:
- 10 campaigns/tenant × 5 AI calls/campaign lifecycle = 50 AI calls/tenant/month
- Avg 1000 input tokens + 500 output tokens per call
- Avg cost/call: ~$0.005 (mix of models)

**Per-tenant AI cost:** 50 × $0.005 = **$0.25/month**

### 5.3. Aggregate AI Cost

| Tenants | Calls/month | Cost/month |
|---|---|---|
| 100 | 5,000 | $25 |
| 500 | 25,000 | $125 |
| 1000 | 50,000 | $250 |

**This is the second-largest cost category after compute.**

### 5.4. Optimization
- Cache AI responses for identical inputs (60% hit rate possible) → 40% reduction
- Use smaller models for routine tasks → 30% reduction
- Batch similar requests → 10% reduction

**Optimized AI cost:** ~$15/$75/$150 for 100/500/1000 tenants.

---

## 6. External API Costs

### 6.1. Per-Provider Cost

| Provider | Per 100 Tenants | Per 500 | Per 1000 |
|---|---|---|---|
| DataForSEO (SERP, keywords) | $50 | $250 | $500 |
| Ahrefs (backlinks, domain authority) | $100 | $500 | $1,000 |
| Hunter.io (email finding) | $20 | $100 | $200 |
| SendGrid (transactional email) | $10 | $50 | $100 |
| **Total external APIs** | **$180** | **$900** | **$1,800** |

These are the **most expensive variable cost** at scale.

### 6.2. Cost Optimization
- Cache SERP results (TTL 24h) → 50% reduction
- Limit API calls per workflow (currently uncapped) → 30% reduction
- Self-host scraper for some providers (already using scrapling) → 20% reduction

---

## 7. Monitoring & Observability

| Item | Cost/month (100 tenants) | (500) | (1000) |
|---|---|---|---|
| Prometheus | $25 | $50 | $100 |
| Grafana Cloud (free tier or self-host) | $0 | $0 | $0 |
| Loki / log aggregation | $30 | $100 | $200 |
| Error tracking (Sentry) | $26 | $80 | $260 |
| Uptime monitoring (Pingdom) | $10 | $10 | $10 |
| **Total monitoring** | **$91** | **$240** | **$570** |

---

## 8. Backup Costs

| Item | Per 100 Tenants | Per 500 | Per 1000 |
|---|---|---|---|
| Local storage (1.5x data) | $0.10 | $0.50 | $1.00 |
| S3 Standard (1 month) | $0.05 | $0.25 | $0.50 |
| S3 Glacier (12 months) | $0.01 | $0.05 | $0.10 |
| **Total backup** | **$0.16** | **$0.80** | **$1.60** |

Backup is cheap. Do it.

---

## 9. Total Cost of Ownership (TCO)

### 9.1. 100 Tenants

| Category | Monthly |
|---|---|
| Compute (1× m6i.xlarge) | $140 |
| Storage (Postgres + MinIO + backups) | $10 |
| AI / Inference | $25 |
| External APIs | $180 |
| Monitoring | $91 |
| Backup | $0.16 |
| **TOTAL** | **$446/month** |
| **Per tenant** | **$4.46/month** |

### 9.2. 500 Tenants

| Category | Monthly |
|---|---|
| Compute (4× m6i.xlarge) | $560 |
| Storage | $50 |
| AI / Inference | $125 |
| External APIs | $900 |
| Monitoring | $240 |
| Backup | $0.80 |
| **TOTAL** | **$1,876/month** |
| **Per tenant** | **$3.75/month** |

### 9.3. 1000 Tenants

| Category | Monthly |
|---|---|
| Compute (8× m6i.xlarge or 2× m6i.4xlarge) | $1,120 |
| Storage | $100 |
| AI / Inference | $250 |
| External APIs | $1,800 |
| Monitoring | $570 |
| Backup | $1.60 |
| **TOTAL** | **$3,842/month** |
| **Per tenant** | **$3.84/month** |

---

## 10. Revenue Model Implications

**If charging $50/tenant/month:**
- 100 tenants: $5,000 revenue / $446 cost = **91% margin**
- 500 tenants: $25,000 revenue / $1,876 cost = **92% margin**
- 1000 tenants: $50,000 revenue / $3,842 cost = **92% margin**

**If charging $20/tenant/month:**
- 100 tenants: $2,000 revenue / $446 cost = **78% margin**
- 500 tenants: $10,000 revenue / $1,876 cost = **81% margin**
- 1000 tenants: $20,000 revenue / $3,842 cost = **81% margin**

**External APIs are the largest variable cost.** At 1000 tenants, $1,800/month external API = 47% of TCO.

---

## 11. Cost-Reduction Strategies (Ranked)

| Strategy | Effort | Savings at 1000t | Notes |
|---|---|---|---|
| Cache SERP data (24h TTL) | Low | $900/month | Biggest win |
| Cap API calls per workflow | Low | $540/month | Add limit |
| Self-host scraper more | Medium | $360/month | Scrapling already used |
| AI response cache | Low | $100/month | 60% hit rate achievable |
| Use smaller AI models | Medium | $75/month | Test quality impact |
| Snapshot table retention | Low | $50/month storage | Prevent runaway growth |
| Single-region vs multi-region | N/A | $0 | We're already single |
| **Total potential savings** | | **~$2,000/month at 1000t** | 52% reduction in TCO |

**After optimizations, 1000 tenants TCO could be ~$1,800/month ($1.80/tenant).**

---

## 12. Score

| Category | Weight | Score | Notes |
|---|---|---|---|
| Compute cost efficiency | 25% | 80/100 | Self-host can hit $1-3/tenant |
| Storage cost efficiency | 15% | 90/100 | Storage is cheap |
| AI cost efficiency | 20% | 60/100 | NIM is expensive, cache helps |
| External API cost | 20% | 40/100 | $1,800/month at 1000t is the killer |
| Monitoring cost | 10% | 70/100 | Could use free tiers |
| Backup cost | 5% | 100/100 | Cheap |
| Cost predictability | 5% | 80/100 | Mostly linear with tenants |
| **Overall** | | **68/100** | External APIs are the swing factor |

---

## 13. Findings

| ID | Finding | Sev | Status |
|---|---|---|---|
| COST-001 | External APIs dominant at scale ($1,800/mo at 1000t) | P0 | Open |
| COST-002 | AI cost unmanaged (no rate limit) | P0 | Open (SEC-002 fix helps) |
| COST-003 | Kafka at 79% CPU idle (misconfiguration) | P1 | Open |
| COST-004 | No AI response caching | P1 | Open |
| COST-005 | No SERP caching | P1 | Open |
| COST-006 | Snapshot tables grow unbounded | P1 | Open |
| COST-007 | No per-tenant cost tracking | P2 | Open |
| COST-008 | No usage-based pricing tier implemented | P2 | Open |

**2 P0 cost-related findings (both could be exploited for cost amplification), 4 P1 optimizations.**

---

## 14. Recommendation

**For Phase 3 (production launch):**

1. **Set per-tenant AI budget** ($5/tenant/month). Hard cap.
2. **Cache SERP results 24h** to avoid duplicate API calls. Saves ~$900/month at scale.
3. **Cap API calls per workflow**. Currently uncapped.
4. **Set up cost anomaly alerts** via Prometheus. If AI spend > $X/hour, alert.
5. **Add per-tenant cost dashboard** so customers can see their own usage.

Without these, an attacker (or a runaway bug) could burn through $10k+ in AI credits in hours.
