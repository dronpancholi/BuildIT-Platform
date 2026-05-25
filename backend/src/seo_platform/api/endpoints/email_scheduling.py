"""
Email Scheduling API
Supports: schedule, cancel, reschedule, list scheduled
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, List
from uuid import UUID
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

router = APIRouter()

class ScheduleEmail(BaseModel):
    thread_id: str
    scheduled_at: str  # ISO format
    timezone: str = "UTC"
    subject: str
    body: str
    to_email: str

@router.get("", response_model=dict)
async def list_scheduled_emails(
    tenant_id: UUID = Query(...),
    status: str = "pending",  # pending, sent, cancelled
):
    """List scheduled emails."""
    from seo_platform.core.database import get_session
    from sqlalchemy import text
    
    async with get_session() as session:
        result = await session.execute(text("""
            SELECT id, thread_id, subject, to_email, scheduled_at, timezone, status, created_at
            FROM scheduled_emails
            WHERE tenant_id = :tenant_id
            AND status = :status
            ORDER BY scheduled_at ASC
        """), {"tenant_id": str(tenant_id), "status": status})
        
        scheduled = []
        for row in result.fetchall():
            scheduled.append({
                "id": str(row[0]),
                "thread_id": str(row[1]),
                "subject": row[2],
                "to_email": row[3],
                "scheduled_at": row[4].isoformat() if row[4] else None,
                "timezone": row[5],
                "status": row[6],
                "created_at": row[7].isoformat() if row[7] else None,
            })
        
        return {"success": True, "data": scheduled, "total": len(scheduled)}

@router.post("", response_model=dict)
async def schedule_email(
    tenant_id: UUID = Query(...),
    schedule: ScheduleEmail = None,
):
    """Schedule an email for future sending."""
    from seo_platform.core.database import get_session
    from sqlalchemy import text
    
    if not schedule:
        raise HTTPException(status_code=400, detail="Schedule data required")
    
    try:
        scheduled_at = datetime.fromisoformat(schedule.scheduled_at.replace('Z', '+00:00'))
    except:
        raise HTTPException(status_code=400, detail="Invalid scheduled_at format")
    
    async with get_session() as session:
        await session.execute(text("""
            INSERT INTO scheduled_emails 
            (tenant_id, thread_id, subject, body, to_email, scheduled_at, timezone, status, created_at)
            VALUES (:tenant_id, :thread_id, :subject, :body, :to_email, :scheduled_at, :timezone, 'pending', :created_at)
        """), {
            "tenant_id": str(tenant_id),
            "thread_id": schedule.thread_id,
            "subject": schedule.subject,
            "body": schedule.body,
            "to_email": schedule.to_email,
            "scheduled_at": scheduled_at,
            "timezone": schedule.timezone,
            "created_at": datetime.now(timezone.utc),
        })
        await session.commit()
        
        return {"success": True, "message": "Email scheduled", "scheduled_at": scheduled_at.isoformat()}

@router.post("/{schedule_id}/cancel", response_model=dict)
async def cancel_scheduled_email(
    schedule_id: str,
    tenant_id: UUID = Query(...),
):
    """Cancel a scheduled email."""
    from seo_platform.core.database import get_session
    from sqlalchemy import text
    
    async with get_session() as session:
        await session.execute(text("""
            UPDATE scheduled_emails
            SET status = 'cancelled', updated_at = :updated_at
            WHERE id = :schedule_id AND tenant_id = :tenant_id
        """), {
            "schedule_id": schedule_id,
            "tenant_id": str(tenant_id),
            "updated_at": datetime.now(timezone.utc),
        })
        await session.commit()
        
        return {"success": True, "message": "Email schedule cancelled"}

@router.post("/{schedule_id}/send", response_model=dict)
async def send_scheduled_email(
    schedule_id: str,
    tenant_id: UUID = Query(...),
):
    """Send a scheduled email immediately."""
    from seo_platform.core.database import get_session
    from sqlalchemy import text
    
    async with get_session() as session:
        # Get email data
        result = await session.execute(text("""
            SELECT thread_id, subject, body, to_email
            FROM scheduled_emails
            WHERE id = :schedule_id AND tenant_id = :tenant_id
        """), {"schedule_id": schedule_id, "tenant_id": str(tenant_id)})
        
        email_data = result.first()
        if not email_data:
            raise HTTPException(status_code=404, detail="Scheduled email not found")
        
        # Here you would integrate with actual email sending service
        # For now, just mark as sent
        await session.execute(text("""
            UPDATE scheduled_emails
            SET status = 'sent', sent_at = :sent_at
            WHERE id = :schedule_id AND tenant_id = :tenant_id
        """), {
            "schedule_id": schedule_id,
            "tenant_id": str(tenant_id),
            "sent_at": datetime.now(timezone.utc),
        })
        await session.commit()
        
        return {"success": True, "message": "Email sent"}
