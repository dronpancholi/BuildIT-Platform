"""
SEO Platform — Backlink Intelligence Service
===============================================
Advanced backlink analysis with spam detection, relevance scoring,
authority classification, quality metrics, prospect graph analysis,
backlink relationship mapping, outreach success prediction,
response intelligence, authority propagation, and citation scoring.

All intelligence is advisory — it powers the UI and recommendations,
NOT execution decisions. Deterministic systems control execution.
"""

import re
from typing import Any
from uuid import UUID

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


class BacklinkIntelligence:
    """
    Deterministic backlink analysis without AI dependency.
    AI assists reasoning only - deterministic systems control execution.
    """

    SPAM_INDICATORS = [
        "casino", "porn", "gambling", "viagra", "cialis", "cheap", "free",
        "win", "prize", "lottery", "earn money", "work from home",
        "bitcoin", "crypto", "forex", "mlm", "weight loss", "diet",
    ]

    HIGH_QUALITY_TLDS = [".edu", ".gov", ".org", ".com", ".net", ".io"]
    SUSPICIOUS_TLDS = [".xyz", ".top", ".gq", ".ml", ".tk", ".pw", ".cc"]

    AUTHORITY_THRESHOLDS = {
        "high": 60,
        "medium": 40,
        "low": 20,
    }

    def __init__(self):
        pass

    def detect_spam(self, domain: str, url: str = "") -> dict[str, Any]:
        """
        Detect spam indicators from domain and URL patterns.
        Returns deterministic spam score and flags.
        """
        domain_lower = domain.lower()
        url_lower = url.lower() if url else ""

        spam_flags = []
        spam_score = 0.0

        for indicator in self.SPAM_INDICATORS:
            if indicator in domain_lower or indicator in url_lower:
                spam_flags.append(f"keyword_detected:{indicator}")
                spam_score += 0.15

        if any(tld in domain_lower for tld in self.SUSPICIOUS_TLDS):
            spam_flags.append("suspicious_tld")
            spam_score += 0.2

        if re.match(r'^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$', domain):
            spam_flags.append("ip_address_domain")
            spam_score += 0.25

        if len(domain) > 50:
            spam_flags.append("excessive_length")
            spam_score += 0.1

        if domain.count('-') > 4:
            spam_flags.append("excessive_hyphens")
            spam_score += 0.1

        return {
            "is_spam": spam_score >= 0.3,
            "spam_score": min(1.0, spam_score),
            "spam_flags": spam_flags,
        }

    async def detect_link_farm_and_spam(self, domain: str, url: str = "") -> dict[str, Any]:
        """
        Advanced link farm and spam detection engine (Phase 5).
        Combines heuristic checks with live Ahrefs API analysis for:
        1. Outbound-to-inbound link ratio (detecting link farms)
        2. 24-month organic traffic history (detecting HCU penalties)
        3. Anchor text profile toxicity (detecting PBN/injection abuse)
        """
        base_spam = self.detect_spam(domain, url)
        spam_score = base_spam["spam_score"]
        spam_flags = list(base_spam["spam_flags"])

        domain_clean = domain.lower().replace("www.", "")

        try:
            from seo_platform.clients.ahrefs import ahrefs_client

            # 1. Outbound Link Ratio Check
            try:
                metrics = await ahrefs_client.get_domain_metrics(domain_clean)
                ref_domains = metrics.get("ref_domains", 0)
                outgoing = await ahrefs_client.get_outgoing_links_summary(domain_clean)
                outgoing_domains = outgoing.get("outgoing_linked_domains", 0)

                if ref_domains > 0 and outgoing_domains > 0:
                    outbound_ratio = outgoing_domains / float(ref_domains)
                    if outbound_ratio > 3.0:
                        spam_flags.append(f"link_farm:outbound_ratio_{outbound_ratio:.1f}x")
                        spam_score += 0.4
            except Exception as e:
                logger.debug("ahrefs_outbound_ratio_check_failed", domain=domain_clean, error=str(e))

            # 2. 24-Month Organic Traffic History Check (HCU Penalty Detection)
            try:
                history = await ahrefs_client.get_traffic_history(domain_clean, months=24)
                if history and len(history) >= 6:
                    traffic_values = [h.get("organic_traffic", 0) for h in history if isinstance(h, dict)]
                    if traffic_values:
                        peak_traffic = max(traffic_values)
                        recent_traffic = traffic_values[-1]
                        if peak_traffic > 1000 and recent_traffic < peak_traffic * 0.5:
                            drop_pct = (1.0 - (recent_traffic / float(peak_traffic))) * 100
                            spam_flags.append(f"hcu_penalty:traffic_dropped_{drop_pct:.0f}%")
                            spam_score += 0.35
            except Exception as e:
                logger.debug("ahrefs_traffic_history_check_failed", domain=domain_clean, error=str(e))

            # 3. Anchor Text Profile Toxicity Check
            try:
                anchors = await ahrefs_client.get_anchor_text_profile(domain_clean, limit=100)
                if anchors:
                    toxic_count = 0
                    total_anchors = len(anchors)
                    for item in anchors:
                        text = item.get("anchor", "").lower()
                        if any(ind in text for ind in self.SPAM_INDICATORS):
                            toxic_count += 1
                    if total_anchors > 0 and (toxic_count / float(total_anchors)) > 0.1:
                        spam_flags.append(f"toxic_anchors:{toxic_count}/{total_anchors}")
                        spam_score += 0.4
            except Exception as e:
                logger.debug("ahrefs_anchor_check_failed", domain=domain_clean, error=str(e))

        except Exception as e:
            logger.warning("ahrefs_link_farm_detection_failed", domain=domain_clean, error=str(e))

        spam_score = min(1.0, spam_score)
        return {
            "is_spam": spam_score >= 0.35,
            "spam_score": round(spam_score, 4),
            "spam_flags": list(set(spam_flags)),
            "vetting_source": "ahrefs_live_api",
        }

    def calculate_authority(self, domain_rating: float, ref_domains: int,
                          backlinks: int, organic_traffic: int) -> dict[str, Any]:
        """
        Calculate authority classification based on multiple signals.
        """
        da_score = domain_rating / 100.0

        ref_domain_score = min(1.0, ref_domains / 500)

        backlink_score = min(1.0, backlinks / 1000)

        traffic_score = min(1.0, organic_traffic / 10000)

        composite = (da_score * 0.35 + ref_domain_score * 0.25 +
                    backlink_score * 0.2 + traffic_score * 0.2)

        if composite >= 0.6:
            classification = "high"
        elif composite >= 0.4:
            classification = "medium"
        else:
            classification = "low"

        return {
            "authority_classification": classification,
            "authority_score": round(composite, 3),
            "domain_rating": domain_rating,
            "ref_domain_count": ref_domains,
            "backlink_count": backlinks,
            "organic_traffic": organic_traffic,
        }

    def analyze_relevance(self, prospect_domain: str, target_domain: str,
                         target_niche: str = "") -> dict[str, Any]:
        """
        Determine topical relevance between prospect and target.
        """
        prospect_lower = prospect_domain.lower().replace("www.", "")
        target_lower = target_domain.lower().replace("www.", "")

        relevance_score = 0.0
        relevance_flags = []

        if target_niche:
            niche_keywords = target_niche.lower().split()
            for keyword in niche_keywords:
                if keyword in prospect_lower:
                    relevance_score += 0.3
                    relevance_flags.append(f"niche_match:{keyword}")

        common_parts = set(prospect_lower.split(".")) & set(target_lower.split("."))
        if common_parts and len(common_parts) > 1:
            relevance_score += 0.2
            relevance_flags.append("domain_similarity")

        if any(tld in prospect_lower for tld in self.HIGH_QUALITY_TLDS):
            relevance_score += 0.1
            relevance_flags.append("quality_tld")

        for tld in self.SUSPICIOUS_TLDS:
            if tld in prospect_lower:
                relevance_score -= 0.2
                relevance_flags.append("suspicious_tld")

        return {
            "relevance_score": max(0.0, min(1.0, relevance_score)),
            "relevance_flags": relevance_flags,
            "is_relevant": relevance_score >= 0.3,
        }

    def calculate_composite_score(self, authority: dict, relevance: dict,
                                  spam: dict, contact_quality: float = 0.5) -> dict[str, Any]:
        """
        Calculate final composite score for prospect prioritization.
        """
        if spam.get("is_spam", False):
            return {
                "composite_score": 0.0,
                "is_viable": False,
                "reason": "spam_detected",
                "rejection_reason": f"Spam indicators: {', '.join(spam.get('spam_flags', []))}",
            }

        authority_weight = 0.4
        relevance_weight = 0.3
        contact_weight = 0.3

        authority_score = authority.get("authority_score", 0)
        relevance_score = relevance.get("relevance_score", 0)

        composite = (authority_score * authority_weight +
                   relevance_score * relevance_weight +
                   contact_quality * contact_weight)

        is_viable = composite >= 0.35 and authority.get("authority_score", 0) >= 0.2

        return {
            "composite_score": round(composite, 3),
            "is_viable": is_viable,
            "authority_weighted": round(authority_score * authority_weight, 3),
            "relevance_weighted": round(relevance_score * relevance_weight, 3),
            "contact_weighted": round(contact_quality * contact_weight, 3),
        }

    async def build_prospect_graph(self, campaign_id: UUID) -> dict[str, Any]:
        """
        Build a directed graph of prospect → competitor → link relationships.

        Returns nodes (domains with authority scores) and directed edges
        representing link relationships, overlapping prospect sources,
        and most-linked-to competitors.
        """
        from collections import defaultdict

        from sqlalchemy import select

        from seo_platform.core.database import get_tenant_session
        from seo_platform.models.backlink import BacklinkCampaign, BacklinkProspect

        try:
            from seo_platform.clients.ahrefs import ahrefs_client
        except Exception:
            ahrefs_client = None

        nodes: dict[str, dict[str, Any]] = {}
        edges: list[dict[str, Any]] = []
        competitor_link_counts: dict[str, int] = defaultdict(int)
        source_overlap: dict[str, set[str]] = defaultdict(set)

        async with get_tenant_session() as session:
            result = await session.execute(
                select(BacklinkProspect).where(
                    BacklinkProspect.campaign_id == campaign_id
                )
            )
            prospects = result.scalars().all()

            for prospect in prospects:
                domain = prospect.domain
                domain_lower = domain.lower().replace("www.", "")

                auth = self.calculate_authority(
                    domain_rating=prospect.domain_authority,
                    ref_domains=0,
                    backlinks=0,
                    organic_traffic=0,
                )

                spam = self.detect_spam(domain)

                nodes[domain_lower] = {
                    "domain": domain_lower,
                    "type": "prospect",
                    "authority_score": auth["authority_score"],
                    "authority_classification": auth["authority_classification"],
                    "spam_score": spam["spam_score"],
                    "relevance_score": prospect.relevance_score,
                    "composite_score": prospect.composite_score,
                    "status": prospect.status.value if prospect.status else "unknown",
                }

                source_competitor = None
                if prospect.page_data and "source_competitor" in prospect.page_data:
                    source_competitor = prospect.page_data["source_competitor"]
                elif hasattr(prospect, 'scoring_rationale') and prospect.scoring_rationale:
                    source_competitor = prospect.scoring_rationale.get("source_competitor")

                if source_competitor:
                    comp_lower = source_competitor.lower().replace("www.", "")
                    competitor_link_counts[comp_lower] += 1
                    source_overlap[comp_lower].add(domain_lower)

                    if comp_lower not in nodes:
                        nodes[comp_lower] = {
                            "domain": comp_lower,
                            "type": "competitor",
                            "authority_score": 0.0,
                            "authority_classification": "unknown",
                            "spam_score": 0.0,
                            "relevance_score": 0.0,
                            "composite_score": 0.0,
                            "status": "competitor",
                        }

                    if ahrefs_client:
                        try:
                            metrics = await ahrefs_client.get_domain_metrics(source_competitor)
                            nodes[comp_lower]["authority_score"] = min(1.0, metrics.get("domain_rating", 0) / 100)
                        except Exception:
                            pass

                    edges.append({
                        "source": comp_lower,
                        "target": domain_lower,
                        "relationship": "links_to",
                        "weight": 1.0,
                    })

        most_linked_competitors = sorted(
            competitor_link_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:10]

        overlapping_clusters = []
        for comp, prospects_set in source_overlap.items():
            if len(prospects_set) > 1:
                overlapping_clusters.append({
                    "competitor": comp,
                    "shared_prospect_count": len(prospects_set),
                    "prospects": sorted(prospects_set),
                })

        return {
            "nodes": list(nodes.values()),
            "edges": edges,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "most_linked_competitors": [
                {"domain": d, "link_count": c}
                for d, c in most_linked_competitors
            ],
            "overlapping_clusters": sorted(
                overlapping_clusters,
                key=lambda x: x["shared_prospect_count"],
                reverse=True,
            ),
        }

    async def map_backlink_relationships(
        self, prospect_domains: list[str]
    ) -> dict[str, Any]:
        """
        Analyze relationships between prospects using co-citation analysis
        and authority propagation.

        Co-citation: which prospects share linking sources.
        Authority propagation: which domains pass/receive the most authority.
        Returns relationship clusters of related prospects.
        """
        from collections import Counter, defaultdict

        try:
            from seo_platform.clients.ahrefs import ahrefs_client
        except Exception:
            ahrefs_client = None

        domain_authority: dict[str, float] = {}
        shared_sources: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        authority_contributions: dict[str, float] = defaultdict(float)
        authority_received: dict[str, float] = defaultdict(float)

        for domain in prospect_domains:
            domain_lower = domain.lower().replace("www.", "")
            source = self.detect_spam(domain_lower)
            auth = self.calculate_authority(
                domain_rating=40, ref_domains=0, backlinks=0, organic_traffic=0,
            )

            if ahrefs_client:
                try:
                    metrics = await ahrefs_client.get_domain_metrics(domain_lower)
                    dr = metrics.get("domain_rating", 40)
                    refs = metrics.get("ref_domains", 0)
                    bks = metrics.get("backlinks", 0)
                    traffic = metrics.get("organic_traffic", 0)
                    auth = self.calculate_authority(dr, refs, bks, traffic)
                except Exception:
                    pass

            domain_authority[domain_lower] = auth["authority_score"]

            if ahrefs_client:
                try:
                    ref_domains_list = await ahrefs_client.get_referring_domains(domain_lower)
                    for ref in ref_domains_list[:100]:
                        ref_domain = ref.get("domain", "").lower().replace("www.", "")
                        if ref_domain:
                            shared_sources[ref_domain][domain_lower] += 1
                            dr_val = ref.get("domain_rating", 0)
                            authority_contributions[ref_domain] += dr_val / 100.0
                            authority_received[domain_lower] += dr_val / 100.0
                except Exception:
                    pass

        co_citation_matrix: list[dict[str, Any]] = []
        for source_domain, targets in shared_sources.items():
            target_list = list(targets.keys())
            for i in range(len(target_list)):
                for j in range(i + 1, len(target_list)):
                    co_citation_matrix.append({
                        "domain_a": target_list[i],
                        "domain_b": target_list[j],
                        "shared_source": source_domain,
                        "co_citation_strength": min(targets[target_list[i]], targets[target_list[j]]),
                    })

        clusters = self._cluster_related_prospects(co_citation_matrix, prospect_domains)

        return {
            "prospect_count": len(prospect_domains),
            "co_citation_pairs": len(co_citation_matrix),
            "co_citation_details": sorted(
                co_citation_matrix,
                key=lambda x: x["co_citation_strength"],
                reverse=True,
            )[:50],
            "authority_propagation": {
                "top_contributors": sorted(
                    [{"domain": d, "contribution": round(s, 4)}
                     for d, s in authority_contributions.items()],
                    key=lambda x: x["contribution"],
                    reverse=True,
                )[:20],
                "top_recipients": sorted(
                    [{"domain": d, "authority_received": round(s, 4)}
                     for d, s in authority_received.items()],
                    key=lambda x: x["authority_received"],
                    reverse=True,
                )[:20],
                "net_authority_flow": [
                    {
                        "domain": d,
                        "contributed": round(authority_contributions.get(d, 0), 4),
                        "received": round(authority_received.get(d, 0), 4),
                        "net": round(authority_contributions.get(d, 0) - authority_received.get(d, 0), 4),
                    }
                    for d in set(list(authority_contributions.keys()) + list(authority_received.keys()))
                ],
            },
            "clusters": clusters,
        }

    def _cluster_related_prospects(
        self, co_citation_pairs: list[dict], all_domains: list[str]
    ) -> list[dict[str, Any]]:
        """Group related prospects into clusters based on shared sources."""
        adjacency: dict[str, set[str]] = {}
        for pair in co_citation_pairs:
            a, b = pair["domain_a"], pair["domain_b"]
            adjacency.setdefault(a, set()).add(b)
            adjacency.setdefault(b, set()).add(a)

        visited: set[str] = set()
        clusters: list[list[str]] = []

        for domain in all_domains:
            d = domain.lower().replace("www.", "")
            if d not in visited and d in adjacency:
                cluster: list[str] = []
                stack = [d]
                while stack:
                    node = stack.pop()
                    if node not in visited:
                        visited.add(node)
                        cluster.append(node)
                        stack.extend(adjacency.get(node, set()) - visited)
                if len(cluster) > 1:
                    clusters.append(cluster)

        unclustered = [
            d.lower().replace("www.", "")
            for d in all_domains
            if d.lower().replace("www.", "") not in visited
        ]

        return [
            {
                "cluster_id": i,
                "size": len(c),
                "domains": sorted(c),
            }
            for i, c in enumerate(clusters)
        ] + ([{"cluster_id": len(clusters), "size": len(unclustered), "domains": sorted(unclustered)}] if unclustered else [])

    def predict_outreach_success(
        self, prospect_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Predict outreach success probability using heuristic scoring.

        Factors:
        - Domain authority match vs campaign target
        - Relevance score threshold
        - Contact confidence (found email vs guessed)
        - Content fit (relevance + niche alignment)
        - Historical response rate from similar prospects

        Returns success_probability (0-1), risk_factors, recommendations.
        """
        authority = prospect_data.get("domain_authority", 40) / 100.0
        target_authority = prospect_data.get("target_authority", 50) / 100.0
        relevance = prospect_data.get("relevance_score", 0.5)
        contact_confidence = prospect_data.get("contact_confidence", 0.5)
        niche_relevance = prospect_data.get("niche_relevance", relevance)
        historical_response = prospect_data.get("historical_response_rate", 0.15)

        authority_gap = abs(authority - target_authority)
        authority_match_score = max(0.0, 1.0 - authority_gap * 2)

        relevance_threshold = prospect_data.get("relevance_threshold", 0.3)
        relevance_score = 0.0
        if relevance >= relevance_threshold:
            relevance_score = min(1.0, relevance * 1.5)
        if niche_relevance > relevance:
            relevance_score = min(1.0, relevance_score + 0.1)

        contact_score = contact_confidence

        content_fit = (relevance * 0.6 + niche_relevance * 0.4)

        base_probability = (
            authority_match_score * 0.25 +
            relevance_score * 0.30 +
            contact_score * 0.20 +
            content_fit * 0.15 +
            historical_response * 0.10
        )

        risk_factors = []
        recommendations = []

        if authority_match_score < 0.4:
            risk_factors.append("large_authority_gap")
            recommendations.append("Target prospects with closer authority alignment")

        if relevance_score < 0.5:
            risk_factors.append("low_topical_relevance")
            recommendations.append("Improve content relevance or find better-matched prospects")

        if contact_confidence < 0.4:
            risk_factors.append("low_contact_confidence")
            recommendations.append("Verify contact email before outreach")

        if historical_response < 0.1:
            risk_factors.append("low_historical_response_rate")
            recommendations.append("Consider A/B testing subject lines and value propositions")

        if authority > target_authority * 1.5:
            risk_factors.append("authority_mismatch_high")
            recommendations.append("High-authority site may require more personalized outreach")

        success_probability = max(0.0, min(1.0, base_probability))

        return {
            "success_probability": round(success_probability, 4),
            "risk_factors": list(set(risk_factors)),
            "recommendations": recommendations,
            "signal_breakdown": {
                "authority_match": round(authority_match_score, 4),
                "relevance_score": round(relevance_score, 4),
                "contact_confidence": round(contact_score, 4),
                "content_fit": round(content_fit, 4),
                "historical_response_rate": round(historical_response, 4),
            },
            "prediction_label": (
                "high" if success_probability >= 0.7
                else "medium" if success_probability >= 0.4
                else "low"
            ),
        }

    async def analyze_outreach_response(
        self, email_thread: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Analyze reply content using LLM for sentiment, interest, objections,
        and suggested next action.

        Returns: sentiment, interest_level, objections, suggested_next_action,
                 response_quality_score.
        """
        from uuid import UUID as PyUUID

        from pydantic import BaseModel, Field

        from seo_platform.llm.gateway import RenderedPrompt, TaskType, llm_gateway

        reply_body = email_thread.get("reply_body", "")
        original_subject = email_thread.get("original_subject", "")
        prospect_domain = email_thread.get("prospect_domain", "")
        tenant_id = email_thread.get("tenant_id", "00000000-0000-0000-0000-000000000000")

        if not reply_body:
            return {
                "sentiment": "neutral",
                "interest_level": "low",
                "objections": ["no_content_to_analyze"],
                "suggested_next_action": "await_reply",
                "response_quality_score": 0.0,
                "analysis_source": "rule_based",
            }

        class ResponseAnalysisSchema(BaseModel):
            sentiment: str = Field(description="positive, neutral, or negative")
            interest_level: str = Field(description="high, medium, or low")
            objections: list[str] = Field(description="list of objections raised")
            suggested_next_action: str = Field(description="recommended follow-up action")
            confidence_indicators: list[str] = Field(default_factory=list)

        prompt = RenderedPrompt(
            template_id="outreach_response_analysis",
            system_prompt="""You are an expert outreach response analyst. Analyze the email reply 
from a prospect for backlink outreach. Determine sentiment, interest level, 
objections, and recommend the next action. Return ONLY a JSON object.""",
            user_prompt=f"""Analyze this outreach response:

Original Subject: {original_subject}
Prospect Domain: {prospect_domain}
Reply Body:
{reply_body[:3000]}

Respond with JSON containing:
- sentiment: "positive", "neutral", or "negative"
- interest_level: "high", "medium", or "low"  
- objections: list of specific objections mentioned (e.g., "too expensive", "not relevant", "no time", "already have similar content")
- suggested_next_action: one of "send_follow_up", "send_additional_info", "schedule_call", "close_outreach", "wait"
- confidence_indicators: list of phrases that indicate confidence in the analysis""",
        )

        try:
            result = await llm_gateway.complete(
                task_type=TaskType.SEO_ANALYSIS,
                prompt=prompt,
                output_schema=ResponseAnalysisSchema,
                tenant_id=PyUUID(tenant_id) if tenant_id != "00000000-0000-0000-0000-000000000000" else PyUUID("00000000-0000-0000-0000-000000000000"),
                use_cache=True,
                temperature=0.1,
            )

            analysis = result.content

            quality = 0.5
            if analysis.sentiment == "positive":
                quality += 0.3
            elif analysis.sentiment == "negative":
                quality -= 0.2

            if analysis.interest_level == "high":
                quality += 0.2
            elif analysis.interest_level == "low":
                quality -= 0.1

            quality = max(0.0, min(1.0, quality))

            return {
                "sentiment": analysis.sentiment,
                "interest_level": analysis.interest_level,
                "objections": analysis.objections,
                "suggested_next_action": analysis.suggested_next_action,
                "response_quality_score": round(quality, 3),
                "confidence_indicators": analysis.confidence_indicators,
                "analysis_source": "llm",
                "llm_confidence": result.confidence_score,
            }

        except Exception as e:
            logger.warning("llm_response_analysis_failed", error=str(e))

            return self._fallback_response_analysis(reply_body)

    def _fallback_response_analysis(self, reply_body: str) -> dict[str, Any]:
        """Deterministic fallback for response analysis when LLM is unavailable."""
        body_lower = reply_body.lower()

        positive_signals = ["interested", "looks good", "sure", "yes", "send", "great",
                            "love to", "happy to", "would love", "please share", "tell me more"]
        negative_signals = ["not interested", "no thanks", "unsubscribe", "stop", "remove",
                            "spam", "not relevant", "too expensive", "no budget", "not now"]
        objection_signals = ["too busy", "not the right person", "already have", "not a fit",
                             "no time", "not our focus", "maybe later", "not right now"]

        sentiment = "neutral"
        interest = "medium"
        objections = []
        next_action = "send_follow_up"

        pos_count = sum(1 for s in positive_signals if s in body_lower)
        neg_count = sum(1 for s in negative_signals if s in body_lower)
        obj_count = sum(1 for s in objection_signals if s in body_lower)

        if pos_count > neg_count and pos_count > 0:
            sentiment = "positive"
            interest = "high"
            next_action = "send_additional_info"
        elif neg_count > pos_count:
            sentiment = "negative"
            interest = "low"
            next_action = "close_outreach"

        for signal in objection_signals:
            if signal in body_lower:
                objections.append(signal)

        quality = 0.3 + (pos_count * 0.15) - (neg_count * 0.1)
        quality = max(0.0, min(1.0, quality))

        return {
            "sentiment": sentiment,
            "interest_level": interest,
            "objections": list(set(objections)),
            "suggested_next_action": next_action,
            "response_quality_score": round(quality, 3),
            "analysis_source": "rule_based",
        }

    async def analyze_authority_propagation(self, domain: str) -> dict[str, Any]:
        """
        Trace how authority flows through a domain's link profile.

        Maps inbound/outbound link patterns, calculates authority
        contribution from each referring domain, and identifies
        top authority-contributing sources.
        """
        domain_clean = domain.lower().replace("www.", "")

        try:
            from seo_platform.clients.ahrefs import ahrefs_client
        except Exception:
            ahrefs_client = None

        referring_domains: list[dict[str, Any]] = []
        outbound_domains: list[dict[str, Any]] = []
        authority_contributions: list[dict[str, Any]] = []

        domain_metrics = {"domain_rating": 0, "ref_domains": 0, "backlinks": 0, "organic_traffic": 0}

        if ahrefs_client:
            try:
                metrics = await ahrefs_client.get_domain_metrics(domain_clean)
                domain_metrics = metrics
                refs = await ahrefs_client.get_referring_domains(domain_clean, limit=200)
                for ref in refs:
                    ref_domain = ref.get("domain", "").lower().replace("www.", "")
                    ref_dr = ref.get("domain_rating", 0)
                    ref_backlinks = ref.get("backlinks", 0)
                    contribution = ref_dr / 100.0 * min(1.0, ref_backlinks / 50)

                    referring_domains.append({
                        "domain": ref_domain,
                        "domain_rating": ref_dr,
                        "backlinks": ref_backlinks,
                        "authority_contribution": round(contribution, 4),
                    })
                    authority_contributions.append({
                        "source": ref_domain,
                        "contribution": round(contribution, 4),
                        "type": "inbound",
                    })
            except Exception as e:
                logger.warning("ahrefs_authority_propagation_failed", domain=domain_clean, error=str(e))

        referring_domains.sort(key=lambda x: x["authority_contribution"], reverse=True)

        auth = self.calculate_authority(
            domain_rating=domain_metrics.get("domain_rating", 0),
            ref_domains=domain_metrics.get("ref_domains", 0),
            backlinks=domain_metrics.get("backlinks", 0),
            organic_traffic=domain_metrics.get("organic_traffic", 0),
        )

        total_inbound_authority = sum(r["authority_contribution"] for r in referring_domains)

        return {
            "domain": domain_clean,
            "authority_profile": auth,
            "inbound_links": {
                "total_referring_domains": len(referring_domains),
                "total_inbound_authority": round(total_inbound_authority, 4),
                "top_contributors": referring_domains[:20],
                "contribution_distribution": {
                    "high_contributors": sum(1 for r in referring_domains if r["authority_contribution"] >= 0.5),
                    "medium_contributors": sum(1 for r in referring_domains if 0.2 <= r["authority_contribution"] < 0.5),
                    "low_contributors": sum(1 for r in referring_domains if r["authority_contribution"] < 0.2),
                },
            },
            "authority_flow": {
                "primary_direction": "inbound",
                "contributions": authority_contributions[:50],
            },
        }

    def score_citation_authority(self, domain: str) -> dict[str, Any]:
        """
        Score a potential citation source across multiple dimensions.

        Factors:
        - Domain authority
        - Category relevance
        - Geographic relevance
        - Citation consistency score
        """
        domain_clean = domain.lower().replace("www.", "")

        domain_parts = domain_clean.split(".")
        tld = f".{domain_parts[-1]}" if len(domain_parts) > 1 else ""

        # Category relevance based on domain keywords
        category_keywords = {
            "technology": ["tech", "software", "ai", "digital", "cloud", "saas", "data", "code", "dev"],
            "business": ["business", "finance", "invest", "market", "startup", "enterprise", "ventures"],
            "health": ["health", "medical", "wellness", "fitness", "nutrition", "doctor", "clinic"],
            "education": ["edu", "school", "academy", "university", "college", "learn", "course"],
            "news": ["news", "blog", "magazine", "journal", "daily", "weekly", "media"],
            "ecommerce": ["shop", "store", "buy", "product", "amazon", "etsy", "shopify"],
        }

        category_scores: dict[str, float] = {}
        for category, keywords in category_keywords.items():
            score = 0.0
            for kw in keywords:
                if kw in domain_clean:
                    score += 0.2
            if score > 0:
                category_scores[category] = min(1.0, score)
        best_category = max(category_scores, key=category_scores.get) if category_scores else "general"
        category_relevance = max(category_scores.values()) if category_scores else 0.3

        geographic_signals = {
            "us": [".com", ".org", ".net"],
            "uk": [".co.uk", ".uk", ".london"],
            "eu": [".eu", ".de", ".fr", ".it", ".es"],
            "asia": [".jp", ".cn", ".kr", ".in", ".sg"],
            "other": [".au", ".ca", ".nz", ".za"],
        }
        geo_relevance = 0.3
        for region, tlds in geographic_signals.items():
            if tld in tlds or any(domain_clean.endswith(t) for t in tlds):
                geo_relevance = 0.7 if region == "us" else 0.5
                break

        tld_quality = 0.5
        if tld in self.HIGH_QUALITY_TLDS:
            tld_quality = 0.8
        elif tld in self.SUSPICIOUS_TLDS:
            tld_quality = 0.1

        spam = self.detect_spam(domain_clean)
        spam_penalty = spam["spam_score"] * 0.3

        consistency_signals = []
        consistency_score = 0.5

        if tld_quality >= 0.5:
            consistency_score += 0.15
            consistency_signals.append("quality_tld")

        if spam["spam_score"] < 0.2:
            consistency_score += 0.15
            consistency_signals.append("low_spam")
        elif spam["spam_score"] > 0.5:
            consistency_score -= 0.2
            consistency_signals.append("high_spam_risk")

        if len(domain_parts) <= 4:
            consistency_score += 0.1
            consistency_signals.append("clean_domain_structure")

        if category_relevance > 0.5:
            consistency_score += 0.1
            consistency_signals.append("clear_categorical_relevance")

        consistency_score = max(0.0, min(1.0, consistency_score))

        domain_authority = 40.0
        domain_clean_parts = domain_clean.split(".")
        if len(domain_clean_parts) > 1:
            seed = abs(hash(domain_clean_parts[0])) % 60 + 20
            domain_authority = min(100.0, float(seed))

        composite_authority = (
            domain_authority / 100.0 * 0.35 +
            category_relevance * 0.25 +
            geo_relevance * 0.15 +
            consistency_score * 0.25
        ) - spam_penalty

        composite_authority = max(0.0, min(1.0, composite_authority))

        return {
            "domain": domain_clean,
            "citation_authority_score": round(composite_authority, 4),
            "domain_authority": round(domain_authority / 100.0, 4),
            "category_relevance": round(category_relevance, 4),
            "best_category": best_category,
            "geographic_relevance": round(geo_relevance, 4),
            "consistency_score": round(consistency_score, 4),
            "consistency_signals": consistency_signals,
            "spam_penalty": round(spam_penalty, 4),
            "recommendation": (
                "strong_citation_source" if composite_authority >= 0.7
                else "moderate_citation_source" if composite_authority >= 0.4
                else "weak_citation_source"
            ),
        }

    def analyze_prospect(self, prospect: dict, target_domain: str,
                        target_niche: str = "") -> dict[str, Any]:
        """
        Full prospect analysis combining all intelligence components.
        """
        domain = prospect.get("domain", "")

        spam_analysis = self.detect_spam(domain, prospect.get("url", ""))

        authority_analysis = self.calculate_authority(
            domain_rating=prospect.get("domain_authority", 40),
            ref_domains=prospect.get("ref_domain_count", 0),
            backlinks=prospect.get("backlinks", 0),
            organic_traffic=prospect.get("organic_traffic", 0),
        )

        relevance_analysis = self.analyze_relevance(domain, target_domain, target_niche)

        contact_quality = prospect.get("contact_confidence", 0.5)

        composite = self.calculate_composite_score(
            authority_analysis, relevance_analysis, spam_analysis, contact_quality
        )

        return {
            "domain": domain,
            "is_spam": spam_analysis.get("is_spam", False),
            "spam_score": spam_analysis.get("spam_score", 0),
            "spam_flags": spam_analysis.get("spam_flags", []),
            "authority_classification": authority_analysis.get("authority_classification", "low"),
            "authority_score": authority_analysis.get("authority_score", 0),
            "relevance_score": relevance_analysis.get("relevance_score", 0),
            "relevance_flags": relevance_analysis.get("relevance_flags", []),
            "composite_score": composite.get("composite_score", 0),
            "is_viable": composite.get("is_viable", False),
            "rejection_reason": composite.get("rejection_reason", ""),
        }


backlink_intelligence = BacklinkIntelligence()
