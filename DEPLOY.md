# BuildIT — Production Deployment Guide

Deploy the full BuildIT platform on a single VPS with Docker Compose.

> **Looking for the full operator runbook?**
> This file is the **5-minute quick start** for getting the stack up.
> For the complete production runbook (pre-flight checks, secret
> management, the 12-step deploy, post-deploy smoke test, operational
> procedures, rollback), see
> **[`DEPLOYMENT_RUNBOOK.md`](./DEPLOYMENT_RUNBOOK.md)**.
>
> For closing the one remaining open certification item (provider API
> keys) and promoting the platform from
> **CONDITIONALLY CERTIFIED → REAL WORLD CERTIFIED**, see
> **[`PROVIDER_PROVISIONING_CHECKLIST.md`](./PROVIDER_PROVISIONING_CHECKLIST.md)**.

---

## Prerequisites

- **Server:** Linux VPS (Ubuntu 22.04+, 4GB RAM min, 8GB recommended)
- **Domain:** A domain pointing to the server IP (e.g., `buildit.example.com`)
- **Software:** Docker + Docker Compose v2 installed on the server

---

## Quick Start (10 minutes)

### 1. Provision a VPS

Any provider works. Recommended specs:

| Provider | Plan | Cost | RAM | CPU |
|----------|------|------|-----|-----|
| Hetzner | CX22 | ~€4/mo | 4GB | 2 vCPU |
| DigitalOcean | Basic | ~$12/mo | 4GB | 2 vCPU |
| Linode | Linode 4GB | ~$12/mo | 4GB | 2 vCPU |

### 2. Install Docker

```bash
# On the server:
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in, or: newgrp docker
```

### 3. Clone & Deploy

```bash
# On the server:
git clone <your-repo-url> buildit
cd buildit

# Set your domain
export DOMAIN=buildit.example.com

# Start everything
cd infrastructure/docker
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

### 4. Verify

```bash
# Check all services are running
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps

# Check logs
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f

# Health check
curl http://localhost/healthz
```

### 5. Set Up SSL (HTTPS)

```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Get certificate (must have DNS pointing to this server)
sudo certbot --nginx -d $DOMAIN

# Auto-renewal
sudo certbot renew --dry-run
```

---

## Post-Deployment: Load Demo Data

Once all services are running, load a demo scenario:

```bash
# Load the TechStart demo scenario
curl -X POST "http://localhost/api/v1/demo/scenarios/load" \
  -H "Content-Type: application/json" \
  -d '{"name": "TechStart", "tenant_id": "00000000-0000-0000-0000-000000000001"}'

# Or load LocalFlorist
curl -X POST "http://localhost/api/v1/demo/scenarios/load" \
  -H "Content-Type: application/json" \
  -d '{"name": "LocalFlorist", "tenant_id": "00000000-0000-0000-0000-000000000001"}'

# Verify readiness
curl "http://localhost/api/v1/demo/readiness?tenant_id=00000000-0000-0000-0000-000000000001"
```

Then open `https://$DOMAIN` in a browser.

---

## What Works in Demo Mode (No External API Keys)

The platform is designed to demonstrate fully without paid API keys:

| Feature | Status | How |
|---------|--------|-----|
| Dashboard UI | ✅ Full | All 40+ dashboard pages render |
| Provider Health Center | ✅ Live | `/dashboard/providers` shows provider status |
| Demo Control Center | ✅ Works | `/dashboard/demo-control` — load/reset scenarios |
| Campaign Workflow Stepper | ✅ Shows data | Pre-seeded campaigns with timeline events |
| Prospect Graph | ✅ Shows data | `/api/v1/prospect-graph` from seeded data |
| AI-Composed Emails | ✅ Pre-seeded | OutreachThread records with sample emails |
| SSE War Room | ✅ Live streams | Real-time queue/worker/health data |
| Citation Data | ✅ Real SQL | Citations from seeded BusinessProfile data |
| Compliance Scoring | ✅ Works | `POST` an email body for scoring |
| Backlink Campaign (Temporal) | ✅ Runs if Temporal is up | Temporal auto-deploys in Docker |
| LLM Email Generation | ⚠️ Needs NVIDIA NIM key | Falls back to deterministic templates |
| Ahrefs / Hunter / Firecrawl | ⚠️ Needs API keys | Falls back to simulated providers |

---

## Service Architecture

```
                         User (HTTPS:443)
                              │
                          [Nginx]
                         /        \
                    /api/*          /*
                   /                     \
              [Backend API]          [Next.js Frontend]
              port 8000               port 3000
                   │
      ┌────────────┼────────────┬──────────────┐
      │            │            │              │
 [PostgreSQL]  [Redis]    [Temporal]      [Kafka]
    :5432       :6379       :7233          :9092
      │            │            │
 [Qdrant]    [MailHog]    [MinIO S3]
  :6333       :1025/8025   :9000
```

### Services Running

| Service | Port | Purpose |
|---------|------|---------|
| Nginx | 80/443 | Reverse proxy + SSL |
| Backend API | 8000 | FastAPI application |
| Frontend | 3000 | Next.js dashboard |
| PostgreSQL | 5432 | Primary database |
| Redis | 6379 | Cache + rate limiting + idempotency |
| Kafka | 9092 | Event bus (SSE streaming) |
| Temporal | 7233 | Workflow orchestration |
| Temporal UI | 8233 | Temporal web console |
| Qdrant | 6333 | Vector database |
| MailHog | 1025/8025 | Email capture (SMTP + UI) |
| MinIO | 9000/9001 | S3-compatible storage |

---

## Resource Usage

| Service | RAM (approx) |
|---------|-------------|
| PostgreSQL | 256 MB |
| Redis | 128 MB |
| Kafka + ZK | 1.0 GB |
| Temporal | 512 MB |
| Qdrant | 256 MB |
| Backend API | 256 MB |
| Frontend | 256 MB |
| Nginx | 32 MB |
| MinIO | 256 MB |
| MailHog | 64 MB |
| **Total** | **~3.0 GB** |

---

## Common Operations

```bash
# View logs for a specific service
docker compose logs -f backend
docker compose logs -f frontend

# Rebuild and restart a service after code changes
docker compose up -d --build backend

# Stop everything
docker compose -f docker-compose.yml -f docker-compose.prod.yml down

# Full reset (delete all data)
docker compose -f docker-compose.yml -f docker-compose.prod.yml down -v
```

---

## Troubleshooting

**"Temporal not configured — skipping"** — Expected. Temporal is optional for demo viewing. The workload UI still works without it.

**"Cannot find module X"** — Ensure the Docker images were built correctly: `docker compose build --no-cache backend`

**Error: address already in use** — Port conflict on the host. Stop any local services using ports 80, 3000, 8000, 5432, 6379.

**Frontend shows blank page** — Check `NEXT_PUBLIC_API_URL` env var. It must point to the API URL accessible from the browser (usually `https://$DOMAIN/api/v1`).

**SSE/War Room not updating** — Ensure `nginx.conf` has `proxy_buffering off` for `/api/v1/stream/` paths. Check browser console for SSE connection errors.
