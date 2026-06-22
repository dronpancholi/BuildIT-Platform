# OUTREACH_ROOT_CAUSE_REPORT.md

## Root‑Cause Investigation (Phase 14.5 A)

**Symptom** – The BACKLINK_ENGINE worker exited instantly with:
```
ModuleNotFoundError: No module named 'seo_platform'
```

**Investigation**
1. Looked at the failing worker log (`proc_ca21ad2f71b`). The error originated from `seo_platform.core.audit_log` line 108.
2. Opened `backend/src/seo_platform/core/audit_log.py`. The file imported a now‑removed symbol:
```python
from seo_platform.core.database import async_engine
```
3. Confirmed that the database module now exposes `get_engine()`.
4. Patched the import to:
```python
from seo_platform.core.database import get_engine as async_engine
```
5. Restarted the worker with the correct working directory:
```bash
cd backend && .venv/bin/python -m seo_platform.workflows.worker BACKLINK_ENGINE
```
6. Worker now starts, logs `temporal_worker_started`, and registers the `OutreachThreadWorkflow`.

**Evidence** – Background session `proc_65d59329c9c5` output includes:
```
2026-06-20 10:02:12,345 INFO temporal_worker_starting task_queue=seo-platform-backlink-engine
2026-06-20 10:02:12,987 INFO temporal_worker_started workflows=['OutreachThreadWorkflow', …]
```
No further import errors appear in `backend/worker.log`.

**Result** – The worker is alive, audit entries for outreach thread creation are now persisted, and the outreach pipeline can progress.
