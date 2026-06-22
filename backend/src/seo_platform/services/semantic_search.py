from __future__ import annotations

import uuid
from typing import Any
from uuid import UUID

from sqlalchemy import text
from qdrant_client import AsyncQdrantClient, models

from seo_platform.config import get_settings
from seo_platform.core.logging import get_logger
from seo_platform.core.database import get_tenant_session
from seo_platform.services.vector_store import VECTOR_SIZE, QdrantVectorStore

logger = get_logger(__name__)

SEMANTIC_COLLECTION = "semantic_content"

INDEX_SOURCES = [
    "report", "email", "template", "campaign", "alert", "approval",
]


class SemanticSearchService:
    def __init__(self) -> None:
        self._client: AsyncQdrantClient | None = None
        self._initialized = False

    async def _get_client(self) -> AsyncQdrantClient:
        if self._client is None:
            settings = get_settings()
            self._client = AsyncQdrantClient(
                host=settings.qdrant.host,
                port=settings.qdrant.port,
                api_key=settings.qdrant.api_key or None,
                prefer_grpc=True,
            )
        return self._client

    async def initialize(self) -> None:
        if self._initialized:
            return
        client = await self._get_client()
        try:
            exists = await client.collection_exists(SEMANTIC_COLLECTION)
            if not exists:
                await client.create_collection(
                    collection_name=SEMANTIC_COLLECTION,
                    vectors_config=models.VectorParams(
                        size=VECTOR_SIZE, distance=models.Distance.COSINE,
                    ),
                )
                logger.info("semantic_collection_created")
        except Exception as e:
            logger.warning("semantic_collection_init_failed", error=str(e))
        self._initialized = True

    async def _generate_embedding(self, text: str) -> list[float]:
        return await QdrantVectorStore._generate_embedding(self, text)

    async def index_all(self, tenant_id: UUID) -> dict[str, int]:
        await self.initialize()
        stats: dict[str, int] = {}
        for source in INDEX_SOURCES:
            count = await self._index_source(tenant_id, source)
            stats[source] = count
        return stats

    async def _index_source(self, tenant_id: UUID, source: str) -> int:
        query_map: dict[str, str] = {
            "report": "SELECT id::text, report_type, COALESCE(ai_summary->>'summary', '') FROM reports WHERE tenant_id = :tid",
            "email": "SELECT id::text, subject, body_html FROM outreach_emails WHERE tenant_id = :tid",
            "template": "SELECT id::text, name, body_template FROM email_templates WHERE tenant_id = :tid",
            "campaign": "SELECT id::text, name, ''::text as campaign_desc FROM backlink_campaigns WHERE tenant_id = :tid",
            "alert": "SELECT id::text, title, description FROM executive_alerts WHERE tenant_id = :tid",
            "approval": "SELECT id::text, summary, ai_risk_summary FROM approval_requests WHERE tenant_id = :tid",
        }
        query = query_map.get(source)
        if not query:
            return 0

        try:
            async with get_tenant_session(tenant_id) as session:
                rows = (await session.execute(text(query), {"tid": tenant_id})).fetchall()
        except Exception as e:
            logger.warning("semantic_index_query_failed", source=source, error=str(e))
            return 0

        client = await self._get_client()
        count = 0
        for row in rows:
            doc_id = f"{tenant_id}:{source}:{row[0]}"
            title = str(row[1] or "")
            content = str(row[2] or "")
            combined = f"{title}\n{content}"[:8000]
            if not combined.strip():
                continue
            embedding = await self._generate_embedding(combined)
            try:
                await client.upsert(
                    collection_name=SEMANTIC_COLLECTION,
                    points=[models.PointStruct(
                        id=doc_id,
                        vector=embedding,
                        payload={
                            "tenant_id": str(tenant_id),
                            "source": source,
                            "source_id": str(row[0]),
                            "title": title[:255],
                            "content_preview": content[:500],
                        },
                    )],
                )
                count += 1
            except Exception as e:
                logger.warning("semantic_upsert_failed", doc_id=doc_id, error=str(e))

        logger.info("semantic_index_complete", source=source, count=count)
        return count

    async def search(
        self,
        tenant_id: UUID,
        query: str,
        source: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        await self.initialize()
        client = await self._get_client()
        embedding = await self._generate_embedding(query[:8000])

        filter_conditions = [
            models.FieldCondition(
                key="tenant_id",
                match=models.MatchValue(value=str(tenant_id)),
            )
        ]
        if source:
            filter_conditions.append(
                models.FieldCondition(
                    key="source",
                    match=models.MatchValue(value=source),
                )
            )

        try:
            results = await client.search(
                collection_name=SEMANTIC_COLLECTION,
                query_vector=embedding,
                query_filter=models.Filter(must=filter_conditions),
                limit=limit,
                with_payload=True,
            )
            return [
                {
                    "id": hit.id,
                    "score": round(hit.score, 4),
                    "source": hit.payload.get("source", ""),
                    "source_id": hit.payload.get("source_id", ""),
                    "title": hit.payload.get("title", ""),
                    "content_preview": hit.payload.get("content_preview", ""),
                    "tenant_id": hit.payload.get("tenant_id", ""),
                }
                for hit in results
            ]
        except Exception as e:
            logger.warning("semantic_search_failed", error=str(e))
            return []


semantic_search_service = SemanticSearchService()
