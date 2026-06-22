#!/usr/bin/env bash
# ============================================================================
# BuildIT — Operational Health Check (for monitoring / cron / on-call)
# ============================================================================
# Lightweight, non-mutating health check intended to be run every 1-5 minutes
# by an external monitor (Datadog, Pingdom, Prometheus blackbox, cron+mail).
#
# Exits:
#   0   all healthy
#   1   one or more components degraded
#   2   one or more components unhealthy (5xx-level failure)
#   3   API unreachable
#
# Does NOT verify business logic (use scripts/deploy_smoke_test.sh for that).
# Does NOT mutate any state.
#
# Usage:
#   ./scripts/operational_health_check.sh
#   API_URL=https://api.example.com ./scripts/operational_health_check.sh
#   JSON=1 ./scripts/operational_health_check.sh   # emit JSON instead of text
#
# Cron example (every minute, alert on non-zero exit):
#   * * * * * /opt/buildit/scripts/operational_health_check.sh || /opt/alert.sh
# ============================================================================

set -uo pipefail

API_URL="${API_URL:-http://localhost:8000}"
TIMEOUT="${TIMEOUT:-5}"
JSON="${JSON:-0}"

if [[ "$JSON" == "1" ]]; then
    exec python3 - "$API_URL" "$TIMEOUT" <<'PY'
import json, sys, urllib.request
api, timeout = sys.argv[1], int(sys.argv[2])
out = {"api_url": api, "reachable": False, "status": None, "components": [], "exit_code": 3}
try:
    with urllib.request.urlopen(f"{api}/api/v1/health", timeout=timeout) as r:
        out["reachable"] = True
        body = json.loads(r.read().decode())
        out["status"] = body.get("status")
        for c in body.get("components", []):
            out["components"].append({
                "name": c["name"],
                "status": c["status"],
                "latency_ms": c.get("latency_ms"),
                "message": c.get("message"),
            })
        if out["status"] == "healthy":
            out["exit_code"] = 0
        elif out["status"] == "degraded":
            out["exit_code"] = 1
        else:
            out["exit_code"] = 2
except Exception as e:
    out["error"] = str(e)
print(json.dumps(out, indent=2))
sys.exit(out["exit_code"])
PY
fi

# ----- Text mode -----
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

if ! command -v python3 &>/dev/null; then
    echo -e "${RED}python3 is required${NC}" >&2
    exit 3
fi

# Pull health JSON, normalize, and parse.
RAW=$(curl -sS -m "$TIMEOUT" "$API_URL/api/v1/health" 2>&1) || {
    echo -e "${RED}UNREACHABLE${NC}  $API_URL/api/v1/health"
    exit 3
}

STATUS=$(echo "$RAW" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "")
if [[ -z "$STATUS" ]]; then
    echo -e "${RED}UNHEALTHY${NC}  $API_URL  (no status field)"
    exit 2
fi

echo -e "BuildIT health  ${YELLOW}$API_URL${NC}  @  $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "────────────────────────────────────────────────────────────"

# Print each component, color-coded.
echo "$RAW" | python3 -c "
import json, sys
data = json.load(sys.stdin)
GREEN = '\033[0;32m'; YELLOW = '\033[1;33m'; RED = '\033[0;31m'; NC = '\033[0m'
for c in data.get('components', []):
    name = c.get('name','?'); status = c.get('status','?'); lat = c.get('latency_ms'); msg = c.get('message') or ''
    if status == 'healthy':
        c_str = f'{GREEN}healthy{NC}'
    elif status == 'degraded':
        c_str = f'{YELLOW}degraded{NC}'
    else:
        c_str = f'{RED}{status}{NC}'
    lat_str = f' ({lat:.1f}ms)' if isinstance(lat,(int,float)) else ''
    msg_str = f'  — {msg}' if msg else ''
    print(f'  {name:<20} {c_str}{lat_str}{msg_str}')
overall = data.get('status','?')
if overall == 'healthy':
    overall_str = f'{GREEN}healthy{NC}'
elif overall == 'degraded':
    overall_str = f'{YELLOW}degraded{NC}'
else:
    overall_str = f'{RED}{overall}{NC}'
print(f'\\n  OVERALL           {overall_str}')
"

# Map overall status to exit code.
case "$STATUS" in
    healthy)   exit 0 ;;
    degraded)  exit 1 ;;
    *)         exit 2 ;;
esac
