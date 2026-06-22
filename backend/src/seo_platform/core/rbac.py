"""
RBAC Middleware — Phase 12G.3
==============================
Role-based access control for all API endpoints.

Roles (hierarchical):
  super_admin  — Full access, including tenant management
  admin        — Access to all features within tenant
  manager      — CRUD on campaigns, approvals, reports; no system settings
  operator     — Execute workflows, view dashboards, manage own tasks
  viewer       — Read-only access to dashboards and reports

Permission matrix enforced via @requires_permission decorator or
RequirePermission FastAPI dependency.
"""

from __future__ import annotations

from enum import Enum
from functools import wraps
from typing import Callable

from fastapi import Depends, HTTPException, Request

from seo_platform.core.auth import get_current_user
from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


class Role(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MANAGER = "manager"
    OPERATOR = "operator"
    VIEWER = "viewer"


ROLE_HIERARCHY: dict[Role, int] = {
    Role.VIEWER: 0,
    Role.OPERATOR: 1,
    Role.MANAGER: 2,
    Role.ADMIN: 3,
    Role.SUPER_ADMIN: 4,
}

PERMISSIONS: dict[str, list[Role]] = {
    # System
    "system:read": [Role.SUPER_ADMIN, Role.ADMIN],
    "system:write": [Role.SUPER_ADMIN, Role.ADMIN],
    # Audit
    "audit:read": [Role.SUPER_ADMIN, Role.ADMIN, Role.MANAGER, Role.OPERATOR, Role.VIEWER],
    # Customers
    "customers:read": [Role.SUPER_ADMIN, Role.ADMIN, Role.MANAGER, Role.OPERATOR, Role.VIEWER],
    "customers:write": [Role.SUPER_ADMIN, Role.ADMIN, Role.MANAGER],
    "customers:delete": [Role.SUPER_ADMIN, Role.ADMIN],
    # Campaigns
    "campaigns:read": [Role.SUPER_ADMIN, Role.ADMIN, Role.MANAGER, Role.OPERATOR, Role.VIEWER],
    "campaigns:write": [Role.SUPER_ADMIN, Role.ADMIN, Role.MANAGER],
    # Approvals
    "approvals:read": [Role.SUPER_ADMIN, Role.ADMIN, Role.MANAGER, Role.OPERATOR, Role.VIEWER],
    "approvals:write": [Role.SUPER_ADMIN, Role.ADMIN, Role.MANAGER],
    "approvals:approve": [Role.SUPER_ADMIN, Role.ADMIN, Role.MANAGER],
    # Automations
    "automation:read": [Role.SUPER_ADMIN, Role.ADMIN, Role.MANAGER, Role.OPERATOR, Role.VIEWER],
    "automation:write": [Role.SUPER_ADMIN, Role.ADMIN, Role.MANAGER],
    # Reports
    "reports:read": [Role.SUPER_ADMIN, Role.ADMIN, Role.MANAGER, Role.OPERATOR, Role.VIEWER],
    "reports:write": [Role.SUPER_ADMIN, Role.ADMIN, Role.MANAGER],
    # Communications
    "communications:read": [Role.SUPER_ADMIN, Role.ADMIN, Role.MANAGER, Role.OPERATOR],
    "communications:write": [Role.SUPER_ADMIN, Role.ADMIN, Role.MANAGER, Role.OPERATOR],
    # Executive
    "executive:read": [Role.SUPER_ADMIN, Role.ADMIN, Role.MANAGER, Role.VIEWER],
    # Planning
    "planning:read": [Role.SUPER_ADMIN, Role.ADMIN, Role.MANAGER, Role.OPERATOR, Role.VIEWER],
    "planning:write": [Role.SUPER_ADMIN, Role.ADMIN, Role.MANAGER],
    "planning:execute": [Role.SUPER_ADMIN, Role.ADMIN, Role.MANAGER],
    # Goals
    "goal:read": [Role.SUPER_ADMIN, Role.ADMIN, Role.MANAGER, Role.OPERATOR, Role.VIEWER],
    "goal:write": [Role.SUPER_ADMIN, Role.ADMIN, Role.MANAGER],
    # Memory
    "memory:read": [Role.SUPER_ADMIN, Role.ADMIN, Role.MANAGER, Role.OPERATOR, Role.VIEWER],
    "memory:write": [Role.SUPER_ADMIN, Role.ADMIN, Role.MANAGER],
    "memory:delete": [Role.SUPER_ADMIN, Role.ADMIN],
    # Agents
    "agent:read": [Role.SUPER_ADMIN, Role.ADMIN, Role.MANAGER, Role.OPERATOR, Role.VIEWER],
    "agent:write": [Role.SUPER_ADMIN, Role.ADMIN, Role.MANAGER],
    "agent:delete": [Role.SUPER_ADMIN, Role.ADMIN],
    # Executions
    "execution:read": [Role.SUPER_ADMIN, Role.ADMIN, Role.MANAGER, Role.OPERATOR, Role.VIEWER],
    "execution:write": [Role.SUPER_ADMIN, Role.ADMIN, Role.MANAGER],
    # Action definitions
    "action:read": [Role.SUPER_ADMIN, Role.ADMIN, Role.MANAGER, Role.OPERATOR, Role.VIEWER],
    "action:write": [Role.SUPER_ADMIN, Role.ADMIN, Role.MANAGER],
    "action:delete": [Role.SUPER_ADMIN, Role.ADMIN],
    # Workflow definitions
    "workflow:read": [Role.SUPER_ADMIN, Role.ADMIN, Role.MANAGER, Role.OPERATOR, Role.VIEWER],
    "workflow:write": [Role.SUPER_ADMIN, Role.ADMIN, Role.MANAGER],
    # User management (Phase 2.5.1)
    "users:read": [Role.SUPER_ADMIN, Role.ADMIN, Role.MANAGER],
    "users:write": [Role.SUPER_ADMIN, Role.ADMIN],
}


def get_user_role(request: Request) -> Role:
    """Extract role from request state (set by auth middleware)."""
    return getattr(request.state, "role", Role.VIEWER)


def requires_permission(permission: str):
    """Decorator to enforce permission on an endpoint.

    Usage:
        @router.get("/campaigns")
        @requires_permission("campaigns:read")
        async def list_campaigns(...): ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from args (FastAPI dependency injection)
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                for _, v in kwargs.items():
                    if isinstance(v, Request):
                        request = v
                        break

            if request:
                role = get_user_role(request)
                allowed_roles = PERMISSIONS.get(permission, [Role.SUPER_ADMIN])
                if role not in allowed_roles and ROLE_HIERARCHY[role] < ROLE_HIERARCHY[allowed_roles[-1]]:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Permission denied: {permission} requires one of {[r.value for r in allowed_roles]}",
                    )
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def check_permission(role: Role, permission: str) -> bool:
    """Check if a role has a specific permission."""
    allowed_roles = PERMISSIONS.get(permission, [Role.SUPER_ADMIN])
    return role in allowed_roles or ROLE_HIERARCHY.get(role, 0) >= ROLE_HIERARCHY.get(allowed_roles[-1], 0)


# ---------------------------------------------------------------------------
# FastAPI dependency — parameterised permission check
# ---------------------------------------------------------------------------

_ROLE_MAP: dict[str, Role] = {e.value: e for e in Role}


async def _audit_rbac_denial(user, permission: str) -> None:
    """Best‑effort audit log entry for an RBAC denial."""
    import uuid
    from datetime import datetime

    from seo_platform.core.database import get_tenant_session
    from seo_platform.core.metrics import seo_rbac_denials_total, seo_security_events_total
    from seo_platform.models.audit_ledger import ActorType, AuditLedgerEntry, DecisionType

    # Emit Prometheus metrics
    seo_rbac_denials_total.labels(permission=permission, role=user.role).inc()
    seo_security_events_total.labels(event_type="rbac_denial", severity="medium").inc()

    try:
        async with get_tenant_session(user.tenant_id) as session:
            entry = AuditLedgerEntry(
                tenant_id=user.tenant_id,
                action_name=f"rbac_denied:{permission}",
                actor_id=user.id,
                actor_type=ActorType.USER.value,
                target_type="rbac",
                target_id=uuid.UUID(int=0),
                summary=f"RBAC denied: {permission} for role {user.role}",
                input_snapshot={"permission": permission, "role": user.role},
                output_snapshot={"decision": "denied"},
                decision=DecisionType.REJECTED,
                risk_level="medium",
                immutable_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
            )
            session.add(entry)
    except Exception:
        logger.warning("Failed to audit RBAC denial (non‑fatal)", exc_info=True)


class RequirePermission:
    """FastAPI dependency — checks the current user has the given permission.

    Usage::

        @router.get("/plans")
        async def list_plans(
            ...,
            user = Depends(RequirePermission("planning:read")),
        ): ...
    """

    def __init__(self, permission: str) -> None:
        self.permission = permission

    async def __call__(self, user = Depends(get_current_user)):  # noqa: B008
        role = _ROLE_MAP.get(user.role)
        if role is None or not check_permission(role, self.permission):
            await _audit_rbac_denial(user, self.permission)
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {self.permission} requires one of "
                f"{[r.value for r in PERMISSIONS.get(self.permission, [Role.SUPER_ADMIN])]}",
            )
        return user
