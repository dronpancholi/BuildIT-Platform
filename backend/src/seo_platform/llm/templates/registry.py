"""
SEO Platform — Centralized Prompt Template Registry
=====================================================
Structured template definitions ensuring absolute prompt determinism.
Every LLM invocation resolves its system/user prompts through this
registry rather than embedding raw strings in business logic.

Design:
- Each PromptTemplate stores the template_id, system_prompt, user_prompt,
  and default token budget.
- Services call ``prompt_registry.render(template_id, **variables)`` to
  obtain a ``RenderedPrompt`` ready for inference.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PromptTemplate(BaseModel):
    """Canonical prompt template definition."""

    template_id: str = Field(..., min_length=1)
    system_prompt: str = Field(..., min_length=1)
    user_prompt: str = Field(..., min_length=1)
    default_token_budget: int = Field(default=2048, ge=256, le=8192)

    def render(self, **variables: Any) -> tuple[str, str]:
        """Return (system_prompt, user_prompt) with variables substituted.

        Variables are replaced via ``str.format(**variables)``. Missing
        keys raise KeyError to prevent silent prompt corruption.
        """
        return (
            self.system_prompt.format(**variables),
            self.user_prompt.format(**variables),
        )


# ---------------------------------------------------------------------------
# Template Definitions
# ---------------------------------------------------------------------------

HUMANIZED_BESPOKE_PITCH = PromptTemplate(
    template_id="humanized_bespoke_pitch",
    default_token_budget=2048,
    system_prompt=(
        "You are an elite enterprise digital PR and backlink acquisition strategist. "
        "Craft a highly bespoke, humanized outreach pitch to an editor/author. "
        "You MUST adhere to these strict editorial rules:\n"
        "1. Opening Rapport: Reference their specific off-page social graph signal "
        "(LinkedIn/Twitter/podcast) with genuine warmth.\n"
        "2. ZERO AI Footprints: Do NOT say 'I noticed your excellent article on X' "
        "or summarize their about page.\n"
        "3. Bespoke Value Exchange: Pitch a specific, high-value editorial asset "
        "(custom graphic, proprietary data quote) from the client.\n"
        "4. Professional Call to Action: Close with a low-friction, conversational next step.\n"
        "Return ONLY a JSON object matching the schema with subject_line, body_content, "
        "value_add_type, and personalization_angle."
    ),
    user_prompt=(
        "Author/Editor: {author_name}\n"
        "Author Social Graph Signal: '{social_signal}'\n\n"
        "Client Name: {client_name}\n"
        "Client Value-Add Asset: '{value_add_asset}'\n\n"
        "Craft the elite bespoke pitch now."
    ),
)

DATA_JOURNALISM_ANGLE_EXTRACTION = PromptTemplate(
    template_id="data_journalism_angle_extraction",
    default_token_budget=3072,
    system_prompt=(
        "You are an elite data journalist at a top-tier business publication. "
        "Analyze the provided dataset and extract the single most newsworthy, "
        "counter-intuitive editorial angle. Return ONLY a JSON object matching "
        "the schema with: headline, counter_intuitive_hook (a specific, "
        "data-driven insight that defies conventional wisdom), "
        "supporting_data_points (array of {{metric_name, metric_value, "
        "percentage_change, statistical_significance}}), "
        "and target_journalist_beat."
    ),
    user_prompt=(
        "Analyze this client dataset for a compelling editorial angle:\n\n"
        "Target beat: {target_beat}\n\n"
        "Dataset ({dataset_record_count} records, showing first 20):\n{dataset_summary}\n\n"
        "Identify the most surprising, counter-intuitive insight that would "
        "earn coverage in a Tier-1 publication."
    ),
)

CLIENT_PERSONA_SUMMARY = PromptTemplate(
    template_id="client_persona_summary",
    default_token_budget=2048,
    system_prompt=(
        "You are a brand strategist. Based on the provided editorial guidelines "
        "and historical email samples, produce a concise brand voice summary "
        "that captures tone, vocabulary constraints, and audience positioning. "
        "Return ONLY valid JSON."
    ),
    user_prompt=(
        "Brand Voice Summary: {brand_voice_summary}\n"
        "Editorial Constraints: {editorial_constraints}\n"
        "Historical Email Samples: {email_samples}\n\n"
        "Produce the refined brand voice summary."
    ),
)

SERP_INTENT_ANALYSIS = PromptTemplate(
    template_id="serp_intent_analysis",
    default_token_budget=2048,
    system_prompt=(
        "You are an elite SEO strategist analyzing Search Engine Results Pages (SERPs). "
        "Given a keyword and its SERP features, determine the dominant search intent "
        "(informational, navigational, commercial, transactional), identify E-E-A-T "
        "requirements, and recommend a content pivot. Return ONLY valid JSON matching "
        "the output schema."
    ),
    user_prompt=(
        "Keyword: {keyword}\n"
        "SERP Features: {serp_features}\n"
        "Top-ranking URLs: {top_urls}\n\n"
        "Analyze intent and recommend content pivot."
    ),
)

EXECUTIVE_REPORTING = PromptTemplate(
    template_id="executive_reporting",
    default_token_budget=4096,
    system_prompt=(
        "You are an executive reporting assistant. Produce a concise, data-driven "
        "campaign performance summary. Use only metrics provided in the context — "
        "do not fabricate numbers. Return ONLY valid JSON matching the output schema."
    ),
    user_prompt=(
        "Campaign: {campaign_name}\n"
        "Period: {period}\n"
        "Metrics: {metrics}\n\n"
        "Generate the executive report."
    ),
)

OUTREACH_EMAIL_GENERATION = PromptTemplate(
    template_id="outreach_email_generation",
    default_token_budget=3072,
    system_prompt=(
        "You are an elite outreach specialist writing on behalf of the client. "
        "Generate a {stage} outreach email.\n"
        "BRAND VOICE SUMMARY: {brand_voice_summary}\n"
        "PROHIBITED BUZZWORDS: {prohibited_words}. "
        "Do NOT use these words under any circumstances.\n"
        "FORMALITY LEVEL: {formality_level}.\n"
        "Return ONLY a JSON object with 'subject', 'body_html', and 'personalized_opening' fields.\n"
        "CRITICAL: Reference the recipient's actual site content without sounding "
        "like an AI summary.\n"
        "{correction_hint}"
    ),
    user_prompt=(
        "CONTEXT:\n"
        "- Recipient name: {contact_name}\n"
        "- Target domain: {domain}\n"
        "- Domain authority: {domain_authority}/100\n"
        "- Relevance score: {relevance_score}/1.0\n"
        "- Topical relevance: {topical_relevance}\n"
        "- Campaign type: {campaign_type}\n"
        "- Value offer: {value_offer}\n\n"
        "WEBSITE CONTENT:\n{site_context}\n\n"
        "{extra_instructions}\n\n"
        "Requirements:\n"
        "- Subject under 60 characters\n"
        "- Professional HTML body\n"
        "- Human-sounding, not templated\n"
        "- Every claim in the opening must be grounded in the WEBSITE CONTENT above"
        "{tone_instruction}"
    ),
)


REGISTRY: dict[str, PromptTemplate] = {
    t.template_id: t
    for t in [
        HUMANIZED_BESPOKE_PITCH,
        DATA_JOURNALISM_ANGLE_EXTRACTION,
        CLIENT_PERSONA_SUMMARY,
        SERP_INTENT_ANALYSIS,
        EXECUTIVE_REPORTING,
        OUTREACH_EMAIL_GENERATION,
    ]
}


def get_template(template_id: str) -> PromptTemplate:
    """Look up a template by id. Raises KeyError if not found.

    Usage::

        template = get_template("humanized_bespoke_pitch")
        sys, usr = template.render(author_name="Jane Doe", ...)
    """
    if template_id not in REGISTRY:
        raise KeyError(f"Unknown prompt template: {template_id!r}. "
                       f"Available: {sorted(REGISTRY)}")
    return REGISTRY[template_id]
