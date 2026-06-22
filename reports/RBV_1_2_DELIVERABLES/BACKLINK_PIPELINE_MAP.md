# BACKLINK PIPELINE MAP

## Frontend
- Next.js dev server (http://localhost:3000) – UI for campaigns, prospects, outreach threads.

## Backend API (FastAPI, /api/v1)
- **/clients** – CRUD client records (requires `status`, `archived_at`).
- **/campaigns** – Create/list campaigns, launch via `POST /campaigns/{id}/launch`.
- **/prospects** – Retrieve prospect list for a tenant.
- **/backlink‑intelligence/** – Prospect discovery, outreach predictions (requires auth).
- **/outreach-operations/** – Dashboard, thread status updates.

## Database (PostgreSQL)
- Tables: `tenants`, `users`, `clients` (now includes `status`, `archived_at`), `campaigns`, `prospects`, `outreach_threads`, `audit_log`, `workflow_events`.

## Temporal
- Workflow `BacklinkCampaignWorkflow` orchestrates prospect scoring, outreach generation, approval, launch, link acquisition.

## Workers
- `dev-worker-all` runs Temporal activities: prospect scoring, outreach drafting, link verification.

## Queues & Messaging
- Kafka topics for campaign events (e.g. `workflow_campaign_started`).

## Automation Rules
- `workflow_automation.py` defines triggers (e.g. follow‑up reminders).

## Storage
- Redis (caching), MinIO (asset storage), Qdrant (vector search), MailHog (email capture).

All components are running locally and reachable via their ports (see `LOCAL_DEPLOYMENT_REPORT.md`).
