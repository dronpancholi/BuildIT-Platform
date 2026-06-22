from __future__ import annotations

from seo_platform.core.auth import get_validated_tenant_id
from uuid import UUID

from fastapi import Depends,  APIRouter, HTTPException, Query

from seo_platform.services.copilot import executive_copilot

router = APIRouter()


@router.post("/ask")
async def ask_copilot(
    question: str = Query(..., description="Natural language question"),
    tenant_id: UUID = Depends(get_validated_tenant_id),
    conversation_id: str | None = Query(None, description="Conversation ID for context"),
) -> dict:
    if not question.strip():
        raise HTTPException(status_code=400, detail="Question is required")
    try:
        result = await executive_copilot.ask(question, tenant_id, conversation_id)
        return {"success": True, "data": result.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
