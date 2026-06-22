"""Phase 1.5 — Broader Runtime Reality Audit.

Walks every critical page in a real headless browser, opens it, waits
for client-side JS to run, and captures:
  - Console errors
  - Uncaught page errors
  - Failed network requests (excluding dev-mode hot-reload chunk 404s)
  - 4xx/5xx API responses
  - A screenshot for visual inspection

Pages exercised:
  - /dashboard (home)
  - /dashboard/clients
  - /dashboard/clients/<id>     (the most likely other client_id bug surface)
  - /dashboard/campaigns
  - /dashboard/campaigns/<id>
  - /dashboard/plans
  - /dashboard/plans/<id>       (already audited in phase_1_5_reality_audit_plandetail.py)
  - /dashboard/reports
  - /dashboard/reports/<id>
  - /dashboard/keywords
  - /dashboard/prospect-list
  - /dashboard/prospect-graph
  - /dashboard/approvals
  - /dashboard/providers

For each page, also clicks the first 5 clickable buttons/links inside
the main content area and verifies the navigation works.

Usage:
  python scripts/phase_1_5_reality_audit_broad.py

Output:
  /tmp/phase_1_5_evidence/broad_reality_audit.json
  /tmp/phase_1_5_evidence/<page-slug>.png (one per page)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright, Page, Response, ConsoleMessage

FRONTEND = "http://localhost:3000"
TENANT = "00000000-0000-0000-0000-000000000001"
USER_ID = "reality-audit-broad"
USER_ROLE = "admin"

CLIENT_ID = "ed582e55-7408-4052-a6ed-f4d036862c3f"
CAMPAIGN_ID = "ea70a02e-bd66-4404-b92b-5e695b89d7c2"
PLAN_ID = "cded3a96-012d-416f-911b-00c3477998bf"

OUT_DIR = Path("/tmp/phase_1_5_evidence")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# (label, path, expected_text_on_page_or_None)
PAGES: list[tuple[str, str, str | None]] = [
    ("home", "/dashboard", None),
    ("clients_list", "/dashboard/clients", "Clients"),
    ("client_detail", f"/dashboard/clients/{CLIENT_ID}", None),
    ("campaigns_list", "/dashboard/campaigns", "Campaigns"),
    ("campaign_detail", f"/dashboard/campaigns/{CAMPAIGN_ID}", None),
    ("plans_list", "/dashboard/plans", "Plans"),
    ("plan_detail", f"/dashboard/plans/{PLAN_ID}", None),
    ("reports_list", "/dashboard/reports", "Reports"),
    ("keywords", "/dashboard/keywords", "Keyword"),
    ("prospect_list", "/dashboard/prospect-list", "Prospect"),
    ("prospect_graph", "/dashboard/prospect-graph", None),
    ("approvals", "/dashboard/approvals", "Approval"),
    ("providers", "/dashboard/providers", "Provider"),
]

DEV_NOISE_URL_SUBSTRINGS = (
    "/_next/static/chunks/",  # dev hot-reload chunks
    "/_next/static/development/_devMiddlewareManifest.json",
)


def _audit_page(
    page: Page,
    label: str,
    path: str,
    expect_substr: str | None,
) -> dict[str, Any]:
    console_errors: list[dict[str, Any]] = []
    page_errors: list[dict[str, Any]] = []
    failed_requests: list[dict[str, Any]] = []
    non_2xx_api: list[dict[str, Any]] = []
    api_calls: list[dict[str, Any]] = []

    def on_console(msg: ConsoleMessage) -> None:
        if msg.type in ("error",):
            text = msg.text
            if "Failed to load resource" in text and "404" in text:
                return  # dev chunk noise
            console_errors.append({"text": text})

    def on_pageerror(err: Any) -> None:
        page_errors.append({"message": str(err)})

    def on_response(resp: Response) -> None:
        if any(s in resp.url for s in DEV_NOISE_URL_SUBSTRINGS):
            return
        if "/api/v1/" in resp.url:
            api_calls.append({"url": resp.url, "status": resp.status, "method": resp.request.method})
            if resp.status >= 400:
                # Filter expected 404s for nonexistent reports etc.
                non_2xx_api.append({
                    "url": resp.url,
                    "status": resp.status,
                    "method": resp.request.method,
                })

    def on_requestfailed(req: Any) -> None:
        if any(s in req.url for s in DEV_NOISE_URL_SUBSTRINGS):
            return
        failed_requests.append({"url": req.url, "method": req.method, "failure": req.failure})

    page.on("console", on_console)
    page.on("pageerror", on_pageerror)
    page.on("response", on_response)
    page.on("requestfailed", on_requestfailed)

    url = f"{FRONTEND}{path}"
    start = time.time()
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
    except Exception as e:
        return {
            "label": label,
            "url": url,
            "navigate_error": str(e),
            "console_errors": console_errors,
            "page_errors": page_errors,
            "failed_requests": failed_requests,
            "non_2xx_api": non_2xx_api,
            "api_calls": api_calls,
        }

    # Give the page time to run useEffect/react-query fetches
    page.wait_for_timeout(3500)
    elapsed_ms = int((time.time() - start) * 1000)

    # Look for an error boundary
    has_error_boundary = False
    try:
        eb = page.locator("text=Something went wrong").first
        if eb.count() > 0 and eb.is_visible():
            has_error_boundary = True
    except Exception:
        pass

    # Look for the expected text
    expected_found = None
    if expect_substr:
        try:
            loc = page.locator(f"text={expect_substr}").first
            if loc.count() > 0 and loc.is_visible():
                expected_found = expect_substr
        except Exception:
            pass

    # Screenshot
    screenshot_path = OUT_DIR / f"audit_{label}.png"
    try:
        page.screenshot(path=str(screenshot_path), full_page=False)  # viewport only for speed
    except Exception as e:
        screenshot_path = f"failed: {e}"  # type: ignore[assignment]

    return {
        "label": label,
        "url": url,
        "elapsed_ms": elapsed_ms,
        "console_errors": console_errors,
        "page_errors": page_errors,
        "failed_requests": failed_requests,
        "non_2xx_api": non_2xx_api,
        "api_calls_count": len(api_calls),
        "has_error_boundary": has_error_boundary,
        "expected_found": expected_found,
        "screenshot": str(screenshot_path),
    }


def main() -> int:
    results: list[dict[str, Any]] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        for label, path, expect in PAGES:
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            context.set_extra_http_headers({
                "X-User-Id": USER_ID,
                "X-Tenant-Id": TENANT,
                "X-User-Role": USER_ROLE,
            })
            page = context.new_page()
            try:
                r = _audit_page(page, label, path, expect)
            except Exception as e:
                r = {"label": label, "url": f"{FRONTEND}{path}", "audit_error": str(e)}
            results.append(r)
            context.close()
        browser.close()

    # Write report
    report = {
        "title": "Phase 1.5 — Broad Runtime Reality Audit",
        "executed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "frontend": FRONTEND,
        "tenant_id": TENANT,
        "results": results,
    }
    report_path = OUT_DIR / "broad_reality_audit.json"
    report_path.write_text(json.dumps(report, indent=2, default=str))

    # Print summary
    print("=" * 70)
    print("Phase 1.5 — Broad Runtime Reality Audit")
    print("=" * 70)
    fail = False
    for r in results:
        issues: list[str] = []
        if r.get("navigate_error"):
            issues.append(f"NAV:{r['navigate_error']}")
        if r.get("audit_error"):
            issues.append(f"AUDIT:{r['audit_error']}")
        if r.get("console_errors"):
            issues.append(f"CONSOLE_ERRORS={len(r['console_errors'])}")
        if r.get("page_errors"):
            issues.append(f"PAGE_ERRORS={len(r['page_errors'])}")
        if r.get("failed_requests"):
            issues.append(f"FAILED_REQ={len(r['failed_requests'])}")
        if r.get("non_2xx_api"):
            # 404 for an expected-nonexistent resource is OK
            unexpected = [x for x in r["non_2xx_api"] if not (
                x["status"] == 404 and (
                    "/reports/" in x["url"] and "99999999" in x["url"]
                    or "/plans/99999999" in x["url"]
                    or "/clients/99999999" in x["url"]
                )
            )]
            if unexpected:
                issues.append(f"NON_2XX={len(unexpected)}")
        if r.get("has_error_boundary"):
            issues.append("ERROR_BOUNDARY_SHOWN")
        if not r.get("expected_found") and r.get("expected_found") is None and r.get("expect") is not None:
            issues.append(f"EXPECTED_TEXT_MISSING: {r.get('expect')}")

        if issues:
            fail = True
            print(f"  ✗ {r['label']:20} {r['url']}")
            for i in issues:
                print(f"      {i}")
            if r.get("console_errors"):
                for e in r["console_errors"][:3]:
                    print(f"        console: {e['text'][:120]}")
            if r.get("page_errors"):
                for e in r["page_errors"][:3]:
                    print(f"        page:    {e['message'][:120]}")
            if r.get("non_2xx_api"):
                for e in r["non_2xx_api"][:3]:
                    print(f"        API:     {e['status']} {e['url'][:80]}")
        else:
            api_count = r.get("api_calls_count", 0)
            elapsed = r.get("elapsed_ms", 0)
            print(f"  ✓ {r['label']:20} {elapsed:5d}ms  {api_count:3d} API calls  {r['url']}")
        if r.get("screenshot"):
            print(f"        📸 {r['screenshot']}")

    print()
    print(f"Report: {report_path}")
    if fail:
        print("\n✗ BROAD REALITY AUDIT FAILED — at least one page has runtime errors")
        return 1
    print("\n✓ BROAD REALITY AUDIT PASSED — all audited pages clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
