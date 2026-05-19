"""
SEO Platform — Compliance Scoring Engine
===========================================
Deterministic post-generation scoring for AI email pitches.
Checks prohibited words, sentence token length, and returns a
mathematical compliance score from 0.0 (fail) to 1.0 (perfect).
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from seo_platform.models.observability import ComplianceResult

logger = logging.getLogger(__name__)


class ComplianceScorer:
    """Scores AI-generated content against brand guideline rules."""

    DEFAULT_PROHIBITED_WORDS: list[str] = [
        "synergy", "leverage", "game-changer", "revolutionary", "disrupt",
        "groundbreaking", "cutting-edge", "state-of-the-art", "best-in-class",
        "next-generation", "i noticed your excellent article", "i loved your post",
        "i came across your", "i stumbled upon your",
    ]
    DEFAULT_MAX_SENTENCE_TOKENS: int = 25

    async def score_email_pitch(
        self,
        tenant_id: UUID,
        email_body: str,
        entity_id: UUID | None = None,
        entity_type: str = "email_pitch",
        prohibited_words: list[str] | None = None,
        max_sentence_tokens: int | None = None,
    ) -> dict[str, Any]:
        """
        Evaluate an email body against compliance rules.

        Returns a dict with score (0.0–1.0), violations list, and pass/fail.
        Persists the result to ComplianceResult in PostgreSQL.
        """
        banned = prohibited_words or self.DEFAULT_PROHIBITED_WORDS
        max_tokens = max_sentence_tokens or self.DEFAULT_MAX_SENTENCE_TOKENS
        violations: dict[str, list[str]] = {"banned_words": [], "long_sentences": []}

        # 1. Banned word scan
        body_lower = email_body.lower()
        for word in banned:
            if word in body_lower:
                violations["banned_words"].append(word)

        # 2. Sentence token clamp check
        sentences = email_body.replace("\n", " ").split(". ")
        max_len_violated = False
        for sent in sentences:
            tokens = sent.split()
            if len(tokens) > max_tokens:
                max_len_violated = True
                violations["long_sentences"].append(
                    f"{len(tokens)} tokens (max {max_tokens})"
                )

        # 3. Compute score
        penalty = 0.0
        if violations["banned_words"]:
            penalty += 0.35 * len(violations["banned_words"])
        if max_len_violated:
            penalty += 0.25

        score = round(max(0.0, 1.0 - penalty), 2)
        passed = score >= 0.7

        # 4. Persist
        await self._persist_result(
            tenant_id=tenant_id,
            entity_id=entity_id or UUID(int=0),
            entity_type=entity_type,
            banned_words_found={w: True for w in violations["banned_words"]},
            max_sentence_length_violated=max_len_violated,
            score=score,
            passed=passed,
            details={
                "violations": violations,
                "prohibited_words_used": prohibited_words,
                "max_tokens_allowed": max_tokens,
            },
        )

        return {
            "score": score,
            "passed": passed,
            "violations": violations,
            "max_sentence_violated": max_len_violated,
        }

    @staticmethod
    async def _persist_result(
        tenant_id: UUID,
        entity_id: UUID,
        entity_type: str,
        banned_words_found: dict[str, Any],
        max_sentence_length_violated: bool,
        score: float,
        passed: bool,
        details: dict[str, Any] | None = None,
    ) -> None:
        try:
            from seo_platform.core.database import get_db_session

            async with get_db_session() as session:
                result = ComplianceResult(
                    tenant_id=tenant_id,
                    entity_id=entity_id,
                    entity_type=entity_type,
                    banned_words_found=banned_words_found,
                    max_sentence_length_violated=max_sentence_length_violated,
                    score=score,
                    passed=passed,
                    details=details or {},
                )
                session.add(result)
        except Exception:
            logger.warning("compliance_persist_failed entity=%s", entity_id)


compliance_scorer = ComplianceScorer()
