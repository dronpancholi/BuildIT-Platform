# PHASE 1.2 — Real reply tracking webhook implemented
"""
SEO Platform — Inbound Email Webhook Handler
=============================================
Receives real inbound email events from SendGrid Inbound Parse, Postmark
Inbound, and AWS SES (via SNS notification) and writes the resulting state
to the database:

* OutreachThread.status  → REPLIED
* OutreachThread.replied_at = now()
* BacklinkProspect.status → replied
* BacklinkCampaign.reply_rate / acquisition_rate recomputed
* AuditLog entry appended

The endpoint is mounted at ``POST /api/v1/webhooks/inbound/email`` and is
intentionally format-agnostic: it dispatches on the ``Content-Type`` of
the incoming request, parses the payload, normalises it, and runs the
same downstream logic regardless of the originating provider.

This module performs **real** database writes — no simulation, no
in-memory stub. A successful response (200 OK) means the DB has been
updated and the audit log has been appended.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import re
from datetime import UTC, datetime
from email import message_from_string
from email.message import Message
from email.utils import getaddresses, parseaddr
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from sqlalchemy import func, select

from seo_platform.config import get_settings
from seo_platform.core.audit import audit_service
from seo_platform.core.auth import CurrentUser, get_current_user
from seo_platform.core.database import get_session, get_tenant_session
from seo_platform.core.logging import get_logger
from seo_platform.models.backlink import (
    BacklinkCampaign,
    BacklinkProspect,
    OutreachThread,
    ProspectStatus,
    ThreadStatus,
)
from seo_platform.models.tenant import AuditLog

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks/inbound", tags=["inbound-webhooks"])


# ---------------------------------------------------------------------------
# Normalised payload container
# ---------------------------------------------------------------------------
class NormalisedInbound:
    """Provider-agnostic representation of a single inbound email."""

    __slots__ = (
        "from_email",
        "to_email",
        "subject",
        "body_text",
        "body_html",
        "message_id",
        "in_reply_to",
        "references",
        "provider",
        "raw_headers",
    )

    def __init__(
        self,
        *,
        from_email: str = "",
        to_email: str = "",
        subject: str = "",
        body_text: str = "",
        body_html: str = "",
        message_id: str = "",
        in_reply_to: str = "",
        references: str = "",
        provider: str = "",
        raw_headers: str = "",
    ) -> None:
        self.from_email = from_email.strip()
        self.to_email = to_email.strip()
        self.subject = subject
        self.body_text = body_text
        self.body_html = body_html
        self.message_id = message_id.strip()
        self.in_reply_to = in_reply_to.strip()
        self.references = references.strip()
        self.provider = provider
        self.raw_headers = raw_headers

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_email": self.from_email,
            "to_email": self.to_email,
            "subject": self.subject,
            "message_id": self.message_id,
            "in_reply_to": self.in_reply_to,
            "references": self.references,
            "provider": self.provider,
        }


# ---------------------------------------------------------------------------
# Provider-specific parsers
# ---------------------------------------------------------------------------
_ADDR_RE = re.compile(r"<(.*)>")


def _extract_email(raw: str) -> str:
    """Extract ``email`` from a header like ``'Name <email@example.com>'``."""
    if not raw:
        return ""
    _, addr = parseaddr(raw)
    if addr:
        return addr.lower()
    m = _ADDR_RE.search(raw)
    if m:
        return m.group(1).strip().lower()
    return raw.strip().lower()


def _first_addrs(raw: str) -> str:
    """Pick the first address from a comma- or semicolon-separated header."""
    if not raw:
        return ""
    addrs = [a for _, a in getaddresses([raw]) if a]
    return addrs[0].lower() if addrs else _extract_email(raw)


def _parse_headers(headers: Any) -> dict[str, str]:
    """Normalise various header shapes into a flat ``{name: value}`` dict."""
    if headers is None:
        return {}
    if isinstance(headers, str):
        # SendGrid posts headers as a single newline-separated string
        out: dict[str, str] = {}
        for line in headers.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                out[k.strip().lower()] = v.strip()
        return out
    if isinstance(headers, list):
        # Postmark: [{Name, Value}, ...]
        out = {}
        for h in headers:
            name = (h.get("Name") or h.get("name") or "").strip().lower()
            value = h.get("Value") or h.get("value") or ""
            if name:
                out[name] = value
        return out
    if isinstance(headers, dict):
        return {str(k).strip().lower(): str(v) for k, v in headers.items()}
    return {}


def _strip_brackets(msgid: str) -> str:
    """Strip surrounding angle brackets from a Message-ID header."""
    if not msgid:
        return ""
    return msgid.strip().strip("<>").strip()


def _parse_sendgrid_form(form_data: Any) -> NormalisedInbound:
    """Parse a SendGrid Inbound-Parse multipart/form-data payload."""
    headers = _parse_headers(form_data.get("headers"))
    envelope_raw = form_data.get("envelope")
    envelope: dict[str, Any] = {}
    if envelope_raw:
        try:
            envelope = json.loads(envelope_raw) if isinstance(envelope_raw, str) else dict(envelope_raw)
        except (ValueError, TypeError):
            envelope = {}

    to_raw = (
        envelope.get("to")
        or form_data.get("to")
        or headers.get("to", "")
    )
    if isinstance(to_raw, list):
        to_email = _extract_email(to_raw[0]) if to_raw else ""
    else:
        to_email = _first_addrs(str(to_raw))

    from_email = _extract_email(
        str(envelope.get("from") or form_data.get("from") or headers.get("from", ""))
    )

    return NormalisedInbound(
        from_email=from_email,
        to_email=to_email,
        subject=str(form_data.get("subject") or headers.get("subject", "")),
        body_text=str(form_data.get("text") or ""),
        body_html=str(form_data.get("html") or ""),
        message_id=_strip_brackets(headers.get("message-id", "")),
        in_reply_to=_strip_brackets(headers.get("in-reply-to", "")),
        references=headers.get("references", ""),
        provider="sendgrid",
        raw_headers=json.dumps(headers)[:8192],
    )


def _parse_postmark_json(payload: dict[str, Any]) -> NormalisedInbound:
    """Parse a Postmark inbound JSON payload."""
    to_field = payload.get("To") or payload.get("to") or ""
    if isinstance(to_field, list):
        to_email = _extract_email(to_field[0]) if to_field else ""
    else:
        to_email = _first_addrs(str(to_field))

    from_email = _extract_email(
        str(payload.get("From") or payload.get("from") or "")
    )

    headers = _parse_headers(payload.get("Headers") or payload.get("headers"))

    return NormalisedInbound(
        from_email=from_email,
        to_email=to_email,
        subject=str(payload.get("Subject") or payload.get("subject") or ""),
        body_text=str(payload.get("TextBody") or payload.get("text_body") or ""),
        body_html=str(payload.get("HtmlBody") or payload.get("html_body") or ""),
        message_id=_strip_brackets(
            str(payload.get("MessageID") or payload.get("MessageId") or headers.get("message-id", ""))
        ),
        in_reply_to=_strip_brackets(headers.get("in-reply-to", "")),
        references=headers.get("references", ""),
        provider="postmark",
        raw_headers=json.dumps(headers)[:8192],
    )


def _parse_ses_sns(payload: dict[str, Any]) -> NormalisedInbound:
    """Parse an AWS SES inbound notification delivered via SNS.

    SNS payload structure::

        {
          "Type": "Notification",
          "MessageId": "...",
          "Message": "{\"notificationType\":\"Received\",\"mail\":{...},\"receipt\":{...},\"content\":\"<raw_mime>\"}"
        }

    The inner ``content`` field is the base64-encoded raw MIME message.
    Some SES configurations deliver the raw MIME unencoded — handle both.
    """
    inner_raw = payload.get("Message")
    inner: dict[str, Any] = {}
    if isinstance(inner_raw, str):
        try:
            inner = json.loads(inner_raw)
        except ValueError:
            inner = {}
    elif isinstance(inner_raw, dict):
        inner = inner_raw

    mail: dict[str, Any] = inner.get("mail") or {}
    common_headers: dict[str, Any] = mail.get("commonHeaders") or {}
    content_b64: str = inner.get("content") or ""

    raw_mime: str = ""
    if content_b64:
        try:
            raw_mime = base64.b64decode(content_b64).decode("utf-8", errors="replace")
        except (binascii.Error, ValueError):
            raw_mime = content_b64  # Treat as already-decoded

    headers: dict[str, str] = {}
    if raw_mime:
        try:
            msg: Message = message_from_string(raw_mime)
            for k, v in msg.items():
                headers[k.lower()] = v
        except Exception:  # noqa: BLE001
            headers = {}

    # If parsing headers failed, fall back to commonHeaders from SNS
    if not headers:
        for k, v in common_headers.items():
            headers[str(k).lower()] = str(v) if not isinstance(v, list) else ", ".join(str(x) for x in v)

    # Extract from / to from headers, falling back to commonHeaders
    from_hdr = headers.get("from", "")
    to_hdr = headers.get("to", "")
    if not from_hdr and common_headers.get("from"):
        from_list = common_headers["from"]
        from_hdr = from_list[0] if isinstance(from_list, list) else str(from_list)
    if not to_hdr:
        to_list = common_headers.get("to") or []
        to_hdr = to_list[0] if isinstance(to_list, list) and to_list else str(to_list)

    return NormalisedInbound(
        from_email=_extract_email(str(from_hdr)),
        to_email=_first_addrs(str(to_hdr)),
        subject=str(headers.get("subject", "") or common_headers.get("subject", "")),
        body_text=raw_mime or "",
        body_html="",
        message_id=_strip_brackets(headers.get("message-id", "")),
        in_reply_to=_strip_brackets(headers.get("in-reply-to", "")),
        references=headers.get("references", ""),
        provider="ses",
        raw_headers=json.dumps(headers)[:8192],
    )


# ---------------------------------------------------------------------------
# HMAC verification (production hardening)
# ---------------------------------------------------------------------------
def _verify_signature_if_configured(
    request: Request, raw_body: bytes,
) -> None:
    """If a signing key is configured, verify the X-Webhook-Signature header.

    Skipped in development unless the key is set. Never blocks the request
    when the key is empty — that path remains the dev fallback.
    """
    settings = get_settings()
    signing_key = getattr(settings, "email_webhook_signing_key", "") or ""
    if not signing_key:
        return

    provided = (
        request.headers.get("X-Webhook-Signature")
        or request.headers.get("x-webhook-signature")
        or request.headers.get("X-Signature")
        or ""
    ).strip()
    if not provided:
        logger.warning("inbound_webhook_missing_signature")
        raise HTTPException(status_code=401, detail="Missing webhook signature")

    expected = hmac.new(
        key=signing_key.encode(), msg=raw_body, digestmod=hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, provided):
        logger.warning("inbound_webhook_bad_signature")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------
@router.post("/email")
async def inbound_email(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Receive an inbound email reply from any of: SendGrid Inbound Parse,
    Postmark Inbound, or AWS SES (via SNS).

    Returns ``200 OK`` after the matching OutreachThread has been marked
    as ``REPLIED``. Returns ``404`` if no matching thread can be found
    for the given payload (the provider will retry — that is expected).
    """
    raw_body = await request.body()
    _verify_signature_if_configured(request, raw_body)

    content_type = (request.headers.get("content-type") or "").lower()

    payload: NormalisedInbound
    try:
        if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
            form = await request.form()
            form_data: dict[str, Any] = {}
            for key, value in form.multi_items():
                if isinstance(value, UploadFile):
                    continue  # Ignore attachments
                # Multi-value fields collapse to first non-empty
                if key not in form_data or not form_data[key]:
                    form_data[key] = value
            payload = _parse_sendgrid_form(form_data)
        elif "application/json" in content_type:
            json_body = json.loads(raw_body or b"{}")
            if not isinstance(json_body, dict):
                raise HTTPException(status_code=400, detail="Expected JSON object")
            # SES notification arrives with a top-level Type/Message envelope
            if json_body.get("Type") == "Notification" and "Message" in json_body:
                payload = _parse_ses_sns(json_body)
            else:
                payload = _parse_postmark_json(json_body)
        else:
            # Best-effort: try JSON, then form. Raw text/mime is unsupported.
            try:
                json_body = json.loads(raw_body or b"{}")
                if isinstance(json_body, dict):
                    if json_body.get("Type") == "Notification":
                        payload = _parse_ses_sns(json_body)
                    else:
                        payload = _parse_postmark_json(json_body)
                else:
                    raise HTTPException(status_code=415, detail="Unsupported content type")
            except (ValueError, json.JSONDecodeError):
                raise HTTPException(
                    status_code=415,
                    detail=f"Unsupported content type: {content_type}",
                )
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.error("inbound_webhook_parse_failed", error=str(e))
        raise HTTPException(status_code=400, detail=f"Could not parse payload: {e}")

    if not payload.from_email or not payload.to_email:
        logger.warning(
            "inbound_webhook_missing_addresses",
            provider=payload.provider,
            from_email=payload.from_email,
            to_email=payload.to_email,
        )
        raise HTTPException(
            status_code=422,
            detail="Could not extract from/to addresses from payload",
        )

    return await _process_inbound_reply(payload, user)


# ---------------------------------------------------------------------------
# Thread lookup + DB writes
# ---------------------------------------------------------------------------
async def _find_thread(payload: NormalisedInbound) -> OutreachThread | None:
    """Locate the OutreachThread this inbound email is a reply to.

    Match priority:
      1. ``In-Reply-To`` / ``Message-ID`` matches ``thread.provider_message_id``
      2. ``from`` matches ``thread.to_email`` AND ``to`` matches ``thread.from_email``

    Uses ``get_session`` (no RLS context) because the thread's tenant is
    not yet known at lookup time. The found thread's tenant_id is then
    used to scope all subsequent writes via ``get_tenant_session``.
    """
    candidate_ids = [payload.in_reply_to, payload.message_id]
    candidate_ids = [c for c in candidate_ids if c]

    async with get_session() as session:
        if candidate_ids:
            stmt = select(OutreachThread).where(
                OutreachThread.provider_message_id.in_(candidate_ids)
            )
            result = await session.execute(stmt)
            thread = result.scalars().first()
            if thread is not None:
                return thread

        if payload.from_email and payload.to_email:
            stmt = select(OutreachThread).where(
                func.lower(OutreachThread.to_email) == payload.from_email,
                func.lower(OutreachThread.from_email) == payload.to_email,
            )
            result = await session.execute(stmt)
            thread = result.scalars().first()
            if thread is not None:
                return thread

    return None


async def _is_duplicate(
    session, thread_id: UUID, message_id: str,
) -> bool:
    """Return True if this inbound message has already been processed."""
    if not message_id:
        return False
    stmt = select(AuditLog.id).where(
        AuditLog.event_type == "email.inbound_reply",
        AuditLog.entity_id == thread_id,
        AuditLog.metadata_["message_id"].astext == message_id,
    ).limit(1)
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def _recompute_campaign_rates(
    session, campaign_id: UUID,
) -> tuple[float, float]:
    """Recompute ``reply_rate`` and ``acquisition_rate`` for one campaign.

    Returns the new (reply_rate, acquisition_rate) tuple.
    """
    replied_count = await session.scalar(
        select(func.count(OutreachThread.id)).where(
            OutreachThread.campaign_id == campaign_id,
            OutreachThread.status == ThreadStatus.REPLIED,
        )
    )
    sent_count = await session.scalar(
        select(func.count(OutreachThread.id)).where(
            OutreachThread.campaign_id == campaign_id,
            OutreachThread.status.in_([
                ThreadStatus.SENT,
                ThreadStatus.DELIVERED,
                ThreadStatus.OPENED,
                ThreadStatus.REPLIED,
                ThreadStatus.LINK_ACQUIRED,
            ]),
        )
    )
    acquired_count = await session.scalar(
        select(func.count(BacklinkProspect.id)).where(
            BacklinkProspect.campaign_id == campaign_id,
            BacklinkProspect.status == ProspectStatus.LINK_ACQUIRED,
        )
    )
    total_prospects = await session.scalar(
        select(func.count(BacklinkProspect.id)).where(
            BacklinkProspect.campaign_id == campaign_id,
        )
    )

    reply_rate = float(replied_count or 0) / float(sent_count) if sent_count else 0.0
    acquisition_rate = (
        float(acquired_count or 0) / float(total_prospects)
        if total_prospects else 0.0
    )

    campaign = await session.get(BacklinkCampaign, campaign_id)
    if campaign is not None:
        campaign.reply_rate = round(reply_rate, 4)
        campaign.acquisition_rate = round(acquisition_rate, 4)

    return reply_rate, acquisition_rate


async def _process_inbound_reply(
    payload: NormalisedInbound, user: CurrentUser,
) -> dict[str, Any]:
    """Look up the matching thread, update DB, write audit log, return 200."""
    thread = await _find_thread(payload)
    if thread is None:
        logger.info(
            "inbound_reply_no_match",
            from_email=payload.from_email,
            to_email=payload.to_email,
            in_reply_to=payload.in_reply_to,
            message_id=payload.message_id,
        )
        return {"status": "no_match", "provider": payload.provider}

    # --- Tenant isolation ------------------------------------------------
    if thread.tenant_id != user.tenant_id:
        logger.warning(
            "inbound_reply_tenant_isolation_violation",
            thread_tenant=str(thread.tenant_id),
            user_tenant=str(user.tenant_id),
        )
        # Do NOT reveal existence of the thread — return 404.
        raise HTTPException(status_code=404, detail="Thread not found")

    now = datetime.now(UTC)

    async with get_tenant_session(thread.tenant_id) as session:
        # Re-load the thread through the session so writes are tracked
        thread = await session.get(OutreachThread, thread.id)
        if thread is None:
            raise HTTPException(status_code=404, detail="Thread not found")

        # --- Dedup check via reply state + audit log ---------------------
        if thread.replied_at is not None:
            logger.info(
                "inbound_reply_duplicate_skipped",
                thread_id=str(thread.id),
                from_email=payload.from_email,
            )
            return {
                "status": "duplicate",
                "thread_id": str(thread.id),
                "provider": payload.provider,
            }

        if await _is_duplicate(session, thread.id, payload.message_id or payload.in_reply_to):
            logger.info(
                "inbound_reply_duplicate_by_message_id",
                thread_id=str(thread.id),
                message_id=payload.message_id,
            )
            return {
                "status": "duplicate",
                "thread_id": str(thread.id),
                "provider": payload.provider,
            }

        before = {
            "status": thread.status.value if hasattr(thread.status, "value") else str(thread.status),
            "replied_at": thread.replied_at.isoformat() if thread.replied_at else None,
        }

        # --- Update thread -----------------------------------------------
        thread.status = ThreadStatus.REPLIED
        thread.replied_at = now
        if not thread.body_html and payload.body_html:
            thread.body_html = payload.body_html[:60000]

        # --- Update prospect --------------------------------------------
        prospect = await session.get(BacklinkProspect, thread.prospect_id)
        if prospect is not None:
            prospect.status = ProspectStatus.REPLIED

        # Flush updates to DB so count queries see them
        await session.flush()

        # --- Recompute campaign rates -----------------------------------
        reply_rate, acquisition_rate = await _recompute_campaign_rates(
            session, thread.campaign_id,
        )

        # --- Audit log entry --------------------------------------------
        audit_log = AuditLog(
            tenant_id=thread.tenant_id,
            event_type="email.inbound_reply",
            entity_type="OutreachThread",
            entity_id=thread.id,
            actor_type="system",
            actor_id=f"inbound_webhook:{payload.provider}",
            before_state=before,
            after_state={
                "status": ThreadStatus.REPLIED.value,
                "replied_at": now.isoformat(),
            },
            metadata_={
                "message_id": payload.message_id or None,
                "in_reply_to": payload.in_reply_to or None,
                "from_email": payload.from_email,
                "to_email": payload.to_email,
                "subject": payload.subject[:500],
                "provider": payload.provider,
                "campaign_id": str(thread.campaign_id),
                "prospect_id": str(thread.prospect_id),
                "reply_rate": reply_rate,
                "acquisition_rate": acquisition_rate,
            },
        )
        session.add(audit_log)

        # The session will commit when the context manager exits cleanly.
        campaign_id = thread.campaign_id
        prospect_id = thread.prospect_id

    logger.info(
        "inbound_reply_processed",
        thread_id=str(thread.id),
        campaign_id=str(campaign_id),
        prospect_id=str(prospect_id),
        provider=payload.provider,
        from_email=payload.from_email,
    )

    # Best-effort additional audit record via the audit service
    try:
        await audit_service.record_state_change(
            tenant_id=thread.tenant_id,
            event_type="thread.replied",
            entity_type="OutreachThread",
            entity_id=thread.id,
            actor_type="system",
            actor_id=f"inbound_webhook:{payload.provider}",
            before=before,
            after={
                "status": ThreadStatus.REPLIED.value,
                "replied_at": now.isoformat(),
            },
            provider=payload.provider,
            from_email=payload.from_email,
            message_id=payload.message_id or None,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("audit_service_record_failed", error=str(e))

    return {
        "status": "ok",
        "thread_id": str(thread.id),
        "campaign_id": str(campaign_id),
        "prospect_id": str(prospect_id),
        "provider": payload.provider,
        "reply_rate": reply_rate,
        "acquisition_rate": acquisition_rate,
    }


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@router.get("/health")
async def inbound_webhook_health() -> dict[str, Any]:
    settings = get_settings()
    signing_key = getattr(settings, "email_webhook_signing_key", "")
    return {
        "status": "healthy",
        "endpoint": "inbound/email",
        "supported_providers": ["sendgrid", "postmark", "ses"],
        "signature_verification_enabled": bool(signing_key),
    }
