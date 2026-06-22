"""
Phase 12I — SEO Copilot V2
============================
Evidence-backed answers to SEO questions.

Answers cite actual platform data.
If data unavailable, says so honestly.
Never fabricates.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text

from seo_platform.core.auth import get_current_user, CurrentUser
from seo_platform.core.database import get_session

router = APIRouter()


class CopilotQuestion(BaseModel):
    question: str
    client_id: str | None = None


def _detect_intent(question: str) -> list[str]:
    """Detect what the operator is asking about."""
    q = question.lower()
    intents = []
    if any(w in q for w in ["ranking", "rank", "position", "serp"]):
        intents.append("rankings")
    if any(w in q for w in ["campaign", "outreach", "email", "thread"]):
        intents.append("campaigns")
    if any(w in q for w in ["keyword", "volume", "difficulty", "search"]):
        intents.append("keywords")
    if any(w in q for w in ["backlink", "link", "domain authority", "da"]):
        intents.append("backlinks")
    if any(w in q for w in ["citation", "directory", "nap", "listing"]):
        intents.append("citations")
    if any(w in q for w in ["prospect", "target", "outreach"]):
        intents.append("prospects")
    if any(w in q for w in ["local", "near me", "google business", "reviews"]):
        intents.append("local_seo")
    if any(w in q for w in ["health", "status", "performance"]):
        intents.append("health")
    if any(w in q for w in ["recommend", "suggest", "should", "next", "do"]):
        intents.append("recommendations")
    if any(w in q for w in ["drop", "decline", "lost", "decrease", "why"]):
        intents.append("diagnosis")
    if not intents:
        intents.append("general")
    return intents


async def _gather_evidence(session, intents: list[str], tenant_id: str, client_id: str | None) -> dict:
    """Gather relevant data from the platform to answer the question."""
    evidence = {}

    if "campaigns" in intents or "health" in intents or "diagnosis" in intents:
        campaigns = await session.execute(
            text("""
                SELECT name, status, health_score, acquisition_rate, reply_rate,
                       target_link_count, acquired_link_count, started_at
                FROM backlink_campaigns
                WHERE tenant_id = :tid
                ORDER BY updated_at DESC LIMIT 10
            """),
            {"tid": tenant_id},
        )
        evidence["campaigns"] = []
        for row in campaigns.fetchall():
            evidence["campaigns"].append({
                "name": row[0],
                "status": row[1],
                "health_score": float(row[2]) if row[2] else None,
                "acquisition_rate": float(row[3]) if row[3] else None,
                "reply_rate": float(row[4]) if row[4] else None,
                "target": row[5],
                "acquired": row[6],
                "started": str(row[7]) if row[7] else None,
            })

    if "keywords" in intents:
        kws = await session.execute(
            text("""
                SELECT keyword, search_volume, difficulty, cpc, intent
                FROM keywords
                WHERE tenant_id = :tid
                ORDER BY search_volume DESC NULLS LAST LIMIT 10
            """),
            {"tid": tenant_id},
        )
        evidence["keywords"] = []
        for row in kws.fetchall():
            evidence["keywords"].append({
                "keyword": row[0],
                "volume": row[1],
                "difficulty": row[2],
                "cpc": float(row[3]) if row[3] else None,
                "intent": row[4],
            })

    if "prospects" in intents or "backlinks" in intents:
        prospects = await session.execute(
            text("""
                SELECT domain, domain_authority, relevance_score, spam_score,
                       composite_score, status
                FROM backlink_prospects
                WHERE tenant_id = :tid
                ORDER BY composite_score DESC NULLS LAST LIMIT 10
            """),
            {"tid": tenant_id},
        )
        evidence["prospects"] = []
        for row in prospects.fetchall():
            evidence["prospects"].append({
                "domain": row[0],
                "da": float(row[1]) if row[1] else None,
                "relevance": float(row[2]) if row[2] else None,
                "spam": float(row[3]) if row[3] else None,
                "composite": float(row[4]) if row[4] else None,
                "status": row[5],
            })

    if "citations" in intents or "local_seo" in intents:
        citations = await session.execute(
            text("""
                SELECT COUNT(*), status
                FROM citation_submissions
                WHERE tenant_id = :tid
                GROUP BY status
            """),
            {"tid": tenant_id},
        )
        evidence["citations_by_status"] = {row[1]: row[0] for row in citations.fetchall()}

        cite_projects = await session.execute(
            text("""
                SELECT COUNT(*) FROM citation_projects WHERE tenant_id = :tid
            """),
            {"tid": tenant_id},
        )
        evidence["citation_projects"] = cite_projects.scalar() or 0

    if "recommendations" in intents:
        recs = await session.execute(
            text("""
                SELECT title, priority, status, confidence, impact_score
                FROM recommendations
                WHERE tenant_id = :tid
                ORDER BY
                    CASE priority WHEN 'P0' THEN 1 WHEN 'P1' THEN 2 WHEN 'P2' THEN 3 ELSE 4 END
                LIMIT 5
            """),
            {"tid": tenant_id},
        )
        evidence["recommendations"] = []
        for row in recs.fetchall():
            evidence["recommendations"].append({
                "title": row[0],
                "priority": row[1],
                "status": row[2],
                "confidence": float(row[3]) if row[3] else None,
                "impact": float(row[4]) if row[4] else None,
            })

    if "rankings" in intents:
        # Check SERP volatility
        volatility = await session.execute(
            text("""
                SELECT keyword, volatility_score, position_changes
                FROM serp_volatility_snapshots
                WHERE tenant_id = :tid
                ORDER BY volatility_score DESC NULLS LAST LIMIT 5
            """),
            {"tid": tenant_id},
        )
        evidence["serp_volatility"] = []
        for row in volatility.fetchall():
            evidence["serp_volatility"].append({
                "keyword": row[0],
                "volatility": float(row[1]) if row[1] else None,
                "position_changes": row[2],
            })

    # Client info
    if client_id:
        client = await session.execute(
            text("SELECT name, domain, niche FROM clients WHERE id = :cid AND tenant_id = :tid"),
            {"cid": client_id, "tid": tenant_id},
        )
        cr = client.fetchone()
        if cr:
            evidence["client"] = {"name": cr[0], "domain": cr[1], "niche": cr[2]}

    # Overall stats
    total_campaigns = await session.execute(
        text("SELECT COUNT(*) FROM backlink_campaigns WHERE tenant_id = :tid"),
        {"tid": tenant_id},
    )
    evidence["total_campaigns"] = total_campaigns.scalar() or 0

    total_prospects = await session.execute(
        text("SELECT COUNT(*) FROM backlink_prospects WHERE tenant_id = :tid"),
        {"tid": tenant_id},
    )
    evidence["total_prospects"] = total_prospects.scalar() or 0

    total_keywords = await session.execute(
        text("SELECT COUNT(*) FROM keywords WHERE tenant_id = :tid"),
        {"tid": tenant_id},
    )
    evidence["total_keywords"] = total_keywords.scalar() or 0

    return evidence


def _generate_answer(question: str, intents: list[str], evidence: dict) -> str:
    """Generate an evidence-backed answer."""
    parts = []

    if "diagnosis" in intents:
        parts.append("**Diagnosis:**")
        campaigns = evidence.get("campaigns", [])
        if not campaigns:
            parts.append("No campaign data found. Create a campaign to start tracking SEO performance.")
        else:
            failed = [c for c in campaigns if c["status"] in ("cancelled", "failed")]
            paused = [c for c in campaigns if c["status"] == "paused"]
            active = [c for c in campaigns if c["status"] == "active"]

            if failed:
                parts.append(f"- {len(failed)} campaign(s) failed/cancelled: {', '.join(c['name'] for c in failed[:3])}")
            if paused:
                parts.append(f"- {len(paused)} campaign(s) paused: {', '.join(c['name'] for c in paused[:3])}")
            if active:
                avg_health = sum(c['health_score'] or 0 for c in active) / len(active) if active else 0
                parts.append(f"- {len(active)} active campaign(s), average health: {avg_health:.0%}")

            low_health = [c for c in active if (c['health_score'] or 0) < 0.5]
            if low_health:
                parts.append(f"- WARNING: {len(low_health)} campaign(s) with health below 50%: {', '.join(c['name'] for c in low_health[:3])}")

    if "campaigns" in intents:
        parts.append("\n**Campaign Status:**")
        campaigns = evidence.get("campaigns", [])
        if not campaigns:
            parts.append("No campaigns found.")
        else:
            for c in campaigns[:5]:
                parts.append(f"- {c['name']}: {c['status']} (health: {c['health_score'] or 'N/A'}, acquired: {c['acquired']}/{c['target']})")

    if "keywords" in intents:
        parts.append("\n**Keywords:**")
        kws = evidence.get("keywords", [])
        if not kws:
            parts.append("No keywords tracked. Add keywords via the Keywords page to start monitoring rankings.")
        else:
            for k in kws[:5]:
                parts.append(f"- '{k['keyword']}': volume {k['volume'] or 'N/A'}, difficulty {k['difficulty'] or 'N/A'}, intent: {k['intent'] or 'unknown'}")

    if "prospects" in intents:
        parts.append("\n**Prospects:**")
        prospects = evidence.get("prospects", [])
        if not prospects:
            parts.append("No prospects discovered yet. Run prospect discovery on a campaign to find link opportunities.")
        else:
            for p in prospects[:5]:
                parts.append(f"- {p['domain']}: DA {p['da'] or 'N/A'}, relevance {p['relevance'] or 'N/A'}, status: {p['status']}")

    if "citations" in intents or "local_seo" in intents:
        parts.append("\n**Citations:**")
        cite_status = evidence.get("citations_by_status", {})
        if not cite_status:
            parts.append("No citation submissions found. Create a citation project to start building local citations.")
        else:
            total = sum(cite_status.values())
            parts.append(f"- {total} total submissions: {', '.join(f'{v} {k}' for k, v in cite_status.items())}")

    if "recommendations" in intents:
        parts.append("\n**Recommendations:**")
        recs = evidence.get("recommendations", [])
        if not recs:
            parts.append("No recommendations generated yet.")
        else:
            for r in recs[:3]:
                parts.append(f"- [{r['priority']}] {r['title']} (impact: {r['impact'] or 'N/A'})")

    if "rankings" in intents:
        parts.append("\n**SERP Volatility:**")
        volatility = evidence.get("serp_volatility", [])
        if not volatility:
            parts.append("No SERP tracking data. Add keywords to track ranking changes.")
        else:
            for v in volatility[:3]:
                parts.append(f"- '{v['keyword']}': volatility {v['volatility'] or 'N/A'}, changes: {v['position_changes'] or 'N/A'}")

    if not parts:
        parts.append("I don't have enough data to answer that question. The platform needs more data to provide insights.")

    # Add data source notice
    parts.append("\n---")
    parts.append("*Data sourced from platform database. All metrics are real — no fabricated values.*")

    return "\n".join(parts)


@router.post("/ask")
async def ask_copilot(
    req: CopilotQuestion,
    user: CurrentUser = Depends(get_current_user),
):
    """Ask the SEO Copilot a question. Returns evidence-backed answer."""
    async with get_session() as session:
        intents = _detect_intent(req.question)
        evidence = await _gather_evidence(session, intents, str(user.tenant_id), req.client_id)
        answer = _generate_answer(req.question, intents, evidence)

    return {
        "success": True,
        "data": {
            "question": req.question,
            "answer": answer,
            "intents_detected": intents,
            "evidence_summary": {
                "campaigns": len(evidence.get("campaigns", [])),
                "keywords": len(evidence.get("keywords", [])),
                "prospects": len(evidence.get("prospects", [])),
                "total_campaigns": evidence.get("total_campaigns", 0),
                "total_prospects": evidence.get("total_prospects", 0),
                "total_keywords": evidence.get("total_keywords", 0),
            },
            "data_completeness": "low" if evidence.get("total_keywords", 0) == 0 else "medium" if evidence.get("total_prospects", 0) == 0 else "high",
        },
        "error": None,
    }
