"""
SEO Platform — Audit Logger Service
====================================
Centralized audit logging utility for recording important actions
across the platform. Other endpoints call `audit_logger.log()` to
create append-only entries in the audit_ledger table.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text

from seo_platform.core.database import get_session
from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


class AuditLogger:
    """Append-only audit trail writer.

    Each call inserts a row into the audit_ledger table. The table's
    database trigger prevents UPDATE/DELETE, making entries immutable.
    """

    async def log(
        self,
        tenant_id: str,
        user_id: str,
        action: str,
        entity_type: str,
        entity_id: str,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
        reason: str = "",
    ) -> None:
        """Write a single audit entry.

        Parameters
        ----------
        tenant_id : str
            UUID of the tenant this action belongs to.
        user_id : str
            UUID of the user (or "system") performing the action.
        action : str
            Action name, e.g. ``"client.create"``, ``"campaign.launch"``.
        entity_type : str
            Entity kind, e.g. ``"client"``, ``"campaign"``, ``"credential"``.
        entity_id : str
            UUID of the entity acted upon.
        before : dict, optional
            State snapshot before the action.
        after : dict, optional
            State snapshot after the action.
        reason : str, optional
            Human-readable reason for the action.
        """
        try:
            entry_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)

            # Derive a risk level from the action name
            risk_level = "low"
            if any(kw in action for kw in ("delete", "archive", "lock", "reject")):
                risk_level = "high"
            elif any(kw in action for kw in ("update", "launch", "approve", "unlock")):
                risk_level = "medium"

            # Build a human-readable summary
            summary = f"{action} on {entity_type} {entity_id}"
            if reason:
                summary += f": {reason}"

            # Build input/output snapshots for replayability
            input_snapshot = {"action": action, "entity_type": entity_type, "entity_id": entity_id}
            if before:
                input_snapshot["before"] = before
            output_snapshot = {}
            if after:
                output_snapshot["after"] = after

            async with get_session() as sess:
                await sess.execute(
                    text("""
                        INSERT INTO audit_ledger (
                            id, tenant_id, action_name, actor_id, actor_type,
                            target_type, target_id, summary,
                            input_snapshot, output_snapshot,
                            decision, risk_level, semantic_hash,
                            created_at, immutable_at
                        ) VALUES (
                            :id, :tenant_id, :action_name, :actor_id, :actor_type,
                            :target_type, :target_id, :summary,
                            :input_snapshot, :output_snapshot,
                            :decision, :risk_level, :semantic_hash,
                            :created_at, :immutable_at
                        )
                    """),
                    {
                        "id": entry_id,
                        "tenant_id": tenant_id,
                        "action_name": action,
                        "actor_id": user_id,
                        "actor_type": "user" if user_id != "system" else "system",
                        "target_type": entity_type,
                        "target_id": entity_id,
                        "summary": summary,
                        "input_snapshot": str(input_snapshot),
                        "output_snapshot": str(output_snapshot),
                        "decision": None,
                        "risk_level": risk_level,
                        "semantic_hash": "0",
                        "created_at": now,
                        "immutable_at": now,
                    },
                )
                await sess.commit()

            logger.debug(
                "audit_entry_created",
                entry_id=entry_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
            )
        except Exception as e:
            # Audit logging should never crash the calling endpoint.
            # Log the failure and continue.
            logger.error(
                "audit_log_failed",
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                error=str(e),
            )


# Singleton for import by other modules
audit_logger = AuditLogger()
