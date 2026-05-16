"""
SEO Platform — Advanced SERP Intelligence Engine
==================================================
SERP feature detection, PAA analysis, snapshot management,
volatility tracking, SERP comparison, competitor overlap, and dominance scoring.

Architecture axiom: AI proposes. Deterministic systems execute.
"""

from __future__ import annotations

import time
from typing import Any
from uuid import UUID  # noqa: TC003

import orjson
from pydantic import BaseModel, Field

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Output Schemas
# ---------------------------------------------------------------------------
class SERPFeatureDetection(BaseModel):
    feature_type: str
    present: bool = False
    confidence: float = 0.0
    details: dict[str, Any] = Field(default_factory=dict)


class SERPFeatureAnalysis(BaseModel):
    keyword: str
    geo: str
    featured_snippet: SERPFeatureDetection = Field(
        default_factory=lambda: SERPFeatureDetection(feature_type="featured_snippet")
    )
    people_also_ask: SERPFeatureDetection = Field(
        default_factory=lambda: SERPFeatureDetection(feature_type="people_also_ask")
    )
    knowledge_panel: SERPFeatureDetection = Field(
        default_factory=lambda: SERPFeatureDetection(feature_type="knowledge_panel")
    )
    video_carousel: SERPFeatureDetection = Field(
        default_factory=lambda: SERPFeatureDetection(feature_type="video_carousel")
    )
    local_pack: SERPFeatureDetection = Field(
        default_factory=lambda: SERPFeatureDetection(feature_type="local_pack")
    )
    image_pack: SERPFeatureDetection = Field(
        default_factory=lambda: SERPFeatureDetection(feature_type="image_pack")
    )
    shopping_results: SERPFeatureDetection = Field(
        default_factory=lambda: SERPFeatureDetection(feature_type="shopping_results")
    )
    tweet_box: SERPFeatureDetection = Field(
        default_factory=lambda: SERPFeatureDetection(feature_type="tweet_box")
    )
    news_box: SERPFeatureDetection = Field(
        default_factory=lambda: SERPFeatureDetection(feature_type="news_box")
    )
    total_features: int = 0


class PAAQuestion(BaseModel):
    question: str
    answer_snippet: str = ""
    intent: str = ""
    related_questions: list[str] = Field(default_factory=list)


class PAAAnalysis(BaseModel):
    keyword: str
    geo: str
    questions: list[PAAQuestion] = Field(default_factory=list)
    total_paa_count: int = 0
    intent_distribution: dict[str, int] = Field(default_factory=dict)


class SERPSnapshotResult(BaseModel):
    position: int
    url: str
    title: str = ""
    domain: str = ""


class SERPSnapshot(BaseModel):
    keyword: str
    geo: str
    timestamp: float = 0.0
    top_10: list[SERPSnapshotResult] = Field(default_factory=list)
    features_present: list[str] = Field(default_factory=list)


class SERPVolatilityReport(BaseModel):
    keyword: str
    geo: str
    volatility_score: float = 0.0
    url_churn_rate: float = 0.0
    avg_position_change: float = 0.0
    feature_appearance_rate: float = 0.0
    feature_disappearance_rate: float = 0.0
    details: dict[str, Any] = Field(default_factory=dict)


class SERPOverlapAnalysis(BaseModel):
    keyword_a: str
    keyword_b: str
    overlap_percentage: float = 0.0
    shared_urls: list[str] = Field(default_factory=list)
    shared_domains: list[str] = Field(default_factory=list)
    shared_features: list[str] = Field(default_factory=list)


class CompetitorOverlapEntry(BaseModel):
    competitor_domain: str
    overlap_percentage: float = 0.0
    shared_keyword_count: int = 0
    top_overlapping_keywords: list[str] = Field(default_factory=list)


class CompetitorSERPOverlapReport(BaseModel):
    target_domain: str
    competitors: list[CompetitorOverlapEntry] = Field(default_factory=list)
    geo: str = ""


class KeywordDominanceEntry(BaseModel):
    keyword: str
    rank: int | None = None
    in_top_3: bool = False
    in_top_10: bool = False
    has_featured_snippet: bool = False


class SERPDominanceReport(BaseModel):
    domain: str
    keyword_count: int = 0
    average_position: float = 0.0
    top_3_count: int = 0
    top_10_count: int = 0
    featured_snippet_count: int = 0
    dominance_score: float = 0.0
    keyword_details: list[KeywordDominanceEntry] = Field(default_factory=list)


class SERPIntentAndEEATAnalysis(BaseModel):
    keyword: str
    dominant_intent: str = "editorial"  # ugc_forum, video, tool, ecommerce, editorial
    intent_confidence: float = 0.0
    entity_associations: list[str] = Field(default_factory=list)
    competitor_eeat_signals: list[dict[str, Any]] = Field(default_factory=list)
    recommended_content_pivot: str = "Maintain standard editorial content"


# ---------------------------------------------------------------------------
# LLM Output Schemas (for structured extraction)
# ---------------------------------------------------------------------------
class _PAAIntentSchema(BaseModel):
    questions: list[dict[str, Any]] = Field(default_factory=list)


class _SERPIntentEEATSchema(BaseModel):
    dominant_intent: str
    intent_confidence: float
    entity_associations: list[str]
    competitor_eeat_signals: list[dict[str, Any]]
    recommended_content_pivot: str


# ---------------------------------------------------------------------------
# Lua scripts for Redis sorted set operations
# ---------------------------------------------------------------------------
_ZADD_SCRIPT = """
redis.call('ZADD', KEYS[1], tonumber(ARGV[1]), ARGV[2])
return 1
"""

_ZRANGE_SCRIPT = """
return redis.call('ZREVRANGEBYSCORE', KEYS[1], ARGV[1], ARGV[2], 'WITHSCORES')
"""

_ZCARD_SCRIPT = """
return redis.call('ZCARD', KEYS[1])
"""

_ZOOM_SCRIPT = """
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', tonumber(ARGV[1]))
return 1
"""


# ---------------------------------------------------------------------------
# Advanced SERP Intelligence Engine
# ---------------------------------------------------------------------------
class SERPIntelligenceEngine:
    """
    Advanced SERP intelligence with feature detection, PAA intelligence,
    snapshot management, volatility tracking, and competitive analysis.

    Every method follows the same reliability pattern:
    1. DataForSEO primary data
    2. LLM augmentation where beneficial (advisory only)
    3. Deterministic fallback if primary fails
    """

    # ------------------------------------------------------------------
    # SERP Intent & EEAT Cognition Layer (Phase 6)
    # ------------------------------------------------------------------
    async def analyze_serp_intent_and_eeat(
        self, keyword: str, tenant_id: UUID, geo: str = "US",
    ) -> SERPIntentAndEEATAnalysis:
        """
        Advanced SERP Intent & EEAT Cognition Engine (Phase 6).
        Combines DataForSEO live SERP snapshots with an advanced LLM reasoning loop to:
        1. Classify SERP intent shifts (ugc_forum, video, tool, ecommerce, editorial)
        2. Identify entity associations and semantic clusters
        3. Evaluate competitor EEAT signals (author credentials, institutional trust)
        4. Recommend dynamic content pivots (e.g. pivoting to Reddit/Quora if UGC dominates)
        """
        logger.info("analyze_serp_intent_and_eeat", keyword=keyword, geo=geo, tenant_id=str(tenant_id))

        result = SERPIntentAndEEATAnalysis(keyword=keyword)

        try:
            from seo_platform.clients.dataforseo import dataforseo_client

            snapshot = await dataforseo_client.get_serp_snapshot(keyword)

            top_results: list[dict[str, Any]] = []
            for task in snapshot.get("tasks", []):
                for item in task.get("result", []):
                    for res_item in item.get("items", []):
                        rank = res_item.get("rank_absolute") or res_item.get("rank", 0)
                        if rank and 1 <= rank <= 10:
                            top_results.append({
                                "rank": rank,
                                "url": res_item.get("url", "") or res_item.get("link", "") or "",
                                "title": res_item.get("title", "") or "",
                                "description": res_item.get("description", "") or res_item.get("snippet", "") or "",
                                "breadcrumb": res_item.get("breadcrumb", "") or "",
                            })

            if top_results:
                try:
                    from seo_platform.llm.gateway import RenderedPrompt, TaskType, llm_gateway

                    results_str = "\n".join(
                        f"{r['rank']}. {r['title']} ({r['url']})\n   Snippet: {r['description']}"
                        for r in top_results
                    )

                    prompt = RenderedPrompt(
                        template_id="serp_intent_eeat_analysis",
                        system_prompt=(
                            "You are an elite SEO SERP intent and EEAT analyst. Analyze the top 10 ranking results "
                            "to determine the dominant search intent and competitor EEAT signals. Return ONLY a JSON object "
                            "matching the schema with: dominant_intent (ugc_forum, video, tool, ecommerce, editorial), "
                            "intent_confidence (0.0 to 1.0), entity_associations (array of strings), "
                            "competitor_eeat_signals (array of objects with domain, author_authority, institutional_trust), "
                            "and recommended_content_pivot (specific strategic instruction)."
                        ),
                        user_prompt=(
                            f"Keyword: '{keyword}'\nGeo: {geo}\n\nTop 10 SERP Results:\n{results_str}\n\n"
                            "Analyze the dominant intent, associated entities, competitor EEAT strength, and recommend a strategic content pivot."
                        ),
                    )

                    llm_result = await llm_gateway.complete(
                        task_type=TaskType.SEO_ANALYSIS,
                        prompt=prompt,
                        output_schema=_SERPIntentEEATSchema,
                        tenant_id=tenant_id,
                    )

                    content = llm_result.content
                    result.dominant_intent = content.dominant_intent
                    result.intent_confidence = round(content.intent_confidence, 4)
                    result.entity_associations = content.entity_associations
                    result.competitor_eeat_signals = content.competitor_eeat_signals
                    result.recommended_content_pivot = content.recommended_content_pivot

                except Exception as e:
                    logger.warning("serp_intent_llm_reasoning_failed", error=str(e))
                    # Deterministic fallback based on URL footprint matching
                    ugc_count = sum(1 for r in top_results if any(d in r["url"].lower() for d in ["reddit.com", "quora.com", "stackexchange", "stackoverflow"]))
                    video_count = sum(1 for r in top_results if any(d in r["url"].lower() for d in ["youtube.com", "vimeo.com"]))
                    tool_count = sum(1 for r in top_results if any(w in r["title"].lower() for w in ["calculator", "tool", "generator", "software"]))
                    ecom_count = sum(1 for r in top_results if any(d in r["url"].lower() for d in ["amazon.com", "ebay.com", "walmart.com", "etsy.com"]))

                    counts = {
                        "ugc_forum": ugc_count,
                        "video": video_count,
                        "tool": tool_count,
                        "ecommerce": ecom_count,
                        "editorial": len(top_results) - (ugc_count + video_count + tool_count + ecom_count),
                    }
                    dominant = max(counts.items(), key=lambda x: x[1])[0]

                    result.dominant_intent = dominant
                    result.intent_confidence = round(counts[dominant] / float(len(top_results)), 2) if top_results else 0.5
                    if dominant == "ugc_forum":
                        result.recommended_content_pivot = "Pivot from standard blog posts to Reddit community engagement and Quora expert answers."
                    elif dominant == "video":
                        result.recommended_content_pivot = "Pivot to YouTube video creation and embedded video carousels."
                    elif dominant == "tool":
                        result.recommended_content_pivot = "Develop an interactive calculator or free engineering tool."

        except Exception as e:
            logger.warning("serp_intent_and_eeat_analysis_failed", keyword=keyword, error=str(e))

        return result

    # ------------------------------------------------------------------
    # SERP Feature Detection
    # ------------------------------------------------------------------
    async def detect_serp_features(
        self, keyword: str, geo: str = "US",
    ) -> SERPFeatureAnalysis:
        """Enhanced SERP feature detection with confidence scoring per feature type."""
        logger.info("detecting_serp_features", keyword=keyword, geo=geo)

        result = SERPFeatureAnalysis(keyword=keyword, geo=geo)

        try:
            from seo_platform.clients.dataforseo import dataforseo_client

            snapshot = await dataforseo_client.get_serp_snapshot(keyword)

            features: dict[str, dict[str, Any]] = {
                "featured_snippet": {"present": False, "confidence": 0.0, "details": {}},
                "people_also_ask": {"present": False, "confidence": 0.0, "details": {"questions": []}},
                "knowledge_panel": {"present": False, "confidence": 0.0, "details": {"type": ""}},
                "video_carousel": {"present": False, "confidence": 0.0, "details": {}},
                "local_pack": {"present": False, "confidence": 0.0, "details": {"count": 0}},
                "image_pack": {"present": False, "confidence": 0.0, "details": {}},
                "shopping_results": {"present": False, "confidence": 0.0, "details": {}},
                "tweet_box": {"present": False, "confidence": 0.0, "details": {}},
                "news_box": {"present": False, "confidence": 0.0, "details": {}},
            }

            for task in snapshot.get("tasks", []):
                for item in task.get("result", []):
                    for res_item in item.get("items", []):
                        self._classify_serp_item_v2(res_item, features)

            for ft in ["featured_snippet", "people_also_ask", "knowledge_panel",
                       "video_carousel", "local_pack", "image_pack", "shopping_results",
                       "tweet_box", "news_box"]:
                fdata = features[ft]
                detection = SERPFeatureDetection(
                    feature_type=ft,
                    present=fdata["present"],
                    confidence=fdata["confidence"],
                    details=fdata["details"],
                )
                setattr(result, ft, detection)

            result.total_features = sum(
                1 for ft in ["featured_snippet", "people_also_ask", "knowledge_panel",
                             "video_carousel", "local_pack", "image_pack", "shopping_results",
                             "tweet_box", "news_box"]
                if getattr(result, ft).present
            )

        except Exception as e:
            logger.warning("serp_feature_detection_failed", keyword=keyword, error=str(e))

        return result

    def _classify_serp_item_v2(
        self, item: dict[str, Any], features: dict[str, dict[str, Any]],
    ) -> None:
        """Enhanced SERP item classifier with confidence scoring and extended feature types."""
        item_type = (item.get("type", "") or "").lower()
        rank_group = str(item.get("rank_group", ""))

        if item_type == "featured_snippet" or item.get("is_featured_snippet"):
            features["featured_snippet"]["present"] = True
            features["featured_snippet"]["confidence"] = 0.9
            features["featured_snippet"]["details"] = {
                "text": item.get("description", "") or item.get("snippet", ""),
                "snippet_type": self._detect_snippet_type(item),
            }

        if item_type == "people_also_ask" or "people_also_ask" in rank_group:
            features["people_also_ask"]["present"] = True
            features["people_also_ask"]["confidence"] = 0.85
            questions = item.get("questions", []) or item.get("items", [])
            for q in questions:
                q_text = q.get("title", "") or q.get("question", "")
                if q_text:
                    features["people_also_ask"]["details"]["questions"].append(q_text)

        if item_type in ("knowledge_panel", "knowledge_graph"):
            features["knowledge_panel"]["present"] = True
            features["knowledge_panel"]["confidence"] = 0.95
            features["knowledge_panel"]["details"]["type"] = item.get("knowledge_panel_type", "entity")

        if item_type == "video" or "video" in item.get("breadcrumb", ""):
            features["video_carousel"]["present"] = True
            features["video_carousel"]["confidence"] = 0.8

        if item_type == "local_pack" or item.get("is_local_pack"):
            features["local_pack"]["present"] = True
            features["local_pack"]["confidence"] = 0.9
            local_items = item.get("items", []) or [item]
            features["local_pack"]["details"]["count"] = len(local_items)

        if item_type in ("images", "image_pack"):
            features["image_pack"]["present"] = True
            features["image_pack"]["confidence"] = 0.85

        if item_type == "shopping" or "shopping" in rank_group:
            features["shopping_results"]["present"] = True
            features["shopping_results"]["confidence"] = 0.8

        if item_type == "tweet" or "twitter" in item.get("breadcrumb", "").lower():
            features["tweet_box"]["present"] = True
            features["tweet_box"]["confidence"] = 0.8

        if item_type == "news" or "news" in item.get("breadcrumb", "").lower():
            features["news_box"]["present"] = True
            features["news_box"]["confidence"] = 0.8

        for sub in item.get("items", []):
            if isinstance(sub, dict):
                self._classify_serp_item_v2(sub, features)

    @staticmethod
    def _detect_snippet_type(item: dict[str, Any]) -> str:
        """Detect featured snippet type: paragraph, list, table, or video."""
        desc = item.get("description", "") or item.get("snippet", "") or ""
        if "<table" in desc.lower():
            return "table"
        if any(c in desc for c in ["\n1.", "\n2.", "\n\u2022", "<ol>", "<ul>"]):
            return "list"
        content_type = (item.get("type", "") or "").lower()
        if content_type == "video":
            return "video"
        return "paragraph"

    # ------------------------------------------------------------------
    # People Also Ask Intelligence
    # ------------------------------------------------------------------
    async def analyze_paa(
        self, keyword: str, geo: str = "US",
    ) -> PAAAnalysis:
        """Extract and analyze People Also Ask data with intent classification."""
        logger.info("analyzing_paa", keyword=keyword, geo=geo)

        result = PAAAnalysis(keyword=keyword, geo=geo)

        try:
            from seo_platform.clients.dataforseo import dataforseo_client

            snapshot = await dataforseo_client.get_serp_snapshot(keyword)

            raw_questions: list[str] = []
            for task in snapshot.get("tasks", []):
                for item in task.get("result", []):
                    for res_item in item.get("items", []):
                        self._extract_paa_questions(res_item, raw_questions)

            result.total_paa_count = len(raw_questions)

            if raw_questions:
                try:
                    from seo_platform.llm.gateway import RenderedPrompt, TaskType, llm_gateway

                    questions_str = "\n".join(f"- {q}" for q in raw_questions)

                    prompt = RenderedPrompt(
                        template_id="paa_intent_analysis",
                        system_prompt="You are a search intent analyst. Classify each PAA question by intent (what/why/how/where/when) and map relationships. Return ONLY a JSON object with: questions (array of {question: string, intent: string, related_questions: array of strings}).",
                        user_prompt=f"PAA Questions for '{keyword}':\n{questions_str}\n\nClassify each question's intent and identify which questions relate to which.",
                    )

                    llm_result = await llm_gateway.complete(
                        task_type=TaskType.SEO_ANALYSIS,
                        prompt=prompt,
                        output_schema=_PAAIntentSchema,
                        tenant_id=UUID(int=0),
                    )

                    intent_dist: dict[str, int] = {}
                    for q_data in llm_result.content.questions:
                        q_text = q_data.get("question", "")
                        intent = q_data.get("intent", "what")
                        related = q_data.get("related_questions", [])

                        intent_dist[intent] = intent_dist.get(intent, 0) + 1

                        result.questions.append(PAAQuestion(
                            question=q_text,
                            answer_snippet="",
                            intent=intent,
                            related_questions=related,
                        ))

                    result.intent_distribution = intent_dist

                except Exception as e:
                    logger.warning("paa_llm_intent_failed", error=str(e))
                    intent_dist: dict[str, int] = {}
                    for q in raw_questions:
                        intent = self._heuristic_paa_intent(q)
                        intent_dist[intent] = intent_dist.get(intent, 0) + 1
                        result.questions.append(PAAQuestion(question=q, intent=intent))
                    result.intent_distribution = intent_dist

        except Exception as e:
            logger.warning("paa_analysis_failed", keyword=keyword, error=str(e))

        return result

    @staticmethod
    def _extract_paa_questions(item: dict[str, Any], questions: list[str]) -> None:
        """Recursively extract PAA questions from SERP items."""
        item_type = (item.get("type", "") or "").lower()
        rank_group = str(item.get("rank_group", ""))

        if item_type == "people_also_ask" or "people_also_ask" in rank_group:
            for q in item.get("questions", []) or item.get("items", []):
                q_text = q.get("title", "") or q.get("question", "") or ""
                if q_text and q_text not in questions:
                    questions.append(q_text)

        for sub in item.get("items", []):
            if isinstance(sub, dict):
                SERPIntelligenceEngine._extract_paa_questions(sub, questions)

    @staticmethod
    def _heuristic_paa_intent(question: str) -> str:
        """Classify PAA question intent heuristically by starting word."""
        q = question.lower().strip()
        if q.startswith(("what", "which", "who")):
            return "what"
        if q.startswith("why"):
            return "why"
        if q.startswith("how"):
            return "how"
        if q.startswith("where"):
            return "where"
        if q.startswith("when"):
            return "when"
        return "what"

    # ------------------------------------------------------------------
    # SERP Historical Snapshots
    # ------------------------------------------------------------------
    async def capture_serp_snapshot(
        self, keyword: str, geo: str, tenant_id: UUID,
    ) -> dict[str, Any]:
        """Capture current SERP state and store in Redis sorted set."""
        logger.info("capturing_serp_snapshot", keyword=keyword, geo=geo, tenant_id=str(tenant_id))

        try:
            from seo_platform.clients.dataforseo import dataforseo_client

            snapshot = await dataforseo_client.get_serp_snapshot(keyword)

            top_10: list[SERPSnapshotResult] = []
            features_present: list[str] = []
            now = time.time()

            for task in snapshot.get("tasks", []):
                for item in task.get("result", []):
                    for res_item in item.get("items", []):
                        rank = res_item.get("rank_absolute") or res_item.get("rank", 0)
                        url = res_item.get("url", "") or res_item.get("link", "") or ""
                        title = res_item.get("title", "") or ""

                        if rank and 1 <= rank <= 10:
                            top_10.append(SERPSnapshotResult(
                                position=rank,
                                url=url,
                                title=title,
                                domain=self._extract_domain(url),
                            ))

                        self._collect_features(res_item, features_present)

            top_10.sort(key=lambda r: r.position)

            snap_obj = SERPSnapshot(
                keyword=keyword,
                geo=geo,
                timestamp=now,
                top_10=top_10,
                features_present=list(set(features_present)),
            )

            from seo_platform.core.redis import TenantRedis

            redis = TenantRedis(tenant_id)
            snap_key = f"serp_snapshot:{keyword}:{geo}"
            snap_json = orjson.dumps(snap_obj.model_dump()).decode()

            await redis.eval_lua(
                _ZADD_SCRIPT,
                keys=[snap_key],
                args=[str(now), snap_json],
            )

            await redis.eval_lua(
                _ZOOM_SCRIPT,
                keys=[snap_key],
                args=[str(now - 86400 * 365)],
            )

            return {"status": "captured", "timestamp": now, "top_10_count": len(top_10)}

        except Exception as e:
            logger.warning("capture_serp_snapshot_failed", keyword=keyword, error=str(e))
            return {"status": "failed", "error": str(e)}

    async def get_serp_snapshot_history(
        self, keyword: str, geo: str, tenant_id: UUID, days: int = 30,
    ) -> list[SERPSnapshot]:
        """Retrieve historical SERP snapshots from Redis sorted set."""
        logger.info("getting_serp_snapshot_history", keyword=keyword, days=days)

        try:
            from seo_platform.core.redis import TenantRedis

            redis = TenantRedis(tenant_id)
            snap_key = f"serp_snapshot:{keyword}:{geo}"
            now = time.time()
            min_ts = now - (days * 86400)

            raw = await redis.eval_lua(
                _ZRANGE_SCRIPT,
                keys=[snap_key],
                args=[str(now), str(min_ts)],
            )

            if not raw:
                return []

            snapshots: list[SERPSnapshot] = []
            for i in range(0, len(raw), 2):
                member = raw[i]
                try:
                    snap_data = orjson.loads(member)
                    snapshots.append(SERPSnapshot(**snap_data))
                except Exception:
                    pass

            return sorted(snapshots, key=lambda s: s.timestamp)

        except Exception as e:
            logger.warning("get_serp_snapshot_history_failed", keyword=keyword, error=str(e))
            return []

    # ------------------------------------------------------------------
    # SERP Volatility Tracking
    # ------------------------------------------------------------------
    async def calculate_serp_volatility(
        self, keyword: str, geo: str = "US", tenant_id: UUID | None = None, days: int = 7,
    ) -> SERPVolatilityReport:
        """Measure SERP volatility by comparing historical snapshots."""
        logger.info("calculating_serp_volatility", keyword=keyword, days=days)

        report = SERPVolatilityReport(keyword=keyword, geo=geo)

        if not tenant_id:
            return report

        try:
            history = await self.get_serp_snapshot_history(
                keyword=keyword, geo=geo, tenant_id=tenant_id, days=days,
            )

            if len(history) < 2:
                return report

            latest = history[-1]
            previous = history[-2]

            latest_urls = {r.url for r in latest.top_10}
            prev_urls = {r.url for r in previous.top_10}

            new_urls = latest_urls - prev_urls
            dropped_urls = prev_urls - latest_urls
            total_urls = latest_urls | prev_urls
            churn = (len(new_urls) + len(dropped_urls)) / max(1, len(total_urls))

            pos_changes: list[float] = []
            prev_pos = {r.url: r.position for r in previous.top_10}
            for r in latest.top_10:
                if r.url in prev_pos:
                    pos_changes.append(float(abs(r.position - prev_pos[r.url])))

            avg_change = sum(pos_changes) / max(1, len(pos_changes))

            latest_features = set(latest.features_present)
            prev_features = set(previous.features_present)
            new_features = latest_features - prev_features
            dropped_features = prev_features - latest_features
            all_features = latest_features | prev_features
            feature_churn = (len(new_features) + len(dropped_features)) / max(1, len(all_features))

            volatility = (churn * 0.35 + (avg_change / 10) * 0.35 + feature_churn * 0.3) * 100

            report.volatility_score = round(min(100.0, volatility), 1)
            report.url_churn_rate = round(churn, 4)
            report.avg_position_change = round(avg_change, 2)
            report.feature_appearance_rate = round(len(new_features) / max(1, len(all_features)), 4)
            report.feature_disappearance_rate = round(len(dropped_features) / max(1, len(all_features)), 4)
            report.details = {
                "snapshots_compared": len(history),
                "new_urls": list(new_urls)[:10],
                "dropped_urls": list(dropped_urls)[:10],
                "new_features": list(new_features),
                "dropped_features": list(dropped_features),
            }

        except Exception as e:
            logger.warning("serp_volatility_calculation_failed", keyword=keyword, error=str(e))

        return report

    # ------------------------------------------------------------------
    # SERP Comparison Engine
    # ------------------------------------------------------------------
    async def compare_serp_feature_presence(
        self, keyword_a: str, keyword_b: str, geo: str = "US",
    ) -> SERPOverlapAnalysis:
        """Compare SERP feature presence and URL overlap between two keywords."""
        logger.info("comparing_serp_features", keyword_a=keyword_a, keyword_b=keyword_b)

        result = SERPOverlapAnalysis(keyword_a=keyword_a, keyword_b=keyword_b)

        try:
            from seo_platform.clients.dataforseo import dataforseo_client

            snap_a = await dataforseo_client.get_serp_snapshot(keyword_a)
            snap_b = await dataforseo_client.get_serp_snapshot(keyword_b)

            urls_a: set[str] = set()
            urls_b: set[str] = set()
            features_a: set[str] = set()
            features_b: set[str] = set()

            for snap, urls, features in [
                (snap_a, urls_a, features_a),
                (snap_b, urls_b, features_b),
            ]:
                for task in snap.get("tasks", []):
                    for item in task.get("result", []):
                        for res_item in item.get("items", []):
                            url = res_item.get("url", "") or res_item.get("link", "") or ""
                            rank = res_item.get("rank_absolute") or res_item.get("rank", 0)
                            if url and rank and 1 <= rank <= 10:
                                urls.add(url)
                            self._collect_features(res_item, features)

            shared_urls = urls_a & urls_b
            all_urls = urls_a | urls_b

            shared_domains: set[str] = set()
            for url in shared_urls:
                shared_domains.add(self._extract_domain(url))

            shared_features = features_a & features_b
            all_features = features_a | features_b

            result.shared_urls = list(shared_urls)
            result.shared_domains = list(shared_domains)
            result.shared_features = list(shared_features)
            result.overlap_percentage = round(
                len(shared_urls) / max(1, len(all_urls)) * 100, 1
            )

        except Exception as e:
            logger.warning("serp_comparison_failed", keyword_a=keyword_a, keyword_b=keyword_b, error=str(e))

        return result

    # ------------------------------------------------------------------
    # Competitor SERP Overlap
    # ------------------------------------------------------------------
    async def analyze_competitor_serp_overlap(
        self, domain: str, competitors: list[str],
        keywords: list[str] | None = None, geo: str = "US",
    ) -> CompetitorSERPOverlapReport:
        """Analyze SERP sharing between a domain and its competitors."""
        logger.info("analyzing_competitor_serp_overlap", domain=domain, competitor_count=len(competitors))

        report = CompetitorSERPOverlapReport(target_domain=domain, geo=geo)

        kw_list = keywords or []

        try:
            from seo_platform.clients.dataforseo import dataforseo_client

            for competitor in competitors:
                shared_keywords: list[str] = []

                for kw in kw_list:
                    snapshot = await dataforseo_client.get_serp_snapshot(kw)
                    target_found = False
                    comp_found = False

                    for task in snapshot.get("tasks", []):
                        for item in task.get("result", []):
                            for res_item in item.get("items", []):
                                url = res_item.get("url", "") or res_item.get("link", "") or ""
                                if domain in url:
                                    target_found = True
                                if competitor in url:
                                    comp_found = True

                    if target_found and comp_found:
                        shared_keywords.append(kw)

                total_overlap = len(shared_keywords)
                overlap_pct = round(total_overlap / max(1, len(kw_list)) * 100, 1) if kw_list else 0.0

                report.competitors.append(CompetitorOverlapEntry(
                    competitor_domain=competitor,
                    overlap_percentage=overlap_pct,
                    shared_keyword_count=total_overlap,
                    top_overlapping_keywords=shared_keywords[:10],
                ))

        except Exception as e:
            logger.warning("competitor_serp_overlap_failed", domain=domain, error=str(e))

        return report

    # ------------------------------------------------------------------
    # SERP Dominance Scoring
    # ------------------------------------------------------------------
    async def score_serp_dominance(
        self, domain: str, keywords: list[str], geo: str = "US",
    ) -> SERPDominanceReport:
        """Score SERP dominance of a domain across a keyword set."""
        logger.info("scoring_serp_dominance", domain=domain, keyword_count=len(keywords))

        report = SERPDominanceReport(domain=domain)

        try:
            from seo_platform.clients.dataforseo import dataforseo_client

            entries: list[KeywordDominanceEntry] = []
            total_pos = 0
            ranked_count = 0
            top_3 = 0
            top_10 = 0
            snippet_count = 0

            for keyword in keywords:
                snapshot = await dataforseo_client.get_serp_snapshot(keyword)
                entry = KeywordDominanceEntry(keyword=keyword)
                found = False

                for task in snapshot.get("tasks", []):
                    for item in task.get("result", []):
                        for res_item in item.get("items", []):
                            url = res_item.get("url", "") or res_item.get("link", "") or ""
                            if domain in url:
                                rank = res_item.get("rank_absolute") or res_item.get("rank", 0)
                                entry.rank = rank
                                if rank and 1 <= rank <= 3:
                                    entry.in_top_3 = True
                                    top_3 += 1
                                if rank and 1 <= rank <= 10:
                                    entry.in_top_10 = True
                                    top_10 += 1
                                if rank:
                                    total_pos += rank
                                    ranked_count += 1
                                found = True
                                break

                        if not found:
                            for res_item in item.get("items", []):
                                if (
                                    res_item.get("type") == "featured_snippet"
                                    and domain in (res_item.get("url", "") or "")
                                ):
                                    entry.has_featured_snippet = True
                                    snippet_count += 1

                entries.append(entry)

            report.keyword_details = entries
            report.keyword_count = len(keywords)
            report.average_position = round(total_pos / max(1, ranked_count), 1) if ranked_count > 0 else 0.0
            report.top_3_count = top_3
            report.top_10_count = top_10
            report.featured_snippet_count = snippet_count

            top_3_ratio = top_3 / max(1, len(keywords))
            top_10_ratio = top_10 / max(1, len(keywords))
            pos_score = 1.0 - (report.average_position / 10) if ranked_count > 0 else 0.0
            snippet_score = snippet_count / max(1, len(keywords))

            dominance = (top_3_ratio * 0.35 + top_10_ratio * 0.25 + pos_score * 0.25 + snippet_score * 0.15) * 100
            report.dominance_score = round(dominance, 1)

        except Exception as e:
            logger.warning("serp_dominance_scoring_failed", domain=domain, error=str(e))

        return report

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract domain from a URL."""
        if not url:
            return ""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc or parsed.path.split("/")[0]
        except Exception:
            return url.split("/")[2] if "://" in url else url.split("/")[0]

    @staticmethod
    def _collect_features(item: dict[str, Any], features: set[str]) -> None:
        """Collect SERP feature types from a result item."""
        item_type = (item.get("type", "") or "").lower()
        if item_type == "featured_snippet" or item.get("is_featured_snippet"):
            features.add("featured_snippet")
        if item_type == "people_also_ask":
            features.add("people_also_ask")
        if item_type in ("knowledge_panel", "knowledge_graph"):
            features.add("knowledge_panel")
        if item_type == "video" or "video" in item.get("breadcrumb", ""):
            features.add("video_carousel")
        if item_type == "local_pack" or item.get("is_local_pack"):
            features.add("local_pack")
        if item_type in ("images", "image_pack"):
            features.add("image_pack")
        if item_type == "shopping":
            features.add("shopping_results")
        if item_type == "tweet":
            features.add("tweet_box")
        if item_type == "news":
            features.add("news_box")

        for sub in item.get("items", []):
            if isinstance(sub, dict):
                SERPIntelligenceEngine._collect_features(sub, features)


serp_intelligence_engine = SERPIntelligenceEngine()
