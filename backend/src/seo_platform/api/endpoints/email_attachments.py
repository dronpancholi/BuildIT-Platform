"""
Email Attachments API
Supports: upload, download, delete, list for drafts
"""

from __future__ import annotations
from seo_platform.core.auth import get_validated_tenant_id
import io
import os
import uuid
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, UploadFile, File, Query, HTTPException
from fastapi.responses import StreamingResponse

router = APIRouter()

@router.post("/upload", response_model=dict)
async def upload_attachment(
    draft_id: str = Query(...),
    tenant_id: UUID = Depends(get_validated_tenant_id),
    file: UploadFile = File(...),
):
    """Upload a file attachment and store in MinIO."""
    from seo_platform.core.database import get_session
    from sqlalchemy import text
    from seo_platform.services.storage.adapter import storage_adapter

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    content = await file.read()
    file_size = len(content)
    ext = os.path.splitext(file.filename)[1].lower()
    object_key = f"{tenant_id}/attachments/{uuid.uuid4()}{ext}"

    # Ensure bucket
    try:
        storage_adapter.ensure_bucket()
    except Exception:
        pass

    # Upload to MinIO
    try:
        storage_adapter.upload_fileobj(io.BytesIO(content), object_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

    # Save record in DB
    async with get_session() as session:
        result = await session.execute(text("""
            INSERT INTO email_attachments
            (draft_id, tenant_id, filename, file_size, mime_type, storage_path, created_at)
            VALUES (:draft_id, :tenant_id, :filename, :file_size, :mime_type, :storage_path, :created_at)
            RETURNING id
        """), {
            "draft_id": draft_id,
            "tenant_id": str(tenant_id),
            "filename": file.filename,
            "file_size": file_size,
            "mime_type": file.content_type or "application/octet-stream",
            "storage_path": object_key,
            "created_at": datetime.now(timezone.utc),
        })
        await session.commit()
        attachment_id = result.scalar()

        return {
            "success": True,
            "data": {
                "id": str(attachment_id),
                "filename": file.filename,
                "file_size": file_size,
                "mime_type": file.content_type,
                "storage_path": object_key,
            },
        }

@router.get("/{draft_id}", response_model=dict)
async def list_attachments(
    draft_id: str,
    tenant_id: UUID = Depends(get_validated_tenant_id),
):
    """List all attachments for a draft."""
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        result = await session.execute(text("""
            SELECT id, draft_id, filename, file_size, mime_type, storage_path, created_at
            FROM email_attachments
            WHERE draft_id = :draft_id AND tenant_id = :tenant_id
            ORDER BY created_at DESC
        """), {"draft_id": draft_id, "tenant_id": str(tenant_id)})

        attachments = []
        for row in result.fetchall():
            attachments.append({
                "id": str(row[0]),
                "draft_id": str(row[1]),
                "filename": row[2],
                "file_size": row[3],
                "mime_type": row[4],
                "storage_path": row[5],
                "created_at": row[6].isoformat() if row[6] else None,
            })

        return {"success": True, "data": attachments}

@router.get("/{attachment_id}/download")
async def download_attachment(
    attachment_id: str,
    tenant_id: UUID = Depends(get_validated_tenant_id),
):
    """Download an attachment file."""
    from seo_platform.core.database import get_session
    from sqlalchemy import text
    from seo_platform.services.storage.adapter import storage_adapter

    async with get_session() as session:
        result = await session.execute(text("""
            SELECT filename, storage_path, mime_type
            FROM email_attachments
            WHERE id = :attachment_id AND tenant_id = :tenant_id
        """), {"attachment_id": attachment_id, "tenant_id": str(tenant_id)})

        row = result.first()
        if not row:
            raise HTTPException(status_code=404, detail="Attachment not found")

        filename, storage_path, mime_type = row

    # Download from MinIO
    try:
        buf = io.BytesIO()
        storage_adapter.s3.download_fileobj(
            storage_adapter.bucket, storage_path, buf
        )
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type=mime_type or "application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@router.delete("/{attachment_id}", response_model=dict)
async def delete_attachment(
    attachment_id: str,
    tenant_id: UUID = Depends(get_validated_tenant_id),
):
    """Delete an attachment."""
    from seo_platform.core.database import get_session
    from sqlalchemy import text
    from seo_platform.services.storage.adapter import storage_adapter

    async with get_session() as session:
        result = await session.execute(text("""
            SELECT storage_path FROM email_attachments
            WHERE id = :attachment_id AND tenant_id = :tenant_id
        """), {"attachment_id": attachment_id, "tenant_id": str(tenant_id)})

        row = result.first()
        if not row:
            raise HTTPException(status_code=404, detail="Attachment not found")

        storage_path = row[0]

        # Delete from MinIO
        try:
            storage_adapter.delete_file(storage_path)
        except Exception:
            pass

        # Delete from DB
        await session.execute(text("""
            DELETE FROM email_attachments
            WHERE id = :attachment_id AND tenant_id = :tenant_id
        """), {"attachment_id": attachment_id, "tenant_id": str(tenant_id)})
        await session.commit()

        return {"success": True, "message": "Attachment deleted"}
