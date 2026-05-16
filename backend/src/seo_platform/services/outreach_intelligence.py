"""
SEO Platform — Outreach Optimization Intelligence
====================================================
Response prediction, subject-line analysis, timing optimization,
prospect prioritization, communication scoring, follow-up intelligence,
and relationship depth scoring.

All intelligence is advisory — it powers the UI and recommendations,
NOT execution decisions. Deterministic systems control execution.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


class OutreachIntelligenceService:
    """
    Outreach optimization intelligence with deterministic scoring.

    All predictions are advisory recommendations, not execution decisions.
    """

    SPAM_TRIGGER_WORDS = [
        "free", "act now", "limited time", "exclusive offer", "click here",
        "buy now", "discount", "urgent", "guaranteed", "earn money",
        "work from home", "congratulations", "winner", "prize", "risk-free",
    ]

    DAY_SCORES = {
        "monday": 0.75, "tuesday": 0.85, "wednesday": 0.90,
        "thursday": 0.80, "friday": 0.60, "saturday": 0.30, "sunday": 0.25,
    }

    def predict_response_likelihood(self, outreach_data: dict) -> dict:
        """
        Predict likelihood of response using prospect and outreach signals.

        Factors:
          Domain authority (lower DA = higher response rate historically)
          Contact confidence (verified email = 3x response rate)
          Relevance score
          Outreach timing (day of week, time of day)
          Subject line sentiment/novelty
          Campaign type baseline
        """
        domain_authority = outreach_data.get("domain_authority", 40)
        contact_confidence = outreach_data.get("contact_confidence", 0.5)
        relevance_score = outreach_data.get("relevance_score", 0.5)
        campaign_type = outreach_data.get("campaign_type", "guest_post")
        subject_line = outreach_data.get("subject_line", "")
        day_of_week = outreach_data.get("day_of_week", "tuesday")

        da_factor = 1.0 - (min(domain_authority, 100) / 100.0) * 0.5
        da_score = max(0.0, da_factor)

        contact_factor = 3.0 if contact_confidence >= 0.7 else 1.5 if contact_confidence >= 0.4 else 1.0
        contact_score = min(1.0, contact_confidence * contact_factor)

        relevance_clamped = max(0.0, min(1.0, relevance_score))
        relevance_factor = relevance_clamped * 0.8 + 0.2

        day_score = self.DAY_SCORES.get(day_of_week.lower(), 0.7)

        campaign_baselines = {
            "guest_post": 0.12, "resource_page": 0.18, "niche_edit": 0.08,
            "broken_link": 0.22, "skyscraper": 0.15, "haro": 0.25,
        }
        campaign_base = campaign_baselines.get(campaign_type, 0.15)

        subject_score = self._score_subject_effectiveness(subject_line)

        composite = (
            da_score * 0.15
            + contact_score * 0.30
            + relevance_factor * 0.20
            + day_score * 0.10
            + campaign_base * 0.15
            + subject_score * 0.10
        )

        composite = max(0.0, min(1.0, composite))

        factors = []
        if contact_confidence >= 0.7:
            factors.append("verified_contact_email")
        elif contact_confidence < 0.4:
            factors.append("unverified_contact")

        if domain_authority <= 40:
            factors.append("lower_da_favorable")
        elif domain_authority >= 70:
            factors.append("high_da_challenging")

        if day_score >= 0.8:
            factors.append("favorable_timing")

        return {
            "probability": round(composite, 4),
            "confidence": round(composite * 0.8 + 0.2, 4),
            "prediction_label": (
                "high" if composite >= 0.5
                else "medium" if composite >= 0.3
                else "low"
            ),
            "factors": factors,
            "signal_breakdown": {
                "domain_authority_score": round(da_score, 4),
                "contact_confidence_score": round(contact_score, 4),
                "relevance_score": round(relevance_factor, 4),
                "timing_day_score": round(day_score, 4),
                "campaign_baseline": round(campaign_base, 4),
                "subject_effectiveness": round(subject_score, 4),
            },
        }

    def _score_subject_effectiveness(self, subject: str) -> float:
        """Score subject line effectiveness (0-1) based on heuristics."""
        if not subject:
            return 0.3
        score = 0.5
        length = len(subject)
        if 30 <= length <= 50:
            score += 0.2
        elif length > 80:
            score -= 0.15
        elif length < 15:
            score -= 0.1

        has_personalization = any(
            marker in subject.lower()
            for marker in ["{name}", "{company}", "{domain}", "{{name"]
        ) or bool(re.search(r'\b(your|you)\b', subject.lower()))
        if has_personalization:
            score += 0.15

        lower_subj = subject.lower()
        spam_count = sum(1 for w in self.SPAM_TRIGGER_WORDS if w in lower_subj)
        score -= spam_count * 0.1

        has_question = "?" in subject
        if has_question:
            score += 0.05

        has_exclamation = "!" in subject
        if has_exclamation:
            score -= 0.05

        return max(0.0, min(1.0, score))

    def analyze_subject_line(self, subject: str, prospect_data: dict) -> dict:
        """
        Analyze subject line effectiveness across multiple dimensions.

        Dimensions:
          Length scoring (30-50 chars optimal)
          Personalization presence (name, company)
          Sentiment analysis (positive/neutral/negative)
          Curiosity gap score
          Spam trigger word detection
        """
        if not subject:
            return {
                "subject": "",
                "overall_score": 0.0,
                "length_score": 0.0,
                "personalization_score": 0.0,
                "sentiment": "neutral",
                "curiosity_gap_score": 0.0,
                "spam_trigger_count": 0,
                "spam_trigger_words": [],
                "recommendations": ["Add a subject line"],
            }

        length = len(subject)
        if 30 <= length <= 50:
            length_score = 1.0
        elif 25 <= length < 30 or 50 < length <= 60:
            length_score = 0.8
        elif 20 <= length < 25 or 60 < length <= 80:
            length_score = 0.5
        elif length < 20:
            length_score = 0.3
        else:
            length_score = 0.1

        lower_subj = subject.lower()
        personalization_score = 0.0
        personalization_signals = []

        name_patterns = [
            r'\{\{?name\}?\}', r'\{\{?first_name\}?\}', r'\{\{?contact\}?\}',
            r'\bhi\b', r'\bhey\b', r'\bhello\b', r'\bdear\b',
        ]
        for pattern in name_patterns:
            if re.search(pattern, lower_subj):
                personalization_score += 0.4
                personalization_signals.append("greeting_detected")
                break

        for marker in ["{company}", "{domain}", "{{company", "{{domain"]:
            if marker in subject:
                personalization_score += 0.3
                personalization_signals.append("company_placeholder")
                break

        if prospect_data.get("contact_name"):
            contact_name = prospect_data["contact_name"].lower().split()[0] if prospect_data["contact_name"] else ""
            if contact_name and contact_name in lower_subj:
                personalization_score = 1.0
                personalization_signals.append("name_personalized")

        company = prospect_data.get("domain", "").lower().replace("www.", "")
        company_name = company.split(".")[0] if "." in company else company
        if company_name and company_name in lower_subj:
            personalization_score = max(personalization_score, 0.8)
            personalization_signals.append("company_personalized")

        personalization_score = min(1.0, personalization_score)

        sentiment = "neutral"
        positive_words = ["great", "love", "excellent", "amazing", "awesome", "best", "happy", "perfect", "opportunity"]
        negative_words = ["problem", "issue", "urgent", "broken", "bad", "terrible", "awful", "worst"]
        pos_count = sum(1 for w in positive_words if w in lower_subj)
        neg_count = sum(1 for w in negative_words if w in lower_subj)
        if pos_count > neg_count:
            sentiment = "positive"
        elif neg_count > pos_count:
            sentiment = "negative"

        curiosity_score = 0.3
        curiosity_signals = {
            "question": "?", "ellipsis": "...", "how_to": "how to",
            "why": "why", "discover": "discover", "secret": "secret",
            "inside": "inside", "revealed": "revealed",
        }
        for signal_name, pattern in curiosity_signals.items():
            if pattern in lower_subj:
                curiosity_score += 0.15
        curiosity_score = min(1.0, curiosity_score)

        detected_spam_words = [w for w in self.SPAM_TRIGGER_WORDS if w in lower_subj]
        spam_trigger_count = len(detected_spam_words)

        overall = (
            length_score * 0.25
            + personalization_score * 0.25
            + curiosity_score * 0.20
        )
        if spam_trigger_count > 0:
            overall -= spam_trigger_count * 0.1
        if sentiment == "positive":
            overall += 0.05
        elif sentiment == "negative":
            overall -= 0.1
        overall = max(0.0, min(1.0, overall))

        recommendations = []
        if length_score < 0.8:
            recommendations.append("Aim for 30-50 character subject lines")
        if personalization_score < 0.5:
            recommendations.append("Add personalization (name or company)")
        if spam_trigger_count > 0:
            recommendations.append(f"Remove spam trigger words: {', '.join(detected_spam_words)}")
        if curiosity_score < 0.5:
            recommendations.append("Increase curiosity gap with questions or intrigue")
        if not recommendations:
            recommendations.append("Subject line is well-optimized")

        return {
            "subject": subject,
            "overall_score": round(overall, 4),
            "dimensions": {
                "length": {
                    "score": round(length_score, 4),
                    "char_count": length,
                    "is_optimal": 30 <= length <= 50,
                },
                "personalization": {
                    "score": round(personalization_score, 4),
                    "signals": personalization_signals,
                },
                "sentiment": {
                    "label": sentiment,
                    "positive_signals": pos_count,
                    "negative_signals": neg_count,
                },
                "curiosity_gap": {
                    "score": round(curiosity_score, 4),
                },
                "spam_triggers": {
                    "count": spam_trigger_count,
                    "detected_words": detected_spam_words,
                },
            },
            "recommendations": recommendations,
        }

    def recommend_outreach_timing(self, prospect_data: dict) -> dict:
        """
        Recommend optimal send times based on prospect's domain industry
        vertical, day of week patterns, and time zone detection.
        """
        domain = prospect_data.get("domain", "")
        industry_vertical = prospect_data.get("industry_vertical", "")
        if not industry_vertical:
            industry_vertical = self._infer_industry_from_domain(domain)

        industry_timing = {
            "technology": {"best_day": "tuesday", "best_hour": 10, "reason": "Tech professionals check email mid-morning"},
            "business": {"best_day": "wednesday", "best_hour": 9, "reason": "Business execs review opportunities early"},
            "health": {"best_day": "monday", "best_hour": 11, "reason": "Healthcare opens week reviewing new content"},
            "education": {"best_day": "tuesday", "best_hour": 10, "reason": "Educators plan mid-week"},
            "news": {"best_day": "monday", "best_hour": 8, "reason": "Media professionals start week early"},
            "ecommerce": {"best_day": "wednesday", "best_hour": 10, "reason": "Mid-week less transactional pressure"},
            "marketing": {"best_day": "tuesday", "best_hour": 10, "reason": "Marketers plan early week"},
            "general": {"best_day": "tuesday", "best_hour": 10, "reason": "Tuesday mid-morning has highest open rates"},
        }

        timing = industry_timing.get(industry_vertical, industry_timing["general"])

        timezone_offset = 0
        tz_signals = {
            ".co.uk": 0, ".uk": 0, ".eu": 1, ".de": 1, ".fr": 1,
            ".jp": 9, ".cn": 8, ".kr": 9, ".in": 5.5, ".sg": 8,
            ".au": 11, ".ca": -5, ".nz": 13, ".za": 2,
        }
        domain_lower = domain.lower().replace("www.", "")
        for tld, offset in tz_signals.items():
            if domain_lower.endswith(tld):
                timezone_offset = offset
                break

        recommended_hour = (timing["best_hour"] + timezone_offset) % 24
        am_pm = "AM" if recommended_hour < 12 else "PM"
        display_hour = recommended_hour if recommended_hour <= 12 else recommended_hour - 12
        if display_hour == 0:
            display_hour = 12

        day_scores_list = [
            {"day": d, "score": s}
            for d, s in self.DAY_SCORES.items()
        ]
        day_scores_list.sort(key=lambda x: x["score"], reverse=True)

        return {
            "domain": domain_lower if "www." not in domain.lower() else domain.lower().replace("www.", ""),
            "industry_vertical": industry_vertical,
            "recommended_time": f"{display_hour}:00 {am_pm}",
            "recommended_hour_utc": recommended_hour,
            "recommended_day": timing["best_day"],
            "detected_timezone_offset": timezone_offset,
            "reason": timing["reason"],
            "day_scores": day_scores_list,
            "alternative_days": [d["day"] for d in day_scores_list if d["score"] >= 0.7 and d["day"] != timing["best_day"]][:2],
        }

    def _infer_industry_from_domain(self, domain: str) -> str:
        """Infer industry vertical from domain name keywords."""
        domain_clean = domain.lower().replace("www.", "")
        patterns = {
            "technology": ["tech", "software", "ai", "digital", "cloud", "saas", "data", "code", "dev", "api", "io"],
            "business": ["business", "finance", "invest", "market", "startup", "enterprise", "ventures", "capital", "inc"],
            "health": ["health", "medical", "wellness", "fitness", "nutrition", "doctor", "clinic", "care", "hospital"],
            "education": ["edu", "school", "academy", "university", "college", "learn", "course", "train", "study"],
            "news": ["news", "blog", "magazine", "journal", "daily", "weekly", "media", "press", "report"],
            "ecommerce": ["shop", "store", "buy", "product", "amazon", "etsy", "shopify", "market", "deal"],
            "marketing": ["marketing", "seo", "social", "brand", "advert", "content", "growth", "agency"],
        }
        for industry, keywords in patterns.items():
            for kw in keywords:
                if kw in domain_clean:
                    return industry
        return "general"

    def prioritize_prospects(
        self, prospects: list[dict], campaign_context: dict | None = None,
    ) -> list[dict]:
        """
        Rank prospects by composite priority score.

        Weights:
          Quality score (40%)
          Response probability (25%)
          Opportunity score (20%)
          Relationship strength (15%)
        """
        scored = []
        for prospect in prospects:
            quality = prospect.get("quality_score", prospect.get("composite_score", 0.5))
            response_prob = prospect.get("response_probability", 0.3)
            opportunity = prospect.get("opportunity_score", 0.4)
            relationship = prospect.get("relationship_score", 0.2)
            da = prospect.get("domain_authority", 40)

            priority = (
                quality * 0.40
                + response_prob * 0.25
                + opportunity * 0.20
                + relationship * 0.15
            )

            scored.append({
                "domain": prospect.get("domain", ""),
                "priority_rank": 0,
                "priority_score": round(priority, 4),
                "scoring_breakdown": {
                    "quality_score_weighted": round(quality * 0.40, 4),
                    "response_probability_weighted": round(response_prob * 0.25, 4),
                    "opportunity_score_weighted": round(opportunity * 0.20, 4),
                    "relationship_strength_weighted": round(relationship * 0.15, 4),
                    "raw_quality": round(quality, 4),
                    "raw_response_probability": round(response_prob, 4),
                    "raw_opportunity": round(opportunity, 4),
                    "raw_relationship": round(relationship, 4),
                },
                "domain_authority": da,
                "contact_email": prospect.get("contact_email", ""),
                "contact_confidence": prospect.get("contact_confidence", 0),
            })

        scored.sort(key=lambda x: x["priority_score"], reverse=True)
        for i, s in enumerate(scored):
            s["priority_rank"] = i + 1

        return scored

    def score_communication_quality(self, email_content: str) -> dict:
        """
        Score email quality across multiple dimensions.

        Dimensions:
          Personalization depth (named variables filled vs placeholders)
          Length appropriateness
          Value proposition clarity
          Call-to-action strength
          Professional tone score
        """
        if not email_content:
            return {
                "overall_score": 0.0,
                "dimensions": {},
                "recommendations": ["Email content is empty"],
            }

        has_placeholders = any(
            marker in email_content
            for marker in ["{name}", "{company}", "{domain}", "{{name", "{{company", "{{domain"]
        )

        if has_placeholders:
            personalization_score = 0.2
        else:
            personalization_score = 0.8

        name_in_body = bool(re.search(r'\bHi\b.*[,:]', email_content)) or bool(
            re.search(r'\bDear\b', email_content)
        )
        if name_in_body:
            personalization_score = max(personalization_score, 0.6)

        word_count = len(email_content.split())
        if 80 <= word_count <= 200:
            length_score = 1.0
        elif 50 <= word_count < 80 or 200 < word_count <= 300:
            length_score = 0.7
        elif word_count < 50:
            length_score = 0.4
        else:
            length_score = 0.2

        lower_content = email_content.lower()
        value_signals = [
            "value", "benefit", "increase", "improve", "growth", "traffic",
            "audience", "readers", "quality", "relevant", "help", "useful",
        ]
        value_count = sum(1 for s in value_signals if s in lower_content)
        value_score = min(1.0, value_count / 5.0)

        cta_signals = [
            r'\b(?:let me know|please let|would you be|are you|interested|happy to|can I|shall we|looking forward|talk soon|reply|schedule|discuss)\b',
        ]
        cta_score = 0.0
        for pattern in cta_signals:
            if re.search(pattern, lower_content):
                cta_score = 0.7
                break
        if any(word in lower_content for word in ["let me know", "reply", "schedule", "call", "talk"]):
            cta_score = max(cta_score, 0.8)

        tone_signals_positive = [
            "pleased", "excited", "great", "wonderful", "appreciate", "thank",
            "grateful", "happy", "delighted", "hope",
        ]
        tone_signals_negative = [
            "urgent", "problem", "issue", "unfortunately", "sorry", "bad",
        ]
        tone_pos = sum(1 for s in tone_signals_positive if s in lower_content)
        tone_neg = sum(1 for s in tone_signals_negative if s in lower_content)
        tone_score = 0.5 + (tone_pos * 0.1) - (tone_neg * 0.1)
        tone_score = max(0.0, min(1.0, tone_score))

        overall = (
            personalization_score * 0.25
            + length_score * 0.15
            + value_score * 0.25
            + cta_score * 0.20
            + tone_score * 0.15
        )
        overall = max(0.0, min(1.0, overall))

        recommendations = []
        if has_placeholders:
            recommendations.append("Replace template placeholders with actual values")
        if length_score < 0.7:
            recommendations.append("Adjust email length to 80-200 words for optimal engagement")
        if value_score < 0.6:
            recommendations.append("Strengthen value proposition with clearer benefits")
        if cta_score < 0.6:
            recommendations.append("Add a clear call-to-action")
        if tone_score < 0.5:
            recommendations.append("Use a more positive and professional tone")
        if not recommendations:
            recommendations.append("Communication quality is well-optimized")

        return {
            "overall_score": round(overall, 4),
            "word_count": word_count,
            "dimensions": {
                "personalization_depth": {
                    "score": round(personalization_score, 4),
                    "has_placeholders": has_placeholders,
                    "greeting_detected": name_in_body,
                },
                "length_appropriateness": {
                    "score": round(length_score, 4),
                    "word_count": word_count,
                    "is_optimal": 80 <= word_count <= 200,
                },
                "value_proposition_clarity": {
                    "score": round(value_score, 4),
                    "value_signal_count": value_count,
                },
                "call_to_action_strength": {
                    "score": round(cta_score, 4),
                },
                "professional_tone": {
                    "score": round(tone_score, 4),
                    "positive_signals": tone_pos,
                    "negative_signals": tone_neg,
                },
            },
            "recommendations": recommendations,
        }

    async def recommend_follow_up(self, email_thread: dict) -> dict:
        """
        Recommend follow-up strategy based on email thread analysis.

        Factors:
          Days since last email
          Response status
          Previous follow-up count
          Optimal timing for next follow-up
          Suggested follow-up angle
        """
        from datetime import datetime

        last_email_at = email_thread.get("last_email_at")
        if isinstance(last_email_at, str):
            try:
                last_email_at = datetime.fromisoformat(last_email_at)
            except Exception:
                last_email_at = None

        if last_email_at is None:
            last_email_at = datetime.now(timezone.utc) - timedelta(days=7)

        if last_email_at.tzinfo is None:
            last_email_at = last_email_at.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        days_since = (now - last_email_at).total_seconds() / 86400.0

        response_status = email_thread.get("response_status", "no_reply")
        follow_up_count = email_thread.get("follow_up_count", 0)
        max_follow_ups = email_thread.get("max_follow_ups", 3)
        previous_sentiment = email_thread.get("previous_sentiment", "neutral")
        thread_id = email_thread.get("thread_id", "")

        if response_status == "replied":
            return {
                "thread_id": thread_id,
                "action": "await_reply_or_close",
                "reason": "Prospect has already replied — continue conversation",
                "days_since_last_email": round(days_since, 1),
                "follow_up_count": follow_up_count,
                "recommended_wait_days": 0,
                "suggested_angle": "continue_conversation",
                "next_steps": ["Respond to their reply", "Address any questions raised"],
            }

        if follow_up_count >= max_follow_ups:
            return {
                "thread_id": thread_id,
                "action": "close_outreach",
                "reason": f"Maximum follow-ups ({max_follow_ups}) reached",
                "days_since_last_email": round(days_since, 1),
                "follow_up_count": follow_up_count,
                "recommended_wait_days": 0,
                "suggested_angle": "none",
                "next_steps": ["Move prospect to unresponsive status", "Consider alternative contact method"],
            }

        optimal_gap = min(3 + follow_up_count * 2, 14)
        if days_since < optimal_gap:
            wait_days = round(optimal_gap - days_since)
            return {
                "thread_id": thread_id,
                "action": "wait",
                "reason": f"Optimal follow-up gap is {optimal_gap} days ({wait_days} days remaining)",
                "days_since_last_email": round(days_since, 1),
                "follow_up_count": follow_up_count,
                "recommended_wait_days": wait_days,
                "suggested_angle": "none",
                "next_steps": [f"Wait {wait_days} more days before following up"],
            }

        angles = [
            "value_add",
            "alternative",
            "social_proof",
            "breakage",
            "personalized_content",
        ]
        available_angles = angles[follow_up_count:] if follow_up_count < len(angles) else ["value_add"]
        primary_angle = available_angles[0] if available_angles else "value_add"

        angle_descriptions = {
            "value_add": "Share additional value or a relevant resource",
            "alternative": "Suggest an alternative approach or content angle",
            "social_proof": "Mention other publications that have featured similar content",
            "breakage": "Reference a broken or outdated resource they may want to update",
            "personalized_content": "Offer a custom content idea tailored to their audience",
        }

        return {
            "thread_id": thread_id,
            "action": "send_follow_up",
            "reason": f"Follow-up #{follow_up_count + 1} ready — {angle_descriptions.get(primary_angle, 'standard follow-up')}",
            "days_since_last_email": round(days_since, 1),
            "follow_up_count": follow_up_count,
            "recommended_wait_days": 0,
            "suggested_angle": primary_angle,
            "angle_description": angle_descriptions.get(primary_angle, ""),
            "available_angles": available_angles,
            "next_steps": [
                "Personalize follow-up based on previous email",
                angle_descriptions.get(primary_angle, "Send follow-up"),
                "Track open and response",
            ],
        }

    async def score_relationship_depth(
        self, tenant_id: UUID, domain: str,
    ) -> dict:
        """
        Score ongoing relationship depth with a domain.

        Factors:
          Email exchange count
          Reply sentiment trend
          Link acquisition history
          Communication frequency
        """
        from sqlalchemy import func, select

        from seo_platform.core.database import get_tenant_session
        from seo_platform.models.backlink import BacklinkProspect, OutreachThread, ThreadStatus

        domain_clean = domain.lower().replace("www.", "")

        email_exchange_count = 0
        reply_sentiment = "neutral"
        link_acquired = False
        link_count = 0
        communication_frequency = 0.0

        async with get_tenant_session(tenant_id) as session:
            prospect_result = await session.execute(
                select(BacklinkProspect).where(
                    BacklinkProspect.domain.ilike(f"%{domain_clean}%"),
                )
            )
            prospect = prospect_result.scalar_one_or_none()

            if prospect:
                threads_result = await session.execute(
                    select(OutreachThread).where(
                        OutreachThread.prospect_id == prospect.id,
                    )
                )
                threads = threads_result.scalars().all()
                email_exchange_count = len(threads)

                replied = [t for t in threads if t.status == ThreadStatus.REPLIED]
                if replied:
                    reply_sentiment = "positive"

                from seo_platform.models.backlink import AcquiredLink
                link_count_result = await session.execute(
                    select(func.count()).select_from(AcquiredLink).where(
                        AcquiredLink.prospect_id == prospect.id,
                        AcquiredLink.status.in_(["verified_live", "verified_nofollow"]),
                    )
                )
                link_count = link_count_result.scalar() or 0
                link_acquired = link_count > 0

                if prospect.updated_at and prospect.created_at:
                    age_days = (datetime.now(timezone.utc) - prospect.created_at.replace(tzinfo=timezone.utc) if prospect.created_at.tzinfo is None else prospect.created_at).total_seconds() / 86400.0
                    communication_frequency = email_exchange_count / max(age_days, 1)

        recency_score = min(1.0, email_exchange_count / 10.0)
        sentiment_score = 0.7 if reply_sentiment == "positive" else 0.4
        acquisition_score = 1.0 if link_acquired else 0.0
        frequency_score = min(1.0, communication_frequency * 5.0)

        overall = (
            recency_score * 0.25
            + sentiment_score * 0.20
            + acquisition_score * 0.35
            + frequency_score * 0.20
        )

        history_summary = (
            f"{email_exchange_count} email exchanges, "
            f"{link_count} link(s) acquired, "
            f"sentiment: {reply_sentiment}"
        )

        next_action = "nurture"
        if not link_acquired and email_exchange_count > 0:
            next_action = "follow_up_for_link"
        elif link_acquired:
            next_action = "maintain_relationship"

        relationship_label = (
            "strong" if overall >= 0.7
            else "moderate" if overall >= 0.4
            else "weak"
        )

        return {
            "domain": domain_clean,
            "relationship_score": round(overall, 4),
            "relationship_label": relationship_label,
            "history_summary": history_summary,
            "next_action": next_action,
            "components": {
                "email_exchange_count": email_exchange_count,
                "reply_sentiment": reply_sentiment,
                "link_acquisition_count": link_count,
                "link_acquired": link_acquired,
                "communication_frequency": round(communication_frequency, 4),
            },
        }

    # ------------------------------------------------------------------
    # Entity & Social Graph Ingestion & Bespoke Pitching (Phase 7)
    # ------------------------------------------------------------------
    async def generate_humanized_bespoke_pitch(
        self, tenant_id: UUID, prospect_data: dict, client_context: dict,
    ) -> dict[str, Any]:
        """
        Advanced Entity & Social Graph Bespoke Pitch Engine (Phase 7).
        Replaces generic AI markdown summarization with genuine relationship building by:
        1. Ingesting author social graph signals (LinkedIn posts, Twitter threads, podcasts)
        2. Ingesting client value-add assets (proprietary data points, custom graphics)
        3. Crafting an elite, humanized pitch that establishes genuine off-page rapport
        4. Completely avoiding synthetic 'I noticed your excellent article' AI footprints
        """
        logger.info("generate_humanized_bespoke_pitch", domain=prospect_data.get("domain", ""), tenant_id=str(tenant_id))

        from pydantic import BaseModel

        class _BespokePitchSchema(BaseModel):
            subject_line: str
            body_content: str
            value_add_type: str
            personalization_angle: str

        author_name = prospect_data.get("contact_name", "Editor")
        social_signal = prospect_data.get("social_graph_signal", "Recent discussion on industry trends and content strategy.")
        
        client_name = client_context.get("client_name", "Our Platform")
        value_add_asset = client_context.get("value_add_asset", "Proprietary benchmark data and custom infographics.")

        try:
            from seo_platform.llm.gateway import RenderedPrompt, TaskType, llm_gateway

            prompt = RenderedPrompt(
                template_id="humanized_bespoke_pitch",
                system_prompt=(
                    "You are an elite enterprise digital PR and backlink acquisition strategist. Craft a highly bespoke, "
                    "humanized outreach pitch to an editor/author. You MUST adhere to these strict editorial rules:\n"
                    "1. Opening Rapport: Reference their specific off-page social graph signal (LinkedIn/Twitter/podcast) with genuine warmth.\n"
                    "2. ZERO AI Footprints: Do NOT say 'I noticed your excellent article on X' or summarize their about page.\n"
                    "3. Bespoke Value Exchange: Pitch a specific, high-value editorial asset (custom graphic, proprietary data quote) from the client.\n"
                    "4. Professional Call to Action: Close with a low-friction, conversational next step.\n"
                    "Return ONLY a JSON object matching the schema with subject_line, body_content, value_add_type, and personalization_angle."
                ),
                user_prompt=(
                    f"Author/Editor: {author_name}\n"
                    f"Author Social Graph Signal: '{social_signal}'\n\n"
                    f"Client Name: {client_name}\n"
                    f"Client Value-Add Asset: '{value_add_asset}'\n\n"
                    "Craft the elite bespoke pitch now."
                ),
            )

            llm_result = await llm_gateway.complete(
                task_type=TaskType.SEO_ANALYSIS,
                prompt=prompt,
                output_schema=_BespokePitchSchema,
                tenant_id=tenant_id,
            )

            content = llm_result.content
            return {
                "subject_line": content.subject_line,
                "body_content": content.body_content,
                "value_add_type": content.value_add_type,
                "personalization_angle": content.personalization_angle,
                "generation_source": "social_graph_bespoke_ai",
            }

        except Exception as e:
            logger.warning("bespoke_pitch_generation_failed", error=str(e))
            # Elite deterministic fallback avoiding generic AI footprints
            first_name = author_name.split()[0] if author_name else "there"
            fallback_subj = f"Quick question regarding your recent thoughts on {client_context.get('industry', 'industry trends')}"
            fallback_body = (
                f"Hi {first_name},\n\n"
                f"I really enjoyed your recent commentary regarding {social_signal.lower()[:50]}. It's rare to see someone address the nuances so directly.\n\n"
                f"We recently compiled some exclusive benchmark data at {client_name} specifically exploring {value_add_asset.lower()[:50]}. "
                f"I thought the custom charts might be a perfect drop-in addition for your upcoming pieces to give your readers an extra visual edge.\n\n"
                f"Would you be open to me sending over a quick preview link to see if it aligns?\n\n"
                f"Best regards,\n{client_name} Team"
            )
            return {
                "subject_line": fallback_subj,
                "body_content": fallback_body,
                "value_add_type": "proprietary_data_charts",
                "personalization_angle": "social_commentary_alignment",
                "generation_source": "elite_deterministic_fallback",
            }


outreach_intelligence = OutreachIntelligenceService()
