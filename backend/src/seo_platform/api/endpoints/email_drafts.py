"""
Email Drafts API
Supports: create, read, update, delete, list drafts
"""

from __future__ import annotations
from seo_platform.core.auth import get_validated_tenant_id
import json
from datetime import datetime, timezone
from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel

router = APIRouter()

class DraftCreate(BaseModel):
    subject: str
    body_html: str
    template_id: str | None = None
    to_email: str | None = None
    variables: dict[str, str] | None = None

class DraftUpdate(BaseModel):
    subject: str | None = None
    body_html: str | None = None
    to_email: str | None = None
    variables: dict[str, str] | None = None

@router.get("", response_model=dict)
async def list_drafts(
    tenant_id: UUID = Depends(get_validated_tenant_id),
    status: str = "draft",
):
    """List email drafts."""
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        result = await session.execute(text("""
            SELECT id, tenant_id, template_id, subject, body_html, to_email,
                   variables, status, created_at, updated_at
            FROM email_drafts
            WHERE tenant_id = :tenant_id AND status = :status
            ORDER BY updated_at DESC
        """), {"tenant_id": str(tenant_id), "status": status})

        drafts = []
        for row in result.fetchall():
            drafts.append({
                "id": str(row[0]),
                "tenant_id": str(row[1]),
                "template_id": row[2],
                "subject": row[3],
                "body_html": row[4],
                "to_email": row[5],
                "variables": json.loads(row[6]) if isinstance(row[6], str) else (row[6] or {}),
                "status": row[7],
                "created_at": row[8].isoformat() if row[8] else None,
                "updated_at": row[9].isoformat() if row[9] else None,
            })

        return {"success": True, "data": drafts, "total": len(drafts)}

@router.post("", response_model=dict)
async def create_draft(
    tenant_id: UUID = Depends(get_validated_tenant_id),
    draft: DraftCreate = None,
):
    """Create a new email draft."""
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    if not draft:
        raise HTTPException(status_code=400, detail="Draft data required")

    async with get_session() as session:
        result = await session.execute(text("""
            INSERT INTO email_drafts
            (tenant_id, template_id, subject, body_html, to_email, variables, status, created_at, updated_at)
            VALUES (:tenant_id, :template_id, :subject, :body_html, :to_email, :variables, 'draft', :created_at, :updated_at)
            RETURNING id
        """), {
            "tenant_id": str(tenant_id),
            "template_id": draft.template_id,
            "subject": draft.subject,
            "body_html": draft.body_html,
            "to_email": draft.to_email,
            "variables": json.dumps(draft.variables or {}),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        })
        await session.commit()
        draft_id = result.scalar()

        return {"success": True, "message": "Draft created", "id": str(draft_id)}

@router.get("/{draft_id}", response_model=dict)
async def get_draft(
    draft_id: str,
    tenant_id: UUID = Depends(get_validated_tenant_id),
):
    """Get a single email draft."""
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        result = await session.execute(text("""
            SELECT id, tenant_id, template_id, subject, body_html, to_email,
                   variables, status, created_at, updated_at
            FROM email_drafts
            WHERE id = :draft_id AND tenant_id = :tenant_id
        """), {"draft_id": draft_id, "tenant_id": str(tenant_id)})

        row = result.first()
        if not row:
            raise HTTPException(status_code=404, detail="Draft not found")

        return {"success": True, "data": {
            "id": str(row[0]),
            "tenant_id": str(row[1]),
            "template_id": row[2],
            "subject": row[3],
            "body_html": row[4],
            "to_email": row[5],
            "variables": row[6] or {},
            "status": row[7],
            "created_at": row[8].isoformat() if row[8] else None,
            "updated_at": row[9].isoformat() if row[9] else None,
        }}

@router.put("/{draft_id}", response_model=dict)
async def update_draft(
    draft_id: str,
    tenant_id: UUID = Depends(get_validated_tenant_id),
    draft: DraftUpdate = None,
):
    """Update an email draft."""
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    if not draft:
        raise HTTPException(status_code=400, detail="Draft data required")

    async with get_session() as session:
        fields = []
        params = {"draft_id": draft_id, "tenant_id": str(tenant_id)}

        if draft.subject is not None:
            fields.append("subject = :subject")
            params["subject"] = draft.subject
        if draft.body_html is not None:
            fields.append("body_html = :body_html")
            params["body_html"] = draft.body_html
        if draft.to_email is not None:
            fields.append("to_email = :to_email")
            params["to_email"] = draft.to_email
        if draft.variables is not None:
            fields.append("variables = :variables")
            params["variables"] = json.dumps(draft.variables)

        if not fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        fields.append("updated_at = :updated_at")
        params["updated_at"] = datetime.now(timezone.utc)

        await session.execute(text(f"""
            UPDATE email_drafts
            SET {', '.join(fields)}
            WHERE id = :draft_id AND tenant_id = :tenant_id
        """), params)
        await session.commit()

        return {"success": True, "message": "Draft updated"}

@router.delete("/{draft_id}", response_model=dict)
async def delete_draft(
    draft_id: str,
    tenant_id: UUID = Depends(get_validated_tenant_id),
):
    """Delete an email draft."""
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        await session.execute(text("""
            DELETE FROM email_drafts
            WHERE id = :draft_id AND tenant_id = :tenant_id
        """), {"draft_id": draft_id, "tenant_id": str(tenant_id)})
        await session.commit()

        return {"success": True, "message": "Draft deleted"}
