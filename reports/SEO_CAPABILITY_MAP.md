# SEO Capability Map — Phase 12A

**Date:** 2026-06-14
**Status:** Complete audit of every SEO capability

---

## Capability Matrix

| # | Capability | Exists | Status | Quality | Notes |
|---|-----------|--------|--------|---------|-------|
| 1 | **Keyword Research** | ✅ | Production Ready | HIGH | Real DB, NIM-powered expansion, clustering, intent classification |
| 2 | **Keyword Clustering** | ✅ | Production Ready | HIGH | Semantic graph + LLM clustering with deterministic fallback |
| 3 | **Keyword Opportunity Scoring** | ✅ | Production Ready | HIGH | Multi-factor: volume, difficulty, CPC, intent, SERP features |
| 4 | **Search Intent Classification** | ✅ | Production Ready | HIGH | LLM-powered with keyword-signal heuristic fallback |
| 5 | **SERP Feature Detection** | ✅ | Production Ready | HIGH | Real DataForSEO snapshots, 9 feature types |
| 6 | **SERP Volatility Tracking** | ✅ | Production Ready | HIGH | Redis-backed snapshot history with Lua scripts |
| 7 | **Competitor Analysis** | ⚠️ | Partially Exists | MEDIUM | Citation gap exists; domain comparison/content gap/keyword gap missing |
| 8 | **Backlink Analysis** | ✅ | Production Ready | HIGH | Ahrefs API integration, spam detection, authority classification |
| 9 | **Prospect Discovery** | ✅ | Production Ready | HIGH | SearXNG, HackerTarget, DNS.google, SecurityTrails, Ahrefs |
| 10 | **Prospect Scoring** | ✅ | Production Ready | HIGH | 6-component weighted scoring with breakdown |
| 11 | **Outreach Email Generation** | ✅ | Production Ready | HIGH | NIM-powered personalization + compliance scoring |
| 12 | **Outreach Response Prediction** | ✅ | Production Ready | MEDIUM | Deterministic formula, no ML training data |
| 13 | **Outreach Timing Optimization** | ✅ | Production Ready | MEDIUM | Industry vertical + timezone heuristic |
| 14 | **Citation Discovery** | ✅ | Production Ready | HIGH | Google NAP footprint scraping via Playwright |
| 15 | **Citation Submission** | ✅ | Production Ready | HIGH | Full Playwright form automation + email verification |
| 16 | **Citation Analytics** | ✅ | Production Ready | HIGH | Real DB-backed NAP consistency, quality scoring |
| 17 | **Local SEO Intelligence** | ⚠️ | Partially Exists | MEDIUM | Directory scoring real; no Google Maps API, no review monitoring |
| 18 | **NAP Consistency** | ✅ | Production Ready | HIGH | Real normalization + scoring against canonical profile |
| 19 | **Link Verification** | ✅ | Production Ready | HIGH | Real HTTP verification with redirect chain capture |
| 20 | **Link Monitoring** | ✅ | Production Ready | HIGH | Scheduled re-verification with regression detection |
| 21 | **Recommendations** | ✅ | Production Ready | HIGH | Multi-factor citation site recommendations with competitor gaps |
| 22 | **AI Recommendations** | ⚠️ | Partially Exists | LOW | SQL rule engine labeled "AI" — not ML |
| 23 | **Copilot** | ❌ | Broken | NONE | Page doesn't exist (404). Backend is keyword-matched DB queries |
| 24 | **Forecasting** | ⚠️ | Partially Exists | LOW | Linear regression only, no real training data |
| 25 | **Prospect Graph** | ✅ | Production Ready | HIGH | Redis-backed domain relationship graph with BFS |
| 26 | **Content Analysis** | ✅ | Production Ready | HIGH | Firecrawl + Qdrant vector store for topical matching |
| 27 | **Email Verification** | ✅ | Production Ready | HIGH | IMAP polling + Playwright link clicking |
| 28 | **Domain Authority** | ✅ | Production Ready | HIGH | OpenPageRank + Ahrefs with Redis caching |
| 29 | **Spam Detection** | ✅ | Production Ready | HIGH | Heuristic + Ahrefs live API (outbound ratio, HCU, anchor toxicity) |
| 30 | **Strategic Intelligence** | ✅ | Production Ready | HIGH | Keyword expansion, authority forecasting, SERP trend prediction |
| 31 | **Email Sending** | ✅ | Production Ready | HIGH | Resend/SendGrid/Mailgun abstraction |
| 32 | **Email Reading** | ✅ | Production Ready | HIGH | IMAP for Gmail/Outlook/Yahoo |
| 33 | **Report Generation** | ✅ | Production Ready | MEDIUM | CSV/XLSX export |
| 34 | **Health Scoring** | ⚠️ | Partially Exists | LOW | campaign_health_snapshots exist but no unified health engine |
| 35 | **Audit Trail** | ✅ | Production Ready | HIGH | Middleware persists to audit_ledger table |

---

## Capability Gaps (What Needs Building)

### P0 — Critical for SEO Agency Value
1. **Competitor Domain Comparison** — No endpoint compares two domains side-by-side
2. **Content Gap Analysis** — No keyword gap identification between client and competitors
3. **Backlink Gap Analysis** — No comparison of who links to competitors but not to client
4. **Copilot V2** — Dead page, needs full rebuild with evidence-backed answers
5. **Unified Health Scoring** — No client/campaign/outreach health score

### P1 — High Value
6. **Keyword Priority Score** — Opportunity scoring exists but no unified priority with local relevance
7. **Outreach Quality Score** — No email quality evaluation before sending
8. **Local Visibility Score** — No unified local SEO health metric
9. **Citation Quality Score** — No scoring of citation site quality beyond importance_score
10. **Prospect Explainability** — Scoring exists but no "why this score" explanation

### P2 — Nice to Have
11. **Review Monitoring** — No Google review tracking
12. **Real Google Maps Data** — Local SEO uses predefined tables, not live API
13. **ML-based Response Prediction** — Currently formula-based

---

## External API Dependencies

| API | Status | Used For |
|-----|--------|----------|
| Ahrefs | ⚠️ NO KEY | Domain metrics, backlink analysis, spam detection |
| DataForSEO | ⚠️ NO KEY | SERP snapshots, keyword data |
| NVIDIA NIM | ✅ KEY IN .env | Keyword expansion, email generation, intent classification |
| Hunter.io | ⚠️ NO KEY | Email verification for prospects |
| SearXNG | ❌ NOT RUNNING | SERP search for prospect discovery |
| Firecrawl | ⚠️ UNKNOWN | Website deep scraping |
| OpenPageRank | ✅ FREE | Domain authority scoring |
| Scrapling | ✅ ACTIVE | HTTP fetching, HTML parsing |
| Playwright | ⚠️ NEEDS INSTALL | Browser automation |
| Qdrant | ❌ NOT RUNNING | Vector store for content matching |

---

## Database State

| Table | Rows | Status |
|-------|------|--------|
| clients | 8 | ✅ Has data |
| backlink_campaigns | 13 | ✅ Has data |
| campaign_health_snapshots | 243 | ✅ Has data |
| recommendations | 7 | ✅ Has data |
| audit_ledger | 20 | ✅ Has data |
| keywords | 0 | ❌ EMPTY |
| keyword_clusters | 0 | ❌ EMPTY |
| backlink_prospects | 0 | ❌ EMPTY |
| outreach_threads | 0 | ❌ EMPTY |
| outreach_emails | 0 | ❌ EMPTY |
| citation_projects | 0 | ❌ EMPTY |
| citation_sites | 0 | ❌ EMPTY |
| citation_submissions | 0 | ❌ EMPTY |

**Critical:** All SEO execution tables are empty. The platform has infrastructure but no SEO data to analyze.
