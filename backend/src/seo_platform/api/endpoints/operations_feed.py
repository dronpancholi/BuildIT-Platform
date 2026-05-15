from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import text

from seo_platform.core.database import get_session
from seo_platform.core.logging import get_logger
from seo_platform.schemas import APIResponse

logger = get_logger(__name__)
router = APIRouter()


class OperationalEvent(BaseModel):
    id: str
    event_type: str
    summary: str
    severity: str
    metadata: dict | None = None
    created_at: str


@router.get("/operations-feed", response_model=APIResponse[list[OperationalEvent]])
async def get_operations_feed(
    limit: int = Query(default=50, ge=1, le=200),
    since: str | None = None,
    severity: str | None = None,
) -> APIResponse[list[OperationalEvent]]:
    """Return recent events from operational_events + business_intelligence_events."""
    events: list[OperationalEvent] = []

    try:
        async with get_session() as session:
            params: dict = {"limit": limit}
            filters = ""
            bie_filters = ""

            if since:
                filters += " AND created_at > :since"
                bie_filters += " AND occurred_at > :since"
                params["since"] = since
            if severity:
                filters += " AND severity = :severity"
                bie_filters += " AND severity = :severity"
                params["severity"] = severity

            query = text(f"""
                SELECT id, event_type, summary, severity, metadata, created_at
                FROM operational_events
                WHERE 1=1{filters}
                UNION ALL
                SELECT id, event_type, title AS summary, severity,
                       jsonb_build_object(
                           'domain', domain, 'description', description,
                           'entity_type', entity_type, 'entity_id', entity_id::text
                       ) AS metadata,
                       occurred_at AS created_at
                FROM business_intelligence_events
                WHERE 1=1{bie_filters}
                ORDER BY created_at DESC
                LIMIT :limit
            """)

            result = await session.execute(query, params)
            for row in result:
                events.append(OperationalEvent(
                    id=str(row[0]),
                    event_type=row[1],
                    summary=row[2],
                    severity=row[3],
                    metadata=row[4] or {},
                    created_at=row[5].isoformat() if row[5] else "",
                ))
    except Exception as e:
        logger.warning("operations_feed_failed", error=str(e))

    return APIResponse(data=events)
