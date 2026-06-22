"""
SEO Platform — Startup Integrity Validation
==============================================

Phase 1.3.5 — Pre-startup checks that refuse to bring the platform up
if the live database is missing the schema that the application code
expects.

This module exists because of a class of incident we hit in Phase 1.3.1:
the application starts cleanly, the startup logs are green, every
middleware mounts, the lifespan event fires `platform_started` — and
then the first request to `/api/v1/plans` returns HTTP 500 because
the table it queries does not exist.

The check runs BEFORE `platform_started` is logged. In production it
is fail-fast. In development it logs a warning for each issue so the
operator can see what is wrong without the platform refusing to come
up (development is for fixing things, production is for not breaking).

Checks performed:
1. Alembic head matches the code's expected head.
2. All Phase 1.3.1 recovered tables exist.
3. P0-11 (`execution_plans`) and P0-13 (`backlink_prospects.email_verification_status`) columns/tables exist.
4. All 7 enum types created in Phase 1.3.1 are present.
5. The `action_definitions` table has all 16 model-declared columns.
6. The four model-backed tables with TimestampMixin have `updated_at`.
7. The `ProviderHealthCenter.PROVIDERS` list is the canonical lowercase list.

Each check returns a tuple of (passed, list_of_issues). The startup
verifier runs them all and returns a single consolidated report.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from sqlalchemy import text

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


# Alembic script location (relative to backend/).
# Used to dynamically discover the migration head.
ALEMBIC_SCRIPT_LOCATION = Path(__file__).resolve().parents[3] / "alembic" / "versions"


def _discover_alembic_heads() -> tuple[set[str], str]:
    """
    Dynamically discover the alembic head(s) by parsing migration files.

    Returns:
        (set_of_head_revisions, error_message_or_empty_string)

    A "head" is a revision that no other revision points to as its down_revision.
    In a clean linear chain there is exactly one head. In a forked chain there
    are multiple (a merge migration is required).

    We parse the file content line-by-line rather than importing the alembic
    module to keep this lightweight and avoid circular imports at startup.
    """
    revisions: dict[str, str | None] = {}  # rev -> down_rev (or None for root)

    if not ALEMBIC_SCRIPT_LOCATION.exists():
        return set(), f"alembic script location not found: {ALEMBIC_SCRIPT_LOCATION}"

    str_re = re.compile(r"""['"]([^'"]+)['"]""")

    for py_file in ALEMBIC_SCRIPT_LOCATION.glob("*.py"):
        if py_file.name.startswith("__"):
            continue
        try:
            lines = py_file.read_text(encoding="utf-8").splitlines()
        except Exception as e:
            return set(), f"failed to read {py_file.name}: {e!r}"

        rev: str | None = None
        down: str | None = None
        for line in lines:
            stripped = line.strip()
            # Match `revision: str = "..."` or `revision = "..."` or `revision: str = None`
            if rev is None and (stripped.startswith("revision:") or stripped.startswith("revision =")):
                # Find the RHS string value
                m = str_re.search(stripped)
                if m:
                    rev = m.group(1).strip()
            elif stripped.startswith("down_revision:") or stripped.startswith("down_revision ="):
                # The RHS is either a string literal or None
                if "None" in stripped.split("=", 1)[-1] and str_re.search(stripped.split("=", 1)[-1]) is None:
                    down = None
                else:
                    m = str_re.search(stripped)
                    if m:
                        down = m.group(1).strip()
                    else:
                        down = None
            # Stop early once both are found
            if rev is not None and "down_revision" in (lines[max(0, lines.index(line) - 3):lines.index(line) + 1][-1] if line in lines else ""):
                pass

        if rev is None:
            continue
        revisions[rev] = down

    if not revisions:
        return set(), "no migration files found"

    # Heads are revisions that no other revision points to as their down_revision
    referenced = {d for d in revisions.values() if d is not None}
    heads = set(revisions.keys()) - referenced
    return heads, ""


def get_expected_alembic_heads() -> set[str]:
    """
    Return the set of expected alembic head revisions, discovered dynamically
    from the migration files on disk.

    Raises RuntimeError if the discovery fails (so the startup check fails loud
    rather than silently accepting a misconfigured state).
    """
    heads, err = _discover_alembic_heads()
    if err:
        raise RuntimeError(f"alembic head discovery failed: {err}")
    return heads

# Tables that must exist (recovered in Phase 1.3.1).
REQUIRED_TABLES: list[str] = [
    "action_executions",
    "approval_policies",
    "approval_requests_v2",
    "audit_ledger",
    "graph_edges",
    "graph_entities",
    "operational_memory",
]

# Enum types that must exist.
REQUIRED_ENUMS: list[str] = [
    "action_execution_status",
    "policy_risk_level",
    "approval_risk_level",
    "actor_type",
    "decision_type",
    "memory_entry_type",
    "memory_source",
    "action_category",
    "action_risk_level",
]

# Columns that the ORM expects on action_definitions (Phase 14 model).
REQUIRED_ACTION_DEFINITIONS_COLUMNS: list[str] = [
    "display_name", "category", "risk_level", "input_schema", "output_schema",
    "permission_required", "requires_approval", "approval_policy",
    "rollback_handler", "execution_timeout_seconds", "max_retries",
    "idempotent", "is_enabled", "version", "custom_metadata", "updated_at",
]

# Model-backed tables that need updated_at (TimestampMixin or explicit).
TABLES_NEEDING_UPDATED_AT: list[str] = [
    "action_definitions",
    "agent_tasks",
    "reports",
    "graph_entities",
]

# Canonical lowercase PROVIDERS list (must match what the recording clients pass).
CANONICAL_PROVIDER_SLUGS: list[str] = [
    "dataforseo", "ahrefs", "scrapling", "searxng",
    "openpagerank", "hunter", "trafilatura",
    "sendgrid", "mailgun", "resend",
]


async def _check_alembic_head(session) -> list[str]:
    issues: list[str] = []
    try:
        # Discover expected head(s) dynamically from migration files on disk.
        # This replaces the previous hardcoded constant.
        try:
            expected_heads = get_expected_alembic_heads()
        except RuntimeError as e:
            issues.append(f"alembic head discovery failed: {e}")
            return issues

        if not expected_heads:
            issues.append("no alembic head found in migration files")
            return issues

        row = (await session.execute(text("SELECT version_num FROM alembic_version"))).first()
        if not row:
            issues.append("alembic_version row missing — database has not been initialized")
        else:
            actual_head = row[0]
            if actual_head not in expected_heads:
                # Build a helpful message. If there are multiple heads (a forked chain),
                # tell the operator to run `alembic merge` to resolve.
                if len(expected_heads) > 1:
                    issues.append(
                        f"alembic_version is {actual_head!r} but the migration tree has "
                        f"{len(expected_heads)} heads: {sorted(expected_heads)}. "
                        f"Run `alembic upgrade head` to apply and merge if needed."
                    )
                else:
                    issues.append(
                        f"alembic_version is {actual_head!r}, expected {sorted(expected_heads)[0]!r}. "
                        f"Run `alembic upgrade head` to apply missing migrations."
                    )
    except Exception as e:
        issues.append(f"alembic_version check failed: {e!r}")
    return issues


async def _check_tables_exist(session) -> list[str]:
    issues: list[str] = []
    try:
        rows = (await session.execute(
            text(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname='public' "
                "  AND tablename = ANY(:names)"
            ),
            {"names": REQUIRED_TABLES},
        )).scalars().all()
        present = set(rows)
        for t in REQUIRED_TABLES:
            if t not in present:
                issues.append(
                    f"required table '{t}' is missing. Phase 1.3.1 recovery migration "
                    f"(i13_recover_missing_tables) must be applied."
                )
    except Exception as e:
        issues.append(f"table existence check failed: {e!r}")
    return issues


async def _check_p0_columns(session) -> list[str]:
    issues: list[str] = []
    # P0-11: execution_plans must exist
    try:
        row = (await session.execute(text("SELECT to_regclass('public.execution_plans')"))).scalar()
        if not row:
            issues.append("P0-11: 'execution_plans' table missing — /api/v1/plans will 500")
    except Exception as e:
        issues.append(f"P0-11 check failed: {e!r}")
    # P0-13: backlink_prospects.email_verification_status must exist
    try:
        row = (await session.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name='backlink_prospects' AND column_name='email_verification_status'"
            )
        )).first()
        if not row:
            issues.append(
                "P0-13: 'backlink_prospects.email_verification_status' column missing — "
                "/api/v1/reports will 500"
            )
    except Exception as e:
        issues.append(f"P0-13 check failed: {e!r}")
    return issues


async def _check_enums(session) -> list[str]:
    issues: list[str] = []
    try:
        rows = (await session.execute(
            text("SELECT typname FROM pg_type WHERE typname = ANY(:names)"),
            {"names": REQUIRED_ENUMS},
        )).scalars().all()
        present = set(rows)
        for name in REQUIRED_ENUMS:
            if name not in present:
                issues.append(f"required enum type '{name}' is missing")
    except Exception as e:
        issues.append(f"enum check failed: {e!r}")
    return issues


async def _check_action_definitions_columns(session) -> list[str]:
    issues: list[str] = []
    try:
        rows = (await session.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='action_definitions'"
            )
        )).scalars().all()
        present = set(rows)
        for col in REQUIRED_ACTION_DEFINITIONS_COLUMNS:
            if col not in present:
                issues.append(f"action_definitions.{col} is missing — Phase 1.3.1 alignment not applied")
    except Exception as e:
        issues.append(f"action_definitions column check failed: {e!r}")
    return issues


async def _check_updated_at_columns(session) -> list[str]:
    issues: list[str] = []
    for tbl in TABLES_NEEDING_UPDATED_AT:
        try:
            row = (await session.execute(
                text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_name=:t AND column_name='updated_at'"
                ),
                {"t": tbl},
            )).first()
            if not row:
                issues.append(f"{tbl}.updated_at is missing — Phase 1.3.1 alignment not applied")
        except Exception as e:
            issues.append(f"{tbl} updated_at check failed: {e!r}")
    return issues


def _check_provider_slugs() -> list[str]:
    """Static check that ProviderHealthCenter.PROVIDERS is the canonical lowercase list."""
    issues: list[str] = []
    try:
        from seo_platform.services.provider_health import ProviderHealthCenter
        actual = [p.lower() for p in ProviderHealthCenter.PROVIDERS]
        expected = list(CANONICAL_PROVIDER_SLUGS)
        if set(actual) != set(expected):
            missing = set(expected) - set(actual)
            extra = set(actual) - set(expected)
            for slug in sorted(missing):
                issues.append(
                    f"ProviderHealthCenter.PROVIDERS missing '{slug}' — health endpoint will "
                    f"silently drop this provider's metrics"
                )
            for slug in sorted(extra):
                issues.append(
                    f"ProviderHealthCenter.PROVIDERS has unknown slug '{slug}'"
                )
    except Exception as e:
        issues.append(f"provider slug check failed: {e!r}")
    return issues


async def run_startup_integrity_check() -> dict[str, Any]:
    """
    Run all startup integrity checks. Returns a structured report.

    The caller (lifespan manager) decides whether to fail-fast or just log
    based on the environment (production = fail-fast, development = warn).
    """
    from seo_platform.core.database import get_db_session

    report: dict[str, Any] = {
        "ok": True,
        "checks": [],
        "issues": [],
    }

    async with get_db_session() as session:
        for name, fn in [
            ("alembic_head", _check_alembic_head),
            ("required_tables", _check_tables_exist),
            ("p0_columns", _check_p0_columns),
            ("required_enums", _check_enums),
            ("action_definitions_columns", _check_action_definitions_columns),
            ("updated_at_columns", _check_updated_at_columns),
        ]:
            issues = await fn(session)
            report["checks"].append({"name": name, "ok": not issues, "issues": issues})
            report["issues"].extend(issues)

    # Static check (no DB needed)
    provider_issues = _check_provider_slugs()
    report["checks"].append({"name": "provider_slugs", "ok": not provider_issues, "issues": provider_issues})
    report["issues"].extend(provider_issues)

    report["ok"] = len(report["issues"]) == 0
    return report


def format_integrity_report(report: dict[str, Any]) -> str:
    """Return a single-line summary suitable for a startup log."""
    if report["ok"]:
        return f"startup_integrity_ok checks={len(report['checks'])}"
    return (
        f"startup_integrity_failed checks={len(report['checks'])} "
        f"issues={len(report['issues'])}: " + "; ".join(report["issues"][:5])
    )
