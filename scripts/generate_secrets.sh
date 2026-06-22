#!/usr/bin/env bash
# ============================================================================
# BuildIT — Secret Generation Helper
# ============================================================================
# Generates cryptographically-strong secrets required for a production
# deployment. Run ONCE on a trusted host, store the outputs in a secrets
# manager (1Password, Vault, AWS Secrets Manager, Doppler, etc.) — NEVER
# commit them to git.
#
# Usage:
#   ./scripts/generate_secrets.sh
#
# Outputs (to stdout):
#   ENCRYPTION_MASTER_KEY    32-byte AES-256-GCM key, base64
#   AUTH_SECRET_KEY          32-byte random secret, base64
#   POSTGRES_PASSWORD        24-byte random password, base64
#   REDIS_PASSWORD (opt.)    24-byte random password, base64
#
# Verification (re-run is safe — values will differ, which is correct).
# ============================================================================

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

gen_base64() {
    local bytes="${1}"
    # /dev/urandom is appropriate for nonces/keys (not CSPRNG-class secrets).
    LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c "${bytes}" | base64 | tr -d '\n'
    echo
}

gen_password() {
    local bytes="${1}"
    python3 -c "
import secrets, string
alphabet = string.ascii_letters + string.digits + '!#%*+,-.:=?@^_~'
print(''.join(secrets.choice(alphabet) for _ in range(${bytes})))
"
}

echo -e "${YELLOW}BuildIT — Secret Generation${NC}"
echo "Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Host:      $(hostname)"
echo "============================================"
echo

echo "# 1. ENCRYPTION_MASTER_KEY (32 bytes, base64 — for AES-256-GCM)"
echo "# Used to encrypt sensitive DB columns. LOSING THIS KEY = DATA LOSS."
ENCRYPTION_MASTER_KEY=$(gen_base64 32)
echo "ENCRYPTION_MASTER_KEY=${ENCRYPTION_MASTER_KEY}"
echo

echo "# 2. AUTH_SECRET_KEY (32 bytes, base64 — for internal JWT/HS256)"
echo "# Used for auth token signing."
AUTH_SECRET_KEY=$(gen_base64 32)
echo "AUTH_SECRET_KEY=${AUTH_SECRET_KEY}"
echo

echo "# 3. POSTGRES_PASSWORD (24 chars, URL-safe)"
echo "# Password for the 'seo_platform_app' DB role."
POSTGRES_PASSWORD=$(gen_password 24)
echo "POSTGRES_PASSWORD=${POSTGRES_PASSWORD}"
echo

echo "# 4. REDIS_PASSWORD (24 chars, URL-safe) — OPTIONAL"
echo "# Skip if Redis is not exposed beyond the docker network."
REDIS_PASSWORD=$(gen_password 24)
echo "REDIS_PASSWORD=${REDIS_PASSWORD}"
echo

echo "# 5. TEMPORAL_DB_PASSWORD (24 chars) — OPTIONAL"
echo "# Internal Temporal DB user."
TEMPORAL_DB_PASSWORD=$(gen_password 24)
echo "TEMPORAL_DB_PASSWORD=${TEMPORAL_DB_PASSWORD}"
echo

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Done. Store these values in a secrets manager.${NC}"
echo -e "${YELLOW}DO NOT commit them to git. DO NOT log them.${NC}"
echo
echo "Next steps:"
echo "  1. Set these values in your secrets manager (1Password, Vault, etc.)"
echo "  2. Inject them into the production host as environment variables"
echo "     or render them into .env.production from a template at boot time"
echo "  3. Rotate every 90 days (or per your org's secret-rotation policy)"
echo "  4. Re-encrypt existing data when rotating ENCRYPTION_MASTER_KEY"
echo "     (use scripts/rotate_encryption_key.sh — not yet implemented)"
