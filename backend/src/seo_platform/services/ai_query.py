from __future__ import annotations

import json
import re
import time
from typing import Any
from uuid import UUID

from sqlalchemy import text
from pydantic import BaseModel, Field

from seo_platform.core.database import get_tenant_session
from seo_platform.core.logging import get_logger
from seo_platform.llm.gateway import LLMGateway, TaskType, RenderedPrompt, LLMResult

logger = get_logger(__name__)

INTENT_PATTERNS: dict[str, dict[str, Any]] = {
    "customer_overview": {
        "patterns": ["customers", "show customers", "list customers", "all customers", "customer list"],
        "sql_template": "SELECT id, name, domain, niche, onboarding_status FROM clients WHERE tenant_id = :tenant_id ORDER BY created_at DESC LIMIT :limit",
    },
    "active_customers": {
        "patterns": ["active customers", "active clients", "onboarded customers"],
        "sql_template": "SELECT id, name, domain, onboarding_status FROM clients WHERE tenant_id = :tenant_id AND onboarding_status = 'onboarded' ORDER BY created_at DESC LIMIT :limit",
    },
    "campaign_performance": {
        "patterns": ["campaign performance", "how are campaigns", "campaign status", "campaign results", "all campaigns", "show campaigns", "list campaigns"],
        "sql_template": "SELECT id, name, campaign_type, status, health_score, target_link_count, acquired_link_count, reply_rate FROM backlink_campaigns WHERE tenant_id = :tenant_id ORDER BY created_at DESC LIMIT :limit",
    },
    "active_campaigns": {
        "patterns": ["active campaigns", "running campaigns", "campaigns active"],
        "sql_template": "SELECT id, name, campaign_type, status, health_score, target_link_count, acquired_link_count FROM backlink_campaigns WHERE tenant_id = :tenant_id AND status = 'active' ORDER BY health_score DESC LIMIT :limit",
    },
    "pending_approvals": {
        "patterns": ["pending approvals", "approvals pending", "needs approval", "waiting for approval"],
        "sql_template": "SELECT id, summary, category, risk_level, status, sla_deadline FROM approval_requests WHERE tenant_id = :tenant_id AND status = 'pending' ORDER BY created_at ASC LIMIT :limit",
    },
    "recent_alerts": {
        "patterns": ["recent alerts", "latest alerts", "active alerts", "alerts", "warnings"],
        "sql_template": "SELECT id, title, severity, status, description, source FROM executive_alerts WHERE tenant_id = :tenant_id AND status = 'open' ORDER BY occurred_at DESC LIMIT :limit",
    },
    "automation_summary": {
        "patterns": ["automation", "automation rules", "automation status", "automation summary"],
        "sql_template": "SELECT id, name, trigger_type, enabled, execution_count, success_count, failure_count FROM automation_rules WHERE tenant_id = :tenant_id ORDER BY created_at DESC LIMIT :limit",
    },
    "keyword_performance": {
        "patterns": ["keywords", "keyword performance", "top keywords", "keyword rankings"],
        "sql_template": "SELECT k.id, k.keyword, k.search_volume, k.difficulty, k.cpc, k.client_id, c.name as client_name FROM keywords k JOIN clients c ON c.id = k.client_id WHERE k.tenant_id = :tenant_id ORDER BY k.search_volume DESC NULLS LAST LIMIT :limit",
    },
    "outreach_results": {
        "patterns": ["outreach", "emails sent", "outreach results", "email performance"],
        "sql_template": "SELECT id, subject, status, to_email, sent_at, opened_at, replied_at FROM outreach_emails WHERE tenant_id = :tenant_id ORDER BY sent_at DESC NULLS LAST LIMIT :limit",
    },
    "campaign_health": {
        "patterns": ["campaign health", "health score", "campaign health summary", "healthy campaigns"],
        "sql_template": "SELECT chs.id, chs.campaign_id, bc.name as campaign_name, chs.health_score, chs.acquisition_rate, chs.reply_rate, chs.captured_at FROM campaign_health_snapshots chs JOIN backlink_campaigns bc ON bc.id = chs.campaign_id WHERE chs.tenant_id = :tenant_id ORDER BY chs.captured_at DESC LIMIT :limit",
    },
    "sla_status": {
        "patterns": ["sla", "sla breaches", "sla status", "approval sla", "service level"],
        "sql_template": "SELECT id, summary, category, risk_level, status, sla_deadline FROM approval_requests WHERE tenant_id = :tenant_id AND sla_deadline IS NOT NULL ORDER BY sla_deadline ASC LIMIT :limit",
    },
    "top_prospects": {
        "patterns": ["top prospects", "best prospects", "high value prospects", "prospect list"],
        "sql_template": "SELECT bp.id, bp.domain, bp.email, bp.score, bp.status, bc.name as campaign_name FROM backlink_prospects bp LEFT JOIN backlink_campaigns bc ON bc.id = bp.campaign_id WHERE bp.tenant_id = :tenant_id ORDER BY bp.score DESC NULLS LAST LIMIT :limit",
    },
    "reports_list": {
        "patterns": ["reports", "report list", "generated reports", "show reports"],
        "sql_template": "SELECT id, report_type, client_id, generated_at FROM reports WHERE tenant_id = :tenant_id ORDER BY generated_at DESC LIMIT :limit",
    },
}


class AIQueryResult(BaseModel):
    intent: str
    sql: str
    explanation: str
    results: list[dict[str, Any]] = Field(default_factory=list)
    latency_ms: float = 0.0


class AIQueryEngine:
    def __init__(self) -> None:
        self._llm = LLMGateway()

    def _detect_intent(self, question: str) -> tuple[str | None, str]:
        question_lower = question.lower().strip()
        best_match: str | None = None
        best_score = 0

        for intent_name, intent_config in INTENT_PATTERNS.items():
            for pattern in intent_config["patterns"]:
                if pattern in question_lower:
                    score = len(pattern.split())
                    if score > best_score:
                        best_score = score
                        best_match = intent_name

        if best_match:
            return best_match, INTENT_PATTERNS[best_match]["sql_template"]

        return None, ""

    async def _llm_generate_sql(self, question: str) -> dict[str, Any]:
        try:
            from pydantic import BaseModel

            class SQLResponse(BaseModel):
                sql: str
                explanation: str

            system_prompt = """Given a natural language question, generate a safe SELECT query for PostgreSQL.
Tables:
- clients(id, name, domain, niche, onboarding_status, profile_data)
- backlink_campaigns(id, name, campaign_type, status, health_score, client_id, target_link_count, acquired_link_count, reply_rate)
- keywords(id, keyword, search_volume, difficulty, cpc, client_id)
- backlink_prospects(id, domain, email, score, status, campaign_id)
- outreach_emails(id, subject, status, to_email, sent_at, opened_at, replied_at)
- approval_requests(id, summary, category, risk_level, status, sla_deadline)
- executive_alerts(id, title, severity, status, description)
- automation_rules(id, name, trigger_type, enabled, execution_count, success_count, failure_count)
- campaign_health_snapshots(id, health_score, acquisition_rate, reply_rate, captured_at, campaign_id)

Rules:
- Always add WHERE tenant_id = :tenant_id
- Add LIMIT :limit
- Only SELECT queries allowed
- Return JSON with keys: sql, explanation"""

            from uuid import uuid4
            llm = LLMGateway()
            prompt = RenderedPrompt(
                template_id="ai_query_sql_gen",
                system_prompt=system_prompt,
                user_prompt=f"Generate SQL for this question: {question}",
                token_budget=1024,
            )
            result: LLMResult = await llm.complete(
                task_type=TaskType.WORKFLOW_ORCHESTRATION,
                prompt=prompt,
                output_schema=SQLResponse,
                tenant_id=uuid4(),
                use_cache=False,
            )
            if isinstance(result.content, SQLResponse):
                return {"sql": result.content.sql, "explanation": result.content.explanation}
            elif isinstance(result.content, dict):
                return {"sql": result.content.get("sql", ""), "explanation": result.content.get("explanation", "")}
            return {"sql": "", "explanation": "Unexpected LLM result shape"}
        except Exception as e:
            logger.warning("llm_sql_gen_failed", error=str(e))
            return {"sql": "", "explanation": f"LLM SQL generation failed: {type(e).__name__}: {str(e)[:200]}"}

    def _validate_sql(self, sql: str) -> bool:
        sql_clean = sql.strip().lower()
        forbidden = ["drop", "delete", "insert", "update", "alter", "truncate", "create", "exec", "call"]
        for keyword in forbidden:
            if re.search(rf'\b{keyword}\b', sql_clean):
                return False
        return sql_clean.startswith("select")

    async def execute_query(self, question: str, tenant_id: UUID) -> AIQueryResult:
        start = time.monotonic()
        sql = ""
        explanation = ""

        intent, sql = self._detect_intent(question)
        if intent:
            explanation = f"Intent matched: {intent}"
        else:
            fallback = await self._llm_generate_sql(question)
            sql = fallback.get("sql", "")
            explanation = fallback.get("explanation", "LLM-generated query")
            intent = "llm_generated"

        if not sql or not self._validate_sql(sql):
            return AIQueryResult(
                intent=intent or "unknown", sql=sql,
                explanation="Query rejected by safety validator",
                results=[{"error": "SQL validation failed"}],
                latency_ms=round((time.monotonic() - start) * 1000, 1),
            )

        try:
            async with get_tenant_session(tenant_id) as session:
                rows = (await session.execute(
                    text(sql),
                    {"tenant_id": tenant_id, "limit": 20},
                )).fetchall()
                columns = list(rows[0]._fields) if rows else []
                results = [
                    {col: str(val) if hasattr(val, 'isoformat') else val
                     for col, val in zip(columns, row, strict=False)}
                    for row in rows
                ]
        except Exception as e:
            logger.warning("ai_query_execution_failed", error=str(e))
            results = [{"error": str(e)}]

        return AIQueryResult(
            intent=intent or "unknown", sql=sql,
            explanation=explanation, results=results,
            latency_ms=round((time.monotonic() - start) * 1000, 1),
        )


ai_query_engine = AIQueryEngine()
