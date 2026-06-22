#!/usr/bin/env python3
"""Phase 1.3 Workstream G - Observability Validation

Validates: Prometheus metrics, audit logs, traces, alerts.
For each major workflow: metric emitted, audit written, trace generated.
"""
import json
import re
import time
import subprocess
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

EVIDENCE_DIR = Path("/tmp/phase_1_3_evidence")
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
BASE = "http://localhost:8000/api/v1"
TENANT = "00000000-0000-0000-0000-000000000001"
H_BASE = {
    "X-User-Id": "00000000-0000-0000-0000-000000000000",
    "X-Tenant-Id": TENANT,
    "X-User-Role": "admin",
    "Content-Type": "application/json",
}


def call_api(method, path, data=None, query=None):
    if path.startswith("/api/v1"):
        path = path[len("/api/v1"):]
    url = f"{BASE}{path}"
    if query:
        qs = "&".join(f"{k}={v}" for k, v in query.items())
        url = f"{url}?{qs}"
    body = json.dumps(data).encode() if data is not None else b""
    req = urllib.request.Request(url, data=body, method=method, headers=H_BASE)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as e:
        try: rb = e.read().decode("utf-8", errors="ignore")
        except: rb = ""
        return e.code, rb
    except Exception as e:
        return 0, str(e)


def db_query(sql):
    out = subprocess.run(
        ["psql", "-h", "localhost", "-U", "dronpancholi", "-d", "seo_platform", "-tA", "-F", "|", "-c", sql],
        capture_output=True, text=True, timeout=10,
    )
    return [l for l in out.stdout.split("\n") if l]


def main():
    print("=" * 70)
    print("PHASE 1.3 WORKSTREAM G — Observability Validation")
    print("=" * 70)
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")
    print()

    results = []

    # 1. Prometheus metrics endpoint
    print("=== 1. Prometheus Metrics Endpoint ===")
    s, body = call_api("GET", "/metrics")
    print(f"  /api/v1/metrics: status={s}, body length={len(body)}")
    if s == 200:
        # Parse Prometheus format
        lines = body.split("\n")
        metric_count = sum(1 for l in lines if re.match(r"^[a-z_][a-z0-9_]+\s+", l))
        metric_names = set()
        for l in lines:
            m = re.match(r"^([a-z_][a-z0-9_]+)\s+", l)
            if m: metric_names.add(m.group(1))
        print(f"  Metric lines: {metric_count}")
        print(f"  Unique metrics: {len(metric_names)}")
        # Show some key ones
        key_metrics = [m for m in metric_names if any(k in m for k in ("http", "request", "api", "workflow", "rate", "outreach", "backlink", "tenant", "auth"))]
        print(f"  Key metrics (sample): {key_metrics[:10]}")
        results.append({
            "check": "prometheus_metrics",
            "endpoint": "/api/v1/metrics",
            "status": s,
            "metric_count": metric_count,
            "unique_metrics": len(metric_names),
            "key_metrics": key_metrics[:20],
        })
    else:
        results.append({
            "check": "prometheus_metrics",
            "endpoint": "/api/v1/metrics",
            "status": s,
            "issue": "metrics endpoint failed",
        })
    print()

    # 2. Audit log writes
    print("=== 2. Audit Log Writes ===")
    # Make a request that should trigger an audit log
    s, body = call_api("GET", "/clients?tenant_id=00000000-0000-0000-0000-000000000001&limit=1")
    # Wait briefly for async audit write
    time.sleep(1)
    audit_rows = db_query("SELECT count(*) FROM audit_log WHERE created_at > now() - interval '30 seconds';")
    recent_audit = int(audit_rows[0]) if audit_rows and audit_rows[0].isdigit() else 0
    print(f"  Recent audit_log rows (last 30s): {recent_audit}")
    # Total audit_log
    total_audit = db_query("SELECT count(*) FROM audit_log;")
    total = int(total_audit[0]) if total_audit and total_audit[0].isdigit() else 0
    print(f"  Total audit_log rows: {total}")
    results.append({
        "check": "audit_log_writes",
        "recent_count": recent_audit,
        "total_count": total,
        "writing": recent_audit > 0,
    })
    print()

    # 3. Trace generation (check via observability/traces endpoint)
    print("=== 3. Trace Generation ===")
    s, body = call_api("GET", "/observability/traces?tenant_id=00000000-0000-0000-0000-000000000001&limit=5")
    print(f"  /observability/traces: status={s}, body length={len(body)}")
    trace_count = 0
    if s == 200 and "traces" in body:
        try:
            j = json.loads(body)
            trace_count = len(j.get("data", {}).get("traces", [])) if isinstance(j.get("data"), dict) else 0
        except: pass
    print(f"  Traces returned: {trace_count}")
    results.append({
        "check": "trace_generation",
        "endpoint": "/observability/traces",
        "status": s,
        "trace_count": trace_count,
    })
    print()

    # 4. Workflow analytics
    print("=== 4. Workflow Analytics ===")
    s, body = call_api("GET", "/observability/workflow-analytics?tenant_id=00000000-0000-0000-0000-000000000001")
    print(f"  /observability/workflow-analytics: status={s}, body length={len(body)}")
    results.append({
        "check": "workflow_analytics",
        "status": s,
        "has_data": s == 200 and len(body) > 100,
    })
    print()

    # 5. Telemetry endpoints
    print("=== 5. Telemetry Endpoints ===")
    telemetry_eps = [
        "/observability/communication-telemetry",
        "/observability/scraping-telemetry",
        "/observability/retry-analytics",
        "/observability/inference-analytics",
    ]
    for ep in telemetry_eps:
        s, body = call_api("GET", f"{ep}?tenant_id=00000000-0000-0000-0000-000000000001")
        print(f"  {ep}: status={s}, body={len(body)}B")
        results.append({
            "check": "telemetry",
            "endpoint": ep,
            "status": s,
            "has_data": s == 200 and len(body) > 100,
        })
    print()

    # 6. Workflow execution evidence
    print("=== 6. Workflow Execution Evidence (Temporal) ===")
    worker_health = call_api("GET", "/health")
    s_h, body_h = worker_health
    if s_h == 200:
        try:
            j = json.loads(body_h)
            for c in j.get("components", []):
                if c["name"] == "workers":
                    print(f"  Workers: {c['status']} — {c.get('message', '')}")
                    results.append({
                        "check": "temporal_workers",
                        "status": c["status"],
                        "active_workflows": c.get("message", ""),
                    })
        except: pass

    # 7. Prometheus format validation
    print("\n=== 7. Prometheus Format Validation ===")
    s, body = call_api("GET", "/metrics")
    if s == 200:
        lines = body.split("\n")
        # Check format
        valid_lines = 0
        comment_lines = 0
        for l in lines:
            if not l.strip(): continue
            if l.startswith("#"): comment_lines += 1
            elif re.match(r"^[a-zA-Z_:][a-zA-Z0-9_:]*(\{[^}]*\})?\s+[-+]?[0-9.eE+\-]+", l):
                valid_lines += 1
        print(f"  Total non-empty lines: {sum(1 for l in lines if l.strip())}")
        print(f"  Comment lines (#): {comment_lines}")
        print(f"  Valid metric lines: {valid_lines}")
        # Check for HELP/TYPE
        has_help = "# HELP" in body
        has_type = "# TYPE" in body
        print(f"  Has HELP comments: {has_help}")
        print(f"  Has TYPE comments: {has_type}")
        results.append({
            "check": "prometheus_format",
            "valid_metric_lines": valid_lines,
            "comment_lines": comment_lines,
            "has_help": has_help,
            "has_type": has_type,
            "format_valid": valid_lines > 0 and has_help and has_type,
        })

    # 8. Save
    with open(EVIDENCE_DIR / "workstream_g_observability.json", "w") as f:
        json.dump({"results": results, "summary": {
            "total_checks": len(results),
            "pass": sum(1 for r in results if r.get("status") == 200 or r.get("writing") is True or r.get("has_data") is True or r.get("format_valid") is True),
        }}, f, indent=2, default=str)

    print()
    print("=" * 70)
    print(f"TOTALS: {len(results)} checks | pass={sum(1 for r in results if r.get('status') == 200 or r.get('writing') is True or r.get('has_data') is True or r.get('format_valid') is True)}")
    print(f"Saved: {EVIDENCE_DIR}/workstream_g_observability.json")
    print("=" * 70)


if __name__ == "__main__":
    main()
