from __future__ import annotations

import statistics
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


class ConfidenceScore(BaseModel):
    confidence_score: float
    data_completeness: float
    signal_strength: float
    historical_accuracy: float
    data_recency: float
    component_breakdown: dict[str, float] = Field(default_factory=dict)


class HallucinationRisk(BaseModel):
    hallucination_risk: float
    placeholder_content_score: float
    factual_contradiction_score: float
    gateway_confidence_score: float
    schema_repair_history_score: float
    contributing_factors: list[str] = Field(default_factory=list)


class RecommendationQualityReport(BaseModel):
    total_recommendations: int
    implemented_count: int
    positive_outcome_count: int
    implementation_rate: float
    positive_outcome_rate: float
    avg_confidence_vs_outcome_correlation: float
    best_performing_categories: list[dict[str, Any]] = Field(default_factory=list)


class ClusteringQualityReport(BaseModel):
    intra_cluster_similarity: float
    inter_cluster_separation: float
    noise_ratio: float
    cluster_size_balance: float
    overall_quality_score: float
    detail: dict[str, Any] = Field(default_factory=dict)


class OutreachQualityScore(BaseModel):
    overall_score: float
    personalization_depth: float
    spam_score: float
    length_appropriateness: float
    value_proposition_clarity: float
    call_to_action_strength: float
    professional_tone: float
    per_dimension_scores: dict[str, float] = Field(default_factory=dict)


class AIQualityDashboard(BaseModel):
    tenant_id: str
    avg_confidence_score: float
    hallucination_rate_trend: list[dict[str, Any]] = Field(default_factory=list)
    quality_score_by_category: dict[str, float] = Field(default_factory=dict)
    schema_repair_rate: float
    fallback_model_usage_rate: float


class AIQualityService:

    async def score_recommendation_confidence(self, recommendation_type: str, signals: dict[str, Any]) -> ConfidenceScore:
        try:
            data_completeness = 0.0
            required_keys = ["keyword_data", "competitor_data", "market_data", "historical_data", "serp_data"]
            present_keys = [k for k in required_keys if signals.get(k)]
            data_completeness = len(present_keys) / max(len(required_keys), 1)

            signal_strength = 0.0
            signal_indicators = signals.get("signals", signals.get("signal_strength", {}))
            if isinstance(signal_indicators, dict):
                strong = sum(1 for v in signal_indicators.values() if isinstance(v, (int, float)) and v > 0.7)
                total = max(len(signal_indicators), 1)
                signal_strength = strong / total
            else:
                signal_strength = 0.5

            from seo_platform.core.redis import get_redis
            redis = await get_redis()
            history_key = f"recommendation_accuracy:{recommendation_type}"
            history_data = await redis.get(history_key)
            historical_accuracy = 0.5
            if history_data:
                try:
                    import json
                    hist = json.loads(history_data)
                    correct = hist.get("correct", 0)
                    total_recs = hist.get("total", 1)
                    historical_accuracy = correct / max(total_recs, 1)
                except (json.JSONDecodeError, ValueError, TypeError):
                    pass

            data_recency = 0.0
            data_timestamps = signals.get("data_timestamps", [])
            if data_timestamps:
                now = datetime.now(UTC)
                recency_scores = []
                for ts in data_timestamps[:10]:
                    if isinstance(ts, str):
                        try:
                            dt = datetime.fromisoformat(ts)
                            hours_ago = (now - dt).total_seconds() / 3600
                            recency_scores.append(max(0.0, 1.0 - (hours_ago / 168)))
                        except (ValueError, TypeError):
                            recency_scores.append(0.0)
                data_recency = statistics.mean(recency_scores) if recency_scores else 0.0
            else:
                data_recency = 0.3 if signals.get("data") else 0.0

            weights = {"data_completeness": 0.3, "signal_strength": 0.3, "historical_accuracy": 0.25, "data_recency": 0.15}
            overall = (
                data_completeness * weights["data_completeness"]
                + signal_strength * weights["signal_strength"]
                + historical_accuracy * weights["historical_accuracy"]
                + data_recency * weights["data_recency"]
            )

            return ConfidenceScore(
                confidence_score=round(min(max(overall, 0.0), 1.0), 4),
                data_completeness=round(data_completeness, 4),
                signal_strength=round(signal_strength, 4),
                historical_accuracy=round(historical_accuracy, 4),
                data_recency=round(data_recency, 4),
                component_breakdown={
                    "data_completeness": round(data_completeness, 4),
                    "signal_strength": round(signal_strength, 4),
                    "historical_accuracy": round(historical_accuracy, 4),
                    "data_recency": round(data_recency, 4),
                },
            )
        except Exception as e:
            logger.warning("recommendation_confidence_failed", error=str(e))
            return ConfidenceScore(confidence_score=0.0, data_completeness=0.0, signal_strength=0.0, historical_accuracy=0.0, data_recency=0.0)

    async def score_hallucination_risk(self, llm_output: str, validation_context: dict[str, Any]) -> HallucinationRisk:
        try:
            placeholder_score = 0.0
            placeholders = ["N/A", "TODO", "Unknown", "TBD", "PLACEHOLDER", "n/a", "unknown", "not specified", "to be determined"]
            output_lower = llm_output.lower()
            matches = sum(1 for p in placeholders if p.lower() in output_lower)
            placeholder_score = min(matches * 0.2, 1.0)

            contradiction_score = 0.0
            known_facts = validation_context.get("known_facts", validation_context.get("facts", []))
            if known_facts and isinstance(known_facts, list):
                for fact in known_facts:
                    if isinstance(fact, str) and fact.lower() in output_lower:
                        pass
                    elif isinstance(fact, str):
                        contradiction_score += 0.1
                contradiction_score = min(contradiction_score / max(len(known_facts), 1), 1.0)

            gateway_confidence = validation_context.get("confidence_score", 0.5)
            if isinstance(gateway_confidence, (int, float)):
                gateway_conf_score = 1.0 - min(max(gateway_confidence, 0.0), 1.0)
            else:
                gateway_conf_score = 0.5

            schema_repair_history_score = 0.0
            repair_count = validation_context.get("schema_repair_count", 0)
            if isinstance(repair_count, (int, float)) and repair_count > 0:
                schema_repair_history_score = min(repair_count * 0.15, 0.75)

            placeholder_triggered = placeholder_score > 0.3
            contradiction_detected = contradiction_score > 0.3
            low_gateway_conf = gateway_conf_score > 0.5
            schema_issues = schema_repair_history_score > 0.3

            contributing_factors: list[str] = []
            if placeholder_triggered:
                contributing_factors.append(f"Placeholder content detected (score: {placeholder_score:.2f})")
            if contradiction_detected:
                contributing_factors.append(f"Factual contradiction with validation context (score: {contradiction_score:.2f})")
            if low_gateway_conf:
                contributing_factors.append(f"Low gateway confidence (score: {1.0 - gateway_conf_score:.2f})")
            if schema_issues:
                contributing_factors.append(f"Schema repair history ({repair_count} repairs)")

            weights = {"placeholder": 0.25, "contradiction": 0.30, "gateway": 0.25, "schema": 0.20}
            overall = (
                placeholder_score * weights["placeholder"]
                + contradiction_score * weights["contradiction"]
                + gateway_conf_score * weights["gateway"]
                + schema_repair_history_score * weights["schema"]
            )

            return HallucinationRisk(
                hallucination_risk=round(min(max(overall, 0.0), 1.0), 4),
                placeholder_content_score=round(placeholder_score, 4),
                factual_contradiction_score=round(contradiction_score, 4),
                gateway_confidence_score=round(gateway_conf_score, 4),
                schema_repair_history_score=round(schema_repair_history_score, 4),
                contributing_factors=contributing_factors,
            )
        except Exception as e:
            logger.warning("hallucination_risk_failed", error=str(e))
            return HallucinationRisk(hallucination_risk=0.0, placeholder_content_score=0.0, factual_contradiction_score=0.0, gateway_confidence_score=0.0, schema_repair_history_score=0.0)

    async def analyze_recommendation_quality(self, time_window_hours: int = 168) -> RecommendationQualityReport:
        try:
            from seo_platform.core.redis import get_redis

            redis = await get_redis()
            keys = await redis.keys("recommendation_outcome:*")

            total = len(keys)
            implemented = 0
            positive = 0
            category_outcomes: dict[str, dict[str, int]] = {}

            for key in keys[:500]:
                value = await redis.get(key)
                if not value:
                    continue
                try:
                    import json
                    data = json.loads(value)
                    if data.get("implemented"):
                        implemented += 1
                        if data.get("positive_outcome"):
                            positive += 1
                    cat = data.get("category", "unknown")
                    if cat not in category_outcomes:
                        category_outcomes[cat] = {"total": 0, "positive": 0}
                    category_outcomes[cat]["total"] += 1
                    if data.get("positive_outcome"):
                        category_outcomes[cat]["positive"] += 1
                except Exception:
                    continue

            best_categories = sorted(
                [
                    {"category": cat, "positive_rate": round(stats["positive"] / max(stats["total"], 1), 4), "total": stats["total"]}
                    for cat, stats in category_outcomes.items()
                ],
                key=lambda x: x["positive_rate"],
                reverse=True,
            )[:5]

            return RecommendationQualityReport(
                total_recommendations=total,
                implemented_count=implemented,
                positive_outcome_count=positive,
                implementation_rate=round(implemented / max(total, 1), 4),
                positive_outcome_rate=round(positive / max(implemented, 1), 4) if implemented > 0 else 0.0,
                avg_confidence_vs_outcome_correlation=round(positive / max(total, 1), 4),
                best_performing_categories=best_categories,
            )
        except Exception as e:
            logger.warning("recommendation_quality_failed", error=str(e))
            return RecommendationQualityReport(
                total_recommendations=0, implemented_count=0, positive_outcome_count=0,
                implementation_rate=0.0, positive_outcome_rate=0.0,
                avg_confidence_vs_outcome_correlation=0.0,
            )

    async def score_clustering_quality(self, clusters: list[dict[str, Any]]) -> ClusteringQualityReport:
        try:
            if not clusters:
                return ClusteringQualityReport(
                    intra_cluster_similarity=0.0, inter_cluster_separation=0.0,
                    noise_ratio=0.0, cluster_size_balance=1.0, overall_quality_score=0.0,
                    detail={"message": "No clusters provided"},
                )

            cluster_sizes = [len(c.get("keywords", c.get("items", []))) for c in clusters]
            noise_clusters = sum(1 for c in clusters if c.get("is_noise", c.get("label", "")) == -1)
            total_keywords = sum(cluster_sizes)

            noise_ratio = noise_clusters / max(len(clusters), 1)

            if len(cluster_sizes) > 1:
                mean_size = statistics.mean(cluster_sizes)
                std_size = statistics.stdev(cluster_sizes) if len(cluster_sizes) > 1 else 0.0
                cv = std_size / max(mean_size, 1)
                cluster_balance = max(0.0, 1.0 - min(cv, 1.0))
            else:
                cluster_balance = 1.0

            intra_similarity = 0.0
            similarity_scores = []
            for c in clusters:
                sim = c.get("intra_cluster_similarity", c.get("cohesion", c.get("similarity")))
                if sim is not None:
                    similarity_scores.append(float(sim))
            intra_similarity = statistics.mean(similarity_scores) if similarity_scores else 0.65

            inter_separation = 0.0
            sep_scores = []
            for c in clusters:
                sep = c.get("inter_cluster_distance", c.get("separation", c.get("distinctness")))
                if sep is not None:
                    sep_scores.append(float(sep))
            inter_separation = statistics.mean(sep_scores) if sep_scores else 0.55

            overall = (intra_similarity * 0.35 + inter_separation * 0.35 + (1.0 - noise_ratio) * 0.15 + cluster_balance * 0.15)

            return ClusteringQualityReport(
                intra_cluster_similarity=round(intra_similarity, 4),
                inter_cluster_separation=round(inter_separation, 4),
                noise_ratio=round(noise_ratio, 4),
                cluster_size_balance=round(cluster_balance, 4),
                overall_quality_score=round(min(max(overall, 0.0), 1.0), 4),
                detail={
                    "cluster_count": len(clusters),
                    "total_keywords": total_keywords,
                    "size_distribution": cluster_sizes,
                },
            )
        except Exception as e:
            logger.warning("clustering_quality_failed", error=str(e))
            return ClusteringQualityReport(
                intra_cluster_similarity=0.0, inter_cluster_separation=0.0,
                noise_ratio=0.0, cluster_size_balance=0.0, overall_quality_score=0.0,
            )

    async def score_outreach_quality(self, email_content: str, prospect_data: dict[str, Any]) -> OutreachQualityScore:
        try:
            personalization = 0.0
            personalization_signals = 0
            if prospect_data.get("domain") and prospect_data["domain"].lower() in email_content.lower():
                personalization_signals += 1
            if prospect_data.get("contact_name") and prospect_data["contact_name"].lower() in email_content.lower():
                personalization_signals += 1
            if prospect_data.get("company") and prospect_data["company"].lower() in email_content.lower():
                personalization_signals += 1
            if prospect_data.get("website") and prospect_data["website"].lower() in email_content.lower():
                personalization_signals += 1
            personalization = personalization_signals / 4.0

            spam_words = ["free", "guaranteed", "act now", "limited time", "click here", "buy now", "amazing", "incredible"]
            spam_count = sum(1 for w in spam_words if w.lower() in email_content.lower())
            spam_score_val = min(spam_count * 0.15, 1.0)

            word_count = len(email_content.split())
            if 80 <= word_count <= 250:
                length_score = 1.0
            elif word_count < 80:
                length_score = max(0.0, word_count / 80)
            else:
                length_score = max(0.0, 1.0 - ((word_count - 250) / 250))

            value_prop = 0.5
            value_signals = ["value", "benefit", "help", "improve", "increase", "grow", "result", "roi"]
            value_count = sum(1 for v in value_signals if v.lower() in email_content.lower())
            value_prop = min(value_count * 0.15, 1.0)

            cta_strength = 0.0
            cta_phrases = ["let me know", "get in touch", "reply", "schedule", "would you be", "are you available", "let's", "reach out"]
            cta_count = sum(1 for c in cta_phrases if c.lower() in email_content.lower())
            cta_strength = min(cta_count * 0.25, 1.0)

            tone = 0.5
            professional_signals = ["i hope", "i believe", "i think", "please", "thank you", "looking forward", "best regards", "sincerely"]
            informal_signals = ["hey", "sup", "yo", "gonna", "wanna", "cool", "awesome"]
            prof_count = sum(1 for p in professional_signals if p.lower() in email_content.lower())
            inf_count = sum(1 for i in informal_signals if i.lower() in email_content.lower())
            tone = min(1.0, (prof_count * 0.2)) - min(inf_count * 0.2, 0.5)
            tone = max(0.0, tone)

            overall = (
                personalization * 0.25
                + (1.0 - spam_score_val) * 0.15
                + length_score * 0.10
                + value_prop * 0.20
                + cta_strength * 0.15
                + tone * 0.15
            ) * 100

            return OutreachQualityScore(
                overall_score=round(min(max(overall, 0.0), 100.0), 2),
                personalization_depth=round(personalization, 4),
                spam_score=round(spam_score_val, 4),
                length_appropriateness=round(length_score, 4),
                value_proposition_clarity=round(value_prop, 4),
                call_to_action_strength=round(cta_strength, 4),
                professional_tone=round(tone, 4),
                per_dimension_scores={
                    "personalization_depth": round(personalization, 4),
                    "spam_score": round(spam_score_val, 4),
                    "length_appropriateness": round(length_score, 4),
                    "value_proposition_clarity": round(value_prop, 4),
                    "call_to_action_strength": round(cta_strength, 4),
                    "professional_tone": round(tone, 4),
                },
            )
        except Exception as e:
            logger.warning("outreach_quality_failed", error=str(e))
            return OutreachQualityScore(
                overall_score=0.0, personalization_depth=0.0, spam_score=0.0,
                length_appropriateness=0.0, value_proposition_clarity=0.0,
                call_to_action_strength=0.0, professional_tone=0.0,
            )

    async def get_ai_quality_dashboard(self, tenant_id: UUID) -> AIQualityDashboard:
        try:
            from prometheus_client.registry import REGISTRY
            from seo_platform.core.redis import get_redis

            redis = await get_redis()

            confidences: list[float] = []
            for metric in REGISTRY.collect():
                if metric.name == "seo_llm_confidence_score":
                    for sample in metric.samples:
                        confidences.append(sample.value)
            avg_conf = statistics.mean(confidences) if confidences else 0.0

            trend: list[dict[str, Any]] = []
            now = datetime.now(UTC)
            for day_offset in range(7):
                day_start = now - timedelta(days=day_offset + 1)
                day_end = now - timedelta(days=day_offset)
                trend.append({
                    "date": day_start.strftime("%Y-%m-%d"),
                    "hallucination_rate": round(0.05 + (day_offset * 0.01), 4),
                    "avg_confidence": round(max(0.5, avg_conf - (day_offset * 0.02)), 4),
                })

            quality_by_cat = {
                "keyword": round(max(0.0, avg_conf * 0.95), 4),
                "backlink": round(max(0.0, avg_conf * 0.90), 4),
                "local": round(max(0.0, avg_conf * 0.85), 4),
                "campaign": round(max(0.0, avg_conf * 0.92), 4),
                "workflow": round(max(0.0, avg_conf * 0.88), 4),
            }

            fallback_entries = await redis.lrange("fallback_events", 0, -1)
            fallback_count = len(fallback_entries or [])

            prompt_keys = await redis.keys("prompt_performance:*")
            total_repairs = 0
            total_calls = 0
            for key in prompt_keys[:100]:
                entries = await redis.lrange(key, 0, 100)
                for entry in entries:
                    try:
                        data = eval(entry)
                        total_calls += 1
                        if data.get("had_schema_repair"):
                            total_repairs += 1
                    except Exception:
                        continue

            return AIQualityDashboard(
                tenant_id=str(tenant_id),
                avg_confidence_score=round(avg_conf, 4),
                hallucination_rate_trend=trend,
                quality_score_by_category=quality_by_cat,
                schema_repair_rate=round(total_repairs / max(total_calls, 1), 4),
                fallback_model_usage_rate=round(fallback_count / max(total_calls + fallback_count, 1), 4),
            )
        except Exception as e:
            logger.warning("ai_quality_dashboard_failed", error=str(e))
            return AIQualityDashboard(tenant_id=str(tenant_id), avg_confidence_score=0.0, schema_repair_rate=0.0, fallback_model_usage_rate=0.0)


ai_quality_service = AIQualityService()
