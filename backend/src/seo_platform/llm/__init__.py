"""
SEO Platform — LLM Package
"""

from seo_platform.llm.gateway import LLMGateway, LLMResult, ModelRole, TaskType, llm_gateway
from seo_platform.llm.templates.registry import (
    REGISTRY,
    PromptTemplate,
    get_template,
)

__all__ = [
    "LLMGateway", "LLMResult", "ModelRole", "PromptTemplate",
    "REGISTRY", "TaskType", "get_template", "llm_gateway",
]
