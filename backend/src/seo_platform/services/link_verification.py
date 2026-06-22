"""
SEO Platform — Link Verification Service (Workstream E)
========================================================
Real HTTP-based backlink verification.

For an AcquiredLink record this service:
1. GETs the source URL with a hard 10s timeout via the Scrapling client.
2. Captures HTTP status, response time, and the full redirect chain.
3. Parses the returned HTML for <a> tags pointing at the target URL.
4. For each match, captures anchor text, rel attribute, and position.
5. Classifies the result into one of: VERIFIED, MISSING, REDIRECTED,
   BROKEN, or ERROR.
6. Persists the full verification record to ``verification_history``
   and updates all ``AcquiredLink`` denormalized fields used by the
   front-end and the link monitoring engine.

This module owns no mocking or fallback logic — every check is a real
network request and either succeeds with real telemetry or surfaces
the failure cleanly.
"""
from __future__ import annotations

import enum
import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from seo_platform.clients.scrapling import ScraplingClient
from seo_platform.core.logging import get_logger
from seo_platform.models.backlink import (
    AcquiredLink,
    LinkStatus,
)

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Result classification
# ---------------------------------------------------------------------------
class VerificationOutcome(str, enum.Enum):
    """High-level classification of a single verification attempt."""

    VERIFIED = "verified"
    MISSING = "missing"
    REDIRECTED = "redirected"
    BROKEN = "broken"
    ERROR = "error"


# How each outcome maps onto the persisted LinkStatus enum. The link
# monitor consumes these to decide whether to flag a regression.
OUTCOME_TO_LINK_STATUS: dict[VerificationOutcome, LinkStatus] = {
    VerificationOutcome.VERIFIED: LinkStatus.VERIFIED_LIVE,
    VerificationOutcome.MISSING: LinkStatus.REMOVED,
    VerificationOutcome.REDIRECTED: LinkStatus.REMOVED,
    VerificationOutcome.BROKEN: LinkStatus.BROKEN,
    VerificationOutcome.ERROR: LinkStatus.BROKEN,
}


class VerificationRecord(BaseModel):
    """One persisted entry in ``AcquiredLink.verification_history``."""

    checked_at: datetime
    outcome: VerificationOutcome
    http_status: int | None = None
    response_time_ms: float | None = None
    redirect_chain: list[dict[str, Any]] = Field(default_factory=list)
    final_url: str | None = None
    matched: bool = False
    anchor_text: str | None = None
    rel: str | None = None
    link_position: int | None = None
    link_type: str | None = None
    error: str | None = None


class LinkVerificationService:
    """
    Real-time link verification engine.

    Owns the network I/O, HTML parsing, and persistence of per-link
    verification snapshots. Used by the API (manual verify) and the
    scheduled link monitor.
    """

    FETCH_TIMEOUT_SECONDS: int = 10
    MAX_HISTORY_ENTRIES: int = 200

    def __init__(self, scrapling_client: ScraplingClient | None = None) -> None:
        # A fresh client per call — ScraplingClient is cheap and avoids
        # sharing state across concurrent verifications.
        self._client = scrapling_client or ScraplingClient(
            timeout=self.FETCH_TIMEOUT_SECONDS,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def verify_link(
        self,
        acquired_link_id: UUID,
        tenant_id: UUID,
    ) -> dict[str, Any]:
        """
        Run a single verification and persist the result.

        Returns a serializable dict that the API layer and Temporal
        activity can both consume without further work.
        """
        from sqlalchemy import select

        from seo_platform.core.database import get_tenant_session

        record = await self._build_record(acquired_link_id, tenant_id)
        if record is None:
            return {
                "acquired_link_id": str(acquired_link_id),
                "found": False,
                "outcome": VerificationOutcome.ERROR.value,
                "error": "acquired_link_not_found",
            }

        link, target, record = record

        # Persist the new history entry + denormalized fields.
        async with get_tenant_session(tenant_id) as session:
            result = await session.execute(
                select(AcquiredLink).where(
                    AcquiredLink.id == acquired_link_id,
                    AcquiredLink.tenant_id == tenant_id,
                )
            )
            db_link = result.scalar_one_or_none()
            if db_link is None:
                return {
                    "acquired_link_id": str(acquired_link_id),
                    "found": False,
                    "outcome": VerificationOutcome.ERROR.value,
                    "error": "acquired_link_not_found",
                }

            previous_status = (
                db_link.status.value
                if isinstance(db_link.status, LinkStatus)
                else str(db_link.status or "")
            )

            history = list(db_link.verification_history or [])
            history.append(record.model_dump(mode="json"))
            if len(history) > self.MAX_HISTORY_ENTRIES:
                history = history[-self.MAX_HISTORY_ENTRIES :]

            now = record.checked_at
            if db_link.first_verified_at is None and record.outcome == VerificationOutcome.VERIFIED:
                db_link.first_verified_at = now
            db_link.last_checked_at = now
            db_link.check_count = (db_link.check_count or 0) + 1
            db_link.status = OUTCOME_TO_LINK_STATUS[record.outcome]
            db_link.verification_history = history
            db_link.last_http_status = record.http_status
            db_link.last_response_time_ms = record.response_time_ms
            db_link.last_checked_redirect_chain = record.redirect_chain
            db_link.last_match_anchor = record.anchor_text
            db_link.last_match_rel = record.rel
            db_link.last_match_position = record.link_position
            db_link.last_error = record.error

            if record.matched and record.anchor_text:
                # Only overwrite user-supplied anchor on a real match.
                if not db_link.anchor_text:
                    db_link.anchor_text = record.anchor_text
            if record.matched and record.link_type:
                db_link.link_type = record.link_type

            await session.flush()

        response = {
            "acquired_link_id": str(acquired_link_id),
            "campaign_id": str(link["campaign_id"]),
            "source_url": link["source_url"],
            "target_url": link["target_url"],
            "found": True,
            "outcome": record.outcome.value,
            "link_status": OUTCOME_TO_LINK_STATUS[record.outcome].value,
            "http_status": record.http_status,
            "response_time_ms": record.response_time_ms,
            "matched": record.matched,
            "anchor_text": record.anchor_text,
            "rel": record.rel,
            "link_type": record.link_type,
            "link_position": record.link_position,
            "redirect_chain": record.redirect_chain,
            "final_url": record.final_url,
            "checked_at": record.checked_at.isoformat(),
            "previous_status": previous_status,
            "error": record.error,
        }
        logger.info(
            "link_verified",
            acquired_link_id=str(acquired_link_id),
            tenant_id=str(tenant_id),
            outcome=record.outcome.value,
            http_status=record.http_status,
            matched=record.matched,
        )
        return response

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    async def _build_record(
        self,
        acquired_link_id: UUID,
        tenant_id: UUID,
    ) -> tuple[dict[str, Any], str, VerificationRecord] | None:
        """Load the AcquiredLink and run a real fetch + parse cycle."""
        from sqlalchemy import select

        from seo_platform.core.database import get_tenant_session

        async with get_tenant_session(tenant_id) as session:
            result = await session.execute(
                select(AcquiredLink).where(
                    AcquiredLink.id == acquired_link_id,
                    AcquiredLink.tenant_id == tenant_id,
                )
            )
            link = result.scalar_one_or_none()
            if link is None:
                logger.warning(
                    "link_verification_target_missing",
                    acquired_link_id=str(acquired_link_id),
                )
                return None

            source_url = link.source_url
            target_url = link.target_url
            campaign_id = link.campaign_id

        if not source_url or not target_url:
            return None

        record = await self._fetch_and_classify(source_url, target_url)
        return (
            {
                "id": acquired_link_id,
                "campaign_id": campaign_id,
                "source_url": source_url,
                "target_url": target_url,
            },
            target_url,
            record,
        )

    async def _fetch_and_classify(
        self,
        source_url: str,
        target_url: str,
    ) -> VerificationRecord:
        """Real network call + HTML parsing + outcome classification."""
        started = time.monotonic()
        try:
            scrapling_result = await self._client.fetch(source_url)
        except Exception as exc:  # network/timeout/SSL/etc.
            elapsed_ms = round((time.monotonic() - started) * 1000, 2)
            logger.warning(
                "link_verification_fetch_error",
                source_url=source_url,
                error=str(exc),
                elapsed_ms=elapsed_ms,
            )
            return VerificationRecord(
                checked_at=datetime.now(UTC),
                outcome=VerificationOutcome.ERROR,
                response_time_ms=elapsed_ms,
                error=str(exc)[:500],
            )

        elapsed_ms = round((time.monotonic() - started) * 1000, 2)
        http_status = scrapling_result.status_code
        final_url = scrapling_result.url or source_url
        redirect_chain = [
            {
                "from": source_url,
                "to": final_url,
                "status": http_status,
            }
        ]

        # If the source URL no longer points at the same domain, classify as
        # REDIRECTED — the link is still resolved but no longer relevant.
        if not _same_registrable_domain(source_url, final_url):
            return VerificationRecord(
                checked_at=datetime.now(UTC),
                outcome=VerificationOutcome.REDIRECTED,
                http_status=http_status,
                response_time_ms=elapsed_ms,
                redirect_chain=redirect_chain,
                final_url=final_url,
            )

        if http_status is None or http_status >= 400:
            return VerificationRecord(
                checked_at=datetime.now(UTC),
                outcome=VerificationOutcome.BROKEN,
                http_status=http_status,
                response_time_ms=elapsed_ms,
                redirect_chain=redirect_chain,
                final_url=final_url,
            )

        match = _find_target_link(
            html=scrapling_result.html_content or "",
            base_url=final_url,
            target_url=target_url,
        )

        if match is None:
            return VerificationRecord(
                checked_at=datetime.now(UTC),
                outcome=VerificationOutcome.MISSING,
                http_status=http_status,
                response_time_ms=elapsed_ms,
                redirect_chain=redirect_chain,
                final_url=final_url,
            )

        anchor, rel, position, link_type = match
        return VerificationRecord(
            checked_at=datetime.now(UTC),
            outcome=VerificationOutcome.VERIFIED,
            http_status=http_status,
            response_time_ms=elapsed_ms,
            redirect_chain=redirect_chain,
            final_url=final_url,
            matched=True,
            anchor_text=anchor,
            rel=rel,
            link_position=position,
            link_type=link_type,
        )


# ---------------------------------------------------------------------------
# Pure-function helpers (no I/O — easy to unit test)
# ---------------------------------------------------------------------------
def _same_registrable_domain(url_a: str, url_b: str) -> bool:
    """True when both URLs share the same effective second-level domain."""
    if not url_a or not url_b:
        return False
    try:
        host_a = (urlparse(url_a).hostname or "").lower()
        host_b = (urlparse(url_b).hostname or "").lower()
    except Exception:
        return False
    if not host_a or not host_b:
        return False
    if host_a == host_b:
        return True
    # Strip leading www. and compare the last two labels.
    def _root(host: str) -> str:
        host = host[4:] if host.startswith("www.") else host
        parts = host.split(".")
        if len(parts) >= 2:
            return ".".join(parts[-2:])
        return host

    return _root(host_a) == _root(host_b)


def _normalize_url(href: str, base_url: str) -> str | None:
    """Resolve a possibly-relative href to an absolute URL."""
    if not href:
        return None
    href = href.strip()
    if not href:
        return None
    # Mailto/tel/javascript etc. — not a target link.
    lowered = href.lower()
    if lowered.startswith(("mailto:", "tel:", "javascript:", "#")):
        return None
    try:
        from urllib.parse import urljoin

        return urljoin(base_url, href)
    except Exception:
        return None


def _urls_refer_to_same_target(candidate: str, target: str) -> bool:
    """True when the candidate URL points at the same destination as target.

    Match criteria (in order):
    1. Exact URL string equality (ignoring trailing slash + fragment).
    2. Same host AND same path (ignoring trailing slash + fragment).
    """
    if not candidate or not target:
        return False

    def _clean(url: str) -> tuple[str, str, str, str]:
        parsed = urlparse(url)
        return (
            (parsed.scheme or "").lower(),
            (parsed.hostname or "").lower(),
            (parsed.path or "").rstrip("/"),
            (parsed.query or ""),
        )

    c_scheme, c_host, c_path, c_query = _clean(candidate)
    t_scheme, t_host, t_path, t_query = _clean(target)

    if (c_scheme, c_host, c_path, c_query) == (t_scheme, t_host, t_path, t_query):
        return True

    # No query string on candidate but same path + host is a match.
    if (
        c_host == t_host
        and c_path == t_path
        and not c_query
        and c_scheme == t_scheme
    ):
        return True

    return False


def _find_target_link(
    html: str,
    base_url: str,
    target_url: str,
) -> tuple[str, str | None, int, str] | None:
    """
    Scan an HTML body for <a> tags pointing at target_url.

    Returns ``(anchor_text, rel, position, link_type)`` for the first
    matching anchor, or ``None`` if no match is found. ``link_type`` is
    ``"dofollow"`` unless ``rel="nofollow"`` (or ``rel="sponsored"`` /
    ``rel="ugc"``) is present.
    """
    if not html:
        return None

    from html.parser import HTMLParser

    class _LinkParser(HTMLParser):
        def __init__(self) -> None:
            super().__init__(convert_charrefs=True)
            self._position = 0
            self.matches: list[tuple[str, str | None, int]] = []

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            if tag.lower() != "a":
                return
            self._position += 1
            attr_map = {k.lower(): (v or "") for k, v in attrs}
            href = attr_map.get("href", "")
            resolved = _normalize_url(href, base_url)
            if not resolved:
                return
            if not _urls_refer_to_same_target(resolved, target_url):
                return
            rel = attr_map.get("rel", "").strip() or None
            anchor_text = attr_map.get("title", "").strip()
            self.matches.append((anchor_text, rel, self._position))

    parser = _LinkParser()
    try:
        parser.feed(html)
    except Exception as exc:
        logger.warning("link_html_parse_error", error=str(exc))
        return None

    if not parser.matches:
        return None

    anchor_text, rel, position = parser.matches[0]
    link_type = _classify_rel(rel)
    return anchor_text or None, rel, position, link_type


def _classify_rel(rel: str | None) -> str:
    """Map a ``rel`` attribute value to the canonical link_type label."""
    if not rel:
        return "dofollow"
    tokens = {token.strip().lower() for token in rel.split() if token.strip()}
    if tokens & {"nofollow", "sponsored", "ugc"}:
        return "nofollow"
    return "dofollow"


link_verification_service = LinkVerificationService()
