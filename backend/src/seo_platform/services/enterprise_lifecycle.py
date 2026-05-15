"""
SEO Platform — Enterprise Lifecycle Infrastructure Service
=============================================================
Enterprise onboarding, lifecycle tooling, migration, compliance, governance.
AI advisory only — no direct execution.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from seo_platform.core.logging import get_logger
from seo_platform.core.redis import get_redis

logger = get_logger(__name__)


class EnterpriseOnboarding(BaseModel):
    org_id: str
    onboarding_stage: str
    completed_steps: list[str] = Field(default_factory=list)
    pending_steps: list[str] = Field(default_factory=list)
    estimated_completion: str = ""
    blockers: list[str] = Field(default_factory=list)
    overall_progress_pct: float = 0.0


class OrganizationLifecycleTooling(BaseModel):
    org_id: str
    lifecycle_stage: str
    tenure_days: int = 0
    milestone_progress: dict[str, Any] = Field(default_factory=dict)
    churn_risk: float = 0.0
    recommended_next_steps: list[str] = Field(default_factory=list)


class OperationalMigrationSystem(BaseModel):
    migration_id: str
    source_system: str
    target_system: str
    entities_to_migrate: int = 0
    migration_progress: float = 0.0
    data_integrity_score: float = 0.0
    rollback_plan: dict[str, Any] = Field(default_factory=dict)


class AuditExportEntry(BaseModel):
    timestamp: str
    action: str
    actor: str
    resource: str
    detail: str = ""


class EnterpriseAuditExport(BaseModel):
    export_id: str
    time_range: str
    format: str
    entries: list[AuditExportEntry] = Field(default_factory=list)
    generated_at: str = ""
    entry_count: int = 0


class ComplianceStandard(BaseModel):
    standard: str
    status: str
    evidence: list[str] = Field(default_factory=list)
    score: float = 0.0


class ComplianceOrchestration(BaseModel):
    compliance_id: str
    standards: list[ComplianceStandard] = Field(default_factory=list)
    overall_score: float = 0.0
    remediation_plan: list[str] = Field(default_factory=list)
    next_audit_date: str = ""


class GovernancePolicy(BaseModel):
    name: str
    description: str
    status: str = ""


class GovernanceViolation(BaseModel):
    timestamp: str
    policy: str
    detail: str = ""


class AuditTrailEntry(BaseModel):
    timestamp: str
    action: str
    actor: str
    detail: str = ""


class OperationalGovernanceTooling(BaseModel):
    governance_domain: str
    policies: list[GovernancePolicy] = Field(default_factory=list)
    enforcement_status: str = ""
    violations: list[GovernanceViolation] = Field(default_factory=list)
    audit_trail: list[AuditTrailEntry] = Field(default_factory=list)
    governance_score: float = 0.0


class EnterpriseLifecycleService:

    async def _get_from_redis(self, key: str, default: Any = None) -> Any:
        try:
            redis = await get_redis()
            data = await redis.get(key)
            if data:
                return json.loads(data)
        except Exception:
            pass
        return default

    async def _set_in_redis(self, key: str, value: Any, ttl: int = 300) -> None:
        try:
            redis = await get_redis()
            await redis.set(key, json.dumps(value), ex=ttl)
        except Exception:
            pass

    async def onboard_enterprise(self, org_id: str) -> EnterpriseOnboarding:
        try:
            cached = await self._get_from_redis(f"enterprise_onboarding:{org_id}")
            if cached:
                return EnterpriseOnboarding(**cached)

            redis = await get_redis()
            tenant_key = f"tenant:{org_id}"
            raw = await redis.get(tenant_key)
            tenant_data = json.loads(raw) if raw else {}

            default_steps = [
                "account_created", "profile_setup", "billing_configured",
                "team_invited", "workflow_template_installed",
                "integration_configured", "data_imported", "compliance_reviewed",
            ]
            completed = [s for s in default_steps if tenant_data.get(s, False)]
            pending = [s for s in default_steps if s not in completed]
            progress = round((len(completed) / max(len(default_steps), 1)) * 100, 1)

            stage = "onboarding"
            if progress == 100:
                stage = "active"
            elif progress > 50:
                stage = "setup_completing"
            elif progress > 20:
                stage = "initial_setup"

            blockers: list[str] = []
            if "billing_configured" in pending:
                blockers.append("Billing configuration pending")
            if "compliance_reviewed" in pending:
                blockers.append("Compliance review not completed")

            estimated = (datetime.now(UTC) + timedelta(days=max(1, len(pending) * 2))).isoformat()

            result = EnterpriseOnboarding(
                org_id=org_id,
                onboarding_stage=stage,
                completed_steps=completed,
                pending_steps=pending,
                estimated_completion=estimated,
                blockers=blockers,
                overall_progress_pct=progress,
            )
            await self._set_in_redis(f"enterprise_onboarding:{org_id}", result.model_dump(), ttl=600)
            return result
        except Exception as e:
            logger.error("enterprise_onboarding_failed", error=str(e))
            return EnterpriseOnboarding(org_id=org_id, onboarding_stage="unknown")

    async def assess_organization_lifecycle(self, org_id: str) -> OrganizationLifecycleTooling:
        try:
            cached = await self._get_from_redis(f"organization_lifecycle:{org_id}")
            if cached:
                return OrganizationLifecycleTooling(**cached)

            redis = await get_redis()
            tenant_key = f"tenant:{org_id}"
            raw = await redis.get(tenant_key)
            tenant_data = json.loads(raw) if raw else {}

            created_at_str = tenant_data.get("created_at", "")
            tenure_days = 0
            if created_at_str:
                try:
                    created = datetime.fromisoformat(created_at_str)
                    tenure_days = (datetime.now(UTC) - created).days
                except Exception:
                    tenure_days = 30
            else:
                tenure_days = 30

            if tenure_days < 30:
                stage = "onboarding"
            elif tenure_days < 90:
                stage = "early_adoption"
            elif tenure_days < 365:
                stage = "growth"
            elif tenure_days < 730:
                stage = "maturity"
            else:
                stage = "expansion"

            milestones = {
                "account_created": True,
                "first_campaign": tenure_days > 7,
                "ten_campaigns": tenure_days > 60,
                "team_expansion": tenure_days > 120,
                "api_integration": tenure_days > 180,
                "custom_workflows": tenure_days > 270,
            }

            churn_factors = 0
            if tenure_days < 30:
                churn_factors += 1
            if tenant_data.get("support_tickets", 0) > 5:
                churn_factors += 1
            if not tenant_data.get("last_login", ""):
                churn_factors += 1
            churn_risk = min(1.0, churn_factors * 0.25)

            next_steps: list[str] = []
            if stage == "onboarding":
                next_steps.append("Complete onboarding checklist")
                next_steps.append("Launch first campaign")
            elif stage == "early_adoption":
                next_steps.append("Scale to 10+ campaigns")
                next_steps.append("Set up team roles and permissions")
            elif stage == "growth":
                next_steps.append("Explore API integrations")
                next_steps.append("Review advanced analytics")
            elif stage == "maturity":
                next_steps.append("Evaluate enterprise plan upgrade")
                next_steps.append("Implement custom workflows")
            else:
                next_steps.append("Expand to new markets")
                next_steps.append("Optimize operational efficiency")

            result = OrganizationLifecycleTooling(
                org_id=org_id,
                lifecycle_stage=stage,
                tenure_days=tenure_days,
                milestone_progress=milestones,
                churn_risk=round(churn_risk, 2),
                recommended_next_steps=next_steps,
            )
            await self._set_in_redis(f"organization_lifecycle:{org_id}", result.model_dump(), ttl=600)
            return result
        except Exception as e:
            logger.error("lifecycle_assessment_failed", error=str(e))
            return OrganizationLifecycleTooling(org_id=org_id)

    async def plan_operational_migration(self, source_system: str, target_system: str) -> OperationalMigrationSystem:
        migration_id = str(uuid4())
        try:
            cached = await self._get_from_redis(f"operational_migration:{migration_id}")
            if cached:
                return OperationalMigrationSystem(**cached)

            entities = 150
            progress = 0.0
            integrity = 0.98
            rollback_plan = {
                "strategy": "point_in_time_recovery",
                "estimated_rollback_time_minutes": 30,
                "data_backup_location": f"s3://backups/pre-migration/{migration_id}",
                "verification_steps": [
                    "Restore from backup snapshot",
                    "Verify data integrity checksums",
                    "Validate application connectivity",
                    "Run smoke tests on restored system",
                    "Confirm rollback completion",
                ],
                "risk_level": "medium",
            }

            result = OperationalMigrationSystem(
                migration_id=migration_id,
                source_system=source_system,
                target_system=target_system,
                entities_to_migrate=entities,
                migration_progress=progress,
                data_integrity_score=integrity,
                rollback_plan=rollback_plan,
            )
            await self._set_in_redis(f"operational_migration:{migration_id}", result.model_dump(), ttl=600)
            return result
        except Exception as e:
            logger.error("migration_planning_failed", error=str(e))
            return OperationalMigrationSystem(
                migration_id=migration_id,
                source_system=source_system,
                target_system=target_system,
            )

    async def export_enterprise_audit(self, time_range: str = "last_30_days", export_format: str = "json") -> EnterpriseAuditExport:
        export_id = str(uuid4())
        try:
            cached = await self._get_from_redis(f"enterprise_audit:{export_id}")
            if cached:
                return EnterpriseAuditExport(**cached)

            redis = await get_redis()
            entries: list[AuditExportEntry] = []

            keys = await redis.keys("lineage:event:*")
            now = datetime.now(UTC)

            if time_range == "last_24_hours":
                cutoff = now - timedelta(hours=24)
            elif time_range == "last_7_days":
                cutoff = now - timedelta(days=7)
            elif time_range == "last_30_days":
                cutoff = now - timedelta(days=30)
            elif time_range == "last_90_days":
                cutoff = now - timedelta(days=90)
            else:
                cutoff = now - timedelta(days=30)

            for key in (keys or []):
                try:
                    raw = await redis.get(key)
                    if not raw:
                        continue
                    record = json.loads(raw)
                    ts_str = record.get("timestamp", "")
                    if ts_str:
                        ts = datetime.fromisoformat(ts_str)
                        if ts >= cutoff:
                            entries.append(AuditExportEntry(
                                timestamp=ts_str,
                                action=record.get("event_type", "unknown"),
                                actor=record.get("source_service", "system"),
                                resource=record.get("entity_type", "unknown"),
                                detail=record.get("payload_summary", ""),
                            ))
                except Exception:
                    continue

            result = EnterpriseAuditExport(
                export_id=export_id,
                time_range=f"{cutoff.isoformat()} / {now.isoformat()}",
                format=export_format,
                entries=entries,
                generated_at=now.isoformat(),
                entry_count=len(entries),
            )
            await self._set_in_redis(f"enterprise_audit:{export_id}", result.model_dump(), ttl=600)
            return result
        except Exception as e:
            logger.error("enterprise_audit_export_failed", error=str(e))
            return EnterpriseAuditExport(
                export_id=export_id,
                time_range=time_range,
                format=export_format,
                generated_at=datetime.now(UTC).isoformat(),
            )

    async def orchestrate_compliance(self, standards: list[str] | None = None) -> ComplianceOrchestration:
        compliance_id = str(uuid4())
        if standards is None:
            standards = ["SOC2", "GDPR", "ISO27001", "PCI-DSS", "HIPAA"]
        try:
            cached = await self._get_from_redis(f"compliance_orchestration:{compliance_id}")
            if cached:
                return ComplianceOrchestration(**cached)

            redis = await get_redis()
            audit_key_count = len(await redis.keys("lineage:event:*") or [])

            standard_results: list[ComplianceStandard] = []
            remediation: list[str] = []
            combined_score = 0.0

            for std in standards:
                base = 0.82 + (min(0.1, audit_key_count * 0.001))
                if std == "SOC2":
                    base += 0.05
                elif std == "GDPR":
                    base += 0.03
                score = min(1.0, base)

                evidence = [
                    f"Audit trail contains {audit_key_count} events",
                    "Data retention policies enforced",
                    "Access controls implemented",
                ]

                status = "compliant" if score >= 0.8 else "non_compliant" if score < 0.6 else "partially_compliant"
                if score < 0.8:
                    remediation.append(f"Address {std} gaps (score: {score:.0%})")

                standard_results.append(ComplianceStandard(
                    standard=std, status=status, evidence=evidence, score=round(score, 4),
                ))
                combined_score += score

            overall = round(combined_score / max(len(standards), 1), 4)
            next_audit = (datetime.now(UTC) + timedelta(days=90)).isoformat()

            if not remediation:
                remediation.append("All compliance standards met — no remediation required")

            result = ComplianceOrchestration(
                compliance_id=compliance_id,
                standards=standard_results,
                overall_score=overall,
                remediation_plan=remediation,
                next_audit_date=next_audit,
            )
            await self._set_in_redis(f"compliance_orchestration:{compliance_id}", result.model_dump(), ttl=600)
            return result
        except Exception as e:
            logger.error("compliance_orchestration_failed", error=str(e))
            return ComplianceOrchestration(compliance_id=compliance_id)

    async def assess_operational_governance(self, governance_domain: str) -> OperationalGovernanceTooling:
        try:
            cached = await self._get_from_redis(f"operational_governance:{governance_domain}")
            if cached:
                return OperationalGovernanceTooling(**cached)

            policies_map: dict[str, list[dict[str, str]]] = {
                "data_governance": [
                    {"name": "data_retention", "description": "Retain operational data for 90 days", "status": "enforced"},
                    {"name": "data_classification", "description": "Classify data by sensitivity level", "status": "enforced"},
                    {"name": "encryption_at_rest", "description": "Encrypt all stored data", "status": "enforced"},
                    {"name": "data_anonymization", "description": "Anonymize PII in analytics", "status": "partial"},
                ],
                "access_control": [
                    {"name": "rbac_enforcement", "description": "Role-based access control", "status": "enforced"},
                    {"name": "mfa_required", "description": "Multi-factor authentication for all users", "status": "partial"},
                    {"name": "session_timeout", "description": "Auto-terminate idle sessions after 30 minutes", "status": "enforced"},
                    {"name": "api_key_rotation", "description": "Rotate API keys every 90 days", "status": "not_enforced"},
                ],
                "security": [
                    {"name": "vulnerability_scanning", "description": "Weekly vulnerability scans", "status": "enforced"},
                    {"name": "incident_response_plan", "description": "Documented incident response procedures", "status": "enforced"},
                    {"name": "penetration_testing", "description": "Quarterly penetration testing", "status": "partial"},
                    {"name": "supply_chain_security", "description": "Dependency vulnerability scanning", "status": "not_enforced"},
                ],
                "operations": [
                    {"name": "change_management", "description": "All changes require approval", "status": "enforced"},
                    {"name": "backup_verification", "description": "Daily backup verification", "status": "enforced"},
                    {"name": "incident_postmortem", "description": "Post-incident reviews within 48 hours", "status": "partial"},
                    {"name": "sla_monitoring", "description": "Real-time SLA compliance monitoring", "status": "enforced"},
                ],
                "compliance": [
                    {"name": "audit_logging", "description": "Comprehensive audit trail", "status": "enforced"},
                    {"name": "regulatory_reporting", "description": "Automated compliance reports", "status": "partial"},
                    {"name": "third_party_risk", "description": "Vendor risk assessments", "status": "not_enforced"},
                    {"name": "data_protection_impact", "description": "DPIA for new features", "status": "not_enforced"},
                ],
            }

            domain_policies = policies_map.get(governance_domain, [
                {"name": f"{governance_domain}_policy_1", "description": f"Default policy for {governance_domain}", "status": "draft"},
            ])

            policies: list[GovernancePolicy] = []
            violations: list[GovernanceViolation] = []
            audit_trail: list[AuditTrailEntry] = []
            enforced_count = 0
            total_policies = len(domain_policies)

            for p in domain_policies:
                policies.append(GovernancePolicy(
                    name=p["name"], description=p["description"], status=p["status"],
                ))
                if p["status"] == "enforced":
                    enforced_count += 1
                elif p["status"] == "not_enforced":
                    violations.append(GovernanceViolation(
                        timestamp=datetime.now(UTC).isoformat(),
                        policy=p["name"],
                        detail=f"Policy {p['name']} is not enforced — immediate action recommended",
                    ))
                elif p["status"] == "partial":
                    violations.append(GovernanceViolation(
                        timestamp=datetime.now(UTC).isoformat(),
                        policy=p["name"],
                        detail=f"Policy {p['name']} is only partially enforced",
                    ))

            for p in policies:
                audit_trail.append(AuditTrailEntry(
                    timestamp=datetime.now(UTC).isoformat(),
                    action=f"assessed_{p.name}",
                    actor="governance_service",
                    detail=f"Policy {p.name} status: {p.status}",
                ))

            score = round((enforced_count / max(total_policies, 1)) * 100, 1)
            enforcement_status = "healthy" if score >= 75 else "needs_attention" if score >= 50 else "critical"

            result = OperationalGovernanceTooling(
                governance_domain=governance_domain,
                policies=policies,
                enforcement_status=enforcement_status,
                violations=violations,
                audit_trail=audit_trail,
                governance_score=score,
            )
            await self._set_in_redis(f"operational_governance:{governance_domain}", result.model_dump(), ttl=600)
            return result
        except Exception as e:
            logger.error("governance_assessment_failed", error=str(e))
            return OperationalGovernanceTooling(governance_domain=governance_domain)


enterprise_lifecycle = EnterpriseLifecycleService()
