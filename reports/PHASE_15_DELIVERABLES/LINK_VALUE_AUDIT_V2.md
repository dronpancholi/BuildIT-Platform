# Link Value Audit (Phase 15D)

**Scope**: All acquired links for the five campaigns evaluated in Phase 15A.

## Link count

| Campaign ID | Links recorded | Links verified (status=`verified_live` or `verified_nofollow`) |
|-------------|---------------|---------------------------------------------------------------|
| 6c06b297-9149-4d1d-a82e-43d3c5673636 | 0 | 0 |
| b82b11d9-b7d8-4dd1-a67c-d1af4826a46a | 0 | 0 |
| f009e745-c1d0-45b6-a3a5-e8c8c4c82995 | 0 | 0 |
| dee400b1-09cb-45d9-9c4c-a3c115dcc406 | 0 | 0 |
| a362c71f-3873-40f0-a8ac-5199938d4e50 | 0 | 0 |

**Total links recorded:** 0

### Why no links?

* The BACKLINK_ENGINE worker completed draft generation and delivery, but the downstream link‑acquisition workflow depends on external services (e.g., crawling, host verification) that are not currently provisioned in the dev environment.
* Kafka connectivity issues observed in `worker.log` indicate that the link‑acquisition activities may be failing silently. The platform logs a warning when a worker cannot consume from the `seo-platform-workflow-workers` queue.

### Recommended actions

1. **Provision link‑acquisition services** – Ensure the `link_acquisition` worker container is running and subscribed to the correct Temporal task queue.
2. **Enable health‑check alerts** – Add a Temporal activity heartbeat for the link‑acquisition step so failures surface in the UI.
3. **Re‑run campaigns after services are up** – Once the pipeline is functional, re‑execute the same campaigns and repeat this audit.

*Prepared on $(date)*
