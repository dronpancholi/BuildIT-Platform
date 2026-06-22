#!/usr/bin/env bash
# Phase 2.1.1 P0-2 — Process Supervisor Installer
# ==================================================
# Installs macOS launchd jobs to keep backend + 6 workers running.
# Idempotent: re-running updates the plist in place.
set -euo pipefail

REPO_ROOT="/Users/dronpancholi/Developer/Project 31A"
BACKEND_DIR="${REPO_ROOT}/backend"
LAUNCH_DIR="${HOME}/Library/LaunchAgents"
PYTHON_BIN="${BACKEND_DIR}/.venv/bin/python"

mkdir -p "${LAUNCH_DIR}"
mkdir -p /tmp/seo-platform-logs

# Common environment for all services
COMMON_ENV=$(cat <<EOF
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
        <key>PYTHONPATH</key>
        <string>${BACKEND_DIR}</string>
        <key>VIRTUAL_ENV</key>
        <string>${BACKEND_DIR}/.venv</string>
        <key>APP_ENV</key>
        <string>development</string>
    </dict>
EOF
)

write_plist() {
    local label="$1"
    local program="$2"
    shift 2
    local args_xml=""
    for arg in "$@"; do
        args_xml="${args_xml}        <string>${arg}</string>
"
    done

    cat > "${LAUNCH_DIR}/${label}.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${label}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${program}</string>
${args_xml}    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ThrottleInterval</key>
    <integer>10</integer>
    <key>StandardOutPath</key>
    <string>/tmp/seo-platform-logs/${label}.out</string>
    <key>StandardErrorPath</key>
    <string>/tmp/seo-platform-logs/${label}.err</string>
${COMMON_ENV}
    <key>WorkingDirectory</key>
    <string>${BACKEND_DIR}</string>
</dict>
</plist>
EOF
}

# 1. Backend (uvicorn)
write_plist "com.seo-platform.backend" \
    "${BACKEND_DIR}/.venv/bin/uvicorn" \
    "src.seo_platform.main:app" \
    "--host" "0.0.0.0" \
    "--port" "8000" \
    "--log-level" "info"

# 2-7. Workers (one per task queue)
for queue in onboarding ai_orchestration seo_intelligence backlink_engine communication reporting; do
    write_plist "com.seo-platform.worker.${queue}" \
        "${PYTHON_BIN}" \
        "-m" "src.seo_platform.workflows.worker" \
        "${queue}"
done

# Load all jobs
echo "[supervisor] Loading launchd jobs..."
for label in com.seo-platform.backend com.seo-platform.worker.onboarding com.seo-platform.worker.ai_orchestration com.seo-platform.worker.seo_intelligence com.seo-platform.worker.backlink_engine com.seo-platform.worker.communication com.seo-platform.worker.reporting; do
    launchctl unload "${LAUNCH_DIR}/${label}.plist" 2>/dev/null || true
    launchctl load "${LAUNCH_DIR}/${label}.plist" 2>&1
    echo "  loaded: ${label}"
done

sleep 3
echo "[supervisor] Process state:"
launchctl list | grep seo-platform | head -20
echo "[supervisor] Done"
