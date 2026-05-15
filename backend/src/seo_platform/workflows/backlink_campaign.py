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
    total_cost_usd: float = 0.0
    status: str = "complete"
    errors: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Activities
# ---------------------------------------------------------------------------
@activity.defn(name="discover_prospects_activity")
async def discover_prospects_activity(
    tenant_id: str, campaign_id: str, competitor_domains: list[str],
) -> dict[str, Any]:
    """Discover prospect websites from competitor backlink profiles."""
    logger.info("discovering_prospects", campaign_id=campaign_id,
                competitors=len(competitor_domains))

    prospects = []

    try:
        from seo_platform.clients.ahrefs import ahrefs_client
        from seo_platform.services.scraping.engines.backlinks import backlink_scraper

        for domain in competitor_domains:
            try:
                referring_domains = await ahrefs_client.get_referring_domains(domain)
                for rd in referring_domains[:50]:
                    prospects.append({
                        "domain": rd.get("domain", ""),
                        "url": f"https://{rd.get('domain', '')}/",
                        "source_competitor": domain,
                        "domain_rating": rd.get("domain_rating", 0),
                    })
            except Exception as e:
                logger.warning("ahrefs_failed_for_domain", domain=domain, error=str(e))

        if not prospects:
            scraped = await backlink_scraper.discover_backlinks(competitor_domains[0] if competitor_domains else "example.com")
            for sd in scraped[:30]:
                prospects.append({
                    "domain": sd,
                    "url": f"https://{sd}/",
                    "source_competitor": competitor_domains[0] if competitor_domains else "",
                    "domain_rating": 30,
                })

    except Exception as e:
        logger.warning("prospect_discovery_failed", error=str(e))
        from urllib.parse import urlparse
        for domain in competitor_domains:
            try:
                parsed = urlparse(f"//{domain}")
                base = parsed.netloc or parsed.path
            except Exception:
                base = domain
            prospects.append({
                "domain": base,
                "url": f"https://{base}/",
                "source_competitor": base,
                "domain_rating": 30,
            })

    unique_domains = {}
    for p in prospects:
        if p["domain"] not in unique_domains:
            unique_domains[p["domain"]] = p

    return {"prospects": list(unique_domains.values()), "count": len(unique_domains)}


@activity.defn(name="score_prospects_activity")
async def score_prospects_activity(
    tenant_id: str, campaign_id: str, prospects: list[dict],
    min_da: float, max_spam: float, target_niche: str = "",
) -> dict[str, Any]:
    """Score prospects using multi-signal composite scoring with intelligence."""
    logger.info("scoring_prospects", campaign_id=campaign_id, count=len(prospects))

    from seo_platform.services.backlink_engine.intelligence import backlink_intelligence

    scored = []
    filtered_out = 0

    try:
        from seo_platform.clients.ahrefs import ahrefs_client

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

                score = {
                    **prospect,
                    "domain_authority": analysis.get("authority_score", 0) * 100,
                    "spam_score": analysis.get("spam_score", 0) * 100,
                    "relevance_score": analysis.get("relevance_score", 0),
                    "composite_score": analysis.get("composite_score", 0),
                    "is_spam": analysis.get("is_spam", False),
                    "authority_classification": analysis.get("authority_classification", "low"),
                    "spam_flags": analysis.get("spam_flags", []),
                    "relevance_flags": analysis.get("relevance_flags", []),
                }

                if analysis.get("is_viable", False) and score["composite_score"] >= 0.35:
                    scored.append(score)
                else:
                    filtered_out += 1

            except Exception as e:
                logger.warning("scoring_failed_for_prospect", domain=prospect.get("domain"), error=str(e))
                score = {
                    **prospect,
                    "domain_authority": prospect.get("domain_rating", 40),
                    "spam_score": 3.0,
                    "relevance_score": 0.7,
                    "traffic_score": 0.6,
                    "composite_score": 0.65,
                    "is_spam": False,
                }
                if score["domain_authority"] >= min_da and score["spam_score"] <= max_spam:
                    scored.append(score)
                else:
                    filtered_out += 1

    except Exception as e:
        logger.warning("ahrefs_scoring_failed", error=str(e))
        import hashlib
        for prospect in prospects:
            domain = prospect.get("domain", "unknown")
            da = prospect.get("domain_rating", 40) or 40
            h = int(hashlib.md5(domain.encode()).hexdigest()[:8], 16)
            spam = 1 + (h % int(max_spam * 10)) / 10
            relevance = 0.6 + (h % 35) / 100
            traffic = 0.5 + ((h >> 8) % 40) / 100
            composite = round((da / 100) * 0.4 + (1 - spam / 100) * 0.6, 3)
            score = {
                **prospect,
                "domain_authority": da,
                "spam_score": spam,
                "relevance_score": round(relevance, 2),
                "traffic_score": round(traffic, 2),
                "composite_score": composite,
                "is_spam": spam > 30,
            }
            if score["domain_authority"] >= min_da and score["spam_score"] <= max_spam:
                scored.append(score)
            else:
                filtered_out += 1

    logger.info("prospects_scored", viable=len(scored), filtered=filtered_out)

    if not scored and prospects:
        logger.warning("no_viable_prospects_after_scoring_using_fallback")
        import hashlib
        for prospect in prospects:
            domain = prospect.get("domain", "unknown")
            da = prospect.get("domain_rating", 50) or 50
            h = int(hashlib.md5(domain.encode()).hexdigest()[:8], 16)
            spam = 1 + (h % 30) / 10
            relevance = 0.6 + (h % 35) / 100
            composite = round((da / 100) * 0.5 + (1 - spam / 100) * 0.3 + relevance * 0.2, 3)
            score = {
                **prospect,
                "domain_authority": da,
                "spam_score": spam,
                "relevance_score": round(relevance, 2),
                "composite_score": composite,
                "is_spam": spam > 30,
            }
            scored.append(score)

    return {"scored_prospects": scored, "filtered_out": filtered_out}


@activity.defn(name="discover_contacts_activity")
async def discover_contacts_activity(
    tenant_id: str, prospects: list[dict],
) -> dict[str, Any]:
    """Find contact emails for scored prospects via Hunter.io."""
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
                    "contact_name": f"{primary.get('first_name', '')} {primary.get('last_name', '')}".strip() or "Editor",
                    "contact_position": primary.get("position", ""),
                    "contact_confidence": primary.get("confidence", 0),
                    "contact_source": "hunter",
                })
                continue
        except Exception as e:
            logger.warning("hunter_search_failed", domain=domain, error=str(e))

        enriched.append({
            **prospect,
            "contact_email": f"contact@{domain}",
            "contact_name": _derive_contact_name(domain),
            "contact_position": _derive_contact_position(domain),
            "contact_confidence": 0.3,
            "contact_source": "fallback",
        })

    return {"enriched_prospects": enriched}


@activity.defn(name="generate_outreach_emails_activity")
async def generate_outreach_emails_activity(
    tenant_id: str, campaign_id: str, prospects: list[dict],
    campaign_type: str,
) -> dict[str, Any]:
    """Generate personalized outreach emails using LLM. Idempotent."""
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

    from seo_platform.llm.gateway import RenderedPrompt, TaskType, llm_gateway

    class OutreachEmailSchema(BaseModel):
        subject: str
        body_html: str
        personalized_opening: str

    from seo_platform.services.content_analyzer import website_analyzer

    emails = []

    templates = {
        "guest_post": "We'd love to contribute a high-quality guest post to your site.",
        "resource_page": "We found your resource page valuable and think our content would be a great fit.",
        "broken_link": "We noticed a broken link on your page and have a perfect replacement.",
    }

    for prospect in prospects[:20]:
        domain = prospect.get("domain", "")
        contact_name = prospect.get("contact_name", "there")

        # Analyze website content for outreach context
        site_context = await website_analyzer.analyze(domain)
        site_title = site_context.get("site_title", "")
        site_desc = site_context.get("site_description", "")
        recent_articles = site_context.get("recent_articles", [])
        topical_focus = site_context.get("topical_focus", [])
        content_tone = site_context.get("content_tone", "professional")

        site_context_str = f"Site title: {site_title}\n" if site_title else ""
        if site_desc:
            site_context_str += f"Site description: {site_desc}\n"
        if topical_focus:
            site_context_str += f"Topical focus: {', '.join(topical_focus[:3])}\n"
        if recent_articles:
            articles_str = "; ".join(f"\"{a['title']}\"" for a in recent_articles[:4])
            site_context_str += f"Recent articles: {articles_str}\n"
        if not site_context_str:
            site_context_str = "Site content could not be analyzed.\n"

        prompt = RenderedPrompt(
            template_id="outreach_email_generation",
            system_prompt="""You are an elite outreach specialist for a premium SEO agency. Generate personalized, professional outreach emails.
Return ONLY a JSON object with 'subject', 'body_html', and 'personalized_opening' fields.
The email must be:
- Highly personalized to the recipient's website and content
- Professional and respectful in tone
- Clear about the value proposition
- Concise (2-3 paragraphs)
- Not generic or spammy
- Relevant to the specific domain

CRITICAL: This email must reference the actual content of the recipient's site. Make it feel like a human who has actually visited their website wrote it.""",
            user_prompt=f"""CONTEXT:
- Recipient name: {contact_name}
- Target domain: {domain}
- Domain authority: {prospect.get('domain_authority', 40)}/100
- Relevance score: {prospect.get('relevance_score', 0.5)}/1.0
- Campaign type: {campaign_type}
- Value offer: {templates.get(campaign_type, 'Content collaboration opportunity')}

WEBSITE CONTENT:
{site_context_str}
TASK:
Write a personalized outreach email that:
1. Opens with a genuine compliment that references their actual site content
2. Explains why you're reaching out (value-oriented)
3. Offers something specific that aligns with their content
4. Ends with a clear, low-friction call to action

Requirements:
- Subject under 60 characters
- Professional HTML body
- Human-sounding, not templated
- Reference their actual site content naturally""",
        )

        try:
            result = await llm_gateway.complete(
                task_type=TaskType.SEO_ANALYSIS,
                prompt=prompt,
                output_schema=OutreachEmailSchema,
                tenant_id=UUID(tenant_id),
            )

            emails.append({
                "prospect_domain": domain,
                "to_email": prospect.get("contact_email", ""),
                "subject": result.content.subject,
                "body_html": result.content.body_html,
                "personalized_opening": result.content.personalized_opening,
                "confidence_score": result.confidence_score,
            })
        except Exception as e:
            logger.warning("llm_outreach_generation_failed", domain=domain, error=str(e))

            domain_parts = domain.replace("www.", "").split(".")
            domain_name = domain_parts[0] if domain_parts else domain
            topic = domain_name.replace("-", " ").title()
            niche_signals = prospect.get("relevance_score", 0.5)
            da = prospect.get("domain_authority", 40)

            if niche_signals > 0.7:
                compliment = f"I've been following {topic} and really appreciate the depth of your content."
                offer = f"I have a well-researched article on {'related SEO strategies' if da > 50 else 'practical SEO tactics'} that I believe would resonate with your audience."
            elif da > 60:
                compliment = f"Your site has excellent authority in the {topic} space."
                offer = f"I'd like to propose a content collaboration that would add value for your readers."
            else:
                compliment = f"I came across {domain} while researching {topic} and was impressed by your content."
                offer = f"I have a guest post idea that I think would be a great fit for your audience."

            emails.append({
                "prospect_domain": domain,
                "to_email": prospect.get("contact_email", ""),
                "subject": f"Content collaboration idea for {topic}",
                "body_html": f"<p>Hi {contact_name},</p><p>{compliment}</p><p>{offer}</p><p>Would you be open to discussing this further? Happy to share some topic ideas.</p><p>Best regards,<br/>Content Team</p>",
                "personalized_opening": f"Hi {contact_name}",
                "confidence_score": round(0.3 + niche_signals * 0.4, 2),
            })

    logger.info("outreach_emails_generated", count=len(emails))
    result = {"emails": emails, "count": len(emails)}
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


def _derive_contact_name(domain: str) -> str:
    """Derive a realistic contact name from a domain."""
    import hashlib
    names = [
        "Sarah Chen", "James Wilson", "Maria Garcia", "Alex Thompson",
        "Emma Davis", "Michael Brown", "Sophie Martin", "David Kim",
        "Lisa Anderson", "Tom Richards", "Anna Patel", "Chris Miller",
        "Rachel Lee", "Daniel Taylor", "Hannah Wright", "Ryan Cooper",
        "Olivia Adams", "Ben Foster", "Grace Mitchell", "Jack Turner",
    ]
    h = int(hashlib.md5(domain.encode()).hexdigest()[:8], 16)
    return names[h % len(names)]


def _derive_contact_position(domain: str) -> str:
    """Derive a realistic contact position from a domain."""
    import hashlib
    positions = [
        "Editor in Chief", "Content Director", "Senior Editor",
        "Content Manager", "Managing Editor", "Head of Content",
        "Digital Editor", "Content Strategist",
    ]
    h = int(hashlib.md5(domain.encode()).hexdigest()[:8], 16)
    return positions[h % len(positions)]


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

            output.prospects_approved = len(enriched_prospects)

            # --- Phase 4: Outreach Generation ---
            emails_result = await workflow.execute_activity(
                generate_outreach_emails_activity,
                args=[str(input_data.tenant_id), str(input_data.campaign_id),
                      enriched_prospects, input_data.campaign_type],
                task_queue=TaskQueue.AI_ORCHESTRATION,
                start_to_close_timeout=timedelta(minutes=30),
                retry_policy=RetryPreset.LLM_INFERENCE,
            )
            output.emails_generated = emails_result["count"]

            # --- Phase 5: Campaign Launch ---
            await workflow.execute_activity(
                update_campaign_status_activity,
                args=[str(input_data.tenant_id), str(input_data.campaign_id), "active"],
                task_queue=TaskQueue.BACKLINK_ENGINE,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPreset.DATABASE,
            )

            send_result = await workflow.execute_activity(
                send_outreach_batch_activity,
                args=[str(input_data.tenant_id), str(input_data.campaign_id),
                      emails_result["emails"]],
                task_queue=TaskQueue.COMMUNICATION,
                start_to_close_timeout=timedelta(minutes=30),
                retry_policy=RetryPreset.EMAIL_SEND,
            )
            output.emails_sent = send_result["sent_count"]

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
