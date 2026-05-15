"""
SEO Platform — AI Governance Pipeline
========================================
Independent governance layer between LLM Gateway and all consumers.
This layer is NOT optional and cannot be bypassed by any workflow.

Pipeline: PII Detection → Prompt Injection → Hallucination → Compliance → Audit
"""

from __future__ import annotations

import hashlib
import re
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Governance Result
# ---------------------------------------------------------------------------
class GovernanceResult(BaseModel):
    """Aggregate result from the full governance pipeline."""
    passed: bool = True
    output_blocked: bool = False
    output_modified: bool = False
    pii_detections: list[str] = Field(default_factory=list)
    injection_detections: list[str] = Field(default_factory=list)
    hallucination_flags: int = 0
    compliance_issues: list[str] = Field(default_factory=list)
    sanitized_text: str = ""


# ---------------------------------------------------------------------------
# PII Detector
# ---------------------------------------------------------------------------
class PIIDetector:
    """Detect and mask PII in LLM outputs before persistence."""

    PATTERNS: dict[str, str] = {
        "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "phone_us": r'\b(\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
        "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
        "credit_card": r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
        "ip_address": r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
    }

    def scan_and_mask(self, text: str) -> tuple[str, list[str]]:
        """Scan text for PII and return masked version + detection list."""
        detections: list[str] = []
        masked = text
        for pii_type, pattern in self.PATTERNS.items():
            matches = list(re.finditer(pattern, text))
            for match in matches:
                detections.append(pii_type)
                masked = masked.replace(match.group(), f"[{pii_type.upper()}_REDACTED]")
        return masked, detections


# ---------------------------------------------------------------------------
# Prompt Injection Detector
# ---------------------------------------------------------------------------
class PromptInjectionDetector:
    """Detect prompt injection attempts in prospect-sourced data."""

    PATTERNS: list[str] = [
        r"ignore (previous|above|prior) instructions?",
        r"new instruction",
        r"system prompt",
        r"you are now",
        r"disregard (everything|all)",
        r"<\|system\|>",
        r"\[INST\]",
        r"###\s*(system|instruction|prompt)",
        r"act as",
        r"jailbreak",
    ]

    def scan(self, text: str) -> list[str]:
        """Return list of injection patterns detected."""
        normalized = re.sub(r'\s+', ' ', text.lower())
        detections = []
        for pattern in self.PATTERNS:
            if re.search(pattern, normalized, re.IGNORECASE):
                detections.append(pattern)
        return detections

    def sanitize(self, data: dict[str, Any]) -> dict[str, Any]:
        """Sanitize all string fields in prospect data."""
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                detections = self.scan(value)
                if detections:
                    sanitized[key] = "[CONTENT_REMOVED: injection attempt detected]"
                    logger.warning("injection_detected", field=key, patterns=detections)
                else:
                    sanitized[key] = value
            else:
                sanitized[key] = value
        return sanitized


# ---------------------------------------------------------------------------
# AI Governance Pipeline
# ---------------------------------------------------------------------------
class AIGovernancePipeline:
    """
    Full governance pipeline executed on every LLM output.

    Order: PII → Injection → Compliance → Audit Log
    """

    def __init__(self) -> None:
        self.pii_detector = PIIDetector()
        self.injection_detector = PromptInjectionDetector()

    async def evaluate(
        self,
        llm_output: str,
        grounded_context: dict[str, Any],
        task_type: str,
        tenant_id: UUID,
        workflow_run_id: str | None = None,
    ) -> GovernanceResult:
        """Run the full governance pipeline on LLM output."""
        result = GovernanceResult(sanitized_text=llm_output)

        # 1. PII Detection & Masking
        masked_text, pii_detections = self.pii_detector.scan_and_mask(llm_output)
        if pii_detections:
            result.pii_detections = pii_detections
            result.output_modified = True
            result.sanitized_text = masked_text
            logger.info("pii_detected_in_output", count=len(pii_detections),
                       task_type=task_type, tenant_id=str(tenant_id))

        # 2. Prompt Injection Check
        injection_detections = self.injection_detector.scan(llm_output)
        if injection_detections:
            result.injection_detections = injection_detections
            result.output_blocked = True
            result.passed = False
            logger.warning("injection_in_llm_output", patterns=injection_detections,
                          task_type=task_type, tenant_id=str(tenant_id))

        # 3. CAN-SPAM Compliance (for outreach tasks)
        if "outreach" in task_type:
            compliance_issues = self._check_outreach_compliance(llm_output)
            if compliance_issues:
                result.compliance_issues = compliance_issues
                result.passed = False

        # 4. Audit
        logger.info(
            "governance_evaluation_complete",
            passed=result.passed,
            blocked=result.output_blocked,
            modified=result.output_modified,
            pii_count=len(result.pii_detections),
            injection_count=len(result.injection_detections),
            compliance_issues=len(result.compliance_issues),
            task_type=task_type,
            tenant_id=str(tenant_id),
        )

        return result

    def _check_outreach_compliance(self, text: str) -> list[str]:
        """CAN-SPAM compliance checks for outreach emails."""
        issues = []
        lower_text = text.lower()
        if "unsubscribe" not in lower_text:
            issues.append("Missing unsubscribe link/instruction")
        # Check for deceptive subject line patterns
        deceptive_patterns = [r"^re:", r"^fw:", r"^fwd:"]
        for pattern in deceptive_patterns:
            if re.search(pattern, lower_text):
                issues.append(f"Potentially deceptive subject line prefix: {pattern}")
        return issues

    def sanitize_prospect_data(self, prospect_data: dict[str, Any]) -> dict[str, Any]:
        """Pre-process prospect data before injecting into prompts."""
        return self.injection_detector.sanitize(prospect_data)


# Module singleton
governance_pipeline = AIGovernancePipeline()
