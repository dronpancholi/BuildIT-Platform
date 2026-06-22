'''Planning engine ORM models.

'''
from __future__ import annotations

import enum, uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from seo_platform.core.database import Base
from seo_platform.models.base import TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin

class ExecutionPlan(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = 'execution_plans'
    __table_args__ = (
        Index('ix_execution_plans_tenant_status', 'tenant_id', 'status'),
    )
    goal_execution_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('goal_executions.id', ondelete='CASCADE'), nullable=False, index=True)
    class PlanStatus(str, enum.Enum):
        GENERATED = 'generated'
        SIMULATED = 'simulated'
        APPROVED = 'approved'
        REJECTED = 'rejected'
        EXECUTING = 'executing'
        COMPLETED = 'completed'
        FAILED = 'failed'
    status: Mapped[PlanStatus] = mapped_column(Enum(PlanStatus, name='plan_status', create_constraint=True, values_callable=lambda x: [e.value for e in x]), nullable=False, default=PlanStatus.GENERATED)
    plan_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    generated_by: Mapped[str] = mapped_column(String(50), nullable=False)
    plan_graph: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    simulation_result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False)
    estimated_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    @property
    def risk_score(self) -> float | None:
        """Risk score stored in ``metadata_json`` if present."""
        return self.metadata_json.get("risk_score") if isinstance(self.metadata_json, dict) else None

    @risk_score.setter
    def risk_score(self, value: float | None) -> None:
        self.metadata_json = self.metadata_json or {}
        self.metadata_json["risk_score"] = value

    @property
    def confidence_score(self) -> float | None:
        """Confidence score stored in ``metadata_json`` if present."""
        return self.metadata_json.get("confidence_score") if isinstance(self.metadata_json, dict) else None

    @confidence_score.setter
    def confidence_score(self, value: float | None) -> None:
        self.metadata_json = self.metadata_json or {}
        self.metadata_json["confidence_score"] = value
    nodes: Mapped[list['PlanNode']] = relationship('PlanNode', back_populates='plan', cascade='all, delete-orphan', lazy='selectin')
    forecasts: Mapped[list['PlanForecast']] = relationship('PlanForecast', back_populates='plan', cascade='all, delete-orphan', lazy='selectin')
    def __repr__(self) -> str:
        return f'<ExecutionPlan {self.id} status={self.status}>'

class PlanNode(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = 'plan_nodes'
    __table_args__ = (
        Index('ix_plan_nodes_tenant_status', 'tenant_id', 'status'),
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('execution_plans.id', ondelete='CASCADE'), nullable=False, index=True)
    node_type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_agent: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    action_definition_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('action_definitions.id', ondelete='SET NULL'), nullable=True)
    class NodeStatus(str, enum.Enum):
        PENDING = 'pending'
        SCHEDULED = 'scheduled'
        RUNNING = 'running'
        COMPLETED = 'completed'
        FAILED = 'failed'
        SKIPPED = 'skipped'
    status: Mapped[NodeStatus] = mapped_column(Enum(NodeStatus, name='plan_node_status', create_constraint=True, values_callable=lambda x: [e.value for e in x]), nullable=False, default=NodeStatus.PENDING)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dependency_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    plan: Mapped[ExecutionPlan] = relationship('ExecutionPlan', back_populates='nodes', lazy='joined')
    def __repr__(self) -> str:
        return f'<PlanNode {self.id} type={self.node_type} status={self.status}>'

class NodeDependency(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = 'node_dependencies'
    __table_args__ = (
        Index('ix_node_dependencies_source_target', 'source_node_id', 'target_node_id'),
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('execution_plans.id', ondelete='CASCADE'), nullable=False, index=True)
    source_node_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('plan_nodes.id', ondelete='CASCADE'), nullable=False)
    target_node_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('plan_nodes.id', ondelete='CASCADE'), nullable=False)
    dependency_type: Mapped[str] = mapped_column(String(30), nullable=False)
    def __repr__(self) -> str:
        return f'<NodeDependency {self.id} type={self.dependency_type}>'

class PlanForecast(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = 'plan_forecasts'
    __table_args__: tuple = ()
    plan_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('execution_plans.id', ondelete='CASCADE'), nullable=False, index=True)
    completion_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_projection: Mapped[float | None] = mapped_column(Float, nullable=True)
    execution_projection: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    bottleneck_prediction: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    plan: Mapped[ExecutionPlan] = relationship('ExecutionPlan', back_populates='forecasts', lazy='joined')
    def __repr__(self) -> str:
        return f'<PlanForecast {self.id} prob={self.completion_probability}>'
