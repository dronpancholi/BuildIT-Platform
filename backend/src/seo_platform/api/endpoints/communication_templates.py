"""
Communication Templates API
Supports: create, read, update, delete, duplicate, archive
Categories: outreach, guest_post, link_insertion, partnership, followup, report
"""

from __future__ import annotations
from seo_platform.core.auth import get_validated_tenant_id
from datetime import datetime, timezone
import json
from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()

class TemplateCreate(BaseModel):
    title: str
    category: str
    subject: str
    body: str
    variables: List[str] = Field(default_factory=list)

class TemplateResponse(BaseModel):
    id: str
    title: str
    category: str
    subject: str
    body: str
    variables: List[str]
    is_archived: bool
    created_at: str
    updated_at: str

@router.get("", response_model=dict)
async def list_templates(
    tenant_id: UUID = Depends(get_validated_tenant_id),
    category: str | None = None,
    include_archived: bool = False,
):
    """List all templates with optional filters."""
    from seo_platform.core.database import get_session
    from sqlalchemy import text
    
    async with get_session() as session:
        query = """
        SELECT id, title, category, subject, body, variables, is_archived, created_at, updated_at
        FROM communication_templates
        WHERE tenant_id = :tenant_id
        AND is_archived = :include_archived
        """
        params = {"tenant_id": str(tenant_id), "include_archived": include_archived}
        
        if category:
            query += " AND category = :category"
            params["category"] = category
            
        result = await session.execute(text(query), params)
        templates = []
        for row in result.fetchall():
            templates.append({
                "id": str(row[0]),
                "title": row[1],
                "category": row[2],
                "subject": row[3],
                "body": row[4],
                "variables": json.loads(row[5]) if isinstance(row[5], str) else (row[5] or []),
                "is_archived": row[6],
                "created_at": row[7].isoformat() if row[7] else None,
                "updated_at": row[8].isoformat() if row[8] else None,
            })
        
        return {"success": True, "data": templates, "total": len(templates)}

@router.post("", response_model=dict)
async def create_template(
    tenant_id: UUID = Depends(get_validated_tenant_id),
    template: TemplateCreate = None,
):
    """Create a new communication template."""
    from seo_platform.core.database import get_session
    from sqlalchemy import text
    
    if not template:
        raise HTTPException(status_code=400, detail="Template data required")
    
    async with get_session() as session:
        await session.execute(text("""
            INSERT INTO communication_templates 
            (tenant_id, title, category, subject, body, variables, created_at, updated_at)
            VALUES (:tenant_id, :title, :category, :subject, :body, :variables, :created_at, :updated_at)
        """), {
            "tenant_id": str(tenant_id),
            "title": template.title,
            "category": template.category,
            "subject": template.subject,
            "body": template.body,
            "variables": json.dumps(template.variables),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        })
        await session.commit()
        
        return {"success": True, "message": "Template created"}

@router.post("/{template_id}/duplicate", response_model=dict)
async def duplicate_template(
    template_id: str,
    tenant_id: UUID = Depends(get_validated_tenant_id),
):
    """Duplicate an existing template."""
    from seo_platform.core.database import get_session
    from sqlalchemy import text
    
    async with get_session() as session:
        # Get original template
        result = await session.execute(text("""
            SELECT title, category, subject, body, variables
            FROM communication_templates
            WHERE id = :template_id AND tenant_id = :tenant_id
        """), {"template_id": template_id, "tenant_id": str(tenant_id)})
        
        original = result.first()
        if not original:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # Create duplicate
        await session.execute(text("""
            INSERT INTO communication_templates 
            (tenant_id, title, category, subject, body, variables, created_at, updated_at)
            VALUES (:tenant_id, :title, :category, :subject, :body, :variables, :created_at, :updated_at)
        """), {
            "tenant_id": str(tenant_id),
            "title": f"{original[0]} (Copy)",
            "category": original[1],
            "subject": original[2],
            "body": original[3],
            "variables": json.dumps(original[4]) if isinstance(original[4], (list, dict)) else original[4],
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        })
        await session.commit()
        
        return {"success": True, "message": "Template duplicated"}

@router.delete("/{template_id}", response_model=dict)
async def delete_template(
    template_id: str,
    tenant_id: UUID = Depends(get_validated_tenant_id),
):
    """Archive (soft delete) a template."""
    from seo_platform.core.database import get_session
    from sqlalchemy import text
    
    async with get_session() as session:
        await session.execute(text("""
            UPDATE communication_templates
            SET is_archived = TRUE, updated_at = :updated_at
            WHERE id = :template_id AND tenant_id = :tenant_id
        """), {
            "template_id": template_id,
            "tenant_id": str(tenant_id),
            "updated_at": datetime.now(timezone.utc),
        })
        await session.commit()
        
        return {"success": True, "message": "Template archived"}
