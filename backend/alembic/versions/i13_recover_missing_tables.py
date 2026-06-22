"""recover_missing_core_tables

Phase 1.3.1 — Database Integrity Recovery.

Creates tables declared in the ORM that have no corresponding migration:
- action_executions
- approval_policies
- approval_requests_v2
- audit_ledger
- graph_entities
- graph_edges
- operational_memory

Also creates the PostgreSQL enum types those tables depend on:
- action_execution_status
- policy_risk_level
- approval_risk_level
- actor_type
- decision_type
- memory_entry_type
- memory_source

All DDL is idempotent (DO blocks / IF NOT EXISTS) so the migration can be
re-run safely against a partially-recovered database.

Revision ID: i13_recover_missing_tables
Revises: h8i9j0k1l2m3
Create Date: 2026-06-05
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "i13_recover_missing_tables"
down_revision: Union[str, None] = "h8i9j0k1l2m3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all missing ORM-declared tables, enum types, FKs, indexes, and RLS."""

    # ------------------------------------------------------------------
    # 1. Enum types
    # ------------------------------------------------------------------
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE action_execution_status AS ENUM (
                'pending','validated','approved','running','completed','failed','rolled_back','cancelled'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE policy_risk_level AS ENUM ('low','medium','high','critical');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE approval_risk_level AS ENUM ('low','medium','high','critical');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE actor_type AS ENUM ('user','system','agent');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE decision_type AS ENUM ('approved','rejected','auto_approved','escalated','bypassed');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE memory_entry_type AS ENUM ('decision','outcome','action','approval','failure','learning','observation');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE memory_source AS ENUM ('agent_orchestrator','planning_engine','execution_engine','approval_service','monitor');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    # ------------------------------------------------------------------
    # 2. Tables — order respects FK dependencies
    # ------------------------------------------------------------------

    # 2.1 approval_policies (no FKs to missing tables)
    op.execute("""
        CREATE TABLE IF NOT EXISTS approval_policies (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            name VARCHAR(100) NOT NULL,
            description TEXT NOT NULL,
            risk_level policy_risk_level NOT NULL,
            action_category VARCHAR(50),
            requires_chain BOOLEAN NOT NULL DEFAULT FALSE,
            chain_order JSONB,
            timeout_hours INTEGER NOT NULL DEFAULT 48,
            escalation_role VARCHAR(50),
            auto_approve_if_no_risk BOOLEAN NOT NULL DEFAULT FALSE,
            requires_justification BOOLEAN NOT NULL DEFAULT TRUE,
            min_approvers INTEGER NOT NULL DEFAULT 1,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE,
            CONSTRAINT uq_approval_policy_name UNIQUE (tenant_id, name)
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_approval_policies_tenant_id ON approval_policies(tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_approval_policy_tenant_active ON approval_policies(tenant_id, is_active);")

    # 2.2 action_executions (FK to action_definitions, no FK to approval_requests_v2 yet)
    op.execute("""
        CREATE TABLE IF NOT EXISTS action_executions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            definition_id UUID NOT NULL REFERENCES action_definitions(id) ON DELETE CASCADE,
            status action_execution_status NOT NULL DEFAULT 'pending',
            input_data JSONB NOT NULL DEFAULT '{}'::jsonb,
            output_data JSONB,
            error_message TEXT,
            started_at TIMESTAMP WITH TIME ZONE,
            completed_at TIMESTAMP WITH TIME ZONE,
            approved_by UUID REFERENCES users(id) ON DELETE SET NULL,
            approved_at TIMESTAMP WITH TIME ZONE,
            approval_request_id UUID,
            correlation_id UUID,
            parent_execution_id UUID REFERENCES action_executions(id) ON DELETE SET NULL,
            retry_count INTEGER NOT NULL DEFAULT 0,
            max_retries INTEGER NOT NULL DEFAULT 3,
            execution_order INTEGER NOT NULL DEFAULT 0,
            idempotency_key VARCHAR(255),
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_action_executions_tenant_id ON action_executions(tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_action_executions_definition_id ON action_executions(definition_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_action_exec_parent ON action_executions(parent_execution_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_action_exec_tenant_status ON action_executions(tenant_id, status);")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_action_exec_idempotency ON action_executions(tenant_id, idempotency_key) WHERE idempotency_key IS NOT NULL;")

    # 2.3 approval_requests_v2 (FK to approval_policies, action_executions, users)
    op.execute("""
        CREATE TABLE IF NOT EXISTS approval_requests_v2 (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            policy_id UUID NOT NULL REFERENCES approval_policies(id) ON DELETE CASCADE,
            execution_id UUID NOT NULL REFERENCES action_executions(id) ON DELETE CASCADE,
            requester_id UUID NOT NULL REFERENCES users(id) ON DELETE SET NULL,
            status approval_status NOT NULL DEFAULT 'pending',
            risk_level approval_risk_level NOT NULL,
            action_summary TEXT NOT NULL,
            input_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
            current_approver_role VARCHAR(50),
            approval_chain JSONB,
            approval_history JSONB,
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            escalated_at TIMESTAMP WITH TIME ZONE,
            final_decision_at TIMESTAMP WITH TIME ZONE,
            final_comment TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_approval_requests_v2_tenant_id ON approval_requests_v2(tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_approval_requests_v2_policy_id ON approval_requests_v2(policy_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_approval_requests_v2_execution_id ON approval_requests_v2(execution_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_approval_requests_v2_requester_id ON approval_requests_v2(requester_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_approval_req_tenant_status_created ON approval_requests_v2(tenant_id, status, created_at);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_approval_req_tenant_current_approver ON approval_requests_v2(tenant_id, current_approver_role, status);")

    # 2.4 Now add the deferred FK from action_executions to approval_requests_v2
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = 'fk_action_executions_approval_request'
                  AND table_name = 'action_executions'
            ) THEN
                ALTER TABLE action_executions
                    ADD CONSTRAINT fk_action_executions_approval_request
                    FOREIGN KEY (approval_request_id)
                    REFERENCES approval_requests_v2(id) ON DELETE SET NULL;
            END IF;
        END $$;
    """)

    # 2.5 audit_ledger
    op.execute("""
        CREATE TABLE IF NOT EXISTS audit_ledger (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            action_name VARCHAR(100) NOT NULL,
            action_execution_id UUID REFERENCES action_executions(id) ON DELETE SET NULL,
            actor_id UUID NOT NULL,
            actor_type actor_type NOT NULL,
            target_type VARCHAR(100) NOT NULL,
            target_id UUID NOT NULL,
            summary TEXT NOT NULL,
            input_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
            output_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
            approval_id UUID REFERENCES approval_requests_v2(id) ON DELETE SET NULL,
            decision decision_type,
            risk_level VARCHAR(20) NOT NULL,
            ip_address VARCHAR(45),
            user_agent VARCHAR(255),
            semantic_hash VARCHAR(64) NOT NULL DEFAULT '0',
            rollback_id UUID REFERENCES action_executions(id) ON DELETE SET NULL,
            immutable_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_ledger_tenant_id ON audit_ledger(tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_ledger_actor_id ON audit_ledger(actor_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_ledger_target_id ON audit_ledger(target_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_ledger_action_name ON audit_ledger(action_name);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_ledger_target_type ON audit_ledger(target_type);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_ledger_action_execution_id ON audit_ledger(action_execution_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_ledger_target ON audit_ledger(target_type, target_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_ledger_actor_created_at ON audit_ledger(actor_id, created_at);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_ledger_action_created_at ON audit_ledger(action_name, created_at);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_ledger_tenant_created_at ON audit_ledger(tenant_id, created_at);")

    # 2.6 operational_memory
    op.execute("""
        CREATE TABLE IF NOT EXISTS operational_memory (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            entry_type memory_entry_type NOT NULL,
            source memory_source NOT NULL,
            source_execution_id UUID REFERENCES action_executions(id) ON DELETE SET NULL,
            summary TEXT NOT NULL,
            detail JSONB NOT NULL DEFAULT '{}'::jsonb,
            tags VARCHAR[],
            confidence FLOAT,
            impact_score FLOAT,
            related_entry_ids UUID[],
            embedding FLOAT[],
            expires_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_operational_memory_tenant_id ON operational_memory(tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_memory_tenant_created ON operational_memory(tenant_id, created_at);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_memory_tenant_entry_type_created ON operational_memory(tenant_id, entry_type, created_at);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_memory_tenant_source_created ON operational_memory(tenant_id, source, created_at);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_memory_tenant_tags ON operational_memory USING gin (tenant_id, tags);")

    # 2.7 graph_entities (no FKs)
    op.execute("""
        CREATE TABLE IF NOT EXISTS graph_entities (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            entity_type VARCHAR(50) NOT NULL,
            entity_id VARCHAR(255) NOT NULL,
            label VARCHAR(255) NOT NULL,
            description TEXT,
            custom_metadata JSON,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_graph_entities_type_id UNIQUE (entity_type, entity_id)
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_graph_entities_tenant_id ON graph_entities(tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_graph_entities_entity_type ON graph_entities(entity_type);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_graph_entities_tenant_type ON graph_entities(tenant_id, entity_type);")

    # 2.8 graph_edges (FK to graph_entities)
    op.execute("""
        CREATE TABLE IF NOT EXISTS graph_edges (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            source_entity_id UUID NOT NULL REFERENCES graph_entities(id) ON DELETE CASCADE,
            target_entity_id UUID NOT NULL REFERENCES graph_entities(id) ON DELETE CASCADE,
            relationship_type VARCHAR(50) NOT NULL,
            weight FLOAT NOT NULL,
            custom_metadata JSON,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_graph_edges_tenant_id ON graph_edges(tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_graph_edges_relationship_type ON graph_edges(relationship_type);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_graph_edges_source ON graph_edges(source_entity_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_graph_edges_target ON graph_edges(target_entity_id);")

    # ------------------------------------------------------------------
    # 3. Row Level Security (idempotent)
    # ------------------------------------------------------------------
    new_tables = [
        "action_executions",
        "approval_policies",
        "approval_requests_v2",
        "audit_ledger",
        "operational_memory",
        "graph_entities",
        "graph_edges",
    ]
    for tbl in new_tables:
        op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {tbl} FORCE ROW LEVEL SECURITY;")
        op.execute(f"DROP POLICY IF EXISTS {tbl}_tenant_isolation ON {tbl};")
        op.execute(
            f"CREATE POLICY {tbl}_tenant_isolation ON {tbl} FOR ALL "
            f"USING (tenant_id = current_setting('app.current_tenant')::uuid) "
            f"WITH CHECK (tenant_id = current_setting('app.current_tenant')::uuid);"
        )


def downgrade() -> None:
    """Drop all recovered tables and enum types in reverse order."""
    tables = [
        "graph_edges",
        "graph_entities",
        "operational_memory",
        "audit_ledger",
        "approval_requests_v2",
        "approval_policies",
        "action_executions",
    ]
    for tbl in tables:
        op.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE;")

    op.execute("DROP TYPE IF EXISTS memory_source;")
    op.execute("DROP TYPE IF EXISTS memory_entry_type;")
    op.execute("DROP TYPE IF EXISTS decision_type;")
    op.execute("DROP TYPE IF EXISTS actor_type;")
    op.execute("DROP TYPE IF EXISTS approval_risk_level;")
    op.execute("DROP TYPE IF EXISTS policy_risk_level;")
    op.execute("DROP TYPE IF EXISTS action_execution_status;")
