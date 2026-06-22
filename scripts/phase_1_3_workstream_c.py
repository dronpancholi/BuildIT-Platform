#!/usr/bin/env python3
"""Phase 1.3 Workstream C - Frontend Reality Audit

Tests 63 frontend pages for:
- HTTP load success
- Static content analysis (fake data, placeholders, TODOs)
- API integration: do they reference real endpoints?
- Dead UI: hardcoded routes, no fetch, no backend call
"""
import json
import re
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
import subprocess

EVIDENCE_DIR = Path("/tmp/phase_1_3_evidence")
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
FRONTEND_PORT = 3000
FRONTEND = f"http://localhost:{FRONTEND_PORT}"

# Page path patterns
DYNAMIC_PARAM_PATTERNS = [
    ("/dashboard/campaigns/[id]", "/dashboard/campaigns/ea70a02e-bd66-4404-b92b-5e695b89d7c2"),
    ("/dashboard/clients/[id]", "/dashboard/clients/ed582e55-7408-4052-a6ed-f4d036862c3f"),
    ("/dashboard/customers/[id]", "/dashboard/customers/ed582e55-7408-4052-a6ed-f4d036862c3f"),
    ("/dashboard/plans/[id]", "/dashboard/plans/cded3a96-fake-plan-id"),
    ("/dashboard/reports/[id]", "/dashboard/reports/latest"),
]

FAKE_PATTERNS = [
    (r"\bDEMO_[A-Z_]+\b", "DEMO_ placeholder constant"),
    (r"\bMock[A-Z][A-Za-z]*\b", "Mock component/variable"),
    (r"lorem ipsum", "Lorem ipsum placeholder"),
    (r"\bTODO\b", "TODO comment"),
    (r"\bFIXME\b", "FIXME comment"),
    (r"placeholder.*=.*[\"']Demo", "Demo placeholder"),
    (r"\[1, 2, 3, 4, 5\]", "Hardcoded numeric array"),
    (r"[\"']Demo [A-Z]", "Demo data string"),
    (r"href=[\"']#[\"']", "Dead href=# link"),
    (r"onClick=\{.*\(\) => \{\}\}", "Empty onClick handler"),
    (r"console\.(log|error|warn)\(", "Browser console call (debug residue)"),
    (r"https://example\.com", "Example.com placeholder"),
    (r"https://your-?domain", "Your-domain placeholder"),
    (r"test[._-]?(data|user|api)", "Test data reference"),
]

DEAD_ROUTE_PATTERNS = [
    r"href=[\"']/dashboard/[a-z-]+/[\"']",  # non-existent sub-routes
]

API_INTEGRATION_PATTERNS = [
    r"fetch\(",
    r"axios\.",
    r"useApi\b",
    r"apiClient\b",
    r"trpc\b",
    r"/api/v1/",
]


def page_files():
    """Yield (relative_path, file_path) for all page.tsx."""
    base = Path("/Users/dronpancholi/Developer/Project 31A/frontend/src/app")
    for f in sorted(base.rglob("page.tsx")):
        rel = "/" + str(f.relative_to(base).parent).replace("/page.tsx", "").replace("/page", "")
        if rel == "//": rel = "/"
        yield rel, f


def fetch_page(path, timeout=10):
    url = f"{FRONTEND}{path}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "WS-C-Auditor/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", errors="ignore")
            return r.status, len(body), body
    except urllib.error.HTTPError as e:
        try: body = e.read().decode("utf-8", errors="ignore")
        except: body = ""
        return e.code, len(body), body
    except Exception as e:
        return 0, 0, f"<error: {e}>"


def analyze_page_content(path, file_path):
    """Read the page file and check for fake data, placeholders, dead UI."""
    issues = []
    try:
        content = file_path.read_text()
    except Exception as e:
        return [{"type": "read_error", "detail": str(e)}]

    for pat, label in FAKE_PATTERNS:
        matches = re.findall(pat, content, re.IGNORECASE)
        if matches:
            issues.append({"type": label, "count": len(matches), "samples": matches[:3]})

    # Check for any API integration
    has_api = any(re.search(pat, content) for pat in API_INTEGRATION_PATTERNS)
    if not has_api and "/page.tsx" in str(file_path):
        # Some pages are pure layout or info — flag if they have no data
        if "<table" in content or "Card" in content or "chart" in content.lower():
            issues.append({"type": "no_api_integration", "detail": "page has tables/cards/charts but no fetch/axios/trpc"})

    # Check for unused imports
    imports = re.findall(r"^import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]", content, re.MULTILINE)
    for imp in imports:
        if imp.startswith("@/") and "node_modules" not in imp:
            module_name = imp.split("/")[-1]
            # check if module name is used in body (rough heuristic)
            body = content.split("import", 1)[-1] if "import" in content else content
            # skip — too noisy

    return issues


def main():
    print("=" * 70)
    print("PHASE 1.3 WORKSTREAM C — Frontend Reality Audit")
    print("=" * 70)
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")
    print()

    pages = list(page_files())
    print(f"Found {len(pages)} pages")
    print()

    results = []
    for rel_path, file_path in pages:
        # Map dynamic routes to a concrete path
        concrete = rel_path
        for pattern, replacement in DYNAMIC_PARAM_PATTERNS:
            concrete = concrete.replace(pattern, replacement)

        # HTTP load
        t0 = time.time()
        status, size, body = fetch_page(concrete, timeout=15)
        latency = time.time() - t0

        # Static analysis
        issues = analyze_page_content(concrete, file_path)

        # Check for hydration errors in body
        hydration_err = "Hydration failed" in body or "Minified React error" in body
        if hydration_err:
            issues.append({"type": "hydration_error", "detail": "page rendered hydration error"})

        result = {
            "path": rel_path,
            "concrete_path": concrete,
            "file": str(file_path.relative_to(file_path.parents[3])),
            "http_status": status,
            "response_size": size,
            "latency_s": round(latency, 3),
            "issues": issues,
            "issue_count": len(issues),
            "load_ok": 200 <= status < 400,
        }
        results.append(result)
        marker = "✓" if result["load_ok"] and not issues else ("✗" if not result["load_ok"] else f"⚠ {len(issues)} issues")
        print(f"  {marker} {rel_path:55s} {status} {size:6d}B {latency:.2f}s")

    # Save
    with open(EVIDENCE_DIR / "workstream_c_frontend_audit.json", "w") as f:
        json.dump({"results": results, "totals": {
            "pages": len(results),
            "loaded": sum(1 for r in results if r["load_ok"]),
            "with_issues": sum(1 for r in results if r["issue_count"] > 0),
            "issue_types": {},
        }}, f, indent=2, default=str)

    # Issue type breakdown
    issue_types = {}
    for r in results:
        for i in r["issues"]:
            issue_types[i["type"]] = issue_types.get(i["type"], 0) + 1

    p_loaded = sum(1 for r in results if r["load_ok"])
    p_clean = sum(1 for r in results if r["load_ok"] and r["issue_count"] == 0)

    print()
    print("=" * 70)
    print(f"TOTALS: {len(results)} pages | loaded={p_loaded} | clean={p_clean}")
    print(f"Issue types: {json.dumps(issue_types, indent=2)}")
    print(f"Saved: {EVIDENCE_DIR}/workstream_c_frontend_audit.json")
    print("=" * 70)


if __name__ == "__main__":
    main()
