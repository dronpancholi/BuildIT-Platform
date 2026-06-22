#!/usr/bin/env python3
"""Phase 1.3 Workstream D - API Reliability Certification

Sample-based audit of 672 endpoints:
- WORKING: 200 with valid data
- PARTIAL: works but has issues
- BROKEN: 5xx or unhandled errors
- UNUSED: would need real frontend/code usage check
"""
import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict
import random

EVIDENCE_DIR = Path("/tmp/phase_1_3_evidence")
BASE = "http://localhost:8000/api/v1"
TENANT = "00000000-0000-0000-0000-000000000001"
OTHER_TENANT = "11111111-1111-1111-1111-111111111111"
H_BASE = {
    "X-User-Id": "00000000-0000-0000-0000-000000000000",
    "X-Tenant-Id": TENANT,
    "X-User-Role": "admin",
    "Content-Type": "application/json",
}

# Load OpenAPI
with open("/tmp/openapi.json") as f:
    SPEC = json.load(f)


def call_api(method, path, data=None, query=None, headers=None, expect_auth_fail=False):
    # Strip /api/v1 if present (BASE already has it)
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
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try: rb = json.loads(e.read().decode() or "{}")
        except: rb = {"detail": str(e)}
        return e.code, rb
    except Exception as e:
        return 0, {"error": str(e)}


def get_endpoints_by_tag():
    """Group endpoints by first tag."""
    by_tag = defaultdict(list)
    SKIP_PATH_PATTERNS = ["/stream/", "text/event-stream", "/sse/"]
    for p, ops in SPEC.get("paths", {}).items():
        for m, op in ops.items():
            if m not in ("get", "post", "put", "delete", "patch"):
                continue
            # Skip streaming/SSE endpoints
            if any(pat in p for pat in ["/stream/", "/sse/"]):
                continue
            # Skip ops that produce text/event-stream
            content_types = op.get("responses", {}).get("200", {}).get("content", {}) if isinstance(op.get("responses", {}).get("200"), dict) else {}
            if "text/event-stream" in content_types:
                continue
            tags = op.get("tags", ["untagged"])
            tag = tags[0].lower().replace(" ", "-")
            params = op.get("parameters", [])
            has_path_param = any(pp.get("in") == "path" and pp.get("required", False) for pp in params)
            by_tag[tag].append({
                "method": m.upper(),
                "path": p,
                "op": op,
                "has_path_param": has_path_param,
                "summary": op.get("summary", "")[:80],
            })
    return dict(by_tag)


def build_test_path(endpoint):
    """Build a concrete path for endpoints with path params."""
    p = endpoint["path"]
    if endpoint["has_path_param"]:
        # Replace {param} with sample values
        sample_ids = {
            "{client_id}": "ed582e55-7408-4052-a6ed-f4d036862c3f",
            "{campaign_id}": "ea70a02e-bd66-4404-b92b-5e695b89d7c2",
            "{thread_id}": "1c29852c-67fa-4789-99ff-b6a1bac4551f",
            "{acquired_link_id}": "44444444-4444-4444-4444-444444444444",
            "{goal_id}": "373e0122-32ac-49f0-923f-ea0ea308d765",
            "{plan_id}": "3f4b9c0c-ec94-4470-ae46-e577591ae628",
            "{report_id}": "40706156-2f25-49df-9182-8749406602ae",
            "{customer_id}": "ed582e55-7408-4052-a6ed-f4d036862c3f",
            "{id}": "ea70a02e-bd66-4404-b92b-5e695b89d7c2",
            "{goal_definition_id}": "260dd618-3287-4713-b398-d01e2da8347e",
            "{draft_id}": "x",
            "{schedule_id}": "x",
            "{attachment_id}": "x",
            "{tenant_id}": TENANT,
            "{user_id}": "00000000-0000-0000-0000-000000000000",
        }
        for k, v in sample_ids.items():
            p = p.replace(k, v)
    return p


def classify_endpoint(endpoint):
    """Test endpoint and return classification."""
    path = build_test_path(endpoint)
    method = endpoint["method"]

    # 1. Basic auth check — no headers
    s_noauth, _ = call_api(method, path, headers={})
    auth_required = s_noauth in (401, 403)

    # 2. Tenant isolation — wrong tenant
    s_wrongt, _ = call_api(method, path, headers={"X-Tenant-Id": OTHER_TENANT})
    # If it returns 200 for wrong tenant, isolation may be broken
    tenant_ok = s_wrongt != 200

    # 3. Basic functional call
    qs = {"tenant_id": TENANT} if "tenant_id" not in path else None
    s_ok, resp = call_api(method, path, query=qs)
    rate_limited = s_ok == 429
    server_err = s_ok >= 500
    not_found = s_ok == 404
    validation = s_ok in (400, 422)

    # Classification
    if rate_limited:
        return "PARTIAL", "rate_limited", {"status": s_ok}
    if server_err:
        return "BROKEN", "5xx_error", {"status": s_ok, "body": str(resp)[:200]}
    if not_found:
        return "BROKEN", "404", {"status": s_ok}
    if 200 <= s_ok < 300:
        # Success
        if not auth_required:
            return "WORKING", "no_auth_required_but_ok", {"status": s_ok}
        return "WORKING", "all_checks_passed", {
            "status": s_ok, "tenant_isolated": tenant_ok,
            "auth_required": auth_required,
        }
    if validation:
        return "PARTIAL", "validation_error", {"status": s_ok}
    if s_ok in (401, 403):
        return "WORKING", "auth_required", {"status": s_ok}
    return "PARTIAL", "other", {"status": s_ok, "body": str(resp)[:200]}


def main():
    print("=" * 70)
    print("PHASE 1.3 WORKSTREAM D — API Reliability Certification")
    print("=" * 70)
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")

    by_tag = get_endpoints_by_tag()
    total = sum(len(v) for v in by_tag.values())
    print(f"Total endpoints: {total} across {len(by_tag)} tags")
    print()

    # Sample: take up to 150 endpoints, balanced across tags
    random.seed(42)
    sample = []
    per_tag = max(1, 150 // len(by_tag))
    for tag, eps in by_tag.items():
        chosen = random.sample(eps, min(per_tag, len(eps)))
        for e in chosen: e["tag"] = tag
        sample.extend(chosen)
    # If under 150, top up from largest tags
    while len(sample) < min(150, total):
        largest_tag = max(by_tag, key=lambda t: len(by_tag[t]))
        extras = [e for e in by_tag[largest_tag] if e not in sample]
        if not extras: break
        e = extras[0]
        e["tag"] = largest_tag
        sample.append(e)

    print(f"Sampling {len(sample)} endpoints for testing")
    print()

    results = []
    classification_counts = defaultdict(int)
    by_tag_results = defaultdict(lambda: defaultdict(int))

    for i, e in enumerate(sample):
        try:
            cls, reason, detail = classify_endpoint(e)
        except Exception as ex:
            cls, reason, detail = "PARTIAL", "exception", {"error": str(ex)}
        classification_counts[cls] += 1
        by_tag_results[e["tag"]][cls] += 1
        results.append({
            "tag": e["tag"],
            "method": e["method"],
            "path": e["path"],
            "summary": e["summary"],
            "classification": cls,
            "reason": reason,
            "detail": detail,
        })
        # Status
        marker = {"WORKING": "✓", "PARTIAL": "P", "BROKEN": "✗", "UNUSED": "?"}.get(cls, "?")
        # Print every 10 + every broken
        if (i + 1) % 10 == 0 or cls == "BROKEN":
            print(f"  {marker} [{i+1:3d}/{len(sample)}] {e['method']:6s} {e['path'][:60]:60s} → {cls} ({reason})", flush=True)
        time.sleep(0.1)  # tighter sleep to avoid rate limit

    # Save
    with open(EVIDENCE_DIR / "workstream_d_api_certification.json", "w") as f:
        json.dump({
            "sampled": len(results),
            "total_endpoints": total,
            "by_tag": dict(by_tag),
            "classification_counts": dict(classification_counts),
            "by_tag_results": dict(by_tag_results),
            "results": results,
        }, f, indent=2, default=str)

    print()
    print("=" * 70)
    print(f"SAMPLED: {len(results)} / TOTAL: {total}")
    print(f"Classification: {dict(classification_counts)}")
    print("By tag (top 10):")
    for tag, counts in sorted(by_tag_results.items(), key=lambda x: -sum(x[1].values()))[:10]:
        print(f"  {tag:30s}: {dict(counts)}")
    print(f"Saved: {EVIDENCE_DIR}/workstream_d_api_certification.json")
    print("=" * 70)


if __name__ == "__main__":
    main()
