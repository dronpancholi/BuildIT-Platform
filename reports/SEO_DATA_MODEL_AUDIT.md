# SEO DATA MODEL AUDIT — Phase 12.5A

**Date:** 2026-06-14  
**Auditor:** SEO Data Architect  

---

## Executive Summary

The platform has **57 tables** in PostgreSQL. Of these, **14 are SEO execution tables** that should contain operational SEO data. Currently, **all 14 are EMPTY** (0 rows). The platform has infrastructure but no fuel.

---

## Complete Table Inventory

### Populated Tables (Infrastructure)

| Table | Rows | Status |
|-------|------|--------|
| tenants | 1 | OK |
| users | 1 | OK |
| clients | 8 | OK |
| backlink_campaigns | 13 | OK |
| campaign_health_snapshots | 477 | OK |
| recommendations | 9 | OK |
| operational_events | 128 | OK |
| business_intelligence_events | 13 | OK |
| approval_requests | 2 | OK |
| audit_ledger | 20 | OK |
| provider_health_metrics | 1 | OK |

### Empty SEO Execution Tables (P0 Critical)

| Table | Model | Columns | Status | Impact |
|-------|-------|---------|--------|--------|
| **keywords** | Keyword | keyword, search_volume, difficulty, cpc, competition, intent, cluster_id | **EMPTY** | Keyword Priority Engine returns nothing |
| **keyword_clusters** | KeywordCluster | name, primary_keyword, total_volume, avg_difficulty, dominant_intent | **EMPTY** | Cluster analysis impossible |
| **keyword_research** | KeywordResearch | seed_keyword, status, result_data | **EMPTY** | Research pipeline dead |
| **keyword_metric_snapshots** | — | (timestamped keyword metrics) | **EMPTY** | Trend analysis impossible |
| **backlink_prospects** | BacklinkProspect | domain, url, status, domain_authority, relevance_score, composite_score, contact_name, contact_email | **EMPTY** | Prospect scoring returns nothing |
| **outreach_threads** | OutreachThread | campaign_id, prospect_id, status, from_email, to_email, subject, body_html, sent_at, opened_at, replied_at | **EMPTY** | Outreach quality engine has no data |
| **outreach_emails** | OutreachEmail | campaign_id, prospect_id, to_email, subject, body_html, status, sent_at, delivered_at, opened_at, replied_at | **EMPTY** | Email tracking dead |
| **citation_sites** | CitationSite | name, url, category, domain_authority, importance_score, is_free, is_active | **EMPTY** | Citation Intelligence has no sites to recommend |
| **citation_projects** | CitationProject | business_name, website_url, category, phone, address, city, state, country | **EMPTY** | Local SEO engine returns "No business profile" |
| **citation_submissions** | CitationSubmissionV2 | project_id, site_id, status, submitted_at, completed_at | **EMPTY** | Citation coverage = 0 |
| **citation_recommendations** | CitationRecommendation | project_id, site_id, priority_score, priority_reason, recommendation_type | **EMPTY** | No citation recommendations |
| **competitor_citations** | CompetitorCitation | project_id, competitor_name, competitor_domain, site_url, citation_url | **EMPTY** | Competitor citation gap impossible |
| **business_profiles** | BusinessProfile | business_name, street_address, city, state_province, postal_code, country_code, phone_number, website_url | **EMPTY** | Local SEO returns 404 for all clients |
| **contacts** | Contact | email, name, domain, client_id | **EMPTY** | No contact data for outreach |

### Empty Supporting Tables (P1 Important)

| Table | Rows | Status |
|-------|------|--------|
| email_templates | 0 | No outreach templates |
| serp_volatility_snapshots | 0 | No SERP tracking data |
| reports | 0 | No generated reports |
| campaign_timeline_events | 0 | No campaign timeline |
| prospect_score_history | 0 | No scoring history |
| acquired_links | 0 | No verified backlinks |
| plan_forecasts | 0 | No forecasting data |
| operational_memory | 0 | No learning data |
| graph_entities | 0 | No knowledge graph |
| graph_edges | 0 | No knowledge graph edges |

### Infrastructure Tables (Not SEO Data)

| Table | Rows | Status |
|-------|------|--------|
| action_definitions | 0 | Not needed for data activation |
| action_executions | 0 | Not needed |
| agent_* (4 tables) | 0 | Not needed |
| approval_policies | 0 | Not needed |
| audit_trail_logs | 0 | Not needed |
| compliance_results | 0 | Not needed |
| credential_audit_log | 0 | Not needed |
| directory_credentials | 0 | Not needed |
| execution_plans | 0 | Not needed |
| goal_* (2 tables) | 0 | Not needed |
| node_dependencies | 0 | Not needed |
| plan_nodes | 0 | Not needed |
| proxy_pools | 0 | Not needed |
| rate_limit_configs | 0 | Not needed |
| provider_keys | 0 | Not needed |
| workflow_events | 0 | Not needed |

---

## Data Flow Analysis

### What the Intelligence Engines Need

| Engine | Required Tables | Current State |
|--------|----------------|---------------|
| **Keyword Priority** | keywords, keyword_clusters | Both EMPTY |
| **Competitor Intelligence** | keywords, backlink_prospects | Both EMPTY |
| **Citation Intelligence** | citation_sites, citation_projects, citation_submissions | All EMPTY |
| **Local SEO** | business_profiles, citation_projects, citation_submissions, citation_sites | All EMPTY |
| **Recommendations V2** | backlink_campaigns, citation_projects, business_profiles | campaigns=13, others EMPTY |
| **SEO Health** | backlink_campaigns, backlink_prospects, outreach_threads, citation_submissions | 13 campaigns, others EMPTY |
| **Outreach Quality** | outreach_threads, outreach_emails | Both EMPTY |
| **Copilot V2** | All tables (reads across everything) | Most EMPTY |

### Current Engine Output (with empty tables)

| Engine | Score | Output |
|--------|-------|--------|
| Keyword Priority | 0/100 | "No keywords found" |
| Competitor Intelligence | N/A | Domain comparison works but has no keyword data |
| Citation Intelligence | 0/100 | "No sites found" |
| Local SEO | 0/100 | "No business profile found" |
| Recommendations V2 | 0 recs | "No campaigns exist" (incorrect — 13 exist) |
| SEO Health | 0/100 | All components zero |
| Outreach Quality | 56.5/100 | Works (evaluates provided text) |
| Copilot V2 | low | "No data" for most questions |

---

## P0 Findings

1. **14 SEO execution tables are completely empty** — Intelligence engines produce useless output
2. **No business profiles** — Local SEO engine always returns 404
3. **No keywords** — Keyword Priority engine always returns 0
4. **No prospects** — Prospect scoring returns nothing
5. **No outreach history** — Outreach quality has no real context
6. **No citation sites** — Citation Intelligence has nothing to recommend
7. **No competitor data** — Competitor analysis impossible

## P1 Findings

1. **No email templates** — Outreach has no templates to use
2. **No SERP snapshots** — Trend analysis impossible
3. **No keyword clusters** — Cluster analysis returns nothing
4. **No contact data** — Outreach can't find contacts
5. **No acquired links** — Link verification has nothing to check

---

## Recommended Action

Build a comprehensive data seeder that populates ALL 14 empty SEO execution tables with realistic development data. This is the single highest-impact action for Phase 12.5.

**Priority:** P0 — Must complete before any intelligence engine can be validated.
