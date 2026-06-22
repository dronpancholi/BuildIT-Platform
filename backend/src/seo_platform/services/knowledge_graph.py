from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import text, select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from seo_platform.config import get_settings
from seo_platform.core.database import get_session, get_session_factory, get_tenant_session
from seo_platform.core.logging import get_logger
from seo_platform.models.knowledge_graph import GraphEntity, GraphEdge

logger = get_logger(__name__)

ENTITY_TYPES = [
    "customer", "campaign", "keyword", "prospect",
    "outreach", "report", "automation", "alert", "approval",
]

RELATION_TYPES = [
    "belongs_to", "targets", "generates", "triggers",
    "mentions", "affects", "requires", "produces",
    "analyzes", "monitors", "approves", "schedules",
]


class KnowledgeGraphService:
    def __init__(self) -> None:
        self._entity_type_map: dict[str, tuple[str, str, str]] | None = None

    async def rebuild(self, tenant_id: UUID) -> dict[str, int]:
        stats: dict[str, int] = {}

        async with get_tenant_session(tenant_id) as session:
            await session.execute(
                text("DELETE FROM graph_edges WHERE tenant_id = :tid"), {"tid": tenant_id}
            )
            await session.execute(
                text("DELETE FROM graph_entities WHERE tenant_id = :tid"), {"tid": tenant_id}
            )
        stats["cleared"] = 0

        for etype in ENTITY_TYPES:
            try:
                async with get_tenant_session(tenant_id) as session:
                    count = await self._index_entity_type(session, tenant_id, etype)
                    stats[etype] = count
            except Exception as e:
                logger.warning("graph_index_etype_failed", entity_type=etype, error=str(e))
                stats[etype] = 0

        try:
            async with get_tenant_session(tenant_id) as session:
                await self._build_edges(session, tenant_id)
        except Exception as e:
            logger.warning("graph_edge_build_failed", error=str(e))

        async with get_tenant_session(tenant_id) as session:
            edge_count = await session.scalar(
                select(func.count()).select_from(GraphEdge).where(GraphEdge.tenant_id == tenant_id)
            )
            stats["edges"] = edge_count or 0
        return stats

    async def _index_entity_type(self, session: AsyncSession, tenant_id: UUID, etype: str) -> int:
        table_map: dict[str, str] = {
            "customer": "clients",
            "campaign": "backlink_campaigns",
            "keyword": "keywords",
            "prospect": "backlink_prospects",
            "outreach": "outreach_emails",
            "report": "reports",
            "automation": "automation_rules",
            "alert": "executive_alerts",
            "approval": "approval_requests",
        }
        table = table_map.get(etype)
        if not table:
            return 0

        try:
            column_map = {
                "executive_alerts": ("id::text", "title", "description"),
                "reports": ("id::text", "report_type", "COALESCE(ai_summary->>'summary', '')"),
                "automation_rules": ("id::text", "name", "COALESCE(description, '')"),
                "approval_requests": ("id::text", "summary", "COALESCE(ai_risk_summary, '')"),
                "clients": ("id::text", "name", "COALESCE(domain, '')"),
                "backlink_campaigns": ("id::text", "name", "COALESCE(('Status: ' || status), '')"),
                "keywords": ("id::text", "keyword", "COALESCE(('Vol: ' || search_volume), '')"),
                "backlink_prospects": ("id::text", "COALESCE(domain, contact_email)", "COALESCE(('Score: ' || composite_score::text), '')"),
                "outreach_emails": ("id::text", "subject", "COALESCE(to_email, '')"),
            }
            id_col, label_col, desc_col = column_map.get(table, ("id::text", "name", "''"))
            rows = (await session.execute(
                text(f"SELECT {id_col}, {label_col}, {desc_col} FROM {table} WHERE tenant_id = :tid"),
                {"tid": tenant_id}
            )).fetchall()

            count = 0
            for row in rows:
                entity = GraphEntity(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    entity_type=etype,
                    entity_id=str(row[0]),
                    label=str(row[1] or row[0]),
                    description=str(row[2] or ""),
                )
                session.add(entity)
                count += 1
            return count
        except Exception as e:
            logger.warning("graph_index_failed", entity_type=etype, error=str(e))
            return 0

    async def _build_edges(self, session: AsyncSession, tenant_id: UUID) -> None:
        try:
            edges = []

            campaigns = (await session.execute(
                text("SELECT id::text, client_id::text FROM backlink_campaigns WHERE tenant_id = :tid"),
                {"tid": tenant_id}
            )).fetchall()
            for cid, clid in campaigns:
                src = await self._resolve_entity(session, tenant_id, "campaign", cid)
                tgt = await self._resolve_entity(session, tenant_id, "customer", clid)
                if src and tgt:
                    edges.append(GraphEdge(
                        tenant_id=tenant_id, source_entity_id=src, target_entity_id=tgt,
                        relationship_type="belongs_to"
                    ))

            prospects = (await session.execute(
                text("SELECT id::text, campaign_id::text FROM backlink_prospects WHERE tenant_id = :tid AND campaign_id IS NOT NULL"),
                {"tid": tenant_id}
            )).fetchall()
            for pid, cid_str in prospects:
                src = await self._resolve_entity(session, tenant_id, "prospect", pid)
                tgt = await self._resolve_entity(session, tenant_id, "campaign", cid_str)
                if src and tgt:
                    edges.append(GraphEdge(
                        tenant_id=tenant_id, source_entity_id=src, target_entity_id=tgt,
                        relationship_type="targets"
                    ))

            emails = (await session.execute(
                text("SELECT id::text, campaign_id::text, prospect_id::text FROM outreach_emails WHERE tenant_id = :tid"),
                {"tid": tenant_id}
            )).fetchall()
            for eid, cid_str, pid_str in emails:
                src = await self._resolve_entity(session, tenant_id, "outreach", eid)
                if cid_str:
                    tgt = await self._resolve_entity(session, tenant_id, "campaign", cid_str)
                    if src and tgt:
                        edges.append(GraphEdge(
                            tenant_id=tenant_id, source_entity_id=src, target_entity_id=tgt,
                            relationship_type="targets"
                        ))
                if pid_str:
                    tgt = await self._resolve_entity(session, tenant_id, "prospect", pid_str)
                    if src and tgt:
                        edges.append(GraphEdge(
                            tenant_id=tenant_id, source_entity_id=src, target_entity_id=tgt,
                            relationship_type="mentions"
                        ))

            approvals = (await session.execute(
                text("SELECT id::text, workflow_run_id FROM approval_requests WHERE tenant_id = :tid AND workflow_run_id IS NOT NULL"),
                {"tid": tenant_id}
            )).fetchall()
            for aid, wrid in approvals:
                src = await self._resolve_entity(session, tenant_id, "approval", aid)
                if src:
                    edges.append(GraphEdge(
                        tenant_id=tenant_id, source_entity_id=src,
                        target_entity_id=src, relationship_type="approves"
                    ))

            for edge in edges:
                session.add(edge)
        except Exception as e:
            logger.error("graph_edge_build_failed", error=str(e))

    async def _resolve_entity(self, session: AsyncSession, tenant_id: UUID, etype: str, eid: str) -> UUID | None:
        if not eid or eid == "None":
            return None
        try:
            result = await session.execute(
                select(GraphEntity.id).where(
                    GraphEntity.tenant_id == tenant_id,
                    GraphEntity.entity_type == etype,
                    GraphEntity.entity_id == eid,
                )
            )
            row = result.scalar_one_or_none()
            return row
        except Exception:
            return None

    async def get_entity(self, tenant_id: UUID, entity_id: UUID) -> dict[str, Any] | None:
        async with get_tenant_session(tenant_id) as session:
            entity = await session.get(GraphEntity, entity_id)
            if not entity or entity.tenant_id != tenant_id:
                return None

            outgoing = (await session.execute(
                select(GraphEdge).where(
                    GraphEdge.source_entity_id == entity_id,
                    GraphEdge.tenant_id == tenant_id,
                )
            )).scalars().all()

            incoming = (await session.execute(
                select(GraphEdge).where(
                    GraphEdge.target_entity_id == entity_id,
                    GraphEdge.tenant_id == tenant_id,
                )
            )).scalars().all()

            return {
                "id": str(entity.id),
                "tenant_id": str(entity.tenant_id),
                "entity_type": entity.entity_type,
                "entity_id": entity.entity_id,
                "label": entity.label,
                "description": entity.description,
                "metadata": entity.custom_metadata,
                "created_at": entity.created_at.isoformat(),
                "updated_at": entity.updated_at.isoformat(),
                "relationships": {
                    "outgoing": [
                        {
                            "id": str(e.id),
                            "type": e.relationship_type,
                            "weight": e.weight,
                            "target": {
                                "id": str(e.target_entity.id),
                                "entity_type": e.target_entity.entity_type,
                                "label": e.target_entity.label,
                            },
                        }
                        for e in outgoing
                    ],
                    "incoming": [
                        {
                            "id": str(e.id),
                            "type": e.relationship_type,
                            "weight": e.weight,
                            "source": {
                                "id": str(e.source_entity.id),
                                "entity_type": e.source_entity.entity_type,
                                "label": e.source_entity.label,
                            },
                        }
                        for e in incoming
                    ],
                },
            }

    async def get_related(self, tenant_id: UUID, entity_id: UUID, depth: int = 1, max_results: int = 20) -> list[dict[str, Any]]:
        async with get_tenant_session(tenant_id) as session:
            entity = await session.get(GraphEntity, entity_id)
            if not entity or entity.tenant_id != tenant_id:
                return []

            visited: set[UUID] = {entity_id}
            results: list[dict[str, Any]] = []
            current_level: list[UUID] = [entity_id]

            for _ in range(depth):
                if not current_level or len(results) >= max_results:
                    break

                outgoing = (await session.execute(
                    select(GraphEdge).where(
                        GraphEdge.source_entity_id.in_(current_level),
                        GraphEdge.tenant_id == tenant_id,
                    )
                )).scalars().all()

                incoming = (await session.execute(
                    select(GraphEdge).where(
                        GraphEdge.target_entity_id.in_(current_level),
                        GraphEdge.tenant_id == tenant_id,
                    )
                )).scalars().all()

                next_level: list[UUID] = []
                for edge in outgoing:
                    tid = edge.target_entity_id
                    if tid not in visited:
                        visited.add(tid)
                        next_level.append(tid)
                        t = edge.target_entity
                        results.append({
                            "id": str(t.id),
                            "entity_type": t.entity_type,
                            "label": t.label,
                            "relationship": edge.relationship_type,
                            "direction": "outgoing",
                            "weight": edge.weight,
                        })

                for edge in incoming:
                    sid = edge.source_entity_id
                    if sid not in visited:
                        visited.add(sid)
                        next_level.append(sid)
                        s = edge.source_entity
                        results.append({
                            "id": str(s.id),
                            "entity_type": s.entity_type,
                            "label": s.label,
                            "relationship": edge.relationship_type,
                            "direction": "incoming",
                            "weight": edge.weight,
                        })

                current_level = next_level

            return results[:max_results]

    async def search_entities(self, tenant_id: UUID, query: str, etype: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        async with get_tenant_session(tenant_id) as session:
            stmt = select(GraphEntity).where(
                GraphEntity.tenant_id == tenant_id,
                or_(
                    GraphEntity.label.ilike(f"%{query}%"),
                    GraphEntity.description.ilike(f"%{query}%"),
                ),
            )
            if etype:
                stmt = stmt.where(GraphEntity.entity_type == etype)
            stmt = stmt.limit(limit)
            rows = (await session.execute(stmt)).scalars().all()
            return [
                {
                    "id": str(r.id),
                    "entity_type": r.entity_type,
                    "entity_id": r.entity_id,
                    "label": r.label,
                }
                for r in rows
            ]


knowledge_graph_service = KnowledgeGraphService()
