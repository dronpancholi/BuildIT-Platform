#!/usr/bin/env python3
"""Phase 1.3 Workstream F - Provider Validation

Validates each external/integration provider:
- Configured? (env var set, secrets present)
- Functional? (real call works)
- Failure path? (returns explicit error, no fake fallback)
"""
import json
import os
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
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try: rb = json.loads(e.read().decode() or "{}")
        except: rb = {"detail": str(e)}
        return e.code, rb
    except Exception as e:
        return 0, {"error": str(e)}


def check_env(name):
    """Check if env var is set in the backend's environment."""
    try:
        out = subprocess.run(
            ["psql", "-h", "localhost", "-U", "dronpancholi", "-d", "seo_platform", "-tA", "-c", f"SELECT 1;"],
            capture_output=True, text=True, timeout=5,
        )
        # Read .env files
        for f in [".env", ".env.development", ".env.production"]:
            p = Path("/Users/dronpancholi/Developer/Project 31A/backend") / f
            if p.exists():
                for line in p.read_text().splitlines():
                    if line.startswith(f"{name}="):
                        v = line.split("=", 1)[1].strip().strip('"').strip("'")
                        return v
    except: pass
    return os.environ.get(name, None)


def check_provider_status():
    """Use the provider-health endpoint to check provider status."""
    s, r = call_api("GET", "/provider-health")
    return s, r


def check_seo_providers():
    """Check if SEO providers are configured via health endpoint."""
    s, h = call_api("GET", "/api/v1/health")
    if s == 200:
        for c in h.get("components", []):
            if c["name"] in ("external_apis", "nim", "playwright"):
                return c
    return None


def main():
    print("=" * 70)
    print("PHASE 1.3 WORKSTREAM F — Provider Validation")
    print("=" * 70)
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")
    print()

    results = []

    # 1. Provider health endpoint
    print("=== 1. Provider Health Endpoint ===")
    s, r = call_api("GET", "/provider-health")
    print(f"  Status: {s}")
    if isinstance(r, dict) and "data" in r:
        providers = r["data"]
        for k, v in (providers if isinstance(providers, dict) else {}).items():
            print(f"  {k}: {v}")
            results.append({
                "provider": k,
                "source": "provider-health",
                "configured": v.get("configured", False) if isinstance(v, dict) else False,
                "status": v.get("status", "unknown") if isinstance(v, dict) else "unknown",
            })
    print()

    # 2. Env var check
    print("=== 2. Environment Variable Configuration ===")
    env_vars = [
        ("HUNTER_API_KEY", "Hunter.io (email verification + contact discovery)"),
        ("SENDGRID_API_KEY", "SendGrid (email delivery)"),
        ("POSTMARK_API_KEY", "Postmark (email delivery)"),
        ("MAILGUN_API_KEY", "Mailgun (email delivery)"),
        ("AWS_ACCESS_KEY_ID", "AWS SES (email delivery)"),
        ("DATAFORSEO_LOGIN", "DataForSEO (SEO data)"),
        ("DATAFORSEO_PASSWORD", "DataForSEO (SEO data)"),
        ("AHREFS_API_KEY", "Ahrefs (backlink analysis)"),
        ("MAILHOG_HOST", "MailHog (dev email)"),
    ]
    for var, desc in env_vars:
        v = check_env(var)
        if v and v not in ("", "your-key-here", "changeme"):
            results.append({"provider": var, "source": "env", "configured": True, "value_redacted": v[:4] + "***" if len(v) > 4 else "***"})
            print(f"  ✓ {var}: CONFIGURED ({desc})")
        else:
            results.append({"provider": var, "source": "env", "configured": False})
            print(f"  ✗ {var}: NOT CONFIGURED ({desc})")
    print()

    # 3. Health component check
    print("=== 3. Health Component Status ===")
    s, h = call_api("GET", "/health")
    if s == 200:
        for c in h.get("components", []):
            msg = c.get("message") or ""
            print(f"  {c['name']:20s}: {c['status']:10s} latency={c.get('latency_ms', 0):.1f}ms msg={msg[:80]}")
            results.append({
                "component": c["name"],
                "source": "health",
                "status": c["status"],
                "configured": c["status"] != "degraded",
                "message": msg,
            })
    print()

    # 4. Functional probe — outbound to known unconfigured provider
    print("=== 4. Functional Probes ===")

    # 4a. Discover — should fail with explicit error
    s, r = call_api("POST", "/campaigns/ea70a02e-bd66-4404-b92b-5e695b89d7c2/discover",
                    data={"tenant_id": TENANT, "max_prospects": 1})
    print(f"  Discover: status={s}")
    if isinstance(r, dict):
        print(f"    Body excerpt: {json.dumps(r)[:200]}")
    # This is correct behavior (provider unconfigured)
    results.append({
        "test": "discover_with_unconfigured_providers",
        "status": s,
        "fabrication": "success_with_fake_data" if (s in (200, 201) and r.get("data") and not r.get("error")) else "no",
        "explicit_error": s in (502, 503) or r.get("error") is not None,
    })

    # 4b. Enrich — should fail with explicit error
    s, r = call_api("POST", "/clients/ed582e55-7408-4052-a6ed-f4d036862c3f/enrich",
                    data={}, query={"tenant_id": TENANT})
    print(f"  Enrich: status={s}")
    if isinstance(r, dict):
        print(f"    Body excerpt: {json.dumps(r)[:200]}")
    # Check if data correctly indicates failure (no fake enrichment)
    enriched_false = r.get("data", {}).get("enriched") is False if isinstance(r.get("data"), dict) else None
    print(f"    enriched=False: {enriched_false}")
    results.append({
        "test": "enrich_with_unconfigured_providers",
        "status": s,
        "fabrication": "no" if enriched_false is True else "yes",
        "explicit_error": enriched_false is True,
    })

    # 4c. Verify — should work (real HTTP fetch)
    s, r = call_api("POST", "/link-verification/44444444-4444-4444-4444-444444444444/verify",
                    data={}, query={"tenant_id": TENANT})
    print(f"  Verify: status={s}")
    if isinstance(r, dict):
        data = r.get("data", {})
        if isinstance(data, dict):
            print(f"    outcome: {data.get('outcome')}, link_status: {data.get('link_status')}, http: {data.get('last_http_status')}")
    results.append({
        "test": "verify_real_http",
        "status": s,
        "fabrication": "no" if s == 200 and r.get("data", {}).get("last_http_status") is not None else "yes",
    })

    # 4d. Send — should fail (no email provider)
    drafts = subprocess.run(
        ["psql", "-h", "localhost", "-U", "dronpancholi", "-d", "seo_platform", "-tA", "-c",
         f"SELECT id FROM outreach_threads WHERE tenant_id='{TENANT}' AND status='draft' LIMIT 1;"],
        capture_output=True, text=True, timeout=5
    ).stdout.strip()
    if drafts:
        s, r = call_api("POST", f"/campaigns/threads/{drafts}/send", data={}, query={"tenant_id": TENANT})
        print(f"  Send: status={s}")
        if isinstance(r, dict):
            print(f"    Body excerpt: {json.dumps(r)[:200]}")
        # mailhog is configured for dev, so it should succeed
        sent_real = r.get("data", {}).get("status") == "sent" if isinstance(r.get("data"), dict) else False
        results.append({
            "test": "send_with_mailhog",
            "status": s,
            "sent": sent_real,
            "provider": r.get("data", {}).get("provider") if isinstance(r.get("data"), dict) else None,
        })

    # 5. Save
    with open(EVIDENCE_DIR / "workstream_f_provider_validation.json", "w") as f:
        json.dump({"results": results, "summary": {
            "total_checks": len(results),
            "providers_configured": sum(1 for r in results if r.get("configured") is True),
            "fabrication_detected": sum(1 for r in results if r.get("fabrication") == "yes"),
            "explicit_errors": sum(1 for r in results if r.get("explicit_error") is True),
        }}, f, indent=2, default=str)

    print()
    print("=" * 70)
    s = {
        "total_checks": len(results),
        "providers_configured": sum(1 for r in results if r.get("configured") is True),
        "fabrication_detected": sum(1 for r in results if r.get("fabrication") == "yes"),
        "explicit_errors": sum(1 for r in results if r.get("explicit_error") is True),
    }
    print(f"TOTALS: {s}")
    print(f"Saved: {EVIDENCE_DIR}/workstream_f_provider_validation.json")
    print("=" * 70)


if __name__ == "__main__":
    main()
