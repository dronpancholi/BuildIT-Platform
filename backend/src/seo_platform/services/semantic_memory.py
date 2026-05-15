"""
SEO Platform — Semantic Operational Memory Service
====================================================
Long-context operational intelligence using Redis for memory storage,
retrieval, lineage tracking, semantic linking, and operational context
reconstruction for workflow executions.

All memory is advisory — it provides context for recommendations and UI,
NOT execution decisions. Deterministic systems control execution.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import orjson
from pydantic import BaseModel, Field

from seo_platform.core.logging import get_logger
from seo_platform.llm.gateway import RenderedPrompt, TaskType, llm_gateway

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Memory Models
# ---------------------------------------------------------------------------
VALID_NAMESPACES = {"workflow", "prospect", "campaign", "outreach", "keyword", "citation"}
RELATIONSHIP_TYPES = {"caused", "related_to", "references", "derived_from", "contradicts"}
MEMORY_TTL_DAYS = 90


class MemoryEntry(BaseModel):
    namespace: str
    key: str
    content: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    stored_at: str = ""
    ttl_days: int = MEMORY_TTL_DAYS


class MemoryLineageEntry(BaseModel):
    key: str
    previous_content: dict[str, Any] = Field(default_factory=dict)
    new_content: dict[str, Any] = Field(default_factory=dict)
    diff: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = ""


class MemoryLink(BaseModel):
    source_key: str
    target_key: str
    relationship_type: str
    created_at: str = ""


class OperationalPhase(BaseModel):
    phase: str
    state: dict[str, Any] = Field(default_factory=dict)
    decisions: list[str] = Field(default_factory=list)
    timestamp: str = ""


class OperationalContext(BaseModel):
    tenant_id: str
    workflow_run_id: str
    workflow_type: str = ""
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    key_decisions: list[str] = Field(default_factory=list)
    state_at_each_phase: list[OperationalPhase] = Field(default_factory=list)
    memory_entries_used: int = 0


class ProspectInteraction(BaseModel):
    timestamp: str
    interaction_type: str
    details: dict[str, Any] = Field(default_factory=dict)


class ProspectMemory(BaseModel):
    tenant_id: str
    campaign_id: str
    prospect_domain: str
    interactions: list[ProspectInteraction] = Field(default_factory=list)


class CampaignMilestone(BaseModel):
    milestone_type: str
    milestone_data: dict[str, Any] = Field(default_factory=dict)
    recorded_at: str = ""


class OrganizationMemoryReport(BaseModel):
    summary: str = ""
    key_learnings: list[str] = Field(default_factory=list)
    patterns: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class IncidentMemoryReconstruction(BaseModel):
    incident_id: str
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    related_entries: list[dict[str, Any]] = Field(default_factory=list)
    root_cause: str = ""
    resolution_path: str = ""
    key_findings: list[str] = Field(default_factory=list)


class OperationalReplayCognition(BaseModel):
    workflow_id: str
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    outcomes: list[str] = Field(default_factory=list)
    patterns: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Redis Key Helpers
# ---------------------------------------------------------------------------
_MEMORY_PREFIX = "semantic_memory"
_LINEAGE_PREFIX = "memory_lineage"
_LINK_PREFIX = "memory_link"
_PROSPECT_PREFIX = "prospect_memory"
_CAMPAIGN_PREFIX = "campaign_milestone"
_CONTEXT_PREFIX = "operational_context"


def _memory_key(namespace: str, key: str) -> str:
    return f"{_MEMORY_PREFIX}:{namespace}:{key}"


def _lineage_key(key: str) -> str:
    return f"{_LINEAGE_PREFIX}:{key}"


def _link_key(source_key: str, target_key: str) -> str:
    return f"{_LINK_PREFIX}:{source_key}:{target_key}"


def _prospect_key(tenant_id: str, domain: str) -> str:
    return f"{_PROSPECT_PREFIX}:{tenant_id}:{domain}"


def _campaign_key(campaign_id: str) -> str:
    return f"{_CAMPAIGN_PREFIX}:{campaign_id}"


def _context_key(workflow_run_id: str) -> str:
    return f"{_CONTEXT_PREFIX}:{workflow_run_id}"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _compute_diff(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    diff: dict[str, Any] = {}
    all_keys = set(old.keys()) | set(new.keys())
    for k in all_keys:
        old_val = old.get(k)
        new_val = new.get(k)
        if old_val != new_val:
            diff[k] = {"old": old_val, "new": new_val}
    return diff


# ---------------------------------------------------------------------------
# Semantic Memory Service
# ---------------------------------------------------------------------------
class SemanticMemoryService:

    # ------------------------------------------------------------------
    # Core CRUD
    # ------------------------------------------------------------------
    async def store_memory(
        self,
        namespace: str,
        key: str,
        content: dict[str, Any],
        metadata: dict[str, Any] | None = None,
        ttl_days: int = MEMORY_TTL_DAYS,
    ) -> MemoryEntry:
        """Store operational memory in Redis with TTL."""
        if namespace not in VALID_NAMESPACES:
            raise ValueError(f"Invalid namespace '{namespace}'. Valid: {VALID_NAMESPACES}")

        redis_key = _memory_key(namespace, key)
        now = _now_iso()

        entry = MemoryEntry(
            namespace=namespace,
            key=key,
            content=content,
            metadata=metadata or {},
            stored_at=now,
            ttl_days=ttl_days,
        )

        try:
            from seo_platform.core.redis import get_redis
            redis = await get_redis()

            existing = await redis.get(redis_key)
            if existing:
                old_content = orjson.loads(existing).get("content", {})
                diff = _compute_diff(old_content, content)
                lineage_entry = orjson.dumps({
                    "key": key,
                    "previous_content": old_content,
                    "new_content": content,
                    "diff": diff,
                    "timestamp": now,
                }).decode()
                lineage_key = _lineage_key(key)
                await redis.rpush(lineage_key, lineage_entry)
                await redis.expire(lineage_key, ttl_days * 86400)

            await redis.setex(
                redis_key,
                ttl_days * 86400,
                entry.model_dump_json(),
            )
            logger.info("memory_stored", namespace=namespace, key=key)
        except Exception as e:
            logger.warning("memory_store_failed", namespace=namespace, key=key, error=str(e))

        return entry

    async def get_memory(self, namespace: str, key: str) -> MemoryEntry | None:
        """Retrieve stored memory by namespace and key."""
        try:
            from seo_platform.core.redis import get_redis
            redis = await get_redis()
            redis_key = _memory_key(namespace, key)
            raw = await redis.get(redis_key)
            if raw:
                return MemoryEntry.model_validate_json(raw)
        except Exception as e:
            logger.warning("memory_retrieval_failed", namespace=namespace, key=key, error=str(e))
        return None

    async def search_memory(
        self,
        namespace: str,
        query_tags: list[str] | None = None,
        limit: int = 20,
    ) -> list[MemoryEntry]:
        """Search memories by namespace and metadata tags."""
        results: list[MemoryEntry] = []

        try:
            from seo_platform.core.redis import get_redis
            redis = await get_redis()
            pattern = f"{_MEMORY_PREFIX}:{namespace}:*"
            keys = await redis.keys(pattern)

            for redis_key in keys[:limit * 3]:
                raw = await redis.get(redis_key)
                if not raw:
                    continue
                try:
                    entry = MemoryEntry.model_validate_json(raw)
                    if query_tags:
                        entry_tags = set(entry.metadata.get("tags", []))
                        if not any(t in entry_tags for t in query_tags):
                            continue
                    results.append(entry)
                    if len(results) >= limit:
                        break
                except Exception:
                    continue

            results.sort(key=lambda e: e.stored_at, reverse=True)
        except Exception as e:
            logger.warning("memory_search_failed", namespace=namespace, error=str(e))

        return results[:limit]

    async def delete_memory(self, namespace: str, key: str) -> bool:
        """Remove a memory entry."""
        try:
            from seo_platform.core.redis import get_redis
            redis = await get_redis()
            redis_key = _memory_key(namespace, key)
            result = await redis.delete(redis_key)
            return result > 0
        except Exception as e:
            logger.warning("memory_delete_failed", namespace=namespace, key=key, error=str(e))
            return False

    # ------------------------------------------------------------------
    # Memory Lineage
    # ------------------------------------------------------------------
    async def get_memory_lineage(self, key: str) -> list[MemoryLineageEntry]:
        """Trace memory history — returns updates with timestamps and diffs."""
        entries: list[MemoryLineageEntry] = []

        try:
            from seo_platform.core.redis import get_redis
            redis = await get_redis()
            lineage_key = _lineage_key(key)
            raw_entries = await redis.lrange(lineage_key, 0, -1)

            for raw in raw_entries:
                try:
                    data = orjson.loads(raw)
                    entries.append(MemoryLineageEntry(
                        key=data.get("key", key),
                        previous_content=data.get("previous_content", {}),
                        new_content=data.get("new_content", {}),
                        diff=data.get("diff", {}),
                        timestamp=data.get("timestamp", ""),
                    ))
                except Exception:
                    continue

            entries.sort(key=lambda e: e.timestamp, reverse=True)
        except Exception as e:
            logger.warning("memory_lineage_failed", key=key, error=str(e))

        return entries

    async def link_memories(
        self,
        source_key: str,
        target_key: str,
        relationship_type: str,
    ) -> MemoryLink:
        """Link two memories with a typed relationship."""
        if relationship_type not in RELATIONSHIP_TYPES:
            raise ValueError(
                f"Invalid relationship type '{relationship_type}'. Valid: {RELATIONSHIP_TYPES}"
            )

        link = MemoryLink(
            source_key=source_key,
            target_key=target_key,
            relationship_type=relationship_type,
            created_at=_now_iso(),
        )

        try:
            from seo_platform.core.redis import get_redis
            redis = await get_redis()
            link_key = _link_key(source_key, target_key)
            await redis.setex(link_key, MEMORY_TTL_DAYS * 86400, link.model_dump_json())
            logger.info("memory_linked", source=source_key, target=target_key, rel=relationship_type)
        except Exception as e:
            logger.warning("memory_link_failed", source=source_key, target=target_key, error=str(e))

        return link

    # ------------------------------------------------------------------
    # Operational Context Reconstruction
    # ------------------------------------------------------------------
    async def reconstruct_operational_context(
        self,
        tenant_id: UUID,
        workflow_run_id: str,
    ) -> OperationalContext:
        """Reconstruct the full context of a workflow execution."""
        logger.info("reconstructing_operational_context", tenant_id=str(tenant_id), run_id=workflow_run_id)
        context = OperationalContext(
            tenant_id=str(tenant_id),
            workflow_run_id=workflow_run_id,
        )

        try:
            mem_entries: list[MemoryEntry] = []
            for namespace in VALID_NAMESPACES:
                entries = await self.search_memory(namespace, limit=50)
                for e in entries:
                    if workflow_run_id in str(e.metadata.get("workflow_run_id", "")):
                        mem_entries.append(e)

            context.memory_entries_used = len(mem_entries)

            timeline: list[dict[str, Any]] = []
            for entry in sorted(mem_entries, key=lambda e: e.stored_at):
                timeline.append({
                    "timestamp": entry.stored_at,
                    "namespace": entry.namespace,
                    "key": entry.key,
                    "summary": entry.content.get("summary", entry.content),
                    "tags": entry.metadata.get("tags", []),
                })

            context.timeline = timeline

            key_decisions: list[str] = []
            for entry in mem_entries:
                decision = entry.content.get("decision") or entry.metadata.get("decision")
                if decision:
                    key_decisions.append(decision)
            context.key_decisions = key_decisions

            try:
                from seo_platform.core.temporal_client import get_temporal_client
                client = await get_temporal_client()
                try:
                    handle = client.get_workflow_handle(workflow_run_id)
                    desc = await handle.describe()
                    wf_type = getattr(desc, "type_name", "unknown")
                    context.workflow_type = wf_type
                except Exception:
                    pass
            except Exception:
                pass

        except Exception as e:
            logger.warning("operational_context_reconstruction_failed", error=str(e))

        return context

    # ------------------------------------------------------------------
    # Prospect Memory
    # ------------------------------------------------------------------
    async def store_prospect_memory(
        self,
        tenant_id: UUID,
        campaign_id: UUID,
        prospect_domain: str,
        interaction_data: dict[str, Any],
    ) -> ProspectInteraction:
        """Store a prospect interaction in their history."""
        t_id = str(tenant_id)
        domain_clean = prospect_domain.lower().replace("www.", "")
        key = _prospect_key(t_id, domain_clean)

        interaction = ProspectInteraction(
            timestamp=_now_iso(),
            interaction_type=interaction_data.get("type", "email_sent"),
            details=interaction_data,
        )

        try:
            from seo_platform.core.redis import get_redis
            redis = await get_redis()
            raw = await redis.get(key)
            if raw:
                try:
                    existing = orjson.loads(raw)
                except Exception:
                    existing = {}
            else:
                existing = {}

            interactions = existing.get("interactions", [])
            interactions.append(interaction.model_dump())
            if len(interactions) > 200:
                interactions = interactions[-200:]

            stored = {
                "tenant_id": t_id,
                "campaign_id": str(campaign_id),
                "prospect_domain": domain_clean,
                "interactions": interactions,
            }
            await redis.setex(key, MEMORY_TTL_DAYS * 86400, orjson.dumps(stored).decode())
            logger.info("prospect_memory_stored", domain=domain_clean)
        except Exception as e:
            logger.warning("prospect_memory_store_failed", domain=domain_clean, error=str(e))

        return interaction

    async def get_prospect_history(
        self,
        tenant_id: UUID,
        prospect_domain: str,
    ) -> list[ProspectInteraction]:
        """Full interaction timeline for a prospect."""
        t_id = str(tenant_id)
        domain_clean = prospect_domain.lower().replace("www.", "")
        key = _prospect_key(t_id, domain_clean)

        try:
            from seo_platform.core.redis import get_redis
            redis = await get_redis()
            raw = await redis.get(key)
            if raw:
                data = orjson.loads(raw)
                return [
                    ProspectInteraction(**i)
                    for i in data.get("interactions", [])
                ]
        except Exception as e:
            logger.warning("prospect_history_failed", domain=domain_clean, error=str(e))

        return []

    # ------------------------------------------------------------------
    # Campaign Memory
    # ------------------------------------------------------------------
    async def store_campaign_milestone(
        self,
        campaign_id: UUID,
        milestone_type: str,
        milestone_data: dict[str, Any],
    ) -> CampaignMilestone:
        """Record a campaign milestone."""
        valid_types = {"launched", "prospect_approved", "email_sent", "link_acquired", "replied"}
        if milestone_type not in valid_types:
            raise ValueError(f"Invalid milestone type '{milestone_type}'. Valid: {valid_types}")

        milestone = CampaignMilestone(
            milestone_type=milestone_type,
            milestone_data=milestone_data,
            recorded_at=_now_iso(),
        )

        try:
            from seo_platform.core.redis import get_redis
            redis = await get_redis()
            key = _campaign_key(str(campaign_id))
            raw = await redis.get(key)
            if raw:
                try:
                    existing = orjson.loads(raw)
                except Exception:
                    existing = []
            else:
                existing = []

            existing.append(milestone.model_dump())
            if len(existing) > 500:
                existing = existing[-500:]

            await redis.setex(key, MEMORY_TTL_DAYS * 86400, orjson.dumps(existing).decode())
            logger.info("campaign_milestone_stored", campaign_id=str(campaign_id), milestone=milestone_type)
        except Exception as e:
            logger.warning("campaign_milestone_store_failed", campaign_id=str(campaign_id), error=str(e))

        return milestone

    async def get_campaign_timeline(
        self,
        campaign_id: UUID,
    ) -> list[CampaignMilestone]:
        """Full campaign execution timeline."""
        key = _campaign_key(str(campaign_id))

        try:
            from seo_platform.core.redis import get_redis
            redis = await get_redis()
            raw = await redis.get(key)
            if raw:
                milestones = orjson.loads(raw)
                return [
                    CampaignMilestone(**m)
                    for m in milestones
                ]
        except Exception as e:
            logger.warning("campaign_timeline_failed", campaign_id=str(campaign_id), error=str(e))

        return []

    # ------------------------------------------------------------------
    # Memory Relevance Scoring
    # ------------------------------------------------------------------
    def score_memory_relevance(
        self,
        memory_entry: MemoryEntry,
        query_context: dict[str, Any],
    ) -> float:
        """Score how relevant a memory is to the current context (0-1)."""
        score = 0.0

        now = datetime.now(UTC)
        try:
            stored = datetime.fromisoformat(memory_entry.stored_at)
            hours_ago = (now - stored).total_seconds() / 3600
        except (ValueError, TypeError):
            hours_ago = 999

        if hours_ago < 1:
            recency_score = 1.0
        elif hours_ago < 24:
            recency_score = 0.8
        elif hours_ago < 168:
            recency_score = 0.5
        elif hours_ago < 720:
            recency_score = 0.3
        else:
            recency_score = 0.1
        score += recency_score * 0.35

        query_tags = set(query_context.get("tags", []))
        memory_tags = set(memory_entry.metadata.get("tags", []))
        if query_tags and memory_tags:
            overlap = len(query_tags & memory_tags)
            union = len(query_tags | memory_tags)
            semantic_score = overlap / max(union, 1)
        else:
            semantic_score = 0.0
        score += semantic_score * 0.30

        query_namespace = query_context.get("namespace", "")
        if query_namespace and memory_entry.namespace == query_namespace:
            score += 0.15

        source_authority = memory_entry.metadata.get("confidence", 0.5)
        if isinstance(source_authority, (int, float)):
            score += source_authority * 0.20
        else:
            score += 0.10

        return round(max(0.0, min(1.0, score)), 4)

    # ------------------------------------------------------------------
    # Long-Term Workflow Memory (TTL 365 days)
    # ------------------------------------------------------------------
    async def store_long_term_workflow_memory(
        self,
        workflow_id: str,
        workflow_type: str,
        execution_data: dict[str, Any],
    ) -> MemoryEntry:
        """Store enriched workflow memory with 365-day TTL using LLM summarization."""
        summary_text = f"Workflow {workflow_id} of type {workflow_type} executed."

        try:
            prompt = RenderedPrompt(
                template_id="long_term_workflow_summary",
                system_prompt=(
                    "You are an operational memory analyst. Summarize workflow execution data "
                    "for long-term archival. Extract key decisions, outcomes, anomalies, and patterns. "
                    "Return valid JSON with: summary (string), decisions (array), outcomes (array), "
                    "key_patterns (array), significance_score (0-1)."
                ),
                user_prompt=(
                    f"Workflow Type: {workflow_type}\n"
                    f"Workflow ID: {workflow_id}\n"
                    f"Execution Data: {execution_data}\n\n"
                    f"Provide a comprehensive summary for long-term operational memory."
                ),
            )

            class SummaryOutput(BaseModel):
                summary: str
                decisions: list[str]
                outcomes: list[str]
                key_patterns: list[str]
                significance_score: float

            result = await llm_gateway.complete(
                task_type=TaskType.HISTORICAL_ANALYSIS,
                prompt=prompt,
                output_schema=SummaryOutput,
                tenant_id=UUID("00000000-0000-0000-0000-000000000000"),
                temperature=0.3,
            )
            output: SummaryOutput = result.content
            summary_text = output.summary
            content = {
                "workflow_id": workflow_id,
                "workflow_type": workflow_type,
                "summary": output.summary,
                "decisions": output.decisions,
                "outcomes": output.outcomes,
                "key_patterns": output.key_patterns,
                "significance_score": output.significance_score,
                "execution_data": execution_data,
            }
            metadata = {
                "workflow_type": workflow_type,
                "workflow_id": workflow_id,
                "confidence": result.confidence_score,
            }
        except Exception as e:
            logger.warning("long_term_workflow_llm_failed", workflow_id=workflow_id, error=str(e))
            content = {
                "workflow_id": workflow_id,
                "workflow_type": workflow_type,
                "summary": summary_text,
                "execution_data": execution_data,
            }
            metadata = {
                "workflow_type": workflow_type,
                "workflow_id": workflow_id,
                "confidence": 0.0,
            }

        return await self.store_memory(
            namespace="workflow",
            key=f"long_term:{workflow_id}",
            content=content,
            metadata=metadata,
            ttl_days=365,
        )

    # ------------------------------------------------------------------
    # Organization Operational Memory
    # ------------------------------------------------------------------
    async def get_organization_operational_memory(
        self, org_id: str,
    ) -> OrganizationMemoryReport:
        all_entries: list[MemoryEntry] = []

        for namespace in VALID_NAMESPACES:
            try:
                entries = await self.search_memory(namespace, limit=100)
                all_entries.extend(entries)
            except Exception:
                continue

        all_entries.sort(key=lambda e: e.stored_at, reverse=True)

        key_learnings: set[str] = set()
        patterns: set[str] = set()
        recommendations: set[str] = set()

        for entry in all_entries[:50]:
            content = entry.content
            if isinstance(content, dict):
                for field in ("decisions", "key_decisions"):
                    vals = content.get(field, [])
                    if isinstance(vals, list):
                        for v in vals[:3]:
                            key_learnings.add(str(v)[:200])

                for field in ("patterns", "key_patterns"):
                    vals = content.get(field, [])
                    if isinstance(vals, list):
                        for v in vals[:3]:
                            patterns.add(str(v)[:200])

                for field in ("recommendations",):
                    vals = content.get(field, [])
                    if isinstance(vals, list):
                        for v in vals[:3]:
                            recommendations.add(str(v)[:200])

            tags = entry.metadata.get("tags", [])
            for tag in tags:
                patterns.add(f"Tag: {tag}")

        summary = (
            f"Organization memory reconstructed from {len(all_entries)} entries "
            f"across {len(VALID_NAMESPACES)} namespaces. "
            f"{len(key_learnings)} learnings, {len(patterns)} patterns, "
            f"{len(recommendations)} recommendations extracted."
        )

        return OrganizationMemoryReport(
            summary=summary,
            key_learnings=list(key_learnings)[:20],
            patterns=list(patterns)[:20],
            recommendations=list(recommendations)[:20],
        )

    # ------------------------------------------------------------------
    # Infrastructure History
    # ------------------------------------------------------------------
    async def store_infrastructure_history(
        self,
        component: str,
        event_data: dict[str, Any],
    ) -> MemoryEntry:
        return await self.store_memory(
            namespace="workflow",
            key=f"infra_history:{component}:{int(time.time())}",
            content={
                "component": component,
                "event_type": event_data.get("event_type", "unknown"),
                "event_data": event_data,
                "timestamp": _now_iso(),
            },
            metadata={
                "component": component,
                "event_type": event_data.get("event_type", "unknown"),
                "tags": ["infrastructure", component],
            },
            ttl_days=365,
        )

    # ------------------------------------------------------------------
    # Incident Memory Reconstruction
    # ------------------------------------------------------------------
    async def reconstruct_incident_memory(
        self, incident_id: str,
    ) -> IncidentMemoryReconstruction:
        timeline: list[dict[str, Any]] = []
        related: list[dict[str, Any]] = []

        all_namespaces = list(VALID_NAMESPACES)
        for namespace in all_namespaces:
            try:
                entries = await self.search_memory(namespace, limit=100)
                for entry in entries:
                    content_str = str(entry.content)
                    meta_str = str(entry.metadata)
                    if incident_id in content_str or incident_id in meta_str:
                        related.append({
                            "namespace": entry.namespace,
                            "key": entry.key,
                            "content": entry.content,
                            "metadata": entry.metadata,
                            "stored_at": entry.stored_at,
                        })
                        timeline.append({
                            "timestamp": entry.stored_at,
                            "namespace": entry.namespace,
                            "key": entry.key,
                            "summary": entry.content.get("summary", "") if isinstance(entry.content, dict) else str(entry.content)[:200],
                        })
            except Exception:
                continue

        timeline.sort(key=lambda t: t.get("timestamp", ""))
        root_cause = ""
        resolution = ""
        findings: list[str] = []

        if timeline:
            root_cause = f"Incident reconstructed from {len(timeline)} memory entries"
            resolution = "Review memory lineage for detailed resolution path"

        for entry in related:
            content = entry.get("content", {})
            if isinstance(content, dict):
                for field in ("root_cause", "cause", "error"):
                    val = content.get(field)
                    if val:
                        findings.append(str(val)[:200])

        if not findings:
            findings.append(f"Incident {incident_id} reconstructed from memory — review logs for details")

        return IncidentMemoryReconstruction(
            incident_id=incident_id,
            timeline=timeline,
            related_entries=related[:30],
            root_cause=root_cause,
            resolution_path=resolution,
            key_findings=findings[:10],
        )

    # ------------------------------------------------------------------
    # Operational Cognition Replay
    # ------------------------------------------------------------------
    async def replay_operational_cognition(
        self, workflow_id: str,
    ) -> OperationalReplayCognition:
        timeline: list[dict[str, Any]] = []
        decisions: list[str] = []
        outcomes: list[str] = []
        patterns: list[str] = []
        recommendations: list[str] = []

        for namespace in VALID_NAMESPACES:
            try:
                entries = await self.search_memory(namespace, limit=100)
                for entry in entries:
                    if workflow_id in str(entry.metadata.get("workflow_id", "")) or \
                       workflow_id in str(entry.metadata.get("workflow_run_id", "")):
                        timeline.append({
                            "timestamp": entry.stored_at,
                            "namespace": entry.namespace,
                            "key": entry.key,
                            "content": entry.content,
                        })

                        content = entry.content
                        if isinstance(content, dict):
                            for d in content.get("decisions", []):
                                decisions.append(str(d)[:200])
                            for d in content.get("key_decisions", []):
                                decisions.append(str(d)[:200])
                            for o in content.get("outcomes", []):
                                outcomes.append(str(o)[:200])
                            for p in content.get("patterns", []):
                                patterns.append(str(p)[:200])
                            for p in content.get("key_patterns", []):
                                patterns.append(str(p)[:200])
                            for r in content.get("recommendations", []):
                                recommendations.append(str(r)[:200])
            except Exception:
                continue

        timeline.sort(key=lambda t: t.get("timestamp", ""))

        if not decisions:
            decisions.append("No explicit decisions recorded in memory")
        if not outcomes:
            outcomes.append("No outcomes recorded")
        if not patterns:
            patterns.append("No patterns extracted")
        if not recommendations:
            recommendations.append("Review workflow lineage for additional context")

        return OperationalReplayCognition(
            workflow_id=workflow_id,
            timeline=timeline,
            decisions=list(set(decisions))[:20],
            outcomes=list(set(outcomes))[:20],
            patterns=list(set(patterns))[:20],
            recommendations=list(set(recommendations))[:20],
        )

    # ------------------------------------------------------------------
    # Historical Optimization Learning
    # ------------------------------------------------------------------
    async def learn_from_historical_optimizations(self) -> OrganizationMemoryReport:
        all_entries: list[MemoryEntry] = []

        for namespace in ("workflow", "campaign"):
            try:
                entries = await self.search_memory(namespace, limit=200)
                all_entries.extend(entries)
            except Exception:
                continue

        optimization_entries = [
            e for e in all_entries
            if "optimization" in str(e.content).lower()
            or "optimize" in str(e.content).lower()
            or "improvement" in str(e.content).lower()
        ][:30]

        learnings: list[str] = []
        patterns_found: list[str] = []
        recs: list[str] = []

        if optimization_entries:
            history_text = ""
            for entry in optimization_entries[:15]:
                history_text += (
                    f"Entry [{entry.stored_at}] ({entry.namespace}/{entry.key}): "
                    f"{str(entry.content)[:300]}\n"
                )

            try:
                prompt = RenderedPrompt(
                    template_id="historical_optimization_learning",
                    system_prompt=(
                        "You are a machine learning engineer analyzing historical optimization data. "
                        "Extract learning patterns, recurring themes, and actionable recommendations. "
                        "Return valid JSON with: learnings (array of strings), patterns (array of strings), "
                        "recommendations (array of strings)."
                    ),
                    user_prompt=(
                        f"Historical Optimization Data:\n{history_text}\n\n"
                        f"Analyze these historical optimization entries and provide:\n"
                        f"1. Key learnings from past optimization efforts\n"
                        f"2. Recurring patterns in optimization data\n"
                        f"3. Actionable recommendations for future optimizations"
                    ),
                )

                class LearningOutput(BaseModel):
                    learnings: list[str]
                    patterns: list[str]
                    recommendations: list[str]

                result = await llm_gateway.complete(
                    task_type=TaskType.HISTORICAL_ANALYSIS,
                    prompt=prompt,
                    output_schema=LearningOutput,
                    tenant_id=UUID("00000000-0000-0000-0000-000000000000"),
                    temperature=0.3,
                )
                output: LearningOutput = result.content
                learnings = output.learnings
                patterns_found = output.patterns
                recs = output.recommendations
            except Exception as e:
                logger.warning("historical_optimization_llm_failed", error=str(e))
                learnings = [f"Analyzed {len(optimization_entries)} optimization entries — LLM analysis unavailable"]
                patterns_found = ["Manual review recommended"]
                recs = ["Enable LLM gateway for automated pattern extraction"]
        else:
            learnings = ["No historical optimization data available to analyze"]
            patterns_found = ["Insufficient data for pattern detection"]
            recs = ["Begin storing optimization metadata to enable future learning"]

        summary = (
            f"Analyzed {len(optimization_entries)} optimization entries out of "
            f"{len(all_entries)} total memory entries. "
            f"Extracted {len(learnings)} learnings, {len(patterns_found)} patterns, "
            f"{len(recs)} recommendations."
        )

        return OrganizationMemoryReport(
            summary=summary,
            key_learnings=learnings,
            patterns=patterns_found,
            recommendations=recs,
        )


semantic_memory = SemanticMemoryService()
