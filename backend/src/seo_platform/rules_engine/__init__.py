"""
SEO Platform — Rules Engine Service
======================================
Deterministic, hot-updatable policy evaluation.

Design: Policies are decoupled from business logic.
Rules are defined declaratively and evaluated deterministically.
Business logic asks "is this allowed?" — never implements the check inline.
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


class RuleOutcome(str, enum.Enum):
    ALLOW = "allow"
    BLOCK = "block"
    WARN = "warn"


class RuleCategory(str, enum.Enum):
    OUTREACH_COMPLIANCE = "outreach_compliance"
    RATE_LIMITING = "rate_limiting"
    CONTENT_POLICY = "content_policy"
    BUDGET_ENFORCEMENT = "budget_enforcement"
    DATA_GOVERNANCE = "data_governance"
    OPERATIONAL_SAFETY = "operational_safety"


class RuleDefinition(BaseModel):
    """A single rule definition with typed evaluation context."""
    rule_id: str
    name: str
    category: RuleCategory
    version: int = 1
    description: str = ""
    is_active: bool = True
    condition: str = ""  # DSL condition expression
    outcome_on_match: RuleOutcome = RuleOutcome.BLOCK
    message: str = ""
    priority: int = 0  # Higher = evaluated first


class RuleEvaluationResult(BaseModel):
    """Result of evaluating a single rule."""
    rule_id: str
    outcome: RuleOutcome
    message: str = ""
    context_snapshot: dict[str, Any] = Field(default_factory=dict)
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RulesCheckResult(BaseModel):
    """Aggregate result of evaluating all applicable rules."""
    allowed: bool
    rules_evaluated: int = 0
    rules_passed: int = 0
    blocking_rules: list[RuleEvaluationResult] = Field(default_factory=list)
    warning_rules: list[RuleEvaluationResult] = Field(default_factory=list)
    evaluation_time_ms: float = 0


# ---------------------------------------------------------------------------
# Built-in Rules (Code-defined; YAML DSL rules loaded at runtime)
# ---------------------------------------------------------------------------
BUILT_IN_RULES: list[RuleDefinition] = [
    RuleDefinition(
        rule_id="outreach.daily_domain_limit",
        name="Daily Domain Send Limit",
        category=RuleCategory.OUTREACH_COMPLIANCE,
        description="Max 1 email per recipient domain per day",
        outcome_on_match=RuleOutcome.BLOCK,
        message="Daily send limit to this domain exceeded",
    ),
    RuleDefinition(
        rule_id="outreach.campaign_touch_limit",
        name="Campaign Touch Limit",
        category=RuleCategory.OUTREACH_COMPLIANCE,
        description="Max 4 touches per contact per campaign (1 initial + 3 follow-ups)",
        outcome_on_match=RuleOutcome.BLOCK,
        message="Maximum touches reached for this contact in this campaign",
    ),
    RuleDefinition(
        rule_id="outreach.unsubscribe_check",
        name="Unsubscribe List Check",
        category=RuleCategory.OUTREACH_COMPLIANCE,
        description="Block sending to contacts on suppression/unsubscribe list",
        outcome_on_match=RuleOutcome.BLOCK,
        message="Contact is on suppression list",
    ),
    RuleDefinition(
        rule_id="outreach.bounce_rate_halt",
        name="Bounce Rate Circuit Breaker",
        category=RuleCategory.OPERATIONAL_SAFETY,
        description="Halt all sends if bounce rate exceeds 5%",
        outcome_on_match=RuleOutcome.BLOCK,
        message="Campaign bounce rate exceeds safety threshold",
    ),
    RuleDefinition(
        rule_id="outreach.spam_rate_halt",
        name="Spam Complaint Rate Circuit Breaker",
        category=RuleCategory.OPERATIONAL_SAFETY,
        description="Halt all sends if spam complaint rate exceeds 0.1%",
        outcome_on_match=RuleOutcome.BLOCK,
        message="Spam complaint rate exceeds safety threshold",
    ),
    RuleDefinition(
        rule_id="budget.tenant_daily_limit",
        name="Tenant Daily Budget Limit",
        category=RuleCategory.BUDGET_ENFORCEMENT,
        description="Block operations if tenant exceeds daily LLM cost budget",
        outcome_on_match=RuleOutcome.BLOCK,
        message="Daily budget limit exceeded for this tenant",
    ),
    RuleDefinition(
        rule_id="budget.workflow_cost_limit",
        name="Per-Workflow Cost Limit",
        category=RuleCategory.BUDGET_ENFORCEMENT,
        description="Halt workflow if cumulative cost exceeds workflow budget",
        outcome_on_match=RuleOutcome.BLOCK,
        message="Workflow has exceeded its cost budget",
    ),
    RuleDefinition(
        rule_id="data.prospect_da_minimum",
        name="Minimum Domain Authority",
        category=RuleCategory.DATA_GOVERNANCE,
        description="Block prospects with DA below tenant's minimum threshold",
        outcome_on_match=RuleOutcome.BLOCK,
        message="Prospect domain authority below minimum threshold",
    ),
    RuleDefinition(
        rule_id="data.prospect_spam_score_max",
        name="Maximum Spam Score",
        category=RuleCategory.DATA_GOVERNANCE,
        description="Block prospects with spam score above tenant's threshold",
        outcome_on_match=RuleOutcome.BLOCK,
        message="Prospect spam score exceeds maximum threshold",
    ),
]


# ---------------------------------------------------------------------------
# Rule Evaluator
# ---------------------------------------------------------------------------
class RuleEvaluator:
    """
    Deterministic rule evaluation engine.

    Evaluates rules against operation context. This is called
    at the start of every Temporal activity (before execution).

    Usage:
        evaluator = RuleEvaluator()
        result = await evaluator.evaluate(
            operation_type="outreach.send_email",
            context={
                "tenant_id": str(tenant_id),
                "recipient_domain": "example.com",
                "campaign_id": str(campaign_id),
                "contact_id": str(contact_id),
            },
        )
        if not result.allowed:
            raise RuleBlockedError(result.blocking_rules[0].rule_id, result.blocking_rules[0].message)
    """

    def __init__(self) -> None:
        self._rules: dict[str, RuleDefinition] = {}
        self._load_built_in_rules()

    def _load_built_in_rules(self) -> None:
        for rule in BUILT_IN_RULES:
            self._rules[rule.rule_id] = rule

    def register_rule(self, rule: RuleDefinition) -> None:
        """Hot-register a new rule (for YAML DSL runtime loading)."""
        self._rules[rule.rule_id] = rule
        logger.info("rule_registered", rule_id=rule.rule_id, version=rule.version)

    def deactivate_rule(self, rule_id: str) -> None:
        """Deactivate a rule without removing it (preserves audit trail)."""
        if rule_id in self._rules:
            self._rules[rule_id].is_active = False
            logger.info("rule_deactivated", rule_id=rule_id)

    async def evaluate(
        self,
        operation_type: str,
        context: dict[str, Any],
        tenant_id: UUID | None = None,
    ) -> RulesCheckResult:
        """
        Evaluate all applicable rules for an operation.

        Returns aggregate result with blocking/warning details.
        This method is deterministic — same input always produces same output.
        """
        import time
        start = time.monotonic()

        applicable_rules = self._get_applicable_rules(operation_type)
        blocking: list[RuleEvaluationResult] = []
        warnings: list[RuleEvaluationResult] = []
        passed = 0

        for rule in sorted(applicable_rules, key=lambda r: r.priority, reverse=True):
            result = await self._evaluate_single_rule(rule, context, tenant_id)
            if result.outcome == RuleOutcome.BLOCK:
                blocking.append(result)
            elif result.outcome == RuleOutcome.WARN:
                warnings.append(result)
            else:
                passed += 1

        elapsed_ms = (time.monotonic() - start) * 1000

        check_result = RulesCheckResult(
            allowed=len(blocking) == 0,
            rules_evaluated=len(applicable_rules),
            rules_passed=passed,
            blocking_rules=blocking,
            warning_rules=warnings,
            evaluation_time_ms=round(elapsed_ms, 2),
        )

        if not check_result.allowed:
            logger.warning(
                "rules_blocked_operation",
                operation_type=operation_type,
                blocking_rules=[r.rule_id for r in blocking],
                tenant_id=str(tenant_id) if tenant_id else None,
            )

        return check_result

    def _get_applicable_rules(self, operation_type: str) -> list[RuleDefinition]:
        """Get active rules matching the operation type prefix."""
        prefix = operation_type.split(".")[0]  # e.g., "outreach" from "outreach.send_email"
        return [
            rule for rule in self._rules.values()
            if rule.is_active and rule.rule_id.startswith(prefix)
        ]

    async def _evaluate_single_rule(
        self,
        rule: RuleDefinition,
        context: dict[str, Any],
        tenant_id: UUID | None,
    ) -> RuleEvaluationResult:
        """
        Evaluate a single rule against context.
        For built-in rules, uses Python evaluation.
        For YAML DSL rules, uses compiled condition evaluation.
        """
        # Built-in rules: lookup evaluation functions
        evaluator_fn = RULE_EVALUATORS.get(rule.rule_id)
        if evaluator_fn:
            outcome = await evaluator_fn(context, tenant_id)
            return RuleEvaluationResult(
                rule_id=rule.rule_id,
                outcome=outcome,
                message=rule.message if outcome != RuleOutcome.ALLOW else "",
                context_snapshot=context,
            )

        # Default: allow (rule exists but no evaluator registered yet)
        return RuleEvaluationResult(
            rule_id=rule.rule_id,
            outcome=RuleOutcome.ALLOW,
        )


# ---------------------------------------------------------------------------
# Rule Evaluator Functions (built-in)
# ---------------------------------------------------------------------------
async def _evaluate_daily_domain_limit(context: dict[str, Any], tenant_id: UUID | None) -> RuleOutcome:
    """Check if daily domain send limit is exceeded."""
    from seo_platform.core.redis import get_redis
    redis = await get_redis()
    domain = context.get("recipient_domain", "")
    if not domain or not tenant_id:
        return RuleOutcome.ALLOW
    key = f"outreach_daily:{tenant_id}:{domain}"
    count = await redis.get(key)
    if count and int(count) >= 1:
        return RuleOutcome.BLOCK
    return RuleOutcome.ALLOW


async def _evaluate_unsubscribe_check(context: dict[str, Any], tenant_id: UUID | None) -> RuleOutcome:
    """Check if contact is on suppression list."""
    from seo_platform.core.redis import get_redis
    redis = await get_redis()
    contact_email = context.get("contact_email", "")
    if not contact_email or not tenant_id:
        return RuleOutcome.ALLOW
    is_suppressed = await redis.sismember(f"suppression_list:{tenant_id}", contact_email)
    return RuleOutcome.BLOCK if is_suppressed else RuleOutcome.ALLOW


# Register evaluator functions
RULE_EVALUATORS: dict[str, Any] = {
    "outreach.daily_domain_limit": _evaluate_daily_domain_limit,
    "outreach.unsubscribe_check": _evaluate_unsubscribe_check,
}


# Module singleton
rule_evaluator = RuleEvaluator()
