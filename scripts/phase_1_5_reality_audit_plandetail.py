"""Phase 1.5 — Runtime Reality Audit for PlanDetailPage.

This script loads the PlanDetailPage in a real headless browser
(Chromium via Playwright), exercises its core interactions, and
captures:

  - JavaScript console errors (uncaught exceptions, React errors)
  - 4xx and 5xx HTTP responses
  - Network failures
  - The rendered text of the "Client ID" field in the side panel
  - A screenshot for visual inspection

This is the level of proof Phase 1.5 demands: a real browser, real
network, real errors, no certifications — just observation.

Usage:
  python scripts/phase_1_5_reality_audit_plandetail.py

Exit codes:
  0  — page loaded, no JS errors, no failed requests, Client ID rendered
  1  — at least one of the above failed
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright, Page, Response, ConsoleMessage

FRONTEND = "http://localhost:3000"
BACKEND = "http://localhost:8000"
TENANT = "00000000-0000-0000-0000-000000000001"
USER_ID = "reality-audit"
USER_ROLE = "admin"

PLAN_ID_WITH_CAMPAIGN = "cded3a96-012d-416f-911b-00c3477998bf"
PLAN_ID_WITHOUT_CAMPAIGN = "33333333-3333-3333-3333-333333333333"
PLAN_ID_NONEXISTENT = "99999999-9999-9999-9999-999999999999"

OUT_DIR = Path("/tmp/phase_1_5_evidence")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _record_event(events: list[dict[str, Any]], kind: str, **kwargs: Any) -> None:
    events.append({"kind": kind, "ts": time.time(), **kwargs})


def _audit_one(
    page: Page,
    plan_id: str,
    label: str,
    events: list[dict[str, Any]],
    expect_client_id_substring: str | None,
) -> dict[str, Any]:
    """Open one plan detail page, observe errors, return a summary."""
    console_errors: list[dict[str, Any]] = []
    page_errors: list[dict[str, Any]] = []
    failed_requests: list[dict[str, Any]] = []
    non_2xx_responses: list[dict[str, Any]] = []

    # Suppress noisy dev-mode errors that are not part of the bug surface:
    #  - Hot-reload chunk 404s from Next dev server (stale chunk references
    #    between rapid hot-reloads). Production builds don't have this.
    #  - Cross-scenario response events captured before listeners were rebound.
    dev_noise_url_substrings = (
        "/_next/static/chunks/",  # dev hot-reload chunks
    )

    def on_console(msg: ConsoleMessage) -> None:
        if msg.type in ("error",):
            text = msg.text
            # Filter dev-mode chunk 404 noise
            if "Failed to load resource" in text and "404" in text:
                return  # not informative in dev mode
            console_errors.append({"text": text, "location": str(msg.location)})

    def on_pageerror(err: Any) -> None:
        page_errors.append({"message": str(err)})

    def on_response(resp: Response) -> None:
        if any(s in resp.url for s in dev_noise_url_substrings):
            return
        if "/api/v1/plans/" in resp.url and f"/plans/{plan_id}" in resp.url and "/approve" not in resp.url:
            _record_event(events, "plan_api_response", url=resp.url, status=resp.status, label=label)
        if resp.status >= 400 and "/api/v1/" in resp.url:
            if resp.status == 404 and plan_id == PLAN_ID_NONEXISTENT and "plans" in resp.url:
                return  # expected
            non_2xx_responses.append({
                "url": resp.url,
                "status": resp.status,
                "status_text": resp.status_text,
            })

    def on_requestfailed(req: Any) -> None:
        if any(s in req.url for s in dev_noise_url_substrings):
            return
        failed_requests.append({
            "url": req.url,
            "method": req.method,
            "failure": req.failure,
        })

    page.on("console", on_console)
    page.on("pageerror", on_pageerror)
    page.on("response", on_response)
    page.on("requestfailed", on_requestfailed)

    url = f"{FRONTEND}/dashboard/plans/{plan_id}"
    _record_event(events, "navigating", url=url, label=label)

    page.goto(url, wait_until="networkidle", timeout=30000)
    # Give react-query a moment to fetch and render
    page.wait_for_timeout(2500)

    # Capture the rendered Client ID cell, if present
    client_id_text: str | None = None
    try:
        # The side panel has a "Client ID" label, and the value is the
        # next sibling span. We locate by the label text.
        locator = page.locator("text=Client ID").first
        if locator.count() > 0:
            # The value is the sibling span in the same flex row
            row = locator.locator("xpath=..")
            client_id_text = row.inner_text().replace("Client ID", "").strip().split("\n")[0].strip()
    except Exception as e:
        _record_event(events, "client_id_extract_failed", error=str(e), label=label)

    # Also detect the "Plan Not Found" empty state for the 404 case
    not_found_text: str | None = None
    try:
        nf = page.locator("text=Plan Not Found").first
        if nf.count() > 0 and nf.is_visible():
            not_found_text = nf.inner_text().strip()
    except Exception:
        pass

    # Screenshot for visual inspection
    screenshot_path = OUT_DIR / f"plandetail_{label}.png"
    page.screenshot(path=str(screenshot_path), full_page=True)

    # Click "Back to Plans" if visible (exercises a button)
    back_clicked = False
    try:
        back_btn = page.locator("text=Back to Plans").first
        if back_btn.count() > 0 and back_btn.is_visible():
            back_btn.click()
            page.wait_for_load_state("networkidle", timeout=10000)
            back_clicked = True
    except Exception as e:
        _record_event(events, "back_button_failed", error=str(e), label=label)

    # If we successfully went back, return to the detail page
    if back_clicked:
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(1500)

    return {
        "label": label,
        "url": url,
        "console_errors": console_errors,
        "page_errors": page_errors,
        "failed_requests": failed_requests,
        "non_2xx_responses": non_2xx_responses,
        "client_id_rendered": client_id_text,
        "plan_not_found_rendered": not_found_text,
        "expect_client_id_substring": expect_client_id_substring,
        "screenshot": str(screenshot_path),
    }


def main() -> int:
    results: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)

        def _run_scenario(label: str, plan_id: str, expect_substr: str) -> dict[str, Any]:
            # Fresh context per scenario so we don't get cross-scenario
            # response/event pollution from the react-query refetch interval
            # (page.tsx:212 polls every 10s).
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            context.set_extra_http_headers({
                "X-User-Id": USER_ID,
                "X-Tenant-Id": TENANT,
                "X-User-Role": USER_ROLE,
            })
            page = context.new_page()
            try:
                return _audit_one(page, plan_id, label, events, expect_substr)
            finally:
                context.close()

        # ---- Scenario A: plan with linked campaign ----
        results.append(_run_scenario("A_with_campaign", PLAN_ID_WITH_CAMPAIGN, "ed582e55"))

        # ---- Scenario B: plan without linked campaign (null case) ----
        results.append(_run_scenario("B_without_campaign", PLAN_ID_WITHOUT_CAMPAIGN, "N/A"))

        # ---- Scenario C: nonexistent plan (404 path) ----
        results.append(_run_scenario("C_nonexistent", PLAN_ID_NONEXISTENT, "Plan Not Found"))

        browser.close()

    # ---- Aggregate and report ----
    report = {
        "title": "Phase 1.5 — Runtime Reality Audit: PlanDetailPage",
        "executed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "frontend": FRONTEND,
        "backend": BACKEND,
        "tenant_id": TENANT,
        "scenarios": results,
        "events": events,
    }
    report_path = OUT_DIR / "plandetail_reality_audit.json"
    report_path.write_text(json.dumps(report, indent=2, default=str))

    # ---- Pass/fail decision ----
    print("=" * 60)
    print("Phase 1.5 — Runtime Reality Audit: PlanDetailPage")
    print("=" * 60)
    fail = False
    for r in results:
        print(f"\n[{r['label']}] {r['url']}")
        print(f"  Client ID rendered: {r['client_id_rendered']!r}")
        print(f"  Expected substring: {r['expect_client_id_substring']!r}")
        if r["console_errors"]:
            print(f"  ✗ {len(r['console_errors'])} console error(s):")
            for e in r["console_errors"][:3]:
                print(f"    - {e['text']}")
            fail = True
        else:
            print("  ✓ no console errors")
        if r["page_errors"]:
            print(f"  ✗ {len(r['page_errors'])} uncaught page error(s):")
            for e in r["page_errors"][:3]:
                print(f"    - {e['message']}")
            fail = True
        else:
            print("  ✓ no uncaught page errors")
        if r["failed_requests"]:
            print(f"  ✗ {len(r['failed_requests'])} failed request(s):")
            for e in r["failed_requests"][:3]:
                print(f"    - {e['method']} {e['url']} ({e['failure']})")
            fail = True
        else:
            print("  ✓ no failed requests")
        if r["non_2xx_responses"]:
            print(f"  ⚠ {len(r['non_2xx_responses'])} non-2xx API response(s):")
            for e in r["non_2xx_responses"][:3]:
                print(f"    - {e['status']} {e['url']}")
            # Only fail if the page itself is broken (Scenario A and B must be 2xx)
            if r["label"] in ("A_with_campaign", "B_without_campaign"):
                fail = True
        if r["expect_client_id_substring"]:
            rendered = r.get("plan_not_found_rendered") or r.get("client_id_rendered")
            if rendered and r["expect_client_id_substring"] in rendered:
                print(f"  ✓ Page rendering matches expectation")
            else:
                print(f"  ✗ Page rendering does NOT match expectation")
                fail = True
        print(f"  📸 screenshot: {r['screenshot']}")

    print()
    print(f"Report: {report_path}")
    if fail:
        print("\n✗ REALITY AUDIT FAILED — at least one scenario has errors")
        return 1
    print("\n✓ REALITY AUDIT PASSED — all scenarios clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
