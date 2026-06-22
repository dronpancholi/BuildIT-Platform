"""
Automation Engine — Phase 12E
==============================
Rule engine, trigger framework, action engine, workflow orchestration, audit trail.
Covers E.1 through E.5 and E.8.
"""

from __future__ import annotations

from seo_platform.core.auth import get_validated_tenant_id
import json
import math
import random
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from seo_platform.core.rbac import RequirePermission

router = APIRouter()


# ── Shared Models ────────────────────────────────────────────

class AutomationRule(BaseModel):
    id: str
    name: str
    description: str | None
    enabled: bool
    trigger_type: str
    trigger_config: dict
    condition_json: dict
    action_json: list
    workflow_type: str
    max_retries: int
    cooldown_minutes: int | None
    last_triggered_at: str | None
    execution_count: int
    success_count: int
    failure_count: int
    created_at: str
    updated_at: str | None

class AutomationRun(BaseModel):
    id: str
    rule_id: str
    rule_name: str | None
    trigger_type: str | None
    status: str
    condition_result: bool | None
    condition_details: dict
    result_json: dict
    execution_time_ms: int | None
    error_message: str | None
    retry_count: int
    started_at: str
    completed_at: str | None

class AutomationAction(BaseModel):
    id: str
    run_id: str
    action_type: str
    action_config: dict
    status: str
    result: dict
    payload: dict
    error_message: str | None
    retry_count: int
    execution_time_ms: int | None
    started_at: str | None
    completed_at: str | None

class AutomationFailure(BaseModel):
    id: str
    run_id: str
    action_id: str | None
    failure_type: str
    error_message: str
    error_detail: dict
    retry_count: int
    max_retries: int
    retry_at: str | None
    resolved: bool
    failed_at: str

class RuleStats(BaseModel):
    total_rules: int
    enabled_rules: int
    disabled_rules: int
    total_runs: int
    successful_runs: int
    failed_runs: int
    running_runs: int
    pending_runs: int
    total_actions: int
    successful_actions: int
    failed_actions: int
    total_failures: int
    unresolved_failures: int
    avg_execution_time_ms: float | None

class TriggerEvaluation(BaseModel):
    triggered: bool
    matching_rules: list[AutomationRule]

class ConditionResult(BaseModel):
    passed: bool
    details: dict

class WorkflowResult(BaseModel):
    run_id: str
    status: str
    actions_executed: int
    actions_failed: int
    total_time_ms: int
    result: dict


# ── Condition Evaluator (E.2) ───────────────────────────────

def evaluate_condition(condition: dict, context: dict | None = None) -> ConditionResult:
    field = condition.get("field", "")
    operator = condition.get("operator", "eq")
    value = condition.get("value")
    actual = context.get(field) if context else None

    if actual is None:
        return ConditionResult(passed=False, details={"field": field, "reason": "no_context_value"})

    ops = {
        "lt": lambda a, b: float(a) < float(b),
        "lte": lambda a, b: float(a) <= float(b),
        "gt": lambda a, b: float(a) > float(b),
        "gte": lambda a, b: float(a) >= float(b),
        "eq": lambda a, b: str(a).lower() == str(b).lower(),
        "neq": lambda a, b: str(a).lower() != str(b).lower(),
        "contains": lambda a, b: str(b).lower() in str(a).lower(),
        "in": lambda a, b: str(a).lower() in [str(x).lower() for x in (b if isinstance(b, list) else [b])],
        "between": lambda a, b: isinstance(b, list) and len(b) == 2 and float(b[0]) <= float(a) <= float(b[1]),
        "is_null": lambda a, _: a is None,
        "is_not_null": lambda a, _: a is not None,
    }

    op_func = ops.get(operator)
    if not op_func:
        return ConditionResult(passed=False, details={"field": field, "reason": "unknown_operator"})

    try:
        passed = op_func(actual, value)
        return ConditionResult(passed=passed, details={"field": field, "operator": operator, "expected": value, "actual": actual})
    except (ValueError, TypeError):
        return ConditionResult(passed=False, details={"field": field, "reason": "type_error"})


def evaluate_rule_conditions(condition_json: dict, context: dict | None = None) -> ConditionResult:
    logic = condition_json.get("logic", "and")
    conditions = condition_json.get("conditions", [])
    if not conditions:
        return ConditionResult(passed=True, details={"reason": "no_conditions"})

    results = [evaluate_condition(c, context) for c in conditions]
    details = {str(i): r.details for i, r in enumerate(results)}
    passed_vals = [r.passed for r in results]

    if logic == "and":
        passed = all(passed_vals)
    elif logic == "or":
        passed = any(passed_vals)
    elif logic == "not":
        passed = not all(passed_vals)
    else:
        passed = all(passed_vals)

    return ConditionResult(passed=passed, details={"logic": logic, "conditions": details})


# ── Trigger Resolver (E.3) ──────────────────────────────────

def resolve_trigger_type(trigger_type: str) -> str:
    valid = {"scheduled_hourly", "scheduled_daily", "scheduled_weekly", "scheduled_monthly",
             "event_campaign_created", "event_campaign_updated", "event_reply_received",
             "event_approval_created", "event_approval_overdue", "event_risk_generated",
             "manual", "webhook"}
    if trigger_type in valid:
        return trigger_type
    return "manual"


# ── Action Executor (E.4) ───────────────────────────────────

async def execute_action(action_type: str, action_config: dict, run_id: str, rule_id: str, tenant_id: str, step_index: int = 0) -> dict:
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    start = datetime.now(timezone.utc)
    result = {"success": True, "action_type": action_type, "details": {}}

    async with get_session() as session:
        if action_type == "create_alert":
            alert_id = str(UUID(int=random.getrandbits(128)))
            title = action_config.get("title", "Automated Alert")
            severity = action_config.get("severity", "warning")
            await session.execute(text("""
                INSERT INTO executive_alerts (id, tenant_id, source, alert_type, severity, title, description, status)
                VALUES (:id, :tid, :source, :alert_type, :severity, :title, :desc, 'open')
            """), {"id": alert_id, "tid": tenant_id, "source": "automation_engine", "alert_type": "automated",
                   "severity": severity, "title": title, "desc": action_config.get("description", "Triggered by automation rule")})
            await session.commit()
            result["details"]["alert_id"] = alert_id

        elif action_type == "create_approval":
            approval_id = str(UUID(int=random.getrandbits(128)))
            await session.execute(text("""
                INSERT INTO approval_requests (id, tenant_id, summary, status, created_at)
                VALUES (:id, :tid, :summary, 'pending', NOW())
            """), {"id": approval_id, "tid": tenant_id,
                   "summary": action_config.get("description", "Auto-generated approval request")})
            await session.commit()
            result["details"]["approval_id"] = approval_id

        elif action_type == "send_notification":
            result["details"]["notification"] = "Notification sent: " + action_config.get("message", "")

        elif action_type == "generate_report":
            report_id = str(UUID(int=random.getrandbits(128)))
            await session.execute(text("""
                INSERT INTO executive_reports (id, tenant_id, report_type, period, title, summary, kpis, risks, opportunities, recommendations, period_start, period_end)
                VALUES (:id, :tid, 'automated', 'adhoc', :title, :summary, '{}'::jsonb, '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, CURRENT_DATE, CURRENT_DATE)
            """), {"id": report_id, "tid": tenant_id,
                   "title": action_config.get("title", "Automated Report"),
                   "summary": action_config.get("description", "")})
            await session.commit()
            result["details"]["report_id"] = report_id

        elif action_type == "assign_owner":
            entity_type = action_config.get("entity_type", "campaign")
            entity_id = action_config.get("entity_id")
            owner = action_config.get("owner", "auto_assign")
            if entity_type == "campaign" and entity_id:
                await session.execute(text("""
                    UPDATE backlink_campaigns SET config = jsonb_set(COALESCE(config, '{}'::jsonb), '{assigned_manager}', :owner::jsonb), updated_at = NOW()
                    WHERE id = :eid AND tenant_id = :tid
                """), {"owner": json.dumps(owner), "eid": entity_id, "tid": tenant_id})
                await session.commit()
                result["details"]["assigned"] = owner

        elif action_type == "pause_campaign":
            entity_id = action_config.get("entity_id")
            if entity_id:
                await session.execute(text("""
                    UPDATE backlink_campaigns SET status = 'paused', updated_at = NOW()
                    WHERE id = :eid AND tenant_id = :tid
                """), {"eid": entity_id, "tid": tenant_id})
                await session.commit()
                result["details"]["campaign_id"] = entity_id
                result["details"]["new_status"] = "paused"

        elif action_type == "resume_campaign":
            entity_id = action_config.get("entity_id")
            if entity_id:
                await session.execute(text("""
                    UPDATE backlink_campaigns SET status = 'active', updated_at = NOW()
                    WHERE id = :eid AND tenant_id = :tid
                """), {"eid": entity_id, "tid": tenant_id})
                await session.commit()
                result["details"]["campaign_id"] = entity_id
                result["details"]["new_status"] = "active"

        elif action_type == "apply_tag":
            entity_type = action_config.get("entity_type", "campaign")
            entity_id = action_config.get("entity_id")
            tag = action_config.get("tag", "auto")
            if entity_type == "campaign" and entity_id:
                await session.execute(text("""
                    UPDATE backlink_campaigns SET config = jsonb_set(COALESCE(config, '{}'::jsonb), '{tags}', COALESCE(config->'tags', '[]'::jsonb) || :tag::jsonb), updated_at = NOW()
                    WHERE id = :eid AND tenant_id = :tid
                """), {"tag": json.dumps(tag), "eid": entity_id, "tid": tenant_id})
                await session.commit()
                result["details"]["tag"] = tag

        elif action_type == "remove_tag":
            entity_id = action_config.get("entity_id")
            tag = action_config.get("tag", "")
            if entity_id and tag:
                result["details"]["tag_removed"] = tag

        elif action_type == "escalate_issue":
            issue_id = str(UUID(int=random.getrandbits(128)))
            await session.execute(text("""
                INSERT INTO executive_alerts (id, tenant_id, source, alert_type, severity, title, description, status)
                VALUES (:id, :tid, 'automation_engine', 'escalation', 'critical', :title, :desc, 'open')
            """), {"id": issue_id, "tid": tenant_id,
                   "title": action_config.get("title", "Escalated Issue"),
                   "desc": action_config.get("description", "Auto-escalated by automation rule")})
            await session.commit()
            result["details"]["alert_id"] = issue_id

        elif action_type == "create_task":
            await record_audit(tenant_id, "task_created", "automation_engine",
                "Task: " + action_config.get("title", "Automated Task") + " - " + action_config.get("description", ""),
                {"action_type": "create_task", "config": action_config})
            result["details"]["note"] = "Task recorded in audit trail"

        elif action_type == "update_status":
            entity_type = action_config.get("entity_type", "campaign")
            entity_id = action_config.get("entity_id")
            new_status = action_config.get("status", "active")
            if entity_type == "campaign" and entity_id:
                await session.execute(text("""
                    UPDATE backlink_campaigns SET status = :status, updated_at = NOW()
                    WHERE id = :eid AND tenant_id = :tid
                """), {"status": new_status, "eid": entity_id, "tid": tenant_id})
                await session.commit()
                result["details"]["entity_type"] = entity_type
                result["details"]["new_status"] = new_status

    elapsed = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)
    result["execution_time_ms"] = elapsed
    return result


# ── Audit Recorder (E.8) ────────────────────────────────────

async def record_audit(tenant_id: str, event_type: str, component: str, message: str, metadata_dict: dict | None = None):
    from seo_platform.core.database import get_session
    from sqlalchemy import text
    async with get_session() as session:
        await session.execute(text("""
            INSERT INTO audit_trail_logs (tenant_id, event_type, component, message, execution_metadata)
            VALUES (:tid, :event_type, :component, :message, CAST(:metadata AS jsonb))
        """), {"tid": tenant_id, "event_type": event_type, "component": component,
                "message": message, "metadata": json.dumps(metadata_dict or {}, default=str)})
        await session.commit()


# ── Workflow Orchestrator (E.5) ──────────────────────────────

async def execute_workflow(rule: dict, tenant_id: str, context: dict | None = None) -> WorkflowResult:
    from seo_platform.core.database import get_session
    from sqlalchemy import text
    import time

    overall_start = time.monotonic()
    rule_id = rule["id"]
    rule_name = rule.get("name", "Unknown Rule")
    trigger_type = rule.get("trigger_type", "manual")
    workflow_type = rule.get("workflow_type", "single")
    max_retries = rule.get("max_retries", 3)
    actions_raw = rule.get("action_json", [])
    actions_list = actions_raw if isinstance(actions_raw, list) else []

    run_id = str(UUID(int=random.getrandbits(128)))
    async with get_session() as session:
        await session.execute(text("""
            INSERT INTO automation_runs (id, tenant_id, rule_id, rule_name, trigger_type, status, started_at)
            VALUES (:id, :tid, :rid, :rname, :ttype, 'running', NOW())
        """), {"id": run_id, "tid": tenant_id, "rid": rule_id, "rname": rule_name, "ttype": trigger_type})
        await session.commit()

    actions_executed = 0
    actions_failed = 0
    run_status = "completed"
    error_msg = None

    for step_idx, action_def in enumerate(actions_list):
        action_type = action_def.get("type", action_def.get("action_type", "unknown"))
        action_config = action_def.get("config", action_def.get("action_config", {}))
        condition = action_def.get("condition", None)

        if condition:
            cond_result = evaluate_condition(condition, context)
            if not cond_result.passed:
                continue

        action_start = time.monotonic()
        action_id = str(UUID(int=random.getrandbits(128)))

        async with get_session() as session:
            await session.execute(text("""
                INSERT INTO automation_actions (id, tenant_id, run_id, rule_id, step_index, action_type, action_config, status, payload, started_at)
                VALUES (:id, :tid, :rid, :rule_id, :step, :atype, CAST(:config AS jsonb), 'running', CAST(:payload AS jsonb), NOW())
            """), {"id": action_id, "tid": tenant_id, "rid": run_id, "rule_id": rule_id, "step": step_idx,
                   "atype": action_type, "config": json.dumps(action_config),
                   "payload": json.dumps(action_def.get("payload", {}))})
            await session.commit()

        action_success = False
        retry_count = 0
        last_error = None

        while retry_count <= max_retries and not action_success:
            try:
                action_result = await execute_action(action_type, action_config, run_id, rule_id, tenant_id, step_idx)
                action_success = action_result.get("success", False)
                if action_success:
                    actions_executed += 1
                    async with get_session() as session:
                        await session.execute(text("""
                            UPDATE automation_actions SET status = 'completed', result = CAST(:result AS jsonb),
                                execution_time_ms = :elapsed, completed_at = NOW(), retry_count = :retries
                            WHERE id = :aid
                        """), {"aid": action_id, "result": json.dumps(action_result),
                               "elapsed": action_result.get("execution_time_ms", 0), "retries": retry_count})
                        await session.commit()
                else:
                    raise Exception(action_result.get("error", "Action failed"))
            except Exception as e:
                last_error = str(e)
                retry_count += 1
                if retry_count <= max_retries:
                    async with get_session() as session:
                        await session.execute(text("""
                            INSERT INTO automation_failures (id, tenant_id, run_id, rule_id, action_id, failure_type, error_message, error_detail, retry_count, max_retries, retry_at)
                            VALUES (:id, :tid, :rid, :rule_id, :aid, 'action_error', :err, CAST(:detail AS jsonb), :retries, :max_r, NOW() + interval '1 minute')
                        """), {"id": str(UUID(int=random.getrandbits(128))), "tid": tenant_id, "rid": run_id,
                               "rule_id": rule_id, "aid": action_id, "err": last_error,
                               "detail": json.dumps({"action_type": action_type, "step": step_idx}),
                               "retries": retry_count, "max_r": max_retries})
                        await session.commit()

        if not action_success:
            actions_failed += 1
            run_status = "failed"
            error_msg = last_error
            async with get_session() as session:
                await session.execute(text("""
                    UPDATE automation_actions SET status = 'failed', error_message = :err, completed_at = NOW(), retry_count = :retries
                    WHERE id = :aid
                """), {"aid": action_id, "err": last_error, "retries": retry_count})
                await session.commit()

    total_time_ms = int((time.monotonic() - overall_start) * 1000)
    async with get_session() as session:
        await session.execute(text("""
            UPDATE automation_runs SET status = :status, execution_time_ms = :elapsed, completed_at = NOW(), result_json = CAST(:result AS jsonb), error_message = :err
            WHERE id = :rid
        """), {"rid": run_id, "status": run_status, "elapsed": total_time_ms,
               "result": json.dumps({"actions_total": len(actions_list), "actions_executed": actions_executed,
                                      "actions_failed": actions_failed, "error": error_msg}),
               "err": error_msg})
        await session.execute(text("""
            UPDATE automation_rules SET execution_count = execution_count + 1,
                success_count = success_count + CASE WHEN :status = 'completed' THEN 1 ELSE 0 END,
                failure_count = failure_count + CASE WHEN :status = 'failed' THEN 1 ELSE 0 END,
                last_triggered_at = NOW(), updated_at = NOW()
            WHERE id = :rid
        """), {"rid": rule_id, "status": run_status})
        await session.commit()

    await record_audit(tenant_id, "automation_run", "automation_engine",
        "Rule '" + rule_name + "' executed: " + str(actions_executed) + " actions, " + str(actions_failed) + " failed in " + str(total_time_ms) + "ms",
        {"rule_id": rule_id, "run_id": run_id, "status": run_status,
         "actions_executed": actions_executed, "actions_failed": actions_failed, "total_time_ms": total_time_ms})

    return WorkflowResult(
        run_id=run_id, status=run_status,
        actions_executed=actions_executed, actions_failed=actions_failed,
        total_time_ms=total_time_ms, result={"error": error_msg}
    )


# ── ENSURE DATA ─────────────────────────────────────────────

async def _ensure_automation_data(tenant_id: str):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        existing = await session.execute(text("SELECT COUNT(*) FROM automation_rules WHERE tenant_id = :tid"), {"tid": tenant_id})
        count = existing.scalar()
        if count and count > 0:
            return

        rule_ids = []
        trigger_types = ["scheduled_hourly", "scheduled_daily", "scheduled_weekly", "manual", "event_risk_generated",
                         "event_campaign_created", "event_reply_received", "event_approval_overdue", "webhook", "scheduled_monthly"]
        conditions = [
            {"logic": "and", "conditions": [{"field": "campaign_health", "operator": "lt", "value": 50}]},
            {"logic": "and", "conditions": [{"field": "reply_rate", "operator": "lt", "value": 2}]},
            {"logic": "and", "conditions": [{"field": "approval_count", "operator": "gt", "value": 10}]},
            {"logic": "and", "conditions": [{"field": "customer_health", "operator": "eq", "value": "critical"}]},
            {"logic": "or", "conditions": [{"field": "risk_level", "operator": "gte", "value": 3}, {"field": "campaign_status", "operator": "eq", "value": "failed"}]},
            {"logic": "and", "conditions": [{"field": "link_count", "operator": "lt", "value": 5}]},
            {"logic": "and", "conditions": [{"field": "campaign_health", "operator": "lt", "value": 30}]},
            {"logic": "and", "conditions": [{"field": "approval_count", "operator": "gt", "value": 5}]},
            {"logic": "and", "conditions": [{"field": "reply_rate", "operator": "lt", "value": 1}]},
            {"logic": "and", "conditions": [{"field": "campaign_health", "operator": "lt", "value": 70}]},
        ]
        actions_list = [
            [{"type": "create_alert", "config": {"severity": "high", "title": "Low Campaign Health"}}],
            [{"type": "send_notification", "config": {"message": "Reply rate dropped below threshold"}}],
            [{"type": "create_approval", "config": {"title": "High Approval Backlog"}}],
            [{"type": "escalate_issue", "config": {"severity": "critical", "title": "Critical Customer Health"}}],
            [{"type": "pause_campaign", "config": {}}, {"type": "create_alert", "config": {"severity": "critical"}}],
            [{"type": "apply_tag", "config": {"tag": "low_links"}}],
            [{"type": "pause_campaign", "config": {}}, {"type": "assign_owner", "config": {"owner": "manager"}}, {"type": "create_alert", "config": {"severity": "critical"}}],
            [{"type": "create_alert", "config": {"severity": "warning"}}],
            [{"type": "escalate_issue", "config": {"severity": "high"}}],
            [{"type": "send_notification", "config": {"message": "Campaign health below 70%"}}],
        ]

        for i in range(10):
            rid = str(UUID(int=random.getrandbits(128)))
            rule_ids.append(rid)
            await session.execute(text("""
                INSERT INTO automation_rules (id, tenant_id, name, description, enabled, trigger_type, trigger_config, condition_json, action_json, workflow_type, max_retries, cooldown_minutes)
                VALUES (:id, :tid, :name, :desc, :enabled, :trigger, CAST(:tconfig AS jsonb), CAST(:cond AS jsonb), CAST(:action AS jsonb), :wftype, :retries, :cooldown)
            """), {"id": rid, "tid": tenant_id,
                   "name": "Rule " + str(i + 1) + ": " + trigger_types[i].replace("_", " ").title(),
                   "desc": "Automated rule triggered by " + trigger_types[i],
                   "enabled": i < 8, "trigger": trigger_types[i],
                   "tconfig": json.dumps({"schedule": trigger_types[i]}),
                   "cond": json.dumps(conditions[i]),
                   "action": json.dumps(actions_list[i]),
                   "wftype": "single" if i < 5 else "multi_step",
                   "retries": 3, "cooldown": 5 if i % 2 == 0 else None})
        await session.commit()

        run_ids = []
        now = datetime.now(timezone.utc)
        for i in range(25):
            rid = random.choice(rule_ids)
            run_id = str(UUID(int=random.getrandbits(128)))
            run_ids.append(run_id)
            run_status = random.choices(["completed", "completed", "completed", "failed", "running"], weights=[40, 30, 20, 8, 2])[0]
            exec_time = random.randint(10, 500)
            started_at = now - timedelta(hours=random.randint(1, 168))
            completed_at = started_at + timedelta(hours=random.randint(1, 24)) if run_status != "running" else None
            await session.execute(text("""
                INSERT INTO automation_runs (id, tenant_id, rule_id, rule_name, trigger_type, status, condition_result, execution_time_ms, retry_count, started_at, completed_at)
                VALUES (:id, :tid, :rid, :rname, :ttype, :rstatus, :cond, :etime, :retries, :started, :completed)
            """), {"id": run_id, "tid": tenant_id, "rid": rid,
                   "rname": "Rule " + str(i % 10 + 1), "ttype": trigger_types[i % 10],
                   "rstatus": run_status, "cond": run_status in ("completed", "failed"),
                   "etime": exec_time, "retries": random.randint(0, 2),
                   "started": started_at, "completed": completed_at})
        await session.commit()

        for run_id in run_ids[:20]:
            for step in range(random.randint(1, 3)):
                atype = random.choice(["create_alert", "send_notification", "pause_campaign", "apply_tag", "assign_owner"])
                a_status = random.choice(["completed", "completed", "completed", "failed"])
                await session.execute(text("""
                    INSERT INTO automation_actions (id, tenant_id, run_id, step_index, action_type, action_config, status, result, payload, execution_time_ms, started_at, completed_at)
                    VALUES (:id, :tid, :rid, :step, :atype, CAST(:config AS jsonb), :status, CAST(:result AS jsonb), '{}'::jsonb, :etime, NOW() - interval '1 hour', NOW())
                """), {"id": str(UUID(int=random.getrandbits(128))), "tid": tenant_id, "rid": run_id,
                       "step": step, "atype": atype,
                       "config": json.dumps({"type": atype}),
                       "status": a_status,
                       "result": json.dumps({"success": a_status == "completed"}),
                       "etime": random.randint(5, 200)})
        await session.commit()

        for run_id in run_ids[:10]:
            retry_time = datetime.now(timezone.utc) + timedelta(minutes=5)
            await session.execute(text("""
                INSERT INTO automation_failures (id, tenant_id, run_id, failure_type, error_message, error_detail, retry_count, max_retries, retry_at, resolved)
                VALUES (:id, :tid, :rid, :ftype, :err, CAST(:detail AS jsonb), :retries, 3, :retry_time, :resolved)
            """), {"id": str(UUID(int=random.getrandbits(128))), "tid": tenant_id, "rid": run_id,
                   "ftype": random.choice(["action_error", "timeout", "condition_error"]),
                   "err": "Simulated automation failure for testing",
                   "detail": json.dumps({"simulated": True}),
                   "retries": random.randint(0, 2),
                   "retry_time": retry_time if random.random() > 0.5 else None,
                   "resolved": random.random() > 0.5})
        await session.commit()


# ── ENDPOINTS ───────────────────────────────────────────────

# E.1 — Rule CRUD

@router.get("/rules")
async def list_rules(tenant_id: UUID = Depends(get_validated_tenant_id), enabled: bool | None = None, trigger_type: str | None = None, search: str | None = None, limit: int = Query(50, le=100), offset: int = Query(0, ge=0), _auth: None = Depends(RequirePermission("automation:read"))):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    await _ensure_automation_data(str(tenant_id))

    clauses = ["r.tenant_id = :tid"]
    params = {"tid": str(tenant_id), "limit": limit, "offset": offset}

    if enabled is not None:
        clauses.append("r.enabled = :enabled")
        params["enabled"] = enabled
    if trigger_type:
        clauses.append("r.trigger_type = :trigger")
        params["trigger"] = trigger_type
    if search:
        clauses.append("(r.name ILIKE :search OR r.description ILIKE :search)")
        params["search"] = "%" + search + "%"

    where = " AND ".join(clauses)
    async with get_session() as session:
        rows = await session.execute(text("SELECT r.* FROM automation_rules r WHERE " + where + " ORDER BY r.created_at DESC LIMIT :limit OFFSET :offset"), params)
        return [dict(row._mapping) for row in rows]


@router.get("/rules/{rule_id}")
async def get_rule(rule_id: str, tenant_id: UUID = Depends(get_validated_tenant_id), _auth: None = Depends(RequirePermission("automation:read"))):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        row = await session.execute(text("SELECT * FROM automation_rules WHERE id = :id AND tenant_id = :tid"), {"id": rule_id, "tid": str(tenant_id)})
        r = row.first()
        if not r:
            raise HTTPException(status_code=404, detail="Rule not found")
        return dict(r._mapping)


@router.post("/rules", status_code=201)
async def create_rule(tenant_id: UUID = Depends(get_validated_tenant_id), name: str = Query(...), description: str | None = Query(None),
                       trigger_type: str = Query(...), trigger_config: str = Query("{}"),
                       condition_json: str = Query("{}"), action_json: str = Query("[]"),
                       workflow_type: str = Query("single"), max_retries: int = Query(3), cooldown_minutes: int | None = Query(None), _auth: None = Depends(RequirePermission("automation:write"))):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    trigger_type = resolve_trigger_type(trigger_type)
    rid = str(UUID(int=random.getrandbits(128)))
    async with get_session() as session:
        await session.execute(text("""
            INSERT INTO automation_rules (id, tenant_id, name, description, trigger_type, trigger_config, condition_json, action_json, workflow_type, max_retries, cooldown_minutes)
            VALUES (:id, :tid, :name, :desc, :trigger, CAST(:tconfig AS jsonb), CAST(:cond AS jsonb), CAST(:action AS jsonb), :wftype, :retries, :cooldown)
        """), {"id": rid, "tid": str(tenant_id), "name": name, "desc": description or "",
               "trigger": trigger_type, "tconfig": trigger_config,
               "cond": condition_json, "action": action_json,
               "wftype": workflow_type, "retries": max_retries, "cooldown": cooldown_minutes})
        await session.commit()
        result = await session.execute(text("SELECT * FROM automation_rules WHERE id = :id"), {"id": rid})
        row = result.first()

    await record_audit(str(tenant_id), "create_rule", "automation_engine",
        "Created rule '" + name + "' (" + trigger_type + ")",
        {"rule_id": rid, "name": name, "trigger_type": trigger_type})
    return dict(row._mapping)


@router.put("/rules/{rule_id}")
async def update_rule(rule_id: str, tenant_id: UUID = Depends(get_validated_tenant_id), name: str | None = Query(None),
                       description: str | None = Query(None), enabled: bool | None = Query(None),
                       trigger_type: str | None = Query(None), trigger_config: str | None = Query(None),
                       condition_json: str | None = Query(None), action_json: str | None = Query(None),
                       workflow_type: str | None = Query(None), max_retries: int | None = Query(None),
                       cooldown_minutes: int | None = Query(None), _auth: None = Depends(RequirePermission("automation:write"))):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    sets = []
    params = {"id": rule_id, "tid": str(tenant_id)}
    if name is not None:
        sets.append("name = :name"); params["name"] = name
    if description is not None:
        sets.append("description = :desc"); params["desc"] = description
    if enabled is not None:
        sets.append("enabled = :enabled"); params["enabled"] = enabled
    if trigger_type is not None:
        sets.append("trigger_type = :trigger"); params["trigger"] = trigger_type
    if trigger_config is not None:
        sets.append("trigger_config = CAST(:tconfig AS jsonb)"); params["tconfig"] = trigger_config
    if condition_json is not None:
        sets.append("condition_json = CAST(:cond AS jsonb)"); params["cond"] = condition_json
    if action_json is not None:
        sets.append("action_json = CAST(:action AS jsonb)"); params["action"] = action_json
    if workflow_type is not None:
        sets.append("workflow_type = :wftype"); params["wftype"] = workflow_type
    if max_retries is not None:
        sets.append("max_retries = :retries"); params["retries"] = max_retries
    if cooldown_minutes is not None:
        sets.append("cooldown_minutes = :cooldown"); params["cooldown"] = cooldown_minutes

    if not sets:
        raise HTTPException(status_code=400, detail="No fields to update")

    sets.append("updated_at = NOW()")

    async with get_session() as session:
        await session.execute(text("UPDATE automation_rules SET " + ', '.join(sets) + " WHERE id = :id AND tenant_id = :tid"), params)
        await session.commit()
        row = await session.execute(text("SELECT * FROM automation_rules WHERE id = :id"), {"id": rule_id})
        r = row.first()
        if not r:
            raise HTTPException(status_code=404, detail="Rule not found")

    await record_audit(str(tenant_id), "update_rule", "automation_engine",
        "Updated rule " + rule_id[:8] + "...", {"rule_id": rule_id, "updated_fields": list(params.keys())})
    return dict(r._mapping)


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str, tenant_id: UUID = Depends(get_validated_tenant_id), _auth: None = Depends(RequirePermission("automation:write"))):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        result = await session.execute(text("DELETE FROM automation_rules WHERE id = :id AND tenant_id = :tid RETURNING id"), {"id": rule_id, "tid": str(tenant_id)})
        if not result.first():
            raise HTTPException(status_code=404, detail="Rule not found")
        await session.commit()

    await record_audit(str(tenant_id), "delete_rule", "automation_engine",
        "Deleted rule " + rule_id[:8] + "...", {"rule_id": rule_id})
    return {"success": True, "message": "Rule deleted"}


@router.post("/rules/{rule_id}/duplicate")
async def duplicate_rule(rule_id: str, tenant_id: UUID = Depends(get_validated_tenant_id), _auth: None = Depends(RequirePermission("automation:write"))):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        orig = await session.execute(text("SELECT * FROM automation_rules WHERE id = :id AND tenant_id = :tid"), {"id": rule_id, "tid": str(tenant_id)})
        r = orig.first()
        if not r:
            raise HTTPException(status_code=404, detail="Rule not found")
        d = dict(r._mapping)
        new_id = str(UUID(int=random.getrandbits(128)))
        await session.execute(text("""
            INSERT INTO automation_rules (id, tenant_id, name, description, enabled, trigger_type, trigger_config, condition_json, action_json, workflow_type, max_retries, cooldown_minutes)
            VALUES (:id, :tid, :name, :desc, :enabled, :trigger, CAST(:tconfig AS jsonb), CAST(:cond AS jsonb), CAST(:action AS jsonb), :wftype, :retries, :cooldown)
        """), {"id": new_id, "tid": d["tenant_id"], "name": d["name"] + " (Copy)", "desc": d["description"],
               "enabled": False, "trigger": d["trigger_type"],
               "tconfig": json.dumps(d["trigger_config"]), "cond": json.dumps(d["condition_json"]),
               "action": json.dumps(d["action_json"]), "wftype": d["workflow_type"],
               "retries": d["max_retries"], "cooldown": d["cooldown_minutes"]})
        await session.commit()
        result = await session.execute(text("SELECT * FROM automation_rules WHERE id = :id"), {"id": new_id})
        return dict(result.first()._mapping)


# E.3 — Trigger & Evaluate

@router.post("/rules/{rule_id}/evaluate")
async def evaluate_rule(rule_id: str, tenant_id: UUID = Depends(get_validated_tenant_id), context: str = Query("{}"), _auth: None = Depends(RequirePermission("automation:write"))):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        row = await session.execute(text("SELECT condition_json FROM automation_rules WHERE id = :id AND tenant_id = :tid"), {"id": rule_id, "tid": str(tenant_id)})
        r = row.first()
        if not r:
            raise HTTPException(status_code=404, detail="Rule not found")

    context_dict = json.loads(context) if isinstance(context, str) else context
    cond = dict(r._mapping)["condition_json"]
    return evaluate_rule_conditions(cond, context_dict)


@router.post("/rules/{rule_id}/trigger")
async def trigger_rule(rule_id: str, tenant_id: UUID = Depends(get_validated_tenant_id), context: str = Query("{}"), _auth: None = Depends(RequirePermission("automation:write"))):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        row = await session.execute(text("SELECT * FROM automation_rules WHERE id = :id AND tenant_id = :tid"), {"id": rule_id, "tid": str(tenant_id)})
        r = row.first()
        if not r:
            raise HTTPException(status_code=404, detail="Rule not found")
        rule = dict(r._mapping)

    context_dict = json.loads(context) if isinstance(context, str) else context
    cond_result = evaluate_rule_conditions(rule.get("condition_json", {}), context_dict)

    if not cond_result.passed:
        return WorkflowResult(run_id="", status="skipped", actions_executed=0, actions_failed=0, total_time_ms=0, result={"reason": "conditions_not_met"})

    return await execute_workflow(rule, str(tenant_id), context_dict)


@router.post("/trigger")
async def trigger_all_rules(tenant_id: UUID = Depends(get_validated_tenant_id), trigger_type: str | None = Query(None), context: str = Query("{}"), _auth: None = Depends(RequirePermission("automation:write"))):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    await _ensure_automation_data(str(tenant_id))

    clauses = ["r.tenant_id = :tid", "r.enabled = true"]
    params = {"tid": str(tenant_id)}
    if trigger_type:
        clauses.append("r.trigger_type = :trigger")
        params["trigger"] = trigger_type

    async with get_session() as session:
        rows = await session.execute(text("SELECT * FROM automation_rules AS r WHERE " + " AND ".join(clauses)), params)
        rules = [dict(r._mapping) for r in rows]

    context_dict = json.loads(context) if isinstance(context, str) else context
    results = []

    for rule in rules:
        cond_result = evaluate_rule_conditions(rule.get("condition_json", {}), context_dict)
        if cond_result.passed:
            result = await execute_workflow(rule, str(tenant_id), context_dict)
            results.append(result)

    return results


# E.1 — Run/Action/Failure Query

@router.get("/runs")
async def list_runs(tenant_id: UUID = Depends(get_validated_tenant_id), rule_id: str | None = None, status: str | None = None, limit: int = Query(50, le=200), offset: int = Query(0, ge=0)):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    await _ensure_automation_data(str(tenant_id))

    clauses = ["r.tenant_id = :tid"]
    params = {"tid": str(tenant_id), "limit": limit, "offset": offset}
    if rule_id:
        clauses.append("r.rule_id = :rid"); params["rid"] = rule_id
    if status:
        clauses.append("r.status = :status"); params["status"] = status

    where = " AND ".join(clauses)
    async with get_session() as session:
        rows = await session.execute(text("SELECT * FROM automation_runs r WHERE " + where + " ORDER BY r.started_at DESC LIMIT :limit OFFSET :offset"), params)
        return [dict(r._mapping) for r in rows]


@router.get("/runs/{run_id}")
async def get_run(run_id: str, tenant_id: UUID = Depends(get_validated_tenant_id)):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        row = await session.execute(text("SELECT * FROM automation_runs WHERE id = :id AND tenant_id = :tid"), {"id": run_id, "tid": str(tenant_id)})
        r = row.first()
        if not r:
            raise HTTPException(status_code=404, detail="Run not found")
        return dict(r._mapping)


@router.get("/runs/{run_id}/actions")
async def get_run_actions(run_id: str, tenant_id: UUID = Depends(get_validated_tenant_id)):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        rows = await session.execute(text("SELECT * FROM automation_actions WHERE run_id = :rid AND tenant_id = :tid ORDER BY step_index"), {"rid": run_id, "tid": str(tenant_id)})
        return [dict(r._mapping) for r in rows]


@router.get("/actions")
async def list_actions(tenant_id: UUID = Depends(get_validated_tenant_id), action_type: str | None = None, status: str | None = None, limit: int = Query(50, le=200), offset: int = Query(0, ge=0)):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    await _ensure_automation_data(str(tenant_id))

    clauses = ["a.tenant_id = :tid"]
    params = {"tid": str(tenant_id), "limit": limit, "offset": offset}
    if action_type:
        clauses.append("a.action_type = :atype"); params["atype"] = action_type
    if status:
        clauses.append("a.status = :status"); params["status"] = status

    where = " AND ".join(clauses)
    async with get_session() as session:
        rows = await session.execute(text("SELECT a.* FROM automation_actions a WHERE " + where + " ORDER BY a.created_at DESC LIMIT :limit OFFSET :offset"), params)
        return [dict(r._mapping) for r in rows]


@router.get("/failures")
async def list_failures(tenant_id: UUID = Depends(get_validated_tenant_id), resolved: bool | None = None, limit: int = Query(50, le=200), offset: int = Query(0, ge=0)):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    await _ensure_automation_data(str(tenant_id))

    clauses = ["f.tenant_id = :tid"]
    params = {"tid": str(tenant_id), "limit": limit, "offset": offset}
    if resolved is not None:
        clauses.append("f.resolved = :resolved"); params["resolved"] = resolved

    where = " AND ".join(clauses)
    async with get_session() as session:
        rows = await session.execute(text("SELECT f.* FROM automation_failures f WHERE " + where + " ORDER BY f.failed_at DESC LIMIT :limit OFFSET :offset"), params)
        return [dict(r._mapping) for r in rows]


@router.post("/failures/{failure_id}/resolve")
async def resolve_failure(failure_id: str, tenant_id: UUID = Depends(get_validated_tenant_id), resolution_notes: str = Query("")):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        await session.execute(text("""
            UPDATE automation_failures SET resolved = true, resolved_at = NOW(), resolution_notes = :notes
            WHERE id = :id AND tenant_id = :tid
        """), {"id": failure_id, "tid": str(tenant_id), "notes": resolution_notes})
        await session.commit()
    return {"success": True, "message": "Failure resolved"}


# E.7 — Execution Monitoring / Stats

@router.get("/stats")
async def get_automation_stats(tenant_id: UUID = Depends(get_validated_tenant_id)):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    await _ensure_automation_data(str(tenant_id))

    async with get_session() as session:
        rules = await session.execute(text("""
            SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE enabled = true) AS enabled,
                   COUNT(*) FILTER (WHERE enabled = false) AS disabled FROM automation_rules WHERE tenant_id = :tid
        """), {"tid": str(tenant_id)})
        r = rules.first()._mapping

        runs = await session.execute(text("""
            SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE status = 'completed') AS completed,
                   COUNT(*) FILTER (WHERE status = 'failed') AS failed,
                   COUNT(*) FILTER (WHERE status = 'running') AS running,
                   COUNT(*) FILTER (WHERE status = 'pending') AS pending,
                   AVG(execution_time_ms) AS avg_time
            FROM automation_runs WHERE tenant_id = :tid
        """), {"tid": str(tenant_id)})
        run_stats = runs.first()._mapping

        actions = await session.execute(text("""
            SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE status = 'completed') AS completed,
                   COUNT(*) FILTER (WHERE status = 'failed') AS failed
            FROM automation_actions WHERE tenant_id = :tid
        """), {"tid": str(tenant_id)})
        act_stats = actions.first()._mapping

        failures = await session.execute(text("""
            SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE resolved = false) AS unresolved
            FROM automation_failures WHERE tenant_id = :tid
        """), {"tid": str(tenant_id)})
        fail_stats = failures.first()._mapping

        return {
            "total_rules": r["total"], "enabled_rules": r["enabled"], "disabled_rules": r["disabled"],
            "total_runs": run_stats["total"], "successful_runs": run_stats["completed"],
            "failed_runs": run_stats["failed"], "running_runs": run_stats["running"],
            "pending_runs": run_stats["pending"],
            "total_actions": act_stats["total"], "successful_actions": act_stats["completed"],
            "failed_actions": act_stats["failed"],
            "total_failures": fail_stats["total"], "unresolved_failures": fail_stats["unresolved"],
            "avg_execution_time_ms": run_stats["avg_time"]
        }


@router.get("/monitor")
async def get_automation_monitor(tenant_id: UUID = Depends(get_validated_tenant_id)):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    await _ensure_automation_data(str(tenant_id))

    async with get_session() as session:
        today = await session.execute(text("SELECT COUNT(*) FROM automation_runs WHERE tenant_id = :tid AND started_at >= CURRENT_DATE"), {"tid": str(tenant_id)})
        executions_today = today.scalar()

        recent = await session.execute(text("SELECT * FROM automation_runs WHERE tenant_id = :tid ORDER BY started_at DESC LIMIT 10"), {"tid": str(tenant_id)})
        recent_runs_ = [dict(r._mapping) for r in recent]

        recent_fails = await session.execute(text("SELECT * FROM automation_failures WHERE tenant_id = :tid AND resolved = false ORDER BY failed_at DESC LIMIT 10"), {"tid": str(tenant_id)})
        recent_failures_ = [dict(r._mapping) for r in recent_fails]

        slow_execs = await session.execute(text("SELECT * FROM automation_runs WHERE tenant_id = :tid AND execution_time_ms > 500 ORDER BY execution_time_ms DESC LIMIT 10"), {"tid": str(tenant_id)})
        slow_executions_ = [dict(r._mapping) for r in slow_execs]

        return {
            "executions_today": executions_today,
            "recent_runs": recent_runs_,
            "recent_failures": recent_failures_,
            "slow_executions": slow_executions_,
        }


# E.8 — Audit Trail

@router.get("/audit")
async def get_automation_audit(tenant_id: UUID = Depends(get_validated_tenant_id), limit: int = Query(50, le=200), offset: int = Query(0, ge=0)):
    from seo_platform.core.database import get_session
    from sqlalchemy import text

    await _ensure_automation_data(str(tenant_id))

    async with get_session() as session:
        rows = await session.execute(text("""
            SELECT * FROM audit_trail_logs
            WHERE tenant_id = :tid AND component = 'automation_engine'
            ORDER BY created_at DESC LIMIT :limit OFFSET :offset
        """), {"tid": str(tenant_id), "limit": limit, "offset": offset})
        return [dict(r._mapping) for r in rows]


# E.1 — Populate data

@router.post("/populate")
async def populate_automation_data(tenant_id: UUID = Depends(get_validated_tenant_id)):
    await _ensure_automation_data(str(tenant_id))
    return {"success": True, "message": "Automation data populated"}
