#!/usr/bin/env bash
# ============================================================================
# Phase 1.5 — Page HTTP Probe (lightweight reality audit)
# ============================================================================
# For every page in the frontend, fetch the page and report:
#   - HTTP status code
#   - Page size
#   - Any error markers in the HTML ("Application error", "Internal Server Error")
#   - Time taken
#
# This is a cheap smoke test. It does NOT exercise buttons, forms, or
# client-side JS — for that, use scripts/phase_1_5_reality_audit_*.py
# with Playwright.
#
# Usage:
#   ./scripts/phase_1_5_page_probe.sh
#   FRONTEND=https://app.example.com ./scripts/phase_1_5_page_probe.sh
# ============================================================================

set -uo pipefail

FRONTEND="${FRONTEND:-http://localhost:3000}"
OUT="/tmp/phase_1_5_evidence/page_probe.json"
mkdir -p "$(dirname "$OUT")"

# Find all pages (skip dynamic [id] routes — they need a real id)
PAGES=$(find "/Users/dronpancholi/Developer/Project 31A/frontend/src/app" -name "page.tsx" 2>/dev/null | \
    grep -v '/\[' | \
    sed -E "s|/Users/dronpancholi/Developer/Project 31A/frontend/src/app||" | \
    sed -E 's|/page\.tsx$||' | \
    sort)

# Also pick a few dynamic routes with a real ID
DYNAMIC_PAGES=(
    "/dashboard/clients/ed582e55-7408-4052-a6ed-f4d036862c3f"
    "/dashboard/campaigns/ea70a02e-bd66-4404-b92b-5e695b89d7c2"
    "/dashboard/plans/cded3a96-012d-416f-911b-00c3477998bf"
    "/dashboard/plans/33333333-3333-3333-3333-333333333333"
)

echo "[" > "$OUT"
FIRST=1
TOTAL=0
PASS=0
FAIL=0
SLOW_MS=0

for page in $PAGES; do
    if [[ "$page" == "" ]]; then
        continue
    fi
    url="$FRONTEND$page"
    # Some Next dev routes 404 on first hit while the chunk compiles.
    # Retry once after 1s to give Next a chance to compile the route.
    for attempt in 1 2; do
        out=$(curl -sS -o /tmp/probe.html -w "%{http_code} %{time_total} %{size_download}" \
              --max-time 30 "$url" 2>&1)
        code=$(echo "$out" | awk '{print $1}')
        time_s=$(echo "$out" | awk '{print $2}')
        size=$(echo "$out" | awk '{print $3}')
        # 404 on first attempt is OK for dynamic routes that need compile
        if [[ "$code" != "404" ]] || [[ "$attempt" == "2" ]]; then
            break
        fi
        sleep 1
    done

    # Check for known error markers
    error_marker=""
    if grep -q "Application error\|Internal Server Error\|TypeError\|ReferenceError" /tmp/probe.html 2>/dev/null; then
        error_marker=$(grep -oE "Application error|Internal Server Error|TypeError|ReferenceError" /tmp/probe.html | head -1)
    fi

    time_ms=$(awk "BEGIN { printf \"%.0f\", $time_s * 1000 }")

    # Pass = 2xx status AND no error marker AND size > 1KB (real page, not blank)
    if [[ "$code" =~ ^2 ]] && [[ -z "$error_marker" ]] && [[ "$size" -gt 1024 ]]; then
        status="PASS"
        PASS=$((PASS+1))
    else
        status="FAIL"
        FAIL=$((FAIL+1))
    fi
    TOTAL=$((TOTAL+1))

    if [[ $FIRST -eq 0 ]]; then
        echo "," >> "$OUT"
    fi
    FIRST=0
    printf '{"path":"%s","code":%s,"size":%s,"time_ms":%s,"error_marker":"%s","status":"%s"}' \
        "$page" "$code" "$size" "$time_ms" "$error_marker" "$status" >> "$OUT"

    printf "%4s  %5s  %6sB  %4sms  %s  %s\n" "$status" "$code" "$size" "$time_ms" "$page" "$error_marker"
done

echo "" >> "$OUT"
echo "]" >> "$OUT"

echo ""
echo "============================================================"
echo "Page Probe Summary"
echo "============================================================"
echo "Total: $TOTAL | PASS: $PASS | FAIL: $FAIL"
echo "Report: $OUT"
