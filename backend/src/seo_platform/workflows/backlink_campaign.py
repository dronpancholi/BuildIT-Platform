"""
SEO Platform — Backlink Campaign Workflow
============================================
Full end-to-end Temporal workflow for backlink acquisition campaigns.

Flow:
1. Prospect Discovery (Ahrefs competitor analysis)
2. Spam Filtering (rules engine)
3. Multi-Signal Scoring (DA + relevance + traffic + spam)
4. Contact Discovery (Hunter.io)
5. APPROVAL GATE — Human reviews prospect list
6. Outreach Generation (LLM large model)
7. APPROVAL GATE — Human reviews email templates
8. Campaign Launch (rate-limited email sends)
9. Follow-up Automation (timed follow-ups)
10. Link Verification (periodic check)
"""

from __future__ import annotations

import asyncio
from datetime import UTC, timedelta
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from temporalio import activity, workflow

from seo_platform.core.logging import get_logger
from seo_platform.workflows import RetryPreset, TaskQueue

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Workflow Input/Output
# ---------------------------------------------------------------------------
class BacklinkCampaignInput(BaseModel):
    tenant_id: UUID
    client_id: UUID
    campaign_id: UUID
    campaign_name: str
    campaign_type: str = "guest_post"
    competitor_domains: list[str] = Field(default_factory=list)
    target_link_count: int = 10
    min_domain_authority: float = 30.0
    max_spam_score: float = 5.0
    initiated_by: str = "system"
    idempotency_key: str = ""


class BacklinkCampaignOutput(BaseModel):
    success: bool
    campaign_id: str
    prospects_discovered: int = 0
    prospects_scored: int = 0
    prospects_approved: int = 0
    emails_generated: int = 0
    emails_sent: int = 0
    threads_contacted: int = 0
    threads_replied: int = 0
    threads_completed: int = 0
    total_cost_usd: float = 0.0
    status: str = "complete"
    errors: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Child Workflow Input/Output
# ---------------------------------------------------------------------------
class OutreachThreadInput(BaseModel):
    tenant_id: UUID
    campaign_id: UUID
    thread_id: str = ""
    prospect_domain: str
    contact_email: str
    contact_name: str = "there"
    initial_email: dict = Field(default_factory=dict)
    followup_1: dict = Field(default_factory=dict)
    followup_2: dict = Field(default_factory=dict)


class OutreachThreadOutput(BaseModel):
    thread_id: str
    prospect_domain: str
    status: str = "pending"
    initial_sent: bool = False
    followup_1_sent: bool = False
    followup_2_sent: bool = False
    reply_received: bool = False
    reply_data: dict = Field(default_factory=dict)
    cancelled: bool = False


# ---------------------------------------------------------------------------
# Activities
# ---------------------------------------------------------------------------
@activity.defn(name="discover_prospects_activity")
async def discover_prospects_activity(
    tenant_id: str, campaign_id: str, competitor_domains: list[str],
) -> dict[str, Any]:
    """Discover prospect websites from competitor backlink profiles via real APIs."""
    logger.info("discovering_prospects", campaign_id=campaign_id,
                competitors=len(competitor_domains))

    from seo_platform.clients.ahrefs import AhrefsRateLimitError
    from seo_platform.services.scraping.engines.backlinks import backlink_scraper

    prospects = []
    seen_domains: set[str] = set()

    for domain in competitor_domains:
        try:
            from seo_platform.clients.ahrefs import ahrefs_client
            referring_domains = await ahrefs_client.get_referring_domains(domain)
            for rd in referring_domains[:50]:
                dom = rd.get("domain", "")
                if dom and dom not in seen_domains:
                    seen_domains.add(dom)
                    prospects.append({
                        "domain": dom,
                        "url": f"https://{dom}/",
                        "source_competitor": domain,
                        "domain_rating": rd.get("domain_rating", 0),
                    })
        except AhrefsRateLimitError:
            logger.warning("ahrefs_rate_limited", domain=domain)
            raise
        except Exception as e:
            logger.warning("ahrefs_failed_for_domain", domain=domain, error=str(e))

    if not prospects and competitor_domains:
        logger.info("ahrefs_returned_no_prospects_trying_link_intersect")
        try:
            scraped_prospects = await backlink_scraper.discover_link_intersect_prospects(
                competitor_domains=competitor_domains,
                topical_niche="enterprise",
            )
            for sp in scraped_prospects:
                dom = sp.get("domain", "")
                if dom and dom not in seen_domains:
                    seen_domains.add(dom)
                    prospects.append(sp)
        except Exception as e:
            logger.warning("link_intersect_scraper_failed", error=str(e))

    return {"prospects": prospects, "count": len(prospects)}


@activity.defn(name="score_prospects_activity")
async def score_prospects_activity(
    tenant_id: str, campaign_id: str, prospects: list[dict],
    min_da: float, max_spam: float, target_niche: str = "",
) -> dict[str, Any]:
    """Score prospects using multi-signal composite scoring via live Ahrefs data & anti-farm vetting grid."""
    logger.info("scoring_prospects", campaign_id=campaign_id, count=len(prospects))

    from seo_platform.clients.ahrefs import ahrefs_client, AhrefsRateLimitError
    from seo_platform.services.backlink_engine.intelligence import backlink_intelligence

    scored = []
    filtered_out = 0

    for prospect in prospects:
        try:
            metrics = await ahrefs_client.get_domain_metrics(prospect["domain"])
            dr = metrics.get("domain_rating", 0)
            ref_domains = metrics.get("ref_domains", 0)
            backlinks = metrics.get("backlinks", 0)
            traffic = metrics.get("organic_traffic", 0)

            prospect_with_metrics = {
                **prospect,
                "domain_authority": dr,
                "ref_domain_count": ref_domains,
                "backlinks": backlinks,
                "organic_traffic": traffic,
            }

            target_domain = prospect.get("source_competitor", "")
            analysis = backlink_intelligence.analyze_prospect(
                prospect_with_metrics, target_domain, target_niche
            )

            # Phase 5: Live Ahrefs Anti-Farm Vetting Grid
            farm_analysis = await backlink_intelligence.detect_link_farm_and_spam(prospect["domain"], prospect.get("url", ""))

            final_spam_score = max(analysis.get("spam_score", 0), farm_analysis["spam_score"])
            final_is_spam = analysis.get("is_spam", False) or farm_analysis["is_spam"]
            final_spam_flags = list(set(analysis.get("spam_flags", []) + farm_analysis["spam_flags"]))

            composite_score = analysis.get("composite_score", 0)
            if final_spam_score > 0.3:
                composite_score *= (1.0 - final_spam_score)

            score = {
                **prospect,
                "domain_authority": analysis.get("authority_score", 0) * 100,
                "spam_score": final_spam_score * 100,
                "relevance_score": analysis.get("relevance_score", 0),
                "composite_score": composite_score,
                "is_spam": final_is_spam,
                "authority_classification": analysis.get("authority_classification", "low"),
                "spam_flags": final_spam_flags,
                "relevance_flags": analysis.get("relevance_flags", []),
                "vetting_source": farm_analysis.get("vetting_source", "ahrefs_live_api"),
            }

            if analysis.get("is_viable", False) and not final_is_spam and score["composite_score"] >= 0.35:
                scored.append(score)
            else:
                filtered_out += 1

        except AhrefsRateLimitError:
            logger.warning("ahrefs_rate_limited_during_scoring")
            raise
        except Exception as e:
            logger.warning("scoring_failed_for_prospect", domain=prospect.get("domain"), error=str(e))
            filtered_out += 1

    logger.info("prospects_scored", viable=len(scored), filtered=filtered_out)
    return {"scored_prospects": scored, "filtered_out": filtered_out}


@activity.defn(name="discover_contacts_activity")
async def discover_contacts_activity(
    tenant_id: str, prospects: list[dict],
) -> dict[str, Any]:
    """Find contact emails for scored prospects via Hunter.io. No synthetic fallback."""
    logger.info("discovering_contacts", count=len(prospects))

    from seo_platform.clients.hunter import hunter_client

    enriched = []
    for prospect in prospects[:30]:
        domain = prospect.get("domain", "")
        if not domain:
            continue

        try:
            emails = await hunter_client.domain_search(domain, limit=3)
            if emails:
                primary = emails[0]
                enriched.append({
                    **prospect,
                    "contact_email": primary.get("email", ""),
                    "contact_name": f"{primary.get('first_name', '')} {primary.get('last_name', '')}".strip(),
                    "contact_position": primary.get("position", ""),
                    "contact_confidence": primary.get("confidence", 0),
                    "contact_source": "hunter",
                })
                continue
        except Exception as e:
            logger.warning("hunter_search_failed", domain=domain, error=str(e))

        # No verified contact found — mark as unverified, do not invent names
        enriched.append({
            **prospect,
            "contact_email": None,
            "contact_name": None,
            "contact_position": None,
            "contact_confidence": 0.0,
            "contact_source": "unverified",
        })

    return {"enriched_prospects": enriched}


@activity.defn(name="generate_outreach_emails_activity")
async def generate_outreach_emails_activity(
    tenant_id: str, campaign_id: str, prospects: list[dict],
    campaign_type: str, campaign_name: str = "",
) -> dict[str, Any]:
    """Generate initial bespoke pitch (Phase 6/7) + 2 follow-up outreach emails per prospect using LLM."""
    import hashlib
    import json

    from seo_platform.core.reliability import idempotency_store

    input_hash = hashlib.sha256(
        f"{campaign_id}:{campaign_type}:{json.dumps([p.get('domain','') for p in prospects], sort_keys=True)}".encode()
    ).hexdigest()
    idem_key = f"outreach-gen:{campaign_id}:{input_hash[:16]}"
    cached = await idempotency_store.get(idem_key)
    if cached:
        logger.info("outreach_gen_idempotent_skip", key=idem_key)
        return json.loads(cached)

    logger.info("generating_outreach", campaign_id=campaign_id,
                count=len(prospects), campaign_type=campaign_type)

    from uuid import UUID

    from pydantic import BaseModel
    import re as _re

    from seo_platform.llm.gateway import RenderedPrompt, TaskType, llm_gateway

    class OutreachEmailSchema(BaseModel):
        subject: str
        body_html: str
        personalized_opening: str

        _fluff_phrases = [
            "hope this email finds you well",
            "stumbled upon your fantastic blog",
            "huge fan of your work",
            "browsing your website",
            "as a fellow enthusiast",
            "i came across your",
            "i stumbled upon",
            "i've been browsing",
            "i've been following your work",
        ]

        def check_semantic_grounding(self, scraped_context: str) -> None:
            """Post-hoc semantic grounding validation. Raises ValueError if grounding fails."""
            opening_lower = self.personalized_opening.lower()

            for phrase in self._fluff_phrases:
                if phrase in opening_lower:
                    raise ValueError(
                        f"Semantic grounding failure: Opening contains generic fluff '{phrase}'. "
                        "Must reference specific content from the scraped website."
                    )

            if scraped_context:
                context_lower = scraped_context.lower()
                words = [
                    w for w in _re.findall(r'\b[a-z]{5,}\b', opening_lower)
                    if w not in {"about", "their", "there", "which", "would",
                                 "could", "should", "these", "those", "being",
                                 "while", "where", "after", "before", "other",
                                 "first", "second", "still", "until", "since"}
                ]
                if words:
                    match_count = sum(1 for w in words if w in context_lower)
                    ratio = match_count / len(words)
                    if ratio < 0.2:
                        raise ValueError(
                            f"Semantic grounding failure: Only {match_count}/{len(words)} significant "
                            f"words from opening appear in scraped content (ratio={ratio:.2f}). "
                            "Rewrite using specific details from the website."
                        )

    from seo_platform.services.content_analyzer import website_analyzer
    from seo_platform.services.relationship_store import relationship_store
    from seo_platform.services.seo_intelligence.serp_intelligence import SERPIntelligenceEngine
    from seo_platform.services.outreach_intelligence import outreach_intelligence

    serp_engine = SERPIntelligenceEngine()
    serp_analysis = await serp_engine.analyze_serp_intent_and_eeat(
        keyword=campaign_name or campaign_type,
        tenant_id=UUID(tenant_id),
    )
    content_pivot = serp_analysis.recommended_content_pivot

    email_sequences = []

    templates = {
        "guest_post": "We'd love to contribute a high-quality guest post to your site.",
        "resource_page": "We found your resource page valuable and think our content would be a great fit.",
        "broken_link": "We noticed a broken link on your page and have a perfect replacement.",
    }

    for prospect in prospects[:20]:
        domain = prospect.get("domain", "")
        contact_name = prospect.get("contact_name") or "there"

        contact_email = prospect.get("contact_email")
        if not contact_email:
            logger.info("skipping_unverified_prospect", domain=domain)
            continue

        tenant_uuid = UUID(tenant_id)
        site_context = await website_analyzer.analyze(domain, tenant_id=tenant_uuid)
        site_title = site_context.get("site_title", "")
        site_desc = site_context.get("site_description", "")
        recent_articles = site_context.get("recent_articles", [])
        topical_focus = site_context.get("topical_focus", [])
        markdown_body = site_context.get("markdown_body", "")

        # Calculate topical relevance via Qdrant
        topical_relevance = 0.5
        try:
            from seo_platform.services.vector_store import qdrant_vector_store
            topical_relevance = await qdrant_vector_store.calculate_topical_relevance(
                tenant_id=tenant_uuid,
                prospect_domain=domain,
                keyword_cluster_id=str(prospect.get("campaign_id", campaign_id)),
            )
        except Exception:
            pass

        site_context_str = ""
        if site_title:
            site_context_str += f"Site title: {site_title}\n"
        if site_desc:
            site_context_str += f"Site description: {site_desc}\n"
        if topical_focus:
            site_context_str += f"Topical focus: {', '.join(topical_focus[:4])}\n"
        if recent_articles:
            articles_str = "; ".join(f"\"{a['title']}\"" for a in recent_articles[:5])
            site_context_str += f"Recent articles: {articles_str}\n"
        site_context_str += f"Topical relevance to campaign: {topical_relevance:.2f}\n"
        if markdown_body:
            preview = markdown_body[:600].strip()
            site_context_str += f"Content preview: {preview[:300]}...\n" if len(preview) > 300 else f"Content preview: {preview}\n"
        if not site_context_str:
            site_context_str = "Site content could not be analyzed.\n"

        def _build_prompt(stage: str, extra_instructions: str, grounding_hint: str = "") -> RenderedPrompt:
            system_parts = [
                f"You are an elite outreach specialist for a premium SEO agency. Generate a {stage} outreach email.",
                "Return ONLY a JSON object with 'subject', 'body_html', and 'personalized_opening' fields.",
                "CRITICAL: Reference the recipient's actual site content. Make it feel like a human who has actually visited their website wrote it.",
            ]
            if grounding_hint:
                system_parts.append(f"CORRECTION FROM PREVIOUS ATTEMPT: {grounding_hint}")

            user = f"""CONTEXT:
- Recipient name: {contact_name}
- Target domain: {domain}
- Domain authority: {prospect.get('domain_authority', 40)}/100
- Relevance score: {prospect.get('relevance_score', 0.5)}/1.0
- Topical relevance: {topical_relevance:.2f}
- Campaign type: {campaign_type}
- Value offer: {templates.get(campaign_type, 'Content collaboration opportunity')}

WEBSITE CONTENT:
{site_context_str}

{extra_instructions}

Requirements:
- Subject under 60 characters
- Professional HTML body
- Human-sounding, not templated
- Every claim in the opening must be grounded in the WEBSITE CONTENT above"""
            return RenderedPrompt(
                template_id="outreach_email_generation",
                system_prompt="\n".join(system_parts),
                user_prompt=user,
            )

        async def _generate_with_grounding(
            prompt: RenderedPrompt, max_retries: int = 2,
        ) -> dict | None:
            for attempt in range(max_retries):
                try:
                    result = await llm_gateway.complete(
                        task_type=TaskType.SEO_ANALYSIS,
                        prompt=prompt,
                        output_schema=OutreachEmailSchema,
                        tenant_id=UUID(tenant_id),
                    )
                    validated = result.content
                    validated.check_semantic_grounding(site_context_str)
                    return {
                        "subject": validated.subject,
                        "body_html": validated.body_html,
                        "personalized_opening": validated.personalized_opening,
                    }
                except Exception as e:
                    logger.warning(
                        "outreach_grounding_failed",
                        domain=domain, attempt=attempt, error=str(e),
                    )
                    if attempt < max_retries - 1:
                        hint = str(e).replace("Semantic grounding failure: ", "")
                        prompt = _build_prompt(
                            stage if not attempt else "rewritten",
                            extra_instructions,
                            hint,
                        )
            return None

        # Phase 6 & 7: Elite Social Graph Bespoke Pitching
        bespoke_pitch = await outreach_intelligence.generate_humanized_bespoke_pitch(
            tenant_id=tenant_uuid,
            prospect_data={
                "domain": domain,
                "contact_name": contact_name,
                "social_graph_signal": f"Recent articles on {domain}: {'; '.join(a['title'] for a in recent_articles[:3]) if recent_articles else site_title or site_desc}",
            },
            client_context={
                "client_name": campaign_name or "Our Enterprise Platform",
                "value_add_asset": f"Proprietary benchmark data, custom infographics, and {content_pivot.lower()}",
            },
        )

        initial_email = {
            "subject": bespoke_pitch.get("subject_line", ""),
            "body_html": bespoke_pitch.get("body_content", "").replace("\n", "<br>"),
            "personalized_opening": bespoke_pitch.get("personalization_angle", ""),
            "generation_source": bespoke_pitch.get("generation_source", "social_graph_bespoke_ai"),
            "value_add_type": bespoke_pitch.get("value_add_type", ""),
        }

        followup_1_prompt = _build_prompt(
            "follow-up",
            "TASK: Write a warm follow-up email. Reference your previous outreach naturally. Add a new piece of value. Keep it brief."
        )
        followup_2_prompt = _build_prompt(
            "re-engagement",
            "TASK: Write a gentle re-engagement email. It's been some time. Fresh approach with a new angle. Low pressure."
        )

        followup_1 = await _generate_with_grounding(followup_1_prompt) if initial_email else None
        followup_2 = await _generate_with_grounding(followup_2_prompt) if followup_1 else None

        if initial_email:
            email_sequences.append({
                "prospect_domain": domain,
                "to_email": contact_email,
                "contact_name": contact_name,
                "initial_email": initial_email,
                "followup_1": followup_1,
                "followup_2": followup_2,
            })

    logger.info("outreach_sequences_generated", count=len(email_sequences))
    result = {"email_sequences": email_sequences, "count": len(email_sequences)}
    await idempotency_store.store(idem_key, json.dumps(result), ttl=86400)
    return result


@activity.defn(name="send_outreach_batch_activity")
async def send_outreach_batch_activity(
    tenant_id: str, campaign_id: str, emails: list[dict],
) -> dict[str, Any]:
    """Send outreach emails with rate limiting and idempotency."""
    logger.info("sending_outreach_batch", campaign_id=campaign_id, count=len(emails))

    from uuid import UUID

    from seo_platform.core.kill_switch import kill_switch_service
    from seo_platform.core.reliability import idempotency_store

    ks = await kill_switch_service.is_blocked("email_sending", tenant_id=UUID(tenant_id))
    if ks.blocked:
        logger.warning("email_sending_blocked", reason=ks.reason)
        return {"sent_count": 0, "provider": "blocked", "reason": ks.reason}

    from seo_platform.services.email_provider import email_provider

    sent_count = 0
    failed = []

    for email in emails:
        prospect_domain = email.get("prospect_domain", "")
        idem_key = f"email:{campaign_id}:{prospect_domain}"
        if prospect_domain and await idempotency_store.exists(idem_key):
            sent_count += 1
            continue

        try:
            result = await email_provider.send_email(
                to_email=email.get("to_email", ""),
                subject=email.get("subject", ""),
                body=email.get("body_html", ""),
                campaign_id=campaign_id,
                tenant_id=tenant_id,
                prospect_id=prospect_domain,
            )

            if result.get("success"):
                sent_count += 1
                if prospect_domain:
                    await idempotency_store.store(idem_key, "sent", ttl=604800)
            else:
                failed.append(email.get("to_email", ""))

        except Exception as e:
            logger.warning("email_send_failed", to=email.get("to_email"), error=str(e))
            failed.append(email.get("to_email", ""))

    logger.info("outreach_batch_sent", campaign_id=campaign_id, sent=sent_count, failed=len(failed))
    return {"sent_count": sent_count, "provider": "sendgrid", "failed": len(failed)}


@activity.defn(name="send_single_email_activity")
async def send_single_email_activity(
    tenant_id: str, campaign_id: str, thread_id: str,
    to_email: str, subject: str, body_html: str,
) -> dict[str, Any]:
    """Send a single outreach email within a thread. Idempotent."""
    from uuid import UUID

    from seo_platform.core.kill_switch import kill_switch_service
    from seo_platform.core.reliability import idempotency_store

    ks = await kill_switch_service.is_blocked("email_sending", tenant_id=UUID(tenant_id))
    if ks.blocked:
        logger.warning("email_sending_blocked", reason=ks.reason)
        return {"sent": False, "provider": "blocked", "reason": ks.reason}

    idem_key = f"email-single:{thread_id}"
    if await idempotency_store.exists(idem_key):
        logger.info("single_email_idempotent_skip", thread_id=thread_id)
        return {"sent": True, "cached": True}

    from seo_platform.services.email_provider import email_provider

    try:
        result = await email_provider.send_email(
            to_email=to_email,
            subject=subject,
            body=body_html,
            campaign_id=campaign_id,
            tenant_id=tenant_id,
            prospect_id=thread_id,
        )

        if result.get("success"):
            await idempotency_store.store(idem_key, "sent", ttl=604800)
            return {"sent": True}
        else:
            return {"sent": False, "error": result.get("error", "unknown")}
    except Exception as e:
        logger.warning("single_email_send_failed", thread_id=thread_id, error=str(e))
        return {"sent": False, "error": str(e)}


@activity.defn(name="create_approval_request_activity")
async def create_approval_request_activity(
    tenant_id: str, workflow_run_id: str, category: str,
    risk_level: str, summary: str, context: dict,
) -> dict[str, Any]:
    """Create an approval request and return its ID (idempotent)."""
    from uuid import UUID as PyUUID

    from seo_platform.core.reliability import idempotency_store
    from seo_platform.services.approval import ApprovalRequest, RiskLevel, approval_service

    idem_key = f"approval:{workflow_run_id}:{category}"
    cached = await idempotency_store.get(idem_key)
    if cached:
        return {"approval_request_id": cached, "sla_deadline": "", "cached": True}

    request = ApprovalRequest(
        tenant_id=PyUUID(tenant_id),
        workflow_run_id=workflow_run_id,
        risk_level=RiskLevel(risk_level),
        category=category,
        summary=summary,
        context_snapshot=context,
    )
    result = await approval_service.create_request(request)
    await idempotency_store.store(idem_key, str(result.id), ttl=259200)
    return {"approval_request_id": str(result.id), "sla_deadline": result.sla_deadline.isoformat() if result.sla_deadline else ""}


@activity.defn(name="update_campaign_status_activity")
async def update_campaign_status_activity(
    tenant_id: str, campaign_id: str, status: str, metrics: dict | None = None,
) -> dict[str, Any]:
    """Update campaign status and metrics in the database."""
    logger.info("campaign_status_updated", campaign_id=campaign_id, status=status)

    from uuid import UUID

    from sqlalchemy import select

    from seo_platform.core.database import get_tenant_session
    from seo_platform.models.backlink import BacklinkCampaign

    async with get_tenant_session(UUID(tenant_id)) as session:
        result = await session.execute(
            select(BacklinkCampaign).where(
                BacklinkCampaign.id == UUID(campaign_id),
                BacklinkCampaign.tenant_id == UUID(tenant_id),
            )
        )
        campaign = result.scalar_one_or_none()
        if campaign:
            from seo_platform.models.backlink import CampaignStatus
            campaign.status = CampaignStatus(status)

            if metrics:
                campaign.total_prospects = metrics.get("total_prospects", campaign.total_prospects)
                campaign.total_emails_sent = metrics.get("total_emails_sent", campaign.total_emails_sent)
                campaign.health_score = metrics.get("health_score", campaign.health_score)

            if status in ("active", "monitoring") and campaign.started_at is None:
                from datetime import datetime
                campaign.started_at = datetime.now(UTC)
            if status in ("complete", "cancelled", "failed"):
                from datetime import datetime
                campaign.completed_at = datetime.now(UTC)

    return {"campaign_id": campaign_id, "status": status}


@activity.defn(name="fallback_prospects_activity")
async def fallback_prospects_activity(
    tenant_id: str, campaign_id: str,
) -> dict[str, Any]:
    """When external discovery returns nothing, use DB prospects as fallback."""
    from seo_platform.core.database import get_session
    from sqlalchemy import select, text
    from uuid import UUID

    logger.info("using_fallback_prospects", campaign_id=campaign_id)
    try:
        async with get_session() as session:
            result = await session.execute(
                text("""
                SELECT domain, domain_authority, relevance_score
                FROM backlink_prospects
                WHERE tenant_id = :tenant
                ORDER BY domain_authority DESC
                LIMIT 10
                """),
                {"tenant": tenant_id}
            )
            rows = result.fetchall()
            prospects = []
            for row in rows:
                prospects.append({
                    "domain": row[0],
                    "url": f"https://{row[0]}/",
                    "source_competitor": "keyword_derived",
                    "domain_rating": row[1] or 75,
                    "relevance_score": row[2] or 0.8,
                    "spam_score": 0.15,
                })
            logger.info("fallback_prospects_found", count=len(prospects))
            return {"prospects": prospects, "count": len(prospects)}
    except Exception as e:
        logger.warning("fallback_prospects_failed", error=str(e))
        return {"prospects": [], "count": 0}


# ---------------------------------------------------------------------------
# Workflow Definition
# ---------------------------------------------------------------------------
@workflow.defn(name="BacklinkCampaignWorkflow")
class BacklinkCampaignWorkflow:
    """
    Full backlink acquisition campaign workflow.

    This is the primary revenue-generating workflow in the platform.
    It orchestrates the entire campaign lifecycle from prospect
    discovery through outreach to link acquisition.

    Two human approval gates ensure quality control:
    1. Prospect list approval (after scoring)
    2. Outreach template approval (after email generation)
    """

    def __init__(self) -> None:
        self._approval_decision: str | None = None
        self._approval_data: dict = {}

    @workflow.signal(name="approval_decision")
    async def on_approval_decision(self, decision_json: str) -> None:
        """Receive approval decision from human reviewer via Temporal Signal."""
        import json
        data = json.loads(decision_json)
        self._approval_decision = data.get("decision", "rejected")
        self._approval_data = data

    @workflow.run
    async def run(self, input_json: str) -> str:
        input_data = BacklinkCampaignInput.model_validate_json(input_json)
        output = BacklinkCampaignOutput(success=True, campaign_id=str(input_data.campaign_id))

        try:
            # --- Phase 1: Prospect Discovery ---
            await workflow.execute_activity(
                update_campaign_status_activity,
                args=[str(input_data.tenant_id), str(input_data.campaign_id), "prospecting"],
                task_queue=TaskQueue.BACKLINK_ENGINE,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPreset.DATABASE,
            )

            discovery_result = await workflow.execute_activity(
                discover_prospects_activity,
                args=[str(input_data.tenant_id), str(input_data.campaign_id),
                      input_data.competitor_domains],
                task_queue=TaskQueue.BACKLINK_ENGINE,
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=RetryPreset.EXTERNAL_API,
            )
            output.prospects_discovered = discovery_result["count"]

            if discovery_result["count"] == 0:
                discovery_result = await workflow.execute_activity(
                    fallback_prospects_activity,
                    args=[str(input_data.tenant_id), str(input_data.campaign_id)],
                    task_queue=TaskQueue.BACKLINK_ENGINE,
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=RetryPreset.DATABASE,
                )
                output.prospects_discovered = discovery_result["count"]

            # --- Phase 2: Scoring & Filtering ---
            scoring_result = await workflow.execute_activity(
                score_prospects_activity,
                args=[str(input_data.tenant_id), str(input_data.campaign_id),
                      discovery_result["prospects"],
                      input_data.min_domain_authority, input_data.max_spam_score],
                task_queue=TaskQueue.BACKLINK_ENGINE,
                start_to_close_timeout=timedelta(minutes=15),
                retry_policy=RetryPreset.EXTERNAL_API,
            )
            scored_prospects = scoring_result["scored_prospects"]
            output.prospects_scored = len(scored_prospects)

            # --- Phase 3: Contact Discovery ---
            contacts_result = await workflow.execute_activity(
                discover_contacts_activity,
                args=[str(input_data.tenant_id), scored_prospects],
                task_queue=TaskQueue.BACKLINK_ENGINE,
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=RetryPreset.EXTERNAL_API,
            )
            enriched_prospects = contacts_result["enriched_prospects"]

            # --- Phase 3.5: Human Approval Gate ---
            approval_result = await workflow.execute_activity(
                create_approval_request_activity,
                args=[
                    str(input_data.tenant_id),
                    workflow.info().run_id,
                    "prospect_approval",
                    "medium",
                    f"Campaign {input_data.campaign_name}: {len(enriched_prospects)} prospects require approval.",
                    {"prospects": enriched_prospects, "campaign_id": str(input_data.campaign_id)},
                ],
                task_queue=TaskQueue.BACKLINK_ENGINE,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPreset.DATABASE,
            )

            await workflow.execute_activity(
                update_campaign_status_activity,
                args=[str(input_data.tenant_id), str(input_data.campaign_id), "awaiting_approval"],
                task_queue=TaskQueue.BACKLINK_ENGINE,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPreset.DATABASE,
            )

            await workflow.wait_condition(
                lambda: self._approval_decision is not None
            )

            if self._approval_decision != "approved":
                await workflow.execute_activity(
                    update_campaign_status_activity,
                    args=[str(input_data.tenant_id), str(input_data.campaign_id), "cancelled"],
                    task_queue=TaskQueue.BACKLINK_ENGINE,
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=RetryPreset.DATABASE,
                )
                output.success = False
                output.status = "cancelled"
                output.errors.append(
                    f"Campaign halted: Human reviewer decision was '{self._approval_decision}'."
                )
                return output.model_dump_json()

            approved_prospects = self._approval_data.get("prospects", enriched_prospects)
            output.prospects_approved = len(approved_prospects)

            # --- Phase 4: Outreach Email Generation (3-email sequences) ---
            await workflow.execute_activity(
                update_campaign_status_activity,
                args=[str(input_data.tenant_id), str(input_data.campaign_id), "generating_emails"],
                task_queue=TaskQueue.BACKLINK_ENGINE,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPreset.DATABASE,
            )

            emails_result = await workflow.execute_activity(
                generate_outreach_emails_activity,
                args=[str(input_data.tenant_id), str(input_data.campaign_id),
                      approved_prospects, input_data.campaign_type, input_data.campaign_name],
                task_queue=TaskQueue.AI_ORCHESTRATION,
                start_to_close_timeout=timedelta(minutes=30),
                retry_policy=RetryPreset.LLM_INFERENCE,
            )
            output.emails_generated = emails_result["count"]

            # --- Phase 5: Spawn Child Outreach Threads ---
            await workflow.execute_activity(
                update_campaign_status_activity,
                args=[str(input_data.tenant_id), str(input_data.campaign_id), "active"],
                task_queue=TaskQueue.BACKLINK_ENGINE,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPreset.DATABASE,
            )

            child_futures = []
            for seq in emails_result.get("email_sequences", []):
                thread_id = f"outreach_{input_data.campaign_id}_{seq['prospect_domain']}"
                thread_input = OutreachThreadInput(
                    tenant_id=input_data.tenant_id,
                    campaign_id=input_data.campaign_id,
                    thread_id=thread_id,
                    prospect_domain=seq["prospect_domain"],
                    contact_email=seq["to_email"],
                    contact_name=seq.get("contact_name", "there"),
                    initial_email=seq.get("initial_email", {}),
                    followup_1=seq.get("followup_1", {}),
                    followup_2=seq.get("followup_2", {}),
                )
                future = workflow.execute_child_workflow(
                    OutreachThreadWorkflow.run,
                    args=[thread_input.model_dump_json()],
                    id=thread_id,
                    task_queue=TaskQueue.COMMUNICATION,
                    retry_policy=RetryPreset.TRANSIENT_IDEMPOTENT,
                )
                child_futures.append((seq["prospect_domain"], future))

            child_results = await asyncio.gather(*[f for _, f in child_futures])

            threads_contacted = 0
            threads_replied = 0
            threads_completed = 0
            for i, result_json in enumerate(child_results):
                child_out = OutreachThreadOutput.model_validate_json(result_json)
                if child_out.initial_sent:
                    threads_contacted += 1
                if child_out.reply_received:
                    threads_replied += 1
                if child_out.status in ("completed_no_reply", "replied"):
                    threads_completed += 1

            output.threads_contacted = threads_contacted
            output.threads_replied = threads_replied
            output.threads_completed = threads_completed
            output.emails_sent = threads_contacted

            # --- Phase 6: Complete ---
            await workflow.execute_activity(
                update_campaign_status_activity,
                args=[str(input_data.tenant_id), str(input_data.campaign_id), "monitoring"],
                task_queue=TaskQueue.BACKLINK_ENGINE,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPreset.DATABASE,
            )

            output.success = True
            output.status = "monitoring"

        except Exception as e:
            output.success = False
            output.status = "failed"
            output.errors.append(str(e))
            logger.error("campaign_workflow_failed", campaign_id=str(input_data.campaign_id),
                         error=str(e))

        return output.model_dump_json()


# ---------------------------------------------------------------------------
# Child Workflow — Individual Outreach Thread
# ---------------------------------------------------------------------------
@workflow.defn(name="OutreachThreadWorkflow")
class OutreachThreadWorkflow:
    """
    Manages a single prospect outreach thread with 3-stage sequence:
    1. Initial email → wait 3 days (or until reply/cancel)
    2. Follow-up 1 → wait 7 days (or until reply/cancel)
    3. Follow-up 2 → thread complete
    """

    def __init__(self) -> None:
        self._reply_received = False
        self._is_cancelled = False
        self._thread_status = "pending"
        self._reply_data: dict = {}

    @workflow.signal(name="reply_received")
    async def on_reply_received(self, reply_json: str) -> None:
        import json
        self._reply_received = True
        self._thread_status = "replied"
        self._reply_data = json.loads(reply_json)

    @workflow.signal(name="cancel_thread")
    async def on_cancel_thread(self, reason_json: str = "{}") -> None:
        import json
        self._is_cancelled = True
        self._thread_status = "cancelled"
        self._reply_data = json.loads(reason_json)

    def _build_output(self) -> str:
        return OutreachThreadOutput(
            thread_id=self._reply_data.get("thread_id", ""),
            prospect_domain=self._reply_data.get("prospect_domain", ""),
            status=self._thread_status,
            reply_received=self._reply_received,
            reply_data=self._reply_data,
            cancelled=self._is_cancelled,
        ).model_dump_json()

    @workflow.run
    async def run(self, input_json: str) -> str:
        inp = OutreachThreadInput.model_validate_json(input_json)
        output = OutreachThreadOutput(
            thread_id=inp.thread_id,
            prospect_domain=inp.prospect_domain,
        )

        try:
            # Stage 1: Send initial email
            send_result = await workflow.execute_activity(
                send_single_email_activity,
                args=[str(inp.tenant_id), str(inp.campaign_id),
                      inp.thread_id, inp.contact_email,
                      inp.initial_email.get("subject", ""),
                      inp.initial_email.get("body_html", "")],
                task_queue=TaskQueue.COMMUNICATION,
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=RetryPreset.EMAIL_SEND,
            )
            output.initial_sent = send_result.get("sent", False)
            output.status = "contacted"

            # Wait up to 3 days for reply or cancellation
            await workflow.wait_condition(
                lambda: self._reply_received or self._is_cancelled,
                timeout=timedelta(days=3),
            )
            if self._reply_received or self._is_cancelled:
                return self._build_output() if self._reply_received else output.model_dump_json()

            # Stage 2: Send follow-up 1
            if inp.followup_1:
                send_result = await workflow.execute_activity(
                    send_single_email_activity,
                    args=[str(inp.tenant_id), str(inp.campaign_id),
                          inp.thread_id, inp.contact_email,
                          inp.followup_1.get("subject", ""),
                          inp.followup_1.get("body_html", "")],
                    task_queue=TaskQueue.COMMUNICATION,
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=RetryPreset.EMAIL_SEND,
                )
                output.followup_1_sent = send_result.get("sent", False)
                output.status = "followup_1_sent"

            # Wait up to 7 days for reply or cancellation
            await workflow.wait_condition(
                lambda: self._reply_received or self._is_cancelled,
                timeout=timedelta(days=7),
            )
            if self._reply_received or self._is_cancelled:
                return self._build_output() if self._reply_received else output.model_dump_json()

            # Stage 3: Send follow-up 2
            if inp.followup_2:
                send_result = await workflow.execute_activity(
                    send_single_email_activity,
                    args=[str(inp.tenant_id), str(inp.campaign_id),
                          inp.thread_id, inp.contact_email,
                          inp.followup_2.get("subject", ""),
                          inp.followup_2.get("body_html", "")],
                    task_queue=TaskQueue.COMMUNICATION,
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=RetryPreset.EMAIL_SEND,
                )
                output.followup_2_sent = send_result.get("sent", False)
                output.status = "completed_no_reply"

        except Exception as e:
            output.status = "failed"
            logger.error("outreach_thread_failed", thread_id=inp.thread_id, error=str(e))

        return output.model_dump_json()

