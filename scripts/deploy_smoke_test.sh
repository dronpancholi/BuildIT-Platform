#!/usr/bin/env bash
# ============================================================================
# BuildIT — Post-Deployment Smoke Test
# ============================================================================
# Run immediately after a deployment OR after a config change OR after a
# provider key rotation. Exits 0 on full pass, 1 on any failure.
#
# Verifies the four P0 gaps fixed in Phase 1.4 are still working:
#   GAP-005  GET /metrics         → 200 Prometheus text (not JSON envelope)
#   GAP-004  GET /clients/{id}/campaigns → tenant-scoped, RBAC, paginated
#   GAP-003  Error envelopes      → all errors in APIResponse shape
#   GAP-002  Async report         → 202 in <1s, status polling works
#
# Also verifies the four core invariants of every deployment:
#   /api/v1/health  → 200 with "status": "healthy" or "degraded" (acceptable)
#   AUTH bypass     → 200 with X-User-Id/Role headers (dev only)
#   CORS            → preflight succeeds
#   Provider health → external_apis either healthy OR degraded with
#                     "No external SEO APIs configured" (no 5xx)
#
# Usage:
#   ./scripts/deploy_smoke_test.sh
#   API_URL=https://api.example.com ./scripts/deploy_smoke_test.sh
#   SKIP_ASYNC=1 ./scripts/deploy_smoke_test.sh    # skip the slow async test
#   VERBOSE=1 ./scripts/deploy_smoke_test.sh       # show full responses
# ============================================================================

set -uo pipefail

# ----- Configuration -----
API_URL="${API_URL:-http://localhost:8000}"
TENANT_ID="${TENANT_ID:-00000000-0000-0000-0000-000000000001}"
USER_ID="${USER_ID:-smoke-test-user}"
USER_ROLE="${USER_ROLE:-admin}"
CLIENT_ID="${CLIENT_ID:-ed582e55-7408-4052-a6ed-f4d036862c3f}"

VERBOSE="${VERBOSE:-0}"
SKIP_ASYNC="${SKIP_ASYNC:-0}"
TIMEOUT="${TIMEOUT:-15}"

# ----- Color helpers -----
if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; BLUE=''; NC=''
fi

# ----- Test counters -----
PASS=0
FAIL=0
SKIPPED=0
FAILED_TESTS=()

# ----- Helpers -----
log_info()  { echo -e "${BLUE}ℹ${NC}  $*"; }
log_pass()  { echo -e "${GREEN}✓${NC}  $*"; PASS=$((PASS+1)); }
log_fail()  { echo -e "${RED}✗${NC}  $*"; FAIL=$((FAIL+1)); FAILED_TESTS+=("$*"); }
log_skip()  { echo -e "${YELLOW}⊘${NC}  $*"; SKIPPED=$((SKIPPED+1)); }
section()   { echo; echo -e "${YELLOW}── $* ──${NC}"; }

# Returns 0 if needle is found in haystack, 1 otherwise.
contains() {
    local needle="$1"; local haystack="$2"
    [[ "$haystack" == *"$needle"* ]]
}

# Normalize JSON by removing all whitespace (handles pretty-printed responses).
# Use: $(jq_compact < /tmp/response.json)
jq_compact() {
    python3 -c "import json,sys; print(json.dumps(json.load(sys.stdin), separators=(',',':')))" < "$1"
}

# curl with the standard dev-bypass headers pre-set.
api_get()  { curl -sS -m "$TIMEOUT" -L -H "X-User-Id: $USER_ID" -H "X-Tenant-Id: $TENANT_ID" -H "X-User-Role: $USER_ROLE" "$@"; }
api_post() { curl -sS -m "$TIMEOUT" -L -X POST -H "Content-Type: application/json" -H "X-User-Id: $USER_ID" -H "X-Tenant-Id: $TENANT_ID" -H "X-User-Role: $USER_ROLE" "$@"; }
raw_get()  { curl -sS -m "$TIMEOUT" -L "$@"; }

# ----------------------------------------------------------------------------
section "0. Connectivity"
# ----------------------------------------------------------------------------
HTTP_CODE=$(raw_get -o /dev/null -w "%{http_code}" "$API_URL/api/v1/health" || echo "000")
if [[ "$HTTP_CODE" == "200" ]]; then
    log_pass "API is reachable at $API_URL (200)"
else
    log_fail "API is NOT reachable at $API_URL (got $HTTP_CODE, expected 200)"
    echo
    echo -e "${RED}Aborting: cannot reach the API. Verify DNS, port, and that uvicorn is running.${NC}"
    exit 1
fi

# ----------------------------------------------------------------------------
section "1. Health Endpoint (core)"
# ----------------------------------------------------------------------------
HEALTH_JSON=$(raw_get "$API_URL/api/v1/health")
HEALTH_COMPACT=$(echo "$HEALTH_JSON" | python3 -c "import json,sys; print(json.dumps(json.load(sys.stdin), separators=(',',':')))" 2>/dev/null || echo "$HEALTH_JSON")
if [[ -z "$HEALTH_JSON" ]]; then
    log_fail "/api/v1/health returned empty body"
else
    if contains '"status":"healthy"' "$HEALTH_COMPACT" || contains '"status":"degraded"' "$HEALTH_COMPACT"; then
        log_pass "/api/v1/health returned a recognized status field"

        # Check that postgresql, redis, kafka, temporal are healthy
        for comp in postgresql redis kafka temporal; do
            if contains "\"name\":\"$comp\",\"status\":\"healthy\"" "$HEALTH_COMPACT"; then
                log_pass "  component '$comp' is healthy"
            else
                log_fail "  component '$comp' is NOT healthy in /api/v1/health"
            fi
        done

        # external_apis can be either healthy (configured) or degraded
        # with the specific "No external SEO APIs configured" message.
        # Both are acceptable. A 5xx or unknown status is a fail.
        if contains "\"name\":\"external_apis\",\"status\":\"healthy\"" "$HEALTH_COMPACT"; then
            log_pass "  component 'external_apis' is healthy (all keys configured)"
        elif contains "\"name\":\"external_apis\",\"status\":\"degraded\"" "$HEALTH_COMPACT" \
             && contains "No external SEO APIs configured" "$HEALTH_COMPACT"; then
            log_info "  component 'external_apis' is degraded (no keys) — expected for CONDITIONALLY CERTIFIED deployments"
        else
            log_fail "  component 'external_apis' has unexpected state"
        fi
    else
        log_fail "/api/v1/health missing or unrecognized status field"
        [[ "$VERBOSE" == "1" ]] && echo "  body: $HEALTH_JSON" | head -c 300
    fi
fi

# ----------------------------------------------------------------------------
section "2. Phase 1.4 GAP-005: Canonical /metrics (Prometheus text)"
# ----------------------------------------------------------------------------
# /metrics must return Prometheus text (not JSON, not 404).
METRICS_HTTP=$(raw_get -o /tmp/smoke_metrics.txt -w "%{http_code}" "$API_URL/metrics")
METRICS_SIZE=$(wc -c < /tmp/smoke_metrics.txt 2>/dev/null || echo 0)
if [[ "$METRICS_HTTP" == "200" ]] && [[ "$METRICS_SIZE" -gt 1000 ]]; then
    if grep -q "^# HELP" /tmp/smoke_metrics.txt && grep -q "^# TYPE" /tmp/smoke_metrics.txt; then
        HELP_COUNT=$(grep -c "^# HELP" /tmp/smoke_metrics.txt)
        TYPE_COUNT=$(grep -c "^# TYPE" /tmp/smoke_metrics.txt)
        log_pass "GET /metrics returns 200 Prometheus (${METRICS_SIZE} bytes, ${HELP_COUNT} HELP, ${TYPE_COUNT} TYPE)"
    else
        log_fail "GET /metrics returns 200 but body is not Prometheus format"
    fi
else
    log_fail "GET /metrics failed (HTTP $METRICS_HTTP, ${METRICS_SIZE} bytes)"
fi
rm -f /tmp/smoke_metrics.txt

# ----------------------------------------------------------------------------
section "3. Phase 1.4 GAP-004: Client campaigns (tenant-scoped, RBAC, paginated)"
# ----------------------------------------------------------------------------
CAMP_HTTP=$(api_get -o /tmp/smoke_camp.json -w "%{http_code}" \
    "$API_URL/api/v1/clients/$CLIENT_ID/campaigns?tenant_id=$TENANT_ID&limit=10")
CAMP_BODY_RAW=$(cat /tmp/smoke_camp.json 2>/dev/null || echo "")
CAMP_BODY=$(python3 -c "import json,sys; print(json.dumps(json.load(open('/tmp/smoke_camp.json')), separators=(',',':')))" 2>/dev/null || echo "$CAMP_BODY_RAW")

if [[ "$CAMP_HTTP" == "200" ]]; then
    if contains '"success":true' "$CAMP_BODY" && contains '"data":[' "$CAMP_BODY" && contains '"meta":' "$CAMP_BODY"; then
        log_pass "GET /clients/{id}/campaigns returns APIResponse envelope (200)"

        # Tenant isolation: confirm the known campaign for this client
        # (ea70a02e-... is seeded against ed582e55-... in the dev DB) appears
        # in the response, AND a different client returns an empty list.
        if contains 'ea70a02e-bd66-4404-b92b-5e695b89d7c2' "$CAMP_BODY"; then
            ISOL_HTTP=$(api_get -o /tmp/smoke_isol.json -w "%{http_code}" \
                "$API_URL/api/v1/clients/00000000-0000-0000-0000-000000000099/campaigns?tenant_id=$TENANT_ID")
            ISOL_BODY=$(cat /tmp/smoke_isol.json 2>/dev/null || echo "")
            if [[ "$ISOL_HTTP" == "404" ]] || [[ "$ISOL_HTTP" == "200" && "$ISOL_BODY" == *'"data":[]'* ]]; then
                log_pass "  tenant isolation: known client returns data, unknown client returns 404/empty"
            else
                log_fail "  tenant isolation: unknown client leaked (HTTP $ISOL_HTTP)"
            fi
        else
            log_fail "  tenant isolation: known campaign for $CLIENT_ID not in response"
        fi
        rm -f /tmp/smoke_isol.json

        # Verify status filter works with uppercase enum (real Phase 1.4 fix)
        FILTER_HTTP=$(api_get -o /tmp/smoke_filt.json -w "%{http_code}" \
            "$API_URL/api/v1/clients/$CLIENT_ID/campaigns?tenant_id=$TENANT_ID&status=ACTIVE")
        if [[ "$FILTER_HTTP" == "200" ]]; then
            log_pass "  status filter accepts uppercase enum (status=ACTIVE → 200)"
        else
            log_fail "  status filter rejected (HTTP $FILTER_HTTP)"
        fi

        # Verify bad status returns 400 (not 500) with the valid enum list
        BAD_HTTP=$(api_get -o /tmp/smoke_bad.json -w "%{http_code}" \
            "$API_URL/api/v1/clients/$CLIENT_ID/campaigns?tenant_id=$TENANT_ID&status=BOGUS")
        BAD_BODY=$(cat /tmp/smoke_bad.json 2>/dev/null || echo "")
        if [[ "$BAD_HTTP" == "400" ]] && contains "Valid:" "$BAD_BODY"; then
            log_pass "  bad status returns 400 with valid enum list (no 500)"
        else
            log_fail "  bad status returned $BAD_HTTP (expected 400 with enum list)"
        fi
    else
        log_fail "GET /clients/{id}/campaigns returned 200 but malformed body"
    fi
else
    log_fail "GET /clients/{id}/campaigns failed (HTTP $CAMP_HTTP)"
fi
rm -f /tmp/smoke_camp.json /tmp/smoke_filt.json /tmp/smoke_bad.json

# ----------------------------------------------------------------------------
section "4. Phase 1.4 GAP-003: Global error envelope"
# ----------------------------------------------------------------------------
# A 404 with a clean envelope is the canary that the global handlers are mounted.
ERR_HTTP=$(api_get -o /tmp/smoke_err.json -w "%{http_code}" \
    "$API_URL/api/v1/clients/00000000-0000-0000-0000-000000000099/campaigns?tenant_id=$TENANT_ID")
ERR_BODY_RAW=$(cat /tmp/smoke_err.json 2>/dev/null || echo "")
ERR_BODY=$(python3 -c "import json,sys; print(json.dumps(json.load(open('/tmp/smoke_err.json')), separators=(',',':')))" 2>/dev/null || echo "$ERR_BODY_RAW")

if [[ "$ERR_HTTP" == "404" ]] \
   && contains '"success":false' "$ERR_BODY" \
   && contains '"error_code":"NOT_FOUND"' "$ERR_BODY" \
   && contains '"retryable":false' "$ERR_BODY"; then
    log_pass "404 returns APIResponse envelope (success:false, error_code:NOT_FOUND, retryable:false)"
else
    log_fail "404 envelope malformed (HTTP $ERR_HTTP, body: ${ERR_BODY:0:200})"
fi
rm -f /tmp/smoke_err.json

# ----------------------------------------------------------------------------
section "5. Phase 1.4 GAP-002: Async report generation"
# ----------------------------------------------------------------------------
if [[ "$SKIP_ASYNC" == "1" ]]; then
    log_skip "Async report test skipped (SKIP_ASYNC=1)"
else
    ASYNC_HTTP=$(api_post -o /tmp/smoke_async.json -w "%{http_code}\n%{time_total}" \
        "$API_URL/api/v1/reports/generate-async?tenant_id=$TENANT_ID" \
        -d "{\"client_id\":\"$CLIENT_ID\",\"report_type\":\"performance\",\"tenant_id\":\"$TENANT_ID\"}")
    ASYNC_CODE=$(echo "$ASYNC_HTTP" | head -1)
    ASYNC_TIME=$(echo "$ASYNC_HTTP" | tail -1)
    ASYNC_BODY_RAW=$(cat /tmp/smoke_async.json 2>/dev/null || echo "")
    ASYNC_BODY=$(python3 -c "import json,sys; print(json.dumps(json.load(open('/tmp/smoke_async.json')), separators=(',',':')))" 2>/dev/null || echo "$ASYNC_BODY_RAW")

    if [[ "$ASYNC_CODE" == "202" ]]; then
        log_pass "POST /reports/generate-async returns 202 in ${ASYNC_TIME}s"

        # Verify envelope shape
        if contains '"status":"pending"' "$ASYNC_BODY" && contains '"status_url":' "$ASYNC_BODY"; then
            log_pass "  response includes status:pending and status_url"
        else
            log_fail "  response missing status:pending or status_url"
        fi

        # Verify < 1s (the whole point of GAP-002)
        if (( $(echo "$ASYNC_TIME < 1.0" | bc -l 2>/dev/null || echo 0) )); then
            log_pass "  response time < 1s (${ASYNC_TIME}s) — async path working"
        else
            log_fail "  response time ≥ 1s (${ASYNC_TIME}s) — async path may be blocked"
        fi
    else
        log_fail "POST /reports/generate-async returned $ASYNC_CODE (expected 202)"
        [[ "$VERBOSE" == "1" ]] && echo "  body: $ASYNC_BODY" | head -c 300
    fi
    rm -f /tmp/smoke_async.json
fi

# ----------------------------------------------------------------------------
section "6. Provider health (no fabrication)"
# ----------------------------------------------------------------------------
# Phase 1.4 made the providers self-aware: when no key is set, the
# /api/v1/health external_apis component reports "degraded" with an
# explicit "No external SEO APIs configured" message — NOT a 5xx, NOT
# silent success. Verify this contract.
HEALTH_AGAIN=$(raw_get "$API_URL/api/v1/health")
HEALTH_AGAIN_COMPACT=$(echo "$HEALTH_AGAIN" | python3 -c "import json,sys; print(json.dumps(json.load(sys.stdin), separators=(',',':')))" 2>/dev/null || echo "$HEALTH_AGAIN")
if contains "No external SEO APIs configured" "$HEALTH_AGAIN_COMPACT" \
   || contains '"name":"external_apis","status":"healthy"' "$HEALTH_AGAIN_COMPACT"; then
    log_pass "Provider health reports state honestly (degraded with reason OR healthy)"
else
    log_fail "Provider health is ambiguous (no explicit reason + not healthy)"
fi

# Verify provider code path is reachable (call link-verification which
# uses provider_health_metrics table); expect 200 or 404, never 500.
# This is a POST endpoint; using api_get (GET) would return 405 Method Not Allowed.
PROV_HTTP=$(api_post -o /dev/null -w "%{http_code}" \
    "$API_URL/api/v1/link-verification/campaigns/00000000-0000-0000-0000-000000000000/verify-all?tenant_id=$TENANT_ID")
if [[ "$PROV_HTTP" == "200" || "$PROV_HTTP" == "404" || "$PROV_HTTP" == "422" ]]; then
    log_pass "Provider-using endpoint responds cleanly (HTTP $PROV_HTTP, no 5xx)"
else
    log_fail "Provider-using endpoint returned $PROV_HTTP (expected 200/404/422, NOT 5xx)"
fi

# ----------------------------------------------------------------------------
section "7. CORS preflight (frontend ↔ backend)"
# ----------------------------------------------------------------------------
CORS_HTTP=$(curl -sS -m "$TIMEOUT" -o /dev/null -w "%{http_code}" \
    -X OPTIONS \
    -H "Origin: $API_URL" \
    -H "Access-Control-Request-Method: GET" \
    -H "Access-Control-Request-Headers: x-tenant-id" \
    "$API_URL/api/v1/health")
if [[ "$CORS_HTTP" == "200" || "$CORS_HTTP" == "204" ]]; then
    log_pass "CORS preflight OK (HTTP $CORS_HTTP)"
else
    log_fail "CORS preflight failed (HTTP $CORS_HTTP) — frontend will not connect"
fi

# ============================================================================
# Summary
# ============================================================================
echo
echo "============================================================"
echo -e "Smoke test results:"
echo -e "  ${GREEN}PASS${NC}:    $PASS"
echo -e "  ${RED}FAIL${NC}:    $FAIL"
echo -e "  ${YELLOW}SKIPPED${NC}: $SKIPPED"
echo "============================================================"

if [[ "$FAIL" -gt 0 ]]; then
    echo
    echo -e "${RED}Failed tests:${NC}"
    for t in "${FAILED_TESTS[@]}"; do
        echo "  - $t"
    done
    echo
    echo -e "${RED}DO NOT promote this deployment. Roll back and investigate.${NC}"
    exit 1
fi

echo
echo -e "${GREEN}All smoke tests passed.${NC}"
echo
if contains "No external SEO APIs configured" "$HEALTH_AGAIN"; then
    echo -e "${YELLOW}Note: deployment is CONDITIONALLY CERTIFIED.${NC}"
    echo "To flip to REAL WORLD CERTIFIED, complete PROVIDER_PROVISIONING_CHECKLIST.md"
    echo "and re-run scripts/phase_1_4_workstream_b_provider_certification.py."
fi
exit 0
