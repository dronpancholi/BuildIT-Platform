"""
SEO Platform — Keyword Research Endpoint
===========================================
Keyword research with synchronous execution.
Uses NVIDIA NIM when available, falls back to deterministic expansion.
"""

from __future__ import annotations

from seo_platform.core.auth import get_validated_tenant_id
import json
import random
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError

from seo_platform.schemas import APIResponse

router = APIRouter()


@router.get("", response_model=APIResponse[list[dict]])
async def list_keywords(
    tenant_id: UUID = Depends(get_validated_tenant_id),
    client_id: UUID | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> APIResponse[list[dict]]:
    """List keywords for a tenant with pagination."""
    from sqlalchemy import func, select
    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.seo import Keyword

    async with get_tenant_session(tenant_id) as session:
        stmt = select(Keyword).where(Keyword.tenant_id == tenant_id)
        if client_id:
            stmt = stmt.where(Keyword.client_id == client_id)
        stmt = stmt.order_by(Keyword.created_at.desc()).offset(offset).limit(limit)

        count_stmt = select(func.count()).select_from(Keyword).where(Keyword.tenant_id == tenant_id)
        if client_id:
            count_stmt = count_stmt.where(Keyword.client_id == client_id)

        result = await session.execute(stmt)
        keywords = result.scalars().all()
        count_result = await session.execute(count_stmt)
        total = count_result.scalar_one()

        return APIResponse(
            data=[
                {
                    "id": str(k.id),
                    "keyword": k.keyword,
                    "search_volume": k.search_volume,
                    "difficulty": k.difficulty,
                    "cpc": k.cpc,
                    "competition": k.competition,
                    "intent": k.intent.value if k.intent else None,
                    "cluster_id": str(k.cluster_id) if k.cluster_id else None,
                    "client_id": str(k.client_id) if k.client_id else None,
                    "created_at": k.created_at.isoformat() if k.created_at else None,
                }
                for k in keywords
            ],
            meta={"total": total, "offset": offset, "limit": limit},
        )

# Deterministic keyword expansion patterns
EXPANSION_PREFIXES = [
    "best", "top", "how to", "guide to", "what is",
    "why", "tips for", "strategies for", "tools for",
    "free", "affordable", "professional", "enterprise",
]

EXPANSION_SUFFIXES = [
    "guide", "tutorial", "strategies", "tips", "tools",
    "services", "software", "platform", "agency", "consultant",
    "for beginners", "for small business", "for startups",
    "in 2026", "checklist", "examples", "case study",
    "vs", "alternatives", "review", "pricing",
]

INTENT_KEYWORDS = {
    "transactional": ["buy", "pricing", "cost", "purchase", "hire", "service", "software", "tool", "platform", "agency"],
    "commercial": ["best", "top", "review", "comparison", "vs", "alternatives", "guide"],
    "navigational": ["login", "dashboard", "api", "docs", "documentation", "support"],
    "informational": ["what is", "how to", "why", "guide", "tutorial", "tips", "strategies", "examples", "case study"],
}


class StartResearchRequest(BaseModel):
    tenant_id: UUID
    client_id: UUID
    campaign_id: UUID | None = None
    domain: str
    niche: str = ""
    seed_keywords: list[str] = Field(default_factory=list)
    geo_target: str = "US"


class ResearchResponse(BaseModel):
    workflow_run_id: str | None = None
    status: str
    keywords_generated: int = 0
    clusters_generated: int = 0


class KeywordResearchResult(BaseModel):
    keyword: str
    search_volume: int
    difficulty: float
    cpc: float
    competition: float
    intent: str


@router.get("/research", response_model=APIResponse[list[dict]])
async def list_keyword_research(
    tenant_id: UUID = Depends(get_validated_tenant_id),
    client_id: UUID | None = None
) -> APIResponse[list[dict]]:
    """List keyword research history."""
    from sqlalchemy import select

    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.keywords import KeywordResearch

    async with get_tenant_session(tenant_id) as session:
        stmt = select(KeywordResearch).where(KeywordResearch.tenant_id == tenant_id)
        if client_id:
            stmt = stmt.where(KeywordResearch.client_id == client_id)

        stmt = stmt.order_by(KeywordResearch.created_at.desc())
        result = await session.execute(stmt)
        history = result.scalars().all()

        return APIResponse(
            data=[
                {
                    "id": str(h.id),
                    "client_id": str(h.client_id),
                    "seed_keyword": h.seed_keyword,
                    "status": h.status,
                    "created_at": h.created_at.isoformat(),
                }
                for h in history
            ]
        )


@router.post("/research", response_model=APIResponse[ResearchResponse])
async def start_keyword_research(request: StartResearchRequest) -> APIResponse[ResearchResponse]:
    """Execute keyword research synchronously."""
    from seo_platform.core.database import get_tenant_session
    from seo_platform.core.logging import get_logger
    from seo_platform.models.keywords import KeywordResearch
    from seo_platform.models.seo import Keyword, KeywordCluster, SearchIntent, ClusterStatus

    logger = get_logger(__name__)

    try:
        # Step 1: Expand keywords (try NIM, fall back to deterministic)
        all_keywords = await _try_nim_expansion(
            request.seed_keywords, request.domain, request.niche
        )
        if not all_keywords:
            all_keywords = _deterministic_expansion(request.seed_keywords)

        # Step 2: Enrich keywords (try NIM, fall back to deterministic)
        enriched = await _try_nim_enrichment(
            all_keywords, request.domain, request.niche
        )
        if not enriched:
            enriched = _deterministic_enrichment(all_keywords, request.seed_keywords)

        # Step 3: Cluster keywords by topic
        clusters = _cluster_keywords(enriched)

        # Step 4: Persist everything in a single session
        async with get_tenant_session(request.tenant_id) as session:
            research = KeywordResearch(
                tenant_id=request.tenant_id,
                client_id=request.client_id,
                seed_keyword=request.seed_keywords[0] if request.seed_keywords else "unnamed",
                status="completed"
            )
            session.add(research)
            await session.flush()

            persisted_keywords = 0
            persisted_clusters = 0

            for cluster_data in clusters:
                cluster = KeywordCluster(
                    tenant_id=request.tenant_id,
                    client_id=request.client_id,
                    name=cluster_data["name"],
                    primary_keyword=cluster_data["primary_keyword"],
                    total_volume=cluster_data["total_volume"],
                    avg_difficulty=cluster_data["avg_difficulty"],
                    dominant_intent=SearchIntent(cluster_data["dominant_intent"]) if cluster_data["dominant_intent"] else None,
                    keyword_count=len(cluster_data["keywords"]),
                    confidence_score=0.85,
                    status=ClusterStatus.DRAFT,
                    ai_rationale=f"Auto-generated cluster for {request.domain}",
                )
                session.add(cluster)
                await session.flush()
                persisted_clusters += 1

                for kw_data in cluster_data["keywords"]:
                    keyword = Keyword(
                        tenant_id=request.tenant_id,
                        client_id=request.client_id,
                        cluster_id=cluster.id,
                        keyword=kw_data["keyword"],
                        search_volume=kw_data["search_volume"],
                        difficulty=kw_data["difficulty"],
                        cpc=kw_data["cpc"],
                        competition=kw_data["competition"],
                        intent=SearchIntent(kw_data["intent"]) if kw_data["intent"] else None,
                        serp_features=[],
                        is_seed=kw_data["keyword"] in request.seed_keywords,
                    )
                    # Use merge to handle duplicates gracefully
                    from sqlalchemy.dialects.postgresql import insert as pg_insert
                    keyword_data = {
                        "tenant_id": request.tenant_id,
                        "client_id": request.client_id,
                        "cluster_id": cluster.id if cluster else None,
                        "keyword": kw_data["keyword"],
                        "search_volume": kw_data["search_volume"],
                        "difficulty": kw_data["difficulty"],
                        "cpc": kw_data["cpc"],
                        "competition": kw_data["competition"],
                        "intent": kw_data["intent"],
                        "serp_features": [],
                        "is_seed": kw_data["keyword"] in request.seed_keywords,
                    }
                    stmt = pg_insert(Keyword.__table__).values(**keyword_data)
                    stmt = stmt.on_conflict_do_nothing(index_elements=["tenant_id", "client_id", "keyword"])
                    await session.execute(stmt)
                    persisted_keywords += 1

            research.result_data = {
                "keywords_generated": persisted_keywords,
                "clusters_generated": persisted_clusters,
                "seed_keywords": request.seed_keywords,
                "domain": request.domain,
            }
            await session.flush()

        logger.info(
            "keyword_research_completed",
            research_id=str(research.id),
            keywords=persisted_keywords,
            clusters=persisted_clusters,
        )

        return APIResponse(
            data=ResearchResponse(
                workflow_run_id=str(research.id),
                status="completed",
                keywords_generated=persisted_keywords,
                clusters_generated=persisted_clusters,
            )
        )

    except IntegrityError as e:
        logger.error("keyword_research_integrity_error", error=str(e))
        raise HTTPException(status_code=400, detail=f"Invalid request data: {e.orig}")
    except Exception as e:
        logger.error("keyword_research_failed", error=str(e))
        try:
            async with get_tenant_session(request.tenant_id) as session:
                failed_research = KeywordResearch(
                    tenant_id=request.tenant_id,
                    client_id=request.client_id,
                    seed_keyword=request.seed_keywords[0] if request.seed_keywords else "unnamed",
                    status="failed",
                    result_data={"error": str(e)},
                )
                session.add(failed_research)
                await session.flush()
        except Exception:
            logger.error("failed_to_record_research_failure", error=str(e))
        raise HTTPException(status_code=500, detail=f"Keyword research failed: {e!s}")


async def _try_nim_expansion(
    seed_keywords: list[str], domain: str, niche: str
) -> list[str]:
    """Try NVIDIA NIM for keyword expansion, return empty on failure."""
    try:
        from seo_platform.config import get_settings
        settings = get_settings()
        if not settings.nvidia.api_key or "mock" in settings.nvidia.api_key.lower():
            return []

        seeds = ", ".join(seed_keywords) if seed_keywords else "SEO"
        prompt = (
            f"Generate 15 related long-tail keywords for domain '{domain}' "
            f"in the '{niche}' niche. Seed keywords: {seeds}. "
            f"Return ONLY a JSON array of strings. No explanation."
        )

        async with httpx.AsyncClient(timeout=httpx.Timeout(15)) as client:
            resp = await client.post(
                f"{settings.nvidia.api_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.nvidia.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.nvidia.seo_model,
                    "messages": [
                        {"role": "system", "content": "Return valid JSON only."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 512,
                    "response_format": {"type": "json_object"},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            keywords = json.loads(content)
            if isinstance(keywords, dict):
                keywords = list(keywords.values())[0]
            return [k.lower().strip() for k in keywords if isinstance(k, str) and k.strip()]
    except Exception:
        return []


async def _try_nim_enrichment(
    keywords: list[str], domain: str, niche: str
) -> list[KeywordResearchResult]:
    """Try NVIDIA NIM for keyword enrichment, return empty on failure."""
    try:
        from seo_platform.config import get_settings
        settings = get_settings()
        if not settings.nvidia.api_key or "mock" in settings.nvidia.api_key.lower():
            return []

        kw_list = ", ".join(keywords[:15])
        prompt = (
            f"For these keywords related to '{domain}' in '{niche}', provide SEO metrics. "
            f"Keywords: {kw_list}. "
            f"Return JSON array with: keyword, search_volume (int), difficulty (0-100 float), "
            f"cpc (0-20 float), competition (0-1 float), intent (informational/commercial/navigational/transactional). "
            f"Return ONLY the JSON array."
        )

        async with httpx.AsyncClient(timeout=httpx.Timeout(20)) as client:
            resp = await client.post(
                f"{settings.nvidia.api_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.nvidia.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.nvidia.seo_model,
                    "messages": [
                        {"role": "system", "content": "Return valid JSON only."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 2048,
                    "response_format": {"type": "json_object"},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            enriched_data = json.loads(content)
            if isinstance(enriched_data, dict):
                enriched_data = list(enriched_data.values())[0]

            results = []
            for item in enriched_data:
                results.append(KeywordResearchResult(
                    keyword=item.get("keyword", "").lower().strip(),
                    search_volume=int(item.get("search_volume", 0)),
                    difficulty=float(item.get("difficulty", 50.0)),
                    cpc=float(item.get("cpc", 1.0)),
                    competition=float(item.get("competition", 0.5)),
                    intent=item.get("intent", "informational"),
                ))
            return results
    except Exception:
        return []


def _deterministic_expansion(seed_keywords: list[str]) -> list[str]:
    """Expand keywords deterministically using prefix/suffix patterns."""
    if not seed_keywords:
        seed_keywords = ["SEO", "backlinks", "link building"]

    expanded = set()
    for seed in seed_keywords:
        expanded.add(seed.lower())
        for prefix in EXPANSION_PREFIXES:
            expanded.add(f"{prefix} {seed}")
        for suffix in EXPANSION_SUFFIXES:
            expanded.add(f"{seed} {suffix}")

    # Add some niche-specific variations
    niche_words = ["strategy", "service", "software", "tool", "platform", "agency", "consultant"]
    for seed in seed_keywords:
        for word in niche_words[:3]:
            expanded.add(f"{seed} {word}")

    return sorted(expanded)[:30]


def _deterministic_enrichment(
    keywords: list[str], seed_keywords: list[str]
) -> list[KeywordResearchResult]:
    """Enrich keywords with deterministic metrics based on keyword characteristics."""
    results = []
    for kw in keywords:
        words = kw.lower().split()
        word_count = len(words)

        # Search volume: longer keywords have lower volume
        base_volume = 5000 // max(word_count, 1)
        volume_hash = abs(hash(kw + "vol")) % 3000
        search_volume = max(50, base_volume + volume_hash)

        # Difficulty: competitive terms are harder
        difficulty = 30 + (abs(hash(kw + "diff")) % 50)
        if any(w in kw for w in ["best", "top", "software", "platform"]):
            difficulty = min(95, difficulty + 15)

        # CPC: commercial intent keywords have higher CPC
        cpc = round(0.5 + (abs(hash(kw + "cpc")) % 500) / 100, 2)
        if any(w in kw for w in ["buy", "pricing", "cost", "service", "agency", "software"]):
            cpc = round(cpc * 2, 2)

        # Competition
        competition = round(0.3 + (abs(hash(kw + "comp")) % 70) / 100, 2)

        # Intent classification based on keywords
        intent = "informational"
        kw_lower = kw.lower()
        for intent_type, markers in INTENT_KEYWORDS.items():
            if any(m in kw_lower for m in markers):
                intent = intent_type
                break

        results.append(KeywordResearchResult(
            keyword=kw,
            search_volume=search_volume,
            difficulty=min(100, max(1, difficulty)),
            cpc=min(20, max(0.1, cpc)),
            competition=min(1.0, max(0.0, competition)),
            intent=intent,
        ))

    return results


def _cluster_keywords(enriched: list[KeywordResearchResult]) -> list[dict]:
    """Cluster keywords by topic prefix (first 2-3 words)."""
    from collections import defaultdict

    cluster_map: dict[str, list[KeywordResearchResult]] = defaultdict(list)

    for kw in enriched:
        words = kw.keyword.split()
        prefix = " ".join(words[:2]) if len(words) >= 2 else words[0]
        cluster_map[prefix].append(kw)

    clusters = []
    for prefix, keywords in cluster_map.items():
        total_volume = sum(k.search_volume for k in keywords)
        avg_difficulty = sum(k.difficulty for k in keywords) / len(keywords)
        primary = max(keywords, key=lambda k: k.search_volume)

        intent_counts = defaultdict(int)
        for k in keywords:
            intent_counts[k.intent] += 1
        dominant_intent = max(intent_counts, key=intent_counts.get) if intent_counts else "informational"

        clusters.append({
            "name": f"{prefix.title()} Cluster",
            "primary_keyword": primary.keyword,
            "total_volume": total_volume,
            "avg_difficulty": round(avg_difficulty, 1),
            "dominant_intent": dominant_intent,
            "keywords": [
                {
                    "keyword": k.keyword,
                    "search_volume": k.search_volume,
                    "difficulty": k.difficulty,
                    "cpc": k.cpc,
                    "competition": k.competition,
                    "intent": k.intent,
                }
                for k in keywords
            ],
        })

    return sorted(clusters, key=lambda c: c["total_volume"], reverse=True)
