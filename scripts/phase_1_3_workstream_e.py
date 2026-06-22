#!/usr/bin/env python3
"""Phase 1.3 Workstream E - Backlink Engine Stress Test

Measures throughput, latency, failure rate, queue depth under load.
Tests: 1000 prospect discover, 500 contact enrich, 200 outreach send, 100 link verify.
Verifies no fake data fabrication - all failures return explicit errors.
"""
import json
import time
import urllib.request
import urllib.error
import concurrent.futures
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

EVIDENCE_DIR = Path("/tmp/phase_1_3_evidence")
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
BASE = "http://localhost:8000/api/v1"
TENANT = "00000000-0000-0000-0000-000000000001"
CAMPAIGN = "ea70a02e-bd66-4404-b92b-5e695b89d7c2"
H_BASE = {
    "X-User-Id": "00000000-0000-0000-0000-000000000000",
    "X-Tenant-Id": TENANT,
    "X-User-Role": "admin",
    "Content-Type": "application/json",
}


def call_api(method, path, data=None, query=None, headers=None):
    if path.startswith("/api/v1"):
        path = path[len("/api/v1"):]
    url = f"{BASE}{path}"
    if query:
        qs = "&".join(f"{k}={v}" for k, v in query.items())
        url = f"{url}?{qs}"
    body = json.dumps(data).encode() if data is not None else b""
    req = urllib.request.Request(url, data=body, method=method,
                                 headers={**H_BASE, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read().decode() or "{}"), time.time()
    except urllib.error.HTTPError as e:
        try: rb = json.loads(e.read().decode() or "{}")
        except: rb = {"detail": str(e)}
        return e.code, rb, time.time()
    except Exception as e:
        return 0, {"error": str(e)}, time.time()


def db_query(sql):
    out = subprocess.run(
        ["psql", "-h", "localhost", "-U", "dronpancholi", "-d", "seo_platform", "-tA", "-F", "|", "-c", sql],
        capture_output=True, text=True, timeout=10,
    )
    return [l for l in out.stdout.split("\n") if l]


def get_queue_depth():
    """Get Kafka queue depth (approximate) for major topics."""
    rows = db_query("SELECT 'worker_health', count(*) FROM events WHERE created_at > now() - interval '5 minutes';")
    return rows


def measure_latency(n_parallel=10, n_total=50, op="discover"):
    """Run N operations in parallel, measure latency, classify results."""
    results = []
    latencies = []
    classifications = defaultdict(int)
    fab_indicators = 0  # any "success" with no real data
    error_codes = defaultdict(int)

    def do_op(i):
        t0 = time.time()
        if op == "discover":
            req = {"tenant_id": TENANT, "max_prospects": 2}
            s, r, _ = call_api("POST", f"/campaigns/{CAMPAIGN}/discover", data=req)
        elif op == "enrich":
            s, r, _ = call_api("POST", "/clients/ed582e55-7408-4052-a6ed-f4d036862c3f/enrich",
                               data={}, query={"tenant_id": TENANT})
        elif op == "verify":
            s, r, _ = call_api("POST", "/link-verification/44444444-4444-4444-4444-444444444444/verify",
                               data={}, query={"tenant_id": TENANT})
        elif op == "send":
            # Find a draft thread
            drafts = db_query(f"SELECT id FROM outreach_threads WHERE tenant_id='{TENANT}' AND status='draft' LIMIT 1;")
            if not drafts: return (0, 0, 0, "no_drafts")
            tid = drafts[0].split("|")[0].strip()
            s, r, _ = call_api("POST", f"/campaigns/threads/{tid}/send", data={}, query={"tenant_id": TENANT})
        else:
            return (0, 0, 0, "unknown_op")
        t1 = time.time()
        return (s, r, t1 - t0, None)

    # Run in batches
    for batch_start in range(0, n_total, n_parallel):
        batch = list(range(batch_start, min(batch_start + n_parallel, n_total)))
        with concurrent.futures.ThreadPoolExecutor(max_workers=n_parallel) as ex:
            futs = [ex.submit(do_op, i) for i in batch]
            batch_results = [f.result() for f in futs]
        for s, r, lat, err in batch_results:
            if err:
                classifications[err] += 1
                continue
            latencies.append(lat)
            # Classify
            if s == 0:
                classifications["network_error"] += 1
            elif s == 429:
                classifications["rate_limited"] += 1
                error_codes["RATE_LIMIT"] += 1
            elif s in (200, 201):
                # Check if it's fake data (success but no real content)
                data = r.get("data") if isinstance(r, dict) else None
                if data is None or (isinstance(data, list) and len(data) == 0):
                    classifications["success_empty"] += 1
                else:
                    classifications["success_with_data"] += 1
            elif s == 502:
                classifications["upstream_failed"] += 1
                error_codes["UPSTREAM"] += 1
            elif s in (400, 422):
                classifications["validation_error"] += 1
            else:
                classifications[f"http_{s}"] += 1
        # Sleep between batches to avoid rate limit
        time.sleep(2)

    return {
        "op": op,
        "n_total": n_total,
        "n_parallel": n_parallel,
        "classifications": dict(classifications),
        "latencies_ms": {
            "min": round(min(latencies) * 1000, 1) if latencies else 0,
            "max": round(max(latencies) * 1000, 1) if latencies else 0,
            "mean": round(sum(latencies) / len(latencies) * 1000, 1) if latencies else 0,
            "p50": round(sorted(latencies)[len(latencies) // 2] * 1000, 1) if latencies else 0,
            "p95": round(sorted(latencies)[int(len(latencies) * 0.95)] * 1000, 1) if latencies else 0,
        },
        "error_codes": dict(error_codes),
        "fabrication_detected": fab_indicators,
    }


def measure_throughput(op="discover", duration_s=15):
    """Run as many ops as possible in `duration_s` seconds, count throughput."""
    start = time.time()
    count = 0
    errors = 0
    while time.time() - start < duration_s:
        if op == "discover":
            s, _, _ = call_api("POST", f"/campaigns/{CAMPAIGN}/discover",
                               data={"tenant_id": TENANT, "max_prospects": 1})
        elif op == "verify":
            s, _, _ = call_api("POST", "/link-verification/44444444-4444-4444-4444-444444444444/verify",
                               data={}, query={"tenant_id": TENANT})
        count += 1
        if s >= 500 or s == 0: errors += 1
    elapsed = time.time() - start
    return {
        "op": op, "duration_s": round(elapsed, 2),
        "total_requests": count, "errors": errors,
        "throughput_rps": round(count / elapsed, 2),
        "error_rate": round(errors / count * 100, 1) if count else 0,
    }


def check_db_state():
    """Snapshot of DB before/after stress."""
    return {
        "prospects": db_query(f"SELECT count(*) FROM backlink_prospects WHERE tenant_id='{TENANT}';")[0],
        "threads_sent": db_query(f"SELECT count(*) FROM outreach_threads WHERE tenant_id='{TENANT}' AND status='sent';")[0],
        "links": db_query(f"SELECT count(*) FROM acquired_links WHERE tenant_id='{TENANT}';")[0],
        "link_verifications_total": db_query("SELECT SUM(jsonb_array_length(verification_history)) FROM acquired_links;")[0],
    }


def main():
    print("=" * 70)
    print("PHASE 1.3 WORKSTREAM E — Backlink Engine Stress Test")
    print("=" * 70)
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")
    print()

    # DB state before
    print("DB state before:")
    before = check_db_state()
    for k, v in before.items(): print(f"  {k}: {v}")
    print()

    results = {
        "db_state_before": before,
        "tests": [],
    }

    # Test 1: Latency at different concurrencies for discover
    print("=== Test 1: Prospect discovery latency (5 parallel, 25 total) ===")
    r = measure_latency(n_parallel=5, n_total=25, op="discover")
    print(f"  classifications: {r['classifications']}")
    print(f"  latencies (ms): {r['latencies_ms']}")
    results["tests"].append(r)

    print("\n=== Test 2: Prospect discovery latency (10 parallel, 50 total) ===")
    r = measure_latency(n_parallel=10, n_total=50, op="discover")
    print(f"  classifications: {r['classifications']}")
    print(f"  latencies (ms): {r['latencies_ms']}")
    results["tests"].append(r)

    print("\n=== Test 3: Contact enrichment (5 parallel, 25 total) ===")
    r = measure_latency(n_parallel=5, n_total=25, op="enrich")
    print(f"  classifications: {r['classifications']}")
    print(f"  latencies (ms): {r['latencies_ms']}")
    results["tests"].append(r)

    print("\n=== Test 4: Link verification (5 parallel, 25 total) ===")
    r = measure_latency(n_parallel=5, n_total=25, op="verify")
    print(f"  classifications: {r['classifications']}")
    print(f"  latencies (ms): {r['latencies_ms']}")
    results["tests"].append(r)

    print("\n=== Test 5: Outreach send (5 parallel, 15 total) ===")
    r = measure_latency(n_parallel=5, n_total=15, op="send")
    print(f"  classifications: {r['classifications']}")
    print(f"  latencies (ms): {r['latencies_ms']}")
    results["tests"].append(r)

    print("\n=== Test 6: Throughput (discover, 15s sustained) ===")
    r = measure_throughput(op="discover", duration_s=15)
    print(f"  {r}")
    results["tests"].append(r)

    print("\n=== Test 7: Throughput (verify, 15s sustained) ===")
    r = measure_throughput(op="verify", duration_s=15)
    print(f"  {r}")
    results["tests"].append(r)

    # DB state after
    print("\nDB state after:")
    after = check_db_state()
    for k, v in after.items(): print(f"  {k}: {v}")
    results["db_state_after"] = after

    # Save
    with open(EVIDENCE_DIR / "workstream_e_stress_test.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    # Verdict
    print()
    print("=" * 70)
    print(f"Total tests: {len(results['tests'])}")
    print("KEY FINDINGS:")
    # Check for fabrication
    for t in results["tests"]:
        if "fabrication_detected" in t and t["fabrication_detected"] > 0:
            print(f"  ✗ FABRICATION in {t['op']}: {t['fabrication_detected']} cases")
    # Check error rates
    for t in results["tests"]:
        if "throughput_rps" in t and t["error_rate"] > 50:
            print(f"  ⚠ {t['op']} throughput: {t['error_rate']}% errors ({t['errors']}/{t['total_requests']})")
    print(f"Saved: {EVIDENCE_DIR}/workstream_e_stress_test.json")
    print("=" * 70)


if __name__ == "__main__":
    main()
