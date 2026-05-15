"""
SEO Platform — Citation AI Planning & Enrichment
=================================================
Utilizes the enterprise NIM models to analyze local SEO opportunities
and automatically map categories across directories.
"""

from uuid import UUID

from pydantic import BaseModel

from seo_platform.core.logging import get_logger
from seo_platform.llm.gateway import RenderedPrompt, TaskType, llm_gateway
from seo_platform.models.citation import BusinessProfile

logger = get_logger(__name__)

class DirectoryRecommendation(BaseModel):
    directory_name: str
    relevance_score: float
    authority_score: float
    reasoning: str

class CitationStrategy(BaseModel):
    priority_directories: list[DirectoryRecommendation]
    niche_opportunities: list[str]
    local_seo_analysis: str

class CategoryMapping(BaseModel):
    source_category: str
    target_directory: str
    mapped_category: str
    confidence: float

class CitationAIIntelligence:

    async def generate_citation_strategy(self, profile: BusinessProfile, tenant_id: UUID) -> CitationStrategy:
        """
        Uses DeepSeek-V4-Pro to analyze the business profile and propose a strategic 
        citation roadmap based on geography and industry niche.
        """
        logger.info("generating_citation_strategy", client_id=str(profile.client_id))

        prompt = RenderedPrompt(
            template_id="citation_strategy_v1",
            system_prompt=(
                "You are an elite Local SEO Strategist. Analyze the provided business profile "
                "and generate a deterministic, highly-targeted directory submission strategy. "
                "Prioritize high-authority general directories and niche-specific geographic targets."
            ),
            user_prompt=(
                f"Business Name: {profile.business_name}\n"
                f"Category: {profile.primary_category}\n"
                f"Location: {profile.city}, {profile.state_province}\n"
                f"Description: {profile.description}\n\n"
                "Generate the citation strategy."
            )
        )

        # Maps to DeepSeek-V4-Pro via LLM Gateway routing architecture
        result = await llm_gateway.complete(
            task_type=TaskType.SEO_ANALYSIS,
            prompt=prompt,
            output_schema=CitationStrategy,
            tenant_id=tenant_id
        )
        return result.content

    async def map_directory_categories(self, profile: BusinessProfile, target_directory: str, tenant_id: UUID) -> CategoryMapping:
        """
        Uses Gemma 4 31B to map our internal canonical category to the specific
        taxonomy required by the target directory (e.g., Yelp vs YellowPages).
        """
        logger.info("mapping_directory_category", directory=target_directory)

        prompt = RenderedPrompt(
            template_id="category_mapping_v1",
            system_prompt=(
                "You are a taxonomy mapping engine. Map the provided canonical business category "
                "to the closest exact match within the target directory's known category tree."
            ),
            user_prompt=(
                f"Canonical Category: {profile.primary_category}\n"
                f"Target Directory: {target_directory}\n"
                f"Business Description: {profile.description}\n\n"
                "Return the exact mapped category string."
            )
        )

        # Maps to Gemma 4 31B IT
        result = await llm_gateway.complete(
            task_type=TaskType.KEYWORD_CLUSTERING, # Re-using utility role map
            prompt=prompt,
            output_schema=CategoryMapping,
            tenant_id=tenant_id
        )
        return result.content

citation_ai_engine = CitationAIIntelligence()
