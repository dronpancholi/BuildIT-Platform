# Scale Validation Report (Phase 15H)

**Objective**: Stress test the platform with large numbers of campaigns, prospects, and outreach drafts to measure latency, throughput, and stability.

**Current test coverage**: Only a modest set of 5 campaigns (see Phase 15A) was executed. No high‑volume load (50+ campaigns, 5000+ prospects) has been performed in this environment due to resource constraints and the observed Kafka connectivity issues.

**Evidence**:

* The `worker.log` contains repeated `NodeNotReadyError` messages for the Kafka broker, preventing high‑throughput queue consumption.
* PostgreSQL performance metrics (e.g., `pg_stat_activity`) show normal load (<10 active queries) during the small‑scale runs.

**Implications**:

* Without a large‑scale run we cannot provide concrete latency or throughput numbers.
* The platform appears stable for the tested load (≤30 prospects per campaign) but scalability remains unproven.

**Recommended scaling steps**

1. **Fix Kafka connectivity** – ensure the `seo-kafka` container is healthy and reachable from worker processes.
2. **Generate bulk data** – use the `backend/scripts/generate_bulk_test_data.py` script (to be created) to insert 50 campaigns, 5000 prospects, and corresponding outreach threads.
3. **Run a timed benchmark** – capture API response times (`/api/v1/campaigns`, `/outreach-operations/threads`) and DB query latencies using `pg_stat_statements`.
4. **Record results** – repeat this report with concrete numbers.

*Prepared on $(date)*
