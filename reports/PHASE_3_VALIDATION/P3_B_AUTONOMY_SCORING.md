# P3-B: Autonomy Scoring Matrix
**Audit Date**: 2026-06-21 | **Phase**: P3 — Commercial Readiness
**Method**: Source code inspection, activity implementation analysis, dependency tracing

---

## Scoring Methodology

Each capability is scored on a 0–10 autonomy scale:
- **0–3**: Human required at every step
- **4–6**: Human required at approval gates only
- **7–9**: System executes end-to-end, humans notified async
- **10**: Fully autonomous, no human touchpoints required

---

## Capability Autonomy Scores

### 1. Prospect Discovery
**Score: 8/10**

| Sub-capability | Implementation | Evidence |
|---|---|---|
| Ahrefs API fetch | Real | `ahrefs_client.get_referring_domains()` |
| DataForSEO fallback | Real | `get_seo_provider().discover_backlink_prospects()` |
| HTML scraping fallback | Real | `backlink_scraper.discover_link_intersect_prospects()` |
| DB prospect fallback | Real | `fallback_prospects_activity()` reads `backlink_prospects` table |
| Zero-prospect halt | Yes | `failed_no_prospects` guard prevents false completion |

**Deduction −2**: Requires external API keys (Ahrefs/DataForSEO) for full effectiveness. Without keys, system enters "zero-cost mode" and relies on DB seeded data.

---

### 2. Prospect Scoring & Filtering
**Score: 9/10**

| Sub-capability | Implementation | Evidence |
|---|---|---|
| Domain Authority scoring | Real | `ahrefs_client.get_domain_metrics()` |
| Spam detection | Real | `backlink_intelligence.detect_link_farm_and_spam()` |
| Composite scoring algorithm | Real | Multi-signal: DA + relevance + traffic + spam |
| Anti-farm vetting grid | Real | Live Ahrefs signal |
| Topical relevance | Real | Qdrant vector similarity |

**Deduction −1**: Ahrefs metrics fall back to `{domain_rating: 0, ...}` on API error — artificially lowering composite scores, potentially causing over-filtering.

---

### 3. Contact Discovery & Verification
**Score: 9/10**

| Sub-capability | Implementation | Evidence |
|---|---|---|
| Email discovery | Real | `hunter_client.domain_search()` |
| Email verification | Real | `hunter_client.verify_email()` → deliverability check |
| Reject undeliverable | Yes | `ProspectStatus.REJECTED` persisted to DB |
| Multi-candidate evaluation | Yes | Iterates all candidates, picks first deliverable |

**Deduction −1**: Hunter.io key required. Without it, contacts_result returns `outreach_ready=False` for all prospects → campaign halts at enrichment guard.

---

### 4. Outreach Email Generation
**Score: 9/10**

| Sub-capability | Implementation | Evidence |
|---|---|---|
| LLM bespoke pitching | Real | `outreach_intelligence.generate_humanized_bespoke_pitch()` |
| Website content scraping | Real | `website_analyzer.analyze(domain)` per prospect |
| Semantic grounding validation | Real | `OutreachEmailSchema.check_semantic_grounding()` |
| Anti-fluff phrase detection | Real | 9 prohibited generic phrases enforced |
| Persona-aware voice | Real | `client_persona_service.get_active_persona_context()` |
| Tier-1 data journalism pitching | Real | `data_journalism_service.generate_bespoke_asset_pitch()` for DR≥75 |
| Follow-up sequences | Real | 3-email sequences (initial + 2 follow-ups) |
| Idempotency | Real | SHA256-keyed Redis TTL 86400s |

**Deduction −1**: LLM gateway still requires NVIDIA NIM or OpenAI fallback. Health check shows "Inference gateway operational" — this is live.

---

### 5. Human Approval Gates
**Score: 6/10** *(by design — intentional human control)*

| Gate | Implementation | Evidence |
|---|---|---|
| Prospect approval | Real Temporal signal wait | `workflow.wait_condition()` |
| Approval request persisted | Yes | `approval_service.create_request()` → DB |
| SLA deadline tracked | Yes | `sla_deadline` returned from `create_approval_request_activity()` |
| Rejection handling | Yes | `cancelled` status set, workflow terminates |
| Email template approval | Present in spec | Second gate in flow |

**Score is 6 by design**: Platform is built to require human approval at prospect gate and email template gate. This is a product decision, not a deficiency.

---

### 6. Email Outreach Sending
**Score: 8/10**

| Sub-capability | Implementation | Evidence |
|---|---|---|
| Real SMTP send | Yes | `email_provider.send_email()` → SendGrid/Mailhog |
| Kill switch | Yes | `kill_switch_service.is_blocked("email_sending")` |
| Per-prospect idempotency | Yes | Redis TTL 604800s |
| Rate limiting | Yes | Batch send with per-email idempotency check |

**Deduction −2**: MailHog is the active email backend in dev (observed in health check). SendGrid requires production key configuration.

---

### 7. Reply Detection & Link Acquisition
**Score: 6/10**

| Sub-capability | Implementation | Evidence |
|---|---|---|
| Kafka event consumer | Real | `consumer.register_handler("backlink.outreach.reply_received", ...)` |
| Acquisition recording | Real | `record_acquired_link_activity()` called on reply event |
| Reply inbox polling | Present | `email_reader_v2.py` (11,894 bytes) exists |

**Deduction −4**: No evidence that `email_reader_v2.py` is running as a scheduled activity or registered in any worker. The Kafka `reply_received` event must originate from somewhere — without the inbox poller active, this is PARTIAL. Automated link acquisition depends on reply detection being operational.

---

### 8. Link Verification
**Score: 10/10**

| Sub-capability | Implementation | Evidence |
|---|---|---|
| Real HTTP fetch | Yes | Scrapling client with 10s timeout |
| HTML link parsing | Yes | Custom `_LinkParser` HTMLParser |
| Anchor/rel extraction | Yes | Full attribute capture |
| Redirect chain tracking | Yes | Source→final URL comparison |
| 5-state classification | Yes | VERIFIED/MISSING/REDIRECTED/BROKEN/ERROR |
| History persistence | Yes | JSONB array, max 200 entries |
| Weekly cron | Yes | `register_scheduled_workflow("ScheduledLinkMonitor", "0 9 * * 1")` |

---

### 9. Campaign Health Monitoring
**Score: 9/10**

| Sub-capability | Implementation | Evidence |
|---|---|---|
| Campaign health scan | Real | `OperationalHealthScan` workflow + `check_campaign_health()` |
| Operational events | Real | `create_operational_event()` → `operational_events` table |
| Recommendation generation | Real | `generate_intelligence_recommendations()` → `recommendations` table |
| Continuous loop | Real | `OperationalLoopEngine` — 10,080 max iterations × 5min |
| SERP monitoring | Partial | `monitor_serp_changes()` counts keywords, doesn't fetch SERP data |

**Deduction −1**: `monitor_serp_changes()` only counts keywords — actual SERP position data is not fetched in this activity.

---

### 10. Reporting
**Score: 8/10**

| Sub-capability | Implementation | Evidence |
|---|---|---|
| `ReportGenerationWorkflow` | Real | `gather_report_data()` + `generate_ai_summary()` + `persist_report()` |
| Campaign ROI calculation | Real | `revenue_attribution_service.calculate_campaign_roi_summary()` |
| ROI validation | Real | Pydantic `@model_validator` validates formula: `max(((closed + traffic) - spend) / spend * 100, 0)` |
| Traffic surge modeling | Model-based | Industry benchmark CTRs + acquired link count |

**Deduction −2**: Traffic surge is simulation-based (position_improvement = link_count × 3, capped at 20). Not using actual SERP rank tracking API.

---

## Autonomy Score Summary

| Capability | Score | Max | Notes |
|---|---|---|---|
| Prospect Discovery | 8 | 10 | API key gated in production |
| Prospect Scoring | 9 | 10 | Ahrefs fallback to zero metrics |
| Contact Discovery | 9 | 10 | Hunter.io key required |
| Email Generation | 9 | 10 | LLM gateway required |
| Human Approval Gates | 6 | 10 | By design — intentional |
| Email Send | 8 | 10 | Dev uses MailHog |
| Reply Detection | 6 | 10 | Inbox poller not verified running |
| Link Verification | 10 | 10 | Fully autonomous |
| Campaign Health Monitoring | 9 | 10 | SERP monitoring partial |
| Reporting | 8 | 10 | Traffic model is simulated |
| **TOTAL** | **82** | **100** | |

**Platform Autonomy Score: 82/100**

---

## Interpretation

The platform achieves **high autonomy (82/100)** for all mechanical operations. The 18-point deficit breaks down:

- **8 points** from legitimate external API dependencies (Ahrefs, Hunter.io, SendGrid, LLM)  
- **4 points** from the intentional human approval design
- **4 points** from partial implementations (reply inbox, SERP fetching)
- **2 points** from simulation-based traffic attribution

**Conclusion**: For a commercially deployed platform with API keys configured, expected autonomy rises to ~90/100. The remaining 10 points represent intentional human oversight design choices and one engineering gap (reply inbox poller).
