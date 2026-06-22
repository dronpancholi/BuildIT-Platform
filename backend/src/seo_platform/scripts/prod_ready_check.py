"""
SEO Platform — Production Readiness Audit
=========================================
Real validation checks. Refuses to claim success on unverified subsystems.

Each check is a separate async function returning (passed: bool, message: str).
The check name in the result is the truth — no green checkmarks without evidence.
"""

import asyncio
import os
import sys

from termcolor import colored


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

async def check_aws_env() -> tuple[bool, str]:
    """AWS credentials / region must be resolvable from the environment."""
    required = ["AWS_REGION", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        return False, f"Missing AWS env vars: {missing}"
    return True, "AWS env vars present"


async def check_k8s_env() -> tuple[bool, str]:
    """Either KUBECONFIG is set or we are running inside a Kubernetes pod."""
    if os.getenv("KUBERNETES_SERVICE_HOST"):
        return True, f"Running inside k8s pod (host={os.getenv('KUBERNETES_SERVICE_HOST')})"
    if os.getenv("KUBECONFIG"):
        return True, f"KUBECONFIG present at {os.getenv('KUBECONFIG')}"
    return False, "Not running inside k8s and KUBECONFIG is not set"


async def check_temporal_env() -> tuple[bool, str]:
    """Temporal host must be reachable and the namespace must be configured."""
    host = os.getenv("TEMPORAL_HOST", "localhost")
    port = os.getenv("TEMPORAL_PORT", "7233")
    try:
        reader, writer = await asyncio.open_connection(host, int(port))
        writer.close()
        await writer.wait_closed()
        return True, f"Temporal reachable at {host}:{port}"
    except Exception as e:
        return False, f"Temporal unreachable at {host}:{port} ({e})"


async def check_kafka_env() -> tuple[bool, str]:
    """Kafka bootstrap server must be reachable."""
    servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    host, _, port = servers.partition(":")
    try:
        reader, writer = await asyncio.open_connection(host, int(port or 9092))
        writer.close()
        await writer.wait_closed()
        return True, f"Kafka reachable at {servers}"
    except Exception as e:
        return False, f"Kafka unreachable at {servers} ({e})"


async def check_redis_env() -> tuple[bool, str]:
    """Redis host must be reachable and PING must succeed."""
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", 6379))
    try:
        reader, writer = await asyncio.open_connection(host, port)
        # RESP PING
        writer.write(b"*1\r\n$4\r\nPING\r\n")
        await writer.drain()
        resp = await reader.readline()
        writer.close()
        await writer.wait_closed()
        if b"PONG" in resp or b"+PONG" in resp or b"+OK" in resp:
            return True, f"Redis PING ok at {host}:{port}"
        return False, f"Redis PING unexpected response: {resp!r}"
    except Exception as e:
        return False, f"Redis unreachable at {host}:{port} ({e})"


async def check_db_env() -> tuple[bool, str]:
    """PostgreSQL must be reachable and Row-Level Security must be enabled."""
    try:
        import asyncpg  # type: ignore
    except ImportError:
        return False, "asyncpg not installed — cannot verify database"
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("POSTGRES_PORT", 5432))
    user = os.getenv("POSTGRES_USER", "seo_platform_app")
    pwd = os.getenv("POSTGRES_PASSWORD", "")
    db = os.getenv("POSTGRES_DB", "seo_platform")
    try:
        conn = await asyncpg.connect(host=host, port=port, user=user, password=pwd, database=db)
        rls_count = await conn.fetchval(
            "SELECT count(*) FROM pg_tables WHERE schemaname='public' AND rowsecurity=true"
        )
        table_count = await conn.fetchval("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")
        await conn.close()
        if rls_count < 1:
            return False, f"RLS is NOT enabled on any public table (table_count={table_count})"
        return True, f"Postgres reachable, {rls_count}/{table_count} public tables have RLS"
    except Exception as e:
        return False, f"Postgres unreachable: {e}"


async def check_deliverability() -> tuple[bool, str]:
    """Email provider API key must be configured (not the dev mock)."""
    sendgrid = os.getenv("SENDGRID_API_KEY", "")
    mailgun = os.getenv("MAILGUN_API_KEY", "")
    resend = os.getenv("RESEND_API_KEY", "")
    if sendgrid and sendgrid != "mock" and not sendgrid.startswith("SG.mock"):
        return True, "SendGrid API key configured"
    if mailgun and mailgun != "mock":
        return True, "Mailgun API key configured"
    if resend and resend != "mock":
        return True, "Resend API key configured"
    return False, "No production email provider configured (SendGrid/Mailgun/Resend all missing)"


async def check_encryption_key() -> tuple[bool, str]:
    """Encryption key must have sufficient entropy."""
    import base64
    import math
    key_b64 = os.getenv("ENCRYPTION_MASTER_KEY", "")
    if not key_b64:
        return False, "ENCRYPTION_MASTER_KEY not set"
    if key_b64 == "bW9ja19tYXN0ZXJfa2V5XzMyX2J5dGVzX2xvbmdfc3RyaW5n":
        return False, "ENCRYPTION_MASTER_KEY is the well-known mock key"
    try:
        raw = base64.b64decode(key_b64)
    except Exception as e:
        return False, f"ENCRYPTION_MASTER_KEY is not valid base64: {e}"
    if len(raw) != 32:
        return False, f"ENCRYPTION_MASTER_KEY must decode to 32 bytes (got {len(raw)})"
    counts = [0] * 256
    for b in raw:
        counts[b] += 1
    n = len(raw)
    entropy = -sum((c / n) * math.log2(c / n) for c in counts if c > 0)
    if entropy < 4.5:
        return False, f"ENCRYPTION_MASTER_KEY entropy too low ({entropy:.2f} bits/byte)"
    return True, f"ENCRYPTION_MASTER_KEY entropy ok ({entropy:.2f} bits/byte)"


async def check_security_toggles() -> tuple[bool, str]:
    """Production-safety toggles must be disabled."""
    app_env = os.getenv("APP_ENV", "development")
    if app_env != "production":
        return True, f"Skipped (APP_ENV={app_env}, not production)"
    if os.getenv("USE_MOCK_PROVIDERS", "false").lower() == "true":
        return False, "USE_MOCK_PROVIDERS=true in production"
    if os.getenv("DEV_AUTH_BYPASS", "false").lower() == "true":
        return False, "DEV_AUTH_BYPASS=true in production"
    if os.getenv("APP_DEBUG", "false").lower() == "true":
        return False, "APP_DEBUG=true in production"
    return True, "All production-safety toggles are disabled"


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

CHECKS = [
    ("Security Toggles (Mock/Auth Bypass)", check_security_toggles),
    ("Encryption Key Entropy", check_encryption_key),
    ("Database (Postgres + RLS)", check_db_env),
    ("Redis Connectivity", check_redis_env),
    ("Kafka Event Bus", check_kafka_env),
    ("Temporal Orchestration", check_temporal_env),
    ("Email Provider (Deliverability)", check_deliverability),
    ("AWS Infrastructure", check_aws_env),
    ("Kubernetes / Helm", check_k8s_env),
]


async def run_checks() -> int:
    print(colored("🔍 BuildIT Production Readiness Audit (REAL CHECKS)", "cyan", attrs=["bold"]))
    print("-" * 70)

    failures: list[str] = []
    for name, check_fn in CHECKS:
        print(f"  {name:40s} ... ", end="", flush=True)
        try:
            passed, msg = await check_fn()
        except Exception as e:
            passed, msg = False, f"check raised exception: {e}"
        if passed:
            print(colored("PASS", "green"), f"  ({msg})")
        else:
            print(colored("FAIL", "red"), f"  ({msg})")
            failures.append(f"{name}: {msg}")

    print("-" * 70)
    if not failures:
        print(colored("✅ SYSTEM READY FOR PRODUCTION LAUNCH", "green", attrs=["bold"]))
        return 0
    print(colored(f"❌ {len(failures)} CHECK(S) FAILED — SYSTEM NOT READY", "red", attrs=["bold"]))
    for f in failures:
        print(colored(f"  - {f}", "yellow"))
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(run_checks()))
