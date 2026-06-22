"""
Audit Logging Middleware — Phase 11.5
=======================================
Structured audit trail for all write operations.
Persists to audit_ledger table AND logs.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

SKIP_PATHS = {"/metrics", "/health", "/healthz", "/ready", "/docs", "/openapi.json", "/redoc"}
SKIP_PREFIXES = ("/api/v1/telemetry/",)

# Map paths to human-readable action descriptions
ACTION_MAP = {
    ("POST", "/clients"): "client.create",
    ("PUT", "/clients"): "client.update",
    ("PATCH", "/clients"): "client.update",
    ("DELETE", "/clients"): "client.delete",
    ("POST", "/campaigns"): "campaign.create",
    ("PUT", "/campaigns"): "campaign.update",
    ("PATCH", "/campaigns"): "campaign.update",
    ("DELETE", "/campaigns"): "campaign.delete",
    ("POST", "/campaigns"): "campaign.create",
    ("POST", "/approvals"): "approval.create",
    ("POST", "/credentials"): "credential.create",
    ("PUT", "/credentials"): "credential.update",
    ("DELETE", "/credentials"): "credential.delete",
    ("POST", "/providers"): "provider.configure",
}


def _extract_entity_id(path: str, body: dict | None) -> str | None:
    """Extract entity ID from path or body."""
    parts = path.strip("/").split("/")
    # Check if last part looks like a UUID
    for part in reversed(parts):
        if len(part) == 36 and part.count("-") == 4:
            return part
    # Check body
    if body and isinstance(body, dict):
        return body.get("id") or body.get("client_id") or body.get("campaign_id")
    return None


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Log every write operation with full context for audit trail."""

    async def dispatch(self, request: Request, call_next):
        if request.method not in WRITE_METHODS:
            return await call_next(request)
        if request.url.path in SKIP_PATHS:
            return await call_next(request)
        if any(request.url.path.startswith(p) for p in SKIP_PREFIXES):
            return await call_next(request)

        # Capture request body for audit
        body = None
        if request.method in ("POST", "PUT", "PATCH"):
            try:
                body_bytes = await request.body()
                body = json.loads(body_bytes) if body_bytes else None
            except Exception:
                body = None

        response = await call_next(request)

        # Determine action
        action = ACTION_MAP.get((request.method, request.url.path))
        if not action:
            # Generic action from method + path
            path_parts = request.url.path.strip("/").split("/")
            resource = path_parts[1] if len(path_parts) > 1 else "unknown"
            method_lower = request.method.lower()
            action = f"{resource}.{method_lower}"

        entity_id = _extract_entity_id(request.url.path, body)
        tenant_id = getattr(request.state, "tenant_id", None)
        user_id = getattr(request.state, "user_id", None)

        audit_entry = {
            "audit_id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "entity_id": entity_id,
            "request_body": body,
        }

        # Log always
        logger.info("audit_log", **{k: v for k, v in audit_entry.items() if k != "request_body"})

        # Persist to database (async, non-blocking)
        try:
            from seo_platform.core.database import get_engine as async_engine
            from sqlalchemy import text

            async with async_engine.begin() as conn:
                await conn.execute(
                    text("""
                        INSERT INTO audit_ledger_entries
                        (id, tenant_id, user_id, action, entity_type, entity_id, details, created_at)
                        VALUES (:id, :tenant_id, :user_id, :action, :entity_type, :entity_id, :details, NOW())
                    """),
                    {
                        "id": str(uuid4()),
                        "tenant_id": tenant_id,
                        "user_id": user_id,
                        "action": action,
                        "entity_type": request.url.path.strip("/").split("/")[1] if len(request.url.path.strip("/").split("/")) > 1 else "unknown",
                        "entity_id": entity_id,
                        "details": json.dumps({
                            "method": request.method,
                            "path": request.url.path,
                            "status_code": response.status_code,
                            "request_body": body,
                        }),
                    },
                )
        except Exception as e:
            logger.warning("audit_persist_failed", error=str(e))

        return response
