# Project 31A — Canonical Repository Report

> Mission objective (Phase S1): identify the canonical source of truth and verify platform start paths.
> Scope-limited scan; only paths actually opened and inspected.

---

## Executive verdict

**Canonical repository** is:

```
/Users/dronpancholi/Developer/01_Strategic/Project 31A
```

The other `~/Developer/Project 31A` is a **stale parallel folder** (no `.git`, missing `backend/` and `frontend/`, last touched 2026-06-19) and must not be used as a working tree.

---

## 1. Repository root

| Field | Value |
|---|---|
| Path | `/Users/dronpancholi/Developer/01_Strategic/Project 31A` |
| Git toplevel | `/Users/dronpancholi/Developer/01_Strategic/Project 31A` |
| Remote | `https://github.com/dronpancholi/BuildIT-Platform.git` |
| Current branch | `backup-before-demo-removal` |
| Tracked vs origin | `ahead 10` (10 unpushed commits on this branch) |
| Last commit | `ac8ba86` — 2026-05-25 — `feat: Phase 12B Sprint 12B.4 Template Picker COMPLETE` |
| Tree state | dirty: modified `.env.*`, `backend/pyproject.toml`, `backend/alembic/versions/0fc31328153b_…`, `backend/src/seo_platform/api/endpoints/adaptive_optimization.py`, etc. |

> **Important:** HEAD commit (`ac8ba86`, 2026-05-25) is **4 weeks older than the latest file mtimes** in the repo (e.g. `backend/` and `frontend/` modified through 2026-06-20). The working tree contains substantial in-progress work that is **not yet committed** on this branch. Treat this as a normal in-flight development state — not a contradiction.

---

## 2. Component paths

| Component | Absolute path |
|---|---|
| **Repository root** | `/Users/dronpancholi/Developer/01_Strategic/Project 31A` |
| **Frontend** | `/Users/dronpancholi/Developer/01_Strategic/Project 31A/frontend` |
| **Backend (API + workers + workflows in one)** | `/Users/dronpancholi/Developer/01_Strategic/Project 31A/backend` |
| **Workflows (Temporal)** | `/Users/dronpancholi/Developer/01_Strategic/Project 31A/backend/src/seo_platform/workflows/` |
| **Workers** | _embedded in `backend/` — Temporal activities registered inside `backend/src/seo_platform/workflows/worker.py` (no separate top-level `workers/` directory exists)_ |
| **Infrastructure (docker/k8s/tf)** | `/Users/dronpancholi/Developer/01_Strategic/Project 31A/infrastructure` (subdirs: `docker/`, `kubernetes/`, `terraform/`) |
| **Database migrations** | `/Users/dronpancholi/Developer/01_Strategic/Project 31A/backend/alembic/` (Alembic; config at `backend/alembic.ini`) |
| **CI workflows** | `/Users/dronpancholi/Developer/01_Strategic/Project 31A/.github/workflows` |
| **Scripts** | `/Users/dronpancholi/Developer/01_Strategic/Project 31A/scripts` |
| **Docs** | `/Users/dronpancholi/Developer/01_Strategic/Project 31A/docs` |

---

## 3. Startup commands (canonical paths)

Each command must be run from the listed working directory.

### Infrastructure (Temporal / Kafka / Redis)
```bash
cd "/Users/dronpancholi/Developer/01_Strategic/Project 31A/infrastructure/docker"
docker compose up -d
```
Compose file lives under `infrastructure/docker/`. Until this is up, **backend startup is expected to fail** at the Temporal client init.

### Backend (FastAPI)
```bash
cd "/Users/dronpancholi/Developer/01_Strategic/Project 31A/backend"
.venv/bin/uvicorn seo_platform.main:app --host 0.0.0.0 --port 8000
```
- Entry point: `backend/src/seo_platform/main.py`
- Venv: `backend/.venv/` (also one at repo root `.venv/` — repo-root venv is the per-session one; backend has its own).
- Notable files referencing startup: `backend/alembic.ini`, `backend/Dockerfile`.

### Frontend
```bash
cd "/Users/dronpancholi/Developer/01_Strategic/Project 31A/frontend"
npm run dev          # (or pnpm/yarn — open `frontend/package.json` to confirm)
```
- Top-of-folder docs: `AGENTS.md`, `CLAUDE.md`, `FRONTEND_V2_PHASE_1_*` confirm an active frontend rewrite story.

### Migrations
```bash
cd "/Users/dronpancholi/Developer/01_Strategic/Project 31A/backend"
# alembic env lives at backend/alembic/env.py — exact CLI flag set should be confirmed before applying
.venv/bin/alembic upgrade head
```
> Migration directory is non-empty (Phase 6 observability migration `0fc31328153b_…` is present and **modified, not committed**).

---

## 4. Duplicate / stale folders found

Searched `~` to depth 5 for any directory named `Project 31A` (or close variants).

| Path | Type | Status |
|---|---|---|
| `/Users/dronpancholi/Developer/01_Strategic/Project 31A` | **Canonical — has `.git`, full backend/frontend/infra** | ✅ USE THIS |
| `/Users/dronpancholi/Developer/Project 31A` | **Stale parallel folder — no `.git`, no `backend/`, no `frontend/`** | ⚠️ DO NOT USE |
| `/Users/dronpancholi/.config/manicode/projects/Project 31A` | Manicode agent project config cache (mirrors paths only) | informational, not a repo |
| `/Users/dronpancholi/~/Developer/01_Strategic/Project 31A` | Symbolic / config re-export of the canonical path | not a duplicate repo |

### Stale folder contents (`Developer/Project 31A`)
Confirmed present (no further inspection performed — Phase S1 explicitly forbids opportunistic exploration):
```
.DS_Store
config/
docs/
graphify-out/        (also exists under canonical, dated Jun 19)
infrastructure/      (dated Jun 18 — older than canonical's infra)
research/
src/                 (dated Jun 19)
```
This folder is read-only evidence at this point. Phase S2+ may decide to delete it; Phase S1 only **names and classifies** it.

---

## 5. Recommended canonical structure (no changes performed)

Keep the current monorepo layout — it is already the source of truth:

```
Project 31A/
├── frontend/                   → Next.js (or current framework) UI
├── backend/
│   ├── src/seo_platform/
│   │   ├── api/                → FastAPI routers/endpoints
│   │   ├── workflows/          ← Temporal workflows + worker.py
│   │   ├── providers/          → serp/data provider integrations
│   │   ├── rules_engine/
│   │   ├── services/
│   │   ├── models/
│   │   └── main.py             → FastAPI entry point
│   ├── alembic/                → DB migrations (Alembic)
│   ├── alembic.ini
│   ├── pyproject.toml
│   └── Dockerfile
├── infrastructure/
│   ├── docker/                 → docker-compose for local Temporal/Kafka/Redis
│   ├── kubernetes/
│   └── terraform/
├── .github/workflows/          → CI
├── scripts/                    → shell/automation utilities
├── docs/
├── reports/                    → past phase reports (archive)
└── graphify-out/               → auxiliary build artifact output
```

No restructuring is recommended for Phase S1.

---

## 6. What this confirms, what it does not

**Confirmed:**
- There is exactly **one** git-backed Project 31A on this host.
- That repo has all required components (backend + frontend + infra + Alembic + Temporal workflows).
- The remote is wired (`origin → BuildIT-Platform`).
- Workers are **embedded** in `backend/` (Temporal activities) — there is no separate worker repo or directory at the top level.

**Not confirmed (deferred per NIM rules):**
- Whether `docker compose up -d` from `infrastructure/docker/` actually brings Temporal/Kafka/Redis up healthy on this host.
- Whether `uvicorn` boots without traceback.
- Whether the `ahead 10` unpushed commits and the dirty-tree modifications compile/run.
- Anything inside `Developer/Project 31A` (the stale folder) beyond directory enumeration.
- Frontend framework version or whether `npm run dev` is the correct entry.

All of the above belong to subsequent phases.

---

## 7. Open questions parked for next phase

1. Confirm exact compose invocation: `up -d`, pwd, file name.
2. Confirm Alembic CLI invocation against `backend/alembic.ini` (any offline flags? async driver?).
3. Confirm frontend dev command (`package.json` script name).
4. Decide whether the 10 unpushed commits on `backup-before-demo-removal` should be pushed before any new work, or rebased onto a mainline branch.
5. Decide what to do with `~/Developer/Project 31A` (delete? rename? leave?).
