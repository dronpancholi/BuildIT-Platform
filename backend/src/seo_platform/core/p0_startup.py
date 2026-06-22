"""
SEO Platform — Phase 2.5.1 P0 Startup Validators
=================================================
Pre-launch checks that refuse to bring the platform up in PRODUCTION if any
of the P0 remediation requirements is not met:

- Auth provider (Clerk) must be configured.
- At least one real email provider (Resend, Mailgun, or SendGrid) must be configured.
- All three SEO providers (DataForSEO, Ahrefs, Hunter) must be configured.
- AI inference (NVIDIA NIM) must be configured.
- Encryption master key must be present and entropy-validated.
- Mock providers and dev auth bypass must be disabled in production.

In DEVELOPMENT, the same checks are run but produce warnings instead of
refusing to start, so the platform is still usable for local coding.

In TESTING, all checks are skipped.
"""

from __future__ import annotations

from typing import Any

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


def validate_p0_production_requirements() -> dict[str, Any]:
    """
    Run all P0 production checks. Returns a structured report.

    The caller (lifespan manager) raises RuntimeError in production if any
    hard check fails. In development, the report is logged as warnings.
    """
    from seo_platform.config import get_settings
    settings = get_settings()

    report: dict[str, Any] = {
        "ok": True,
        "checks": [],
        "errors": [],
        "warnings": [],
    }

    def _add(check_name: str, ok: bool, error: str | None = None, warning: str | None = None) -> None:
        report["checks"].append({
            "name": check_name,
            "ok": ok,
            "error": error,
            "warning": warning,
        })
        if error:
            report["errors"].append(f"[{check_name}] {error}")
        if warning:
            report["warnings"].append(f"[{check_name}] {warning}")

    # ------------------------------------------------------------
    # 1. Auth provider (Clerk)
    # ------------------------------------------------------------
    if settings.is_production:
        if settings.auth.provider != "clerk":
            _add("auth_provider", False,
                 error=f"AUTH_PROVIDER must be 'clerk' in production, got {settings.auth.provider!r}")
        elif not settings.auth.jwks_url:
            _add("auth_jwks", False,
                 error="AUTH_JWKS_URL is required in production (Clerk JWKS endpoint)")
        elif not settings.auth.publishable_key:
            _add("auth_publishable_key", False,
                 error="AUTH_PUBLISHABLE_KEY is required in production")
        elif settings.dev_auth_bypass:
            _add("dev_auth_bypass_disabled", False,
                 error="DEV_AUTH_BYPASS must be false in production")
        else:
            _add("auth_provider", True)
    else:
        if not settings.auth.jwks_url and not settings.dev_auth_bypass:
            _add("auth_provider", ok=True,
                 warning="AUTH_JWKS_URL not set; dev_auth_bypass=true is the only way to authenticate in non-prod")
        else:
            _add("auth_provider", True)

    # ------------------------------------------------------------
    # 2. Email provider (at least one of Resend, Mailgun, SendGrid)
    # ------------------------------------------------------------
    email_providers_configured = sum([
        bool(settings.resend.api_key),
        bool(settings.mailgun.api_key and settings.mailgun.domain),
        bool(settings.sendgrid.api_key),
    ])
    if settings.is_production:
        if email_providers_configured == 0:
            _add("email_provider", False,
                 error=(
                     "At least one real email provider must be configured in production "
                     "(RESEND_API_KEY or MAILGUN_API_KEY+MAILGUN_DOMAIN or SENDGRID_API_KEY). "
                     "MailHog fallback is disabled in production."
                 ))
        else:
            _add("email_provider", True)
    else:
        if email_providers_configured == 0:
            _add("email_provider", ok=True,
                 warning="No real email provider configured; MailHog will be used (dev only)")
        else:
            _add("email_provider", True)

    # ------------------------------------------------------------
    # 3. SEO providers (DataForSEO, Ahrefs, Hunter)
    # ------------------------------------------------------------
    if settings.is_production:
        missing = []
        if not (settings.dataforseo.login and settings.dataforseo.password):
            missing.append("DATAFORSEO_LOGIN/DATAFORSEO_PASSWORD")
        if not settings.ahrefs.api_key:
            missing.append("AHREFS_API_KEY")
        if not settings.hunter.api_key:
            missing.append("HUNTER_API_KEY")
        if missing:
            _add("seo_providers", False,
                 error=f"Missing required SEO provider config: {', '.join(missing)}")
        else:
            _add("seo_providers", True)
    else:
        missing = []
        if not (settings.dataforseo.login and settings.dataforseo.password):
            missing.append("DATAFORSEO")
        if not settings.ahrefs.api_key:
            missing.append("AHREFS")
        if not settings.hunter.api_key:
            missing.append("HUNTER")
        if missing:
            _add("seo_providers", ok=True,
                 warning=f"SEO APIs not configured: {', '.join(missing)}; "
                         "system will use free fallback providers (scrapling/SearXNG/Hunter mock). "
                         "Outreach quality is lower but the system remains fully functional.")
        else:
            _add("seo_providers", True)

    # ------------------------------------------------------------
    # 4. AI inference (NVIDIA NIM)
    # ------------------------------------------------------------
    if settings.is_production:
        if not settings.nvidia.api_key:
            _add("ai_provider", False,
                 error="NVIDIA_NIM_API_KEY is required in production")
        else:
            _add("ai_provider", True)
    else:
        if not settings.nvidia.api_key:
            _add("ai_provider", ok=True,
                 warning="NVIDIA_NIM_API_KEY not set; AI features will fail")
        else:
            _add("ai_provider", True)

    # ------------------------------------------------------------
    # 5. Encryption master key
    # ------------------------------------------------------------
    from seo_platform.core.encryption import validate_encryption_key
    from seo_platform.config import get_settings as _gs
    s = _gs()
    master_key = getattr(s, "encryption_master_key", "")
    if settings.is_production:
        if not master_key:
            _add("encryption_master_key", False,
                 error="ENCRYPTION_MASTER_KEY is required in production")
        else:
            try:
                validate_encryption_key(master_key)
                _add("encryption_master_key", True)
            except ValueError as e:
                _add("encryption_master_key", False, error=str(e))
    else:
        if not master_key:
            _add("encryption_master_key", ok=True,
                 warning="ENCRYPTION_MASTER_KEY not set")
        else:
            try:
                validate_encryption_key(master_key)
                _add("encryption_master_key", True)
            except ValueError as e:
                _add("encryption_master_key", False, error=str(e))

    # ------------------------------------------------------------
    # 6. Mock providers must be disabled in production
    # ------------------------------------------------------------
    if settings.is_production and settings.use_mock_providers:
        _add("mock_providers_disabled", False,
             error="USE_MOCK_PROVIDERS must be false in production")
    else:
        _add("mock_providers_disabled", True)

    report["ok"] = len(report["errors"]) == 0
    return report


def format_p0_report(report: dict[str, Any]) -> str:
    """One-line summary suitable for startup logs."""
    if report["ok"]:
        return f"p0_requirements_ok checks={len(report['checks'])} warnings={len(report['warnings'])}"
    return (
        f"p0_requirements_failed checks={len(report['checks'])} "
        f"errors={len(report['errors'])} warnings={len(report['warnings'])}: "
        + "; ".join(report["errors"][:5])
    )
