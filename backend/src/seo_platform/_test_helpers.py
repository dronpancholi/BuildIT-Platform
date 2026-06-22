"""Shared test helpers: FakeSession, SimpleResult, FakeSessionContext."""

from __future__ import annotations

import uuid
import datetime


# Mapping from known SQL table names to model classes
_TABLE_MODEL_MAP: dict[str, type] = {}


def _ensure_table_map():
    """Lazy-import model classes and populate the table-name to class map."""
    if _TABLE_MODEL_MAP:
        return
    from seo_platform.models.agent import AgentDefinition as _AgentDefinition
    from seo_platform.models.goal import GoalExecution as _GoalExecution
    from seo_platform.models.goal import GoalDefinition as _GoalDefinition
    from seo_platform.models.planning import ExecutionPlan as _ExecutionPlan
    from seo_platform.models.planning import PlanNode as _PlanNode
    from seo_platform.models.planning import NodeDependency as _NodeDependency
    from seo_platform.models.planning import PlanForecast as _PlanForecast
    from seo_platform.models.audit_ledger import AuditLedgerEntry as _AuditLedgerEntry
    _TABLE_MODEL_MAP.update({
        "agent_definitions": _AgentDefinition,
        "goal_executions": _GoalExecution,
        "goal_definitions": _GoalDefinition,
        "execution_plans": _ExecutionPlan,
        "plan_nodes": _PlanNode,
        "node_dependencies": _NodeDependency,
        "plan_forecasts": _PlanForecast,
        "audit_ledger": _AuditLedgerEntry,
    })


def _entity_class_for_stmt(stmt) -> type | None:
    """Try to determine which model class a SQLAlchemy statement targets.
    Looks for `<table>.` (table-name dot) in the SQL text.
    This distinguishes the primary query table from aliased JOIN tables.
    """
    _ensure_table_map()
    stxt = str(stmt).lower()
    best_cls = None
    best_len = 0
    for table, cls in _TABLE_MODEL_MAP.items():
        if f'{table}.' in stxt and len(table) > best_len:
            best_cls = cls
            best_len = len(table)
    return best_cls


class SimpleResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return self

    def all(self):
        return list(self._items)

    def first(self):
        return self._items[0] if self._items else None


class FakeSession:
    """Reusable fake async SQLAlchemy session for integration and unit tests.

    - add() / delete() / refresh() are synchronous (matching real SQLAlchemy).
    - flush() / commit() / rollback() / execute() are awaitable.
    - flush() assigns deterministic UUIDs to objects missing an id.
    - execute() returns objects whose model class matches the SQL statement.
    """

    def __init__(self):
        self.store = {}
        self.added = []
        self.committed = False

    def add(self, instance):
        if not getattr(instance, "id", None):
            instance.id = uuid.uuid4()
        self.store[(type(instance), instance.id)] = instance
        self.added.append(instance)

    def delete(self, instance):
        key = (type(instance), instance.id)
        self.store.pop(key, None)
        if instance in self.added:
            self.added.remove(instance)

    def refresh(self, instance):
        pass

    def expire_all(self):
        pass

    async def get(self, model, obj_id):
        return self.store.get((model, obj_id))

    async def execute(self, stmt):
        entity_cls = _entity_class_for_stmt(stmt)
        if entity_cls is None:
            return SimpleResult([])
        items = [obj for (cls_, _), obj in self.store.items() if cls_ is entity_cls]
        return SimpleResult(items)

    async def flush(self):
        for (cls_, obj_id), obj in list(self.store.items()):
            if obj_id is None:
                new_id = uuid.uuid4()
                obj.id = new_id
                del self.store[(cls_, None)]
                self.store[(cls_, new_id)] = obj

    async def commit(self):
        self.committed = True

    async def rollback(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeSessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False
