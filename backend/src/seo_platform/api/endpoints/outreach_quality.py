"""
Phase 12E — Outreach Intelligence Engine
===========================================
Evaluates outreach email quality before sending.

Scores: personalization, relevance, readability, spam risk, response probability.
Every email gets an explainable quality score.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from seo_platform.core.auth import get_current_user

router = APIRouter()


class EmailQualityRequest(BaseModel):
    subject: str
    body: str
    prospect_domain: str | None = None
    prospect_name: str | None = None
    campaign_type: str | None = None


def _score_email_quality(req: EmailQualityRequest) -> dict:
    """Compute email quality score with full breakdown."""
    components = {}

    # Personalization score (0-25)
    personalization_signals = []
    body_lower = req.body.lower()

    if req.prospect_name and req.prospect_name.lower() in body_lower:
        personalization_signals.append("Prospect name used")
    if req.prospect_domain and req.prospect_domain.lower() in body_lower:
        personalization_signals.append("Prospect domain referenced")
    if any(w in body_lower for w in ["your site", "your content", "your article", "your blog"]):
        personalization_signals.append("Specific reference to their content")
    if any(w in body_lower for w in ["i noticed", "i saw", "i read", "i came across"]):
        personalization_signals.append("Personal observation mentioned")

    pers_score = min(25, len(personalization_signals) * 8)
    components["personalization"] = {
        "score": pers_score,
        "max": 25,
        "signals": personalization_signals,
        "reason": f"{len(personalization_signals)} personalization signals detected" if personalization_signals else "No personalization detected — email appears generic",
    }

    # Readability score (0-25)
    words = req.body.split()
    word_count = len(words)
    sentences = req.body.split(".")
    sentence_count = max(1, len(sentences))

    avg_words_per_sentence = word_count / sentence_count
    readability_signals = []

    if 50 <= word_count <= 300:
        readability_signals.append(f"Good length ({word_count} words)")
    elif word_count < 50:
        readability_signals.append(f"Too short ({word_count} words)")
    else:
        readability_signals.append(f"Too long ({word_count} words)")

    if avg_words_per_sentence <= 20:
        readability_signals.append("Short, readable sentences")
    else:
        readability_signals.append(f"Long sentences (avg {avg_words_per_sentence:.0f} words)")

    if req.body.count("\n\n") >= 1:
        readability_signals.append("Uses paragraph breaks")

    read_score = 0
    if 50 <= word_count <= 300:
        read_score += 10
    if avg_words_per_sentence <= 20:
        read_score += 8
    if req.body.count("\n\n") >= 1:
        read_score += 4
    if word_count > 0:
        read_score += 3  # base score for having content

    components["readability"] = {
        "score": min(25, read_score),
        "max": 25,
        "signals": readability_signals,
        "reason": f"Readability analysis: {', '.join(readability_signals)}",
    }

    # Relevance score (0-25)
    relevance_signals = []
    if req.campaign_type:
        type_keywords = {
            "guest_post": ["guest post", "write for us", "contribute", "article"],
            "broken_link": ["broken link", "404", "resource", "replacement"],
            "resource_page": ["resource", "list", "curated", "guide"],
            "niche_edit": ["update", "edit", "add", "include"],
        }
        for kw in type_keywords.get(req.campaign_type, []):
            if kw in body_lower:
                relevance_signals.append(f"Campaign-type relevant ({kw})")

    if any(w in body_lower for w in ["valuable", "helpful", "useful", "benefit"]):
        relevance_signals.append("Value proposition present")
    if any(w in body_lower for w in ["collaborate", "partnership", "work together"]):
        relevance_signals.append("Collaboration framing")

    rel_score = min(25, len(relevance_signals) * 8 + 5)
    components["relevance"] = {
        "score": rel_score,
        "max": 25,
        "signals": relevance_signals,
        "reason": f"{len(relevance_signals)} relevance signals" if relevance_signals else "Low relevance signals — email may not match campaign goal",
    }

    # Spam risk score (0-25, lower spam = higher score)
    spam_words = [
        "free", "buy", "discount", "offer", "limited time", "act now",
        "click here", "subscribe", "unsubscribe", "money", "cash",
        "guarantee", "no obligation", "risk free", "winner", "congratulations",
        "dear friend", "dear sir", "to whom", "increase your", "boost your",
    ]
    spam_hits = [w for w in spam_words if w in body_lower]
    spam_score = 25 - min(25, len(spam_hits) * 5)

    spam_signals = []
    if spam_hits:
        spam_signals.append(f"Spam words found: {', '.join(spam_hits)}")
    else:
        spam_signals.append("No spam trigger words detected")

    if req.body.isupper():
        spam_score -= 10
        spam_signals.append("ALL CAPS detected")

    if req.body.count("!") > 3:
        spam_score -= 5
        spam_signals.append(f"Excessive exclamation marks ({req.body.count('!')})")

    components["spam_risk"] = {
        "score": max(0, spam_score),
        "max": 25,
        "signals": spam_signals,
        "reason": f"Spam analysis: {', '.join(spam_signals)}",
    }

    # Response probability (0-25)
    response_signals = []
    prob = 0.15  # base probability

    if pers_score >= 15:
        prob += 0.15
        response_signals.append("High personalization increases response")
    if read_score >= 15:
        prob += 0.10
        response_signals.append("Good readability increases response")
    if spam_score >= 20:
        prob += 0.10
        response_signals.append("Clean content avoids spam filters")
    if word_count <= 200:
        prob += 0.05
        response_signals.append("Concise email improves response")

    response_prob = min(0.95, prob)
    response_score = round(response_prob * 25, 1)

    components["response_probability"] = {
        "score": response_score,
        "max": 25,
        "estimated_probability": round(response_prob, 2),
        "signals": response_signals,
        "reason": f"Estimated response probability: {response_prob:.0%}. {', '.join(response_signals) if response_signals else 'Low signals for response'}",
    }

    total = sum(c["score"] for c in components.values())

    if total >= 85:
        tier = "EXCELLENT"
    elif total >= 70:
        tier = "GOOD"
    elif total >= 50:
        tier = "FAIR"
    elif total >= 30:
        tier = "POOR"
    else:
        tier = "DO_NOT_SEND"

    return {
        "score": total,
        "max_score": 100,
        "percentage": round(total, 1),
        "tier": tier,
        "components": components,
        "recommendation": _get_recommendation(tier, components),
    }


def _get_recommendation(tier: str, components: dict) -> str:
    if tier == "DO_NOT_SEND":
        return "Do not send this email. It has high spam risk and low personalization. Rewrite with prospect-specific details."
    elif tier == "POOR":
        return "Major improvements needed. Add prospect name, reference their content, remove spam words."
    elif tier == "FAIR":
        return "Decent but could be better. Consider adding more personalization and shortening the email."
    elif tier == "GOOD":
        return "Good quality email. Minor improvements possible in personalization or readability."
    else:
        return "Excellent email quality. Ready to send."


@router.post("/quality")
async def evaluate_email_quality(
    req: EmailQualityRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """Evaluate outreach email quality before sending."""
    result = _score_email_quality(req)
    return {
        "success": True,
        "data": result,
        "error": None,
    }
