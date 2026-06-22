# PROJECT 31A — PLATFORM DATA FLOWS BIBLE (DOCUMENT 11)
## Version 1.0.0
## Classification: CONFIDENTIAL — FOR INTERNAL DEVELOPMENT AND DUE DILIGENCE ONLY

---

## 1. UNIFIED SYSTEM DATA LIFECYCLE

Project 31A orchestrates data flows across external APIs, local scraping caches, vector indices, relational schemas, and asynchronous event streams. Data transitions through four lifecycle phases:
1. **Ingestion & Validation:** Verification of domains, schemas, and credentials.
2. **Analysis & Vectorization:** Generating keyword volume metrics, SERP maps, and text embeddings.
3. **Prospecting & Outreach Routing:** Domain discovery, email deliverability validation, and personalized dispatches.
4. **Acquisition & Lifecycle Verification:** Reply classifications, verified link detections, and time-series snapshots.

---

## 2. CLIENT ONBOARDING FLOW & INGESTION

The onboarding sequence handles domain DNS checks, technology fingerprinters, and competitor discovery.

```
Domain Input ──► validate_client_domain_activity (DNS check)
                          │
                          ▼
                 enrich_business_profile_activity (Wappalyzer / Scrapling)
                          │
                          ▼
                 discover_competitors_activity (Ahrefs / DataForSEO)
                          │
                          ▼
                 save_onboarding_results_activity ──► Client Status: Active
```

1. **DNS check:** `validate_client_domain_activity` validates DNS MX records, SSL expiration, and HTTP response codes.
2. **Business Enrichment:** `enrich_business_profile_activity` uses Scrapling and Wappalyzer to extract descriptions, contact emails, and tags, writing them to `Client.profile_data`.
3. **Competitor Discovery:** `discover_competitors_activity` calls Ahrefs to identify top competitor domains and writes the list to `Client.competitors`.
4. **Results Persistence:** `save_onboarding_results_activity` updates the database state and sets the client status to `active`.

---

## 3. KEYWORD RESEARCH & VECTORIZATION DATA PIPELINE

Keyword discovery runs through a multi-provider pipeline to generate metric snapshots and semantic vector collections.

```
Seed Words ──► DataForSEO Live API ──► Volume/CPC/Difficulty (Ahrefs)
                                                 │
                                                 ▼
Name Groups (Gemma LLM) ◄── HDBSCAN Clustering ◄── Embeddings (nv-embedqa)
```

1. **Expansion:** `expand_keywords_activity` submits seeds to the DataForSEO live keyword ideas endpoint.
2. **Metric Enrichment:** `enrich_keywords_activity` queries Ahrefs v3 search metrics to obtain search volumes, Cost-Per-Click, and difficulty metrics.
3. **Embedding Generation:** `generate_keyword_embeddings_activity` routes keyword strings to the `nv-embedqa-e5-v5` model.
4. **Vector Storage:** The generated 1024-dimensional vectors are stored in **Qdrant** with payload properties (`tenant_id`, `client_id`). The vector UUID is written to `Keyword.embedding_vector_id`.
5. **Semantic Clustering:** `cluster_keywords_activity` retrieves vector embeddings from Qdrant, processes them via HDBSCAN density clustering, and writes `KeywordCluster` associations to the database.

---

## 4. PROSPECTING & CONTACT ACQUISITION FLOW

This pipeline extracts target backlink opportunities, filters out spam sites, and harvests validated contact details.

```
Ahrefs Competitor Domains ──► discover_prospects_activity ──► score_prospects_activity (Spam & DA check)
                                                                       │
                                                                       ▼
Reject Target ◄── Risky/Invalid ◄── Hunter Verify ◄── discover_contacts_activity
```

1. **Domain Intersect:** `discover_prospects_activity` calls Ahrefs referring domains endpoint for each competitor domain, outputting a list of potential target websites.
2. **Vetting & Spam Vetting:** `score_prospects_activity` fetches domain metrics and checks the domain against the link farm detector. Viable targets are written to `backlink_prospects` with status `new`.
3. **Contact Harvesting:** `discover_contacts_activity` executes a Hunter.io domain search to identify up to 3 email candidates.
4. **Email Verification:** Calls Hunter email verifier.
   - If status is `deliverable`, saves the contact email and marks the prospect as outreach-ready.
   - If `undeliverable` or `risky`, rejects the prospect.

---

## 5. OUTREACH DISPATCH & RESPONSE WEBHOOK LOOP

This loop handles email dispatch, delivery monitoring, and reply classifications.

```
Outreach Queue ──► send_single_email_activity ──► Inbound Mail Webhook
                                                          │
                                                          ▼
Classify Reply (Gemma LLM) ◄── Kafka Event Broker ◄── parse_reply_activity
          │
          ├─► Positive Reply ──► Signal Campaign Workflow ──► Approve Deal
          │
          └─► Negative Reply ──► Signal Campaign Workflow ──► Archive Thread
```

1. **Dispatch:** The worker checks SRE kill switches, retrieves credentials from the vault, and dispatches the outreach email.
2. **Telemetry Ingestion:** The email provider emits webhooks tracking dispatches (`delivered`, `opened`). The API receives these webhooks and updates the database.
3. **Inbound Response Webhook:** When a prospect replies, the incoming SMTP server routes the mail payload to `/api/v1/webhooks/inbound-email`.
4. **Event Streaming:** The API parses the payload and publishes an event to the Kafka topic `backlink.outreach.reply_received`.
5. **Worker Processing:** The worker event consumer reads the event and launches `parse_reply_activity`.
6. **Reply Classification:** The activity routes the text to the `Gemma` LLM model.
   - If classified as `interested`, signals the parent campaign workflow, raising an alert in the action center.
   - If classified as `not interested`, updates the thread status to `unsubscribed`.

---

## 6. DATA RETENTION & TENANT PURGING POLICY

To maintain compliance (e.g. GDPR, CCPA) and manage infrastructure costs, the database implements a strict data retention and purging policy.

- **Data Lifetimes:**
  - `audit_log`: Maintained for `365` days (1 year) using PostgreSQL partition pruning.
  - `prospect_score_history`: Retained for `90` days.
  - `campaign_health_snapshots`: Retained for `180` days.
- **Tenant Purging Sequence:** When a tenant is purged (`DELETE FROM tenants WHERE id = :tenant_id`), the cascading triggers execute:
  1. `CASCADE` constraints drop all records in `users`, `clients`, `backlink_campaigns`, `backlink_prospects`, `outreach_threads`, and `acquired_links` automatically.
  2. The purge service deletes associated vector payloads from Qdrant using the filter `{ "tenant_id": tenant_id }`.
  3. The service calls MinIO/S3 APIs to delete all object storage directories matching `s3://reports/{tenant_id}/*`.
  4. Records the deletion transaction in the global append-only ledger for compliance.
