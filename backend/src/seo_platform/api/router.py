"""
SEO Platform — API Router Registry
=====================================
Central router aggregating all service endpoint groups.
"""

from __future__ import annotations

from fastapi import APIRouter

from seo_platform.api.endpoints.advanced_analytics import router as advanced_analytics_router
from seo_platform.api.endpoints.ai_ops import router as ai_ops_router
from seo_platform.api.endpoints.ai_quality import router as ai_quality_router
from seo_platform.api.endpoints.ai_resilience import router as ai_resilience_router
from seo_platform.api.endpoints.scraping_scaling import router as scraping_scaling_router
from seo_platform.api.endpoints.communication_reliability import router as communication_reliability_router
from seo_platform.api.endpoints.approvals import router as approvals_router
from seo_platform.api.endpoints.event_lineage import router as event_lineage_router
from seo_platform.api.endpoints.backlink_intelligence import router as backlink_intelligence_router
from seo_platform.api.endpoints.campaigns import router as campaigns_router
from seo_platform.api.endpoints.outreach_intelligence import router as outreach_intelligence_router
from seo_platform.api.endpoints.prospect_graph import router as prospect_graph_router
from seo_platform.api.endpoints.prospects import router as prospects_router  # Phase 1.5: root-level /prospects for prospect-list page
# from seo_platform.api.endpoints.citations import router as citations_router  # OLD: uses phantom columns
from seo_platform.api.endpoints.citation_projects import router as citation_projects_router
from seo_platform.api.endpoints.citation_sites import router as citation_sites_router
from seo_platform.api.endpoints.citation_submissions import router as citation_submissions_router
from seo_platform.api.endpoints.citation_export import router as citation_export_router
from seo_platform.api.endpoints.clients import router as clients_router
from seo_platform.api.endpoints.health import router as health_router
from seo_platform.api.endpoints.infrastructure_intelligence import router as infrastructure_intelligence_router
from seo_platform.api.endpoints.intelligence import router as intelligence_router
from seo_platform.api.endpoints.keywords import router as keywords_router
from seo_platform.api.endpoints.plans import router as plans_router
from seo_platform.api.endpoints.kill_switches import router as kill_switches_router
from seo_platform.api.endpoints.observability import router as observability_router
from seo_platform.api.endpoints.realtime.events import router as realtime_router
from seo_platform.api.endpoints.realtime.operational import router as operational_realtime_router
from seo_platform.api.endpoints.realtime.sse import router as sse_router
from seo_platform.api.endpoints.reports import router as reports_router
from seo_platform.api.endpoints.scale import router as scale_router
from seo_platform.api.endpoints.seo_intelligence import keyword_intelligence_router
from seo_platform.api.endpoints.seo_intelligence import router as seo_intelligence_router
from seo_platform.api.endpoints.serp_intelligence import router as serp_intelligence_router
from seo_platform.api.endpoints.tenants import router as tenants_router
from seo_platform.api.endpoints.identity import router as identity_router
from seo_platform.api.endpoints.local_seo import router as local_seo_router
from seo_platform.api.endpoints.recommendations import router as recommendations_router
from seo_platform.api.endpoints.semantic_memory import router as semantic_memory_router
from seo_platform.api.endpoints.event_infrastructure import router as event_infrastructure_router
from seo_platform.api.endpoints.sre_observability import router as sre_observability_router
from seo_platform.api.endpoints.workflow_status import router as workflow_status_router
from seo_platform.api.endpoints.workflow_resilience import router as workflow_resilience_router
from seo_platform.api.endpoints.distributed_hardening import router as distributed_hardening_router
from seo_platform.api.endpoints.overload_protection import router as overload_protection_router
from seo_platform.api.endpoints.deployment import router as deployment_router
from seo_platform.api.endpoints.complexity_management import router as complexity_management_router
from seo_platform.api.endpoints.seo_strategic import router as seo_strategic_router
from seo_platform.api.endpoints.backlink_acquisition import router as backlink_acquisition_router
from seo_platform.api.endpoints.infrastructure_self_analysis import router as infrastructure_self_analysis_router
from seo_platform.api.endpoints.anomaly_prediction import router as anomaly_prediction_router
from seo_platform.api.endpoints.operational_assistant import router as operational_assistant_router
from seo_platform.api.endpoints.predictive_intelligence import router as predictive_intelligence_router
from seo_platform.api.endpoints.adaptive_optimization import router as adaptive_optimization_router
from seo_platform.api.endpoints.enterprise_cognition import router as enterprise_cognition_router
from seo_platform.api.endpoints.orchestration_intelligence import router as orchestration_intelligence_router
from seo_platform.api.endpoints.autonomy_orchestrator import router as autonomy_orchestrator_router
from seo_platform.api.endpoints.agents import router as agents_router
from seo_platform.api.endpoints.goals import router as goals_router
from seo_platform.api.endpoints.strategic_growth import router as strategic_growth_router
from seo_platform.api.endpoints.governance_service import router as governance_service_router
from seo_platform.api.endpoints.maintainability_service import router as maintainability_service_router
from seo_platform.api.endpoints.incident_response import router as incident_response_router
from seo_platform.api.endpoints.incident_intelligence import router as incident_intelligence_router
from seo_platform.api.endpoints.infrastructure_economics import router as infrastructure_economics_router
from seo_platform.api.endpoints.scraping_resilience import router as scraping_resilience_router
from seo_platform.api.endpoints.enterprise_lifecycle import router as enterprise_lifecycle_router
from seo_platform.api.endpoints.advanced_sre import router as advanced_sre_router
from seo_platform.api.endpoints.global_infrastructure import router as global_infrastructure_router
from seo_platform.api.endpoints.global_orchestration import router as global_orchestration_router
from seo_platform.api.endpoints.enterprise_ecosystem import router as enterprise_ecosystem_router
from seo_platform.api.endpoints.cross_tenant_intelligence import router as cross_tenant_intelligence_router
from seo_platform.api.endpoints.autonomous_coordination import router as autonomous_coordination_router
from seo_platform.api.endpoints.strategic_seo_cognition import router as strategic_seo_cognition_router
from seo_platform.api.endpoints.operational_lifecycle import router as operational_lifecycle_router
from seo_platform.api.endpoints.maintainability_dominance import router as maintainability_dominance_router
from seo_platform.api.endpoints.operational_evolution import router as operational_evolution_router
from seo_platform.api.endpoints.production_economics import router as production_economics_router
from seo_platform.api.endpoints.organizational_intelligence import router as organizational_intelligence_router
from seo_platform.api.endpoints.extreme_scale_orchestration import router as extreme_scale_orchestration_router
from seo_platform.api.endpoints.operations_feed import router as operations_feed_router
from seo_platform.api.endpoints.incident_evolution import router as incident_evolution_router
from seo_platform.api.endpoints.ecosystem_maturity import router as ecosystem_maturity_router
from seo_platform.api.endpoints.platform_stewardship import router as platform_stewardship_router
from seo_platform.api.endpoints.realtime_telemetry import router as realtime_telemetry_router
from seo_platform.api.endpoints.business_intelligence import router as business_intelligence_router
from seo_platform.api.endpoints.intelligence_queries import router as intelligence_queries_router
from seo_platform.api.endpoints.providers import router as providers_router
from seo_platform.api.endpoints.providers_unified import router as providers_unified_router
from seo_platform.api.endpoints.webhooks import router as webhooks_router
from seo_platform.api.endpoints.inbound_webhooks import router as inbound_webhooks_router
from seo_platform.api.endpoints.provider_health import router as provider_health_router
from seo_platform.api.endpoints.demo_scenarios import router as demo_scenarios_router
from seo_platform.api.endpoints.campaign_timeline import router as campaign_timeline_router
from seo_platform.api.endpoints.search import router as search_router
from seo_platform.api.endpoints.link_verification import router as link_verification_router
from seo_platform.api.endpoints.seo_tasks import router as seo_tasks_router
from seo_platform.api.endpoints.recovery import router as recovery_router
from seo_platform.api.endpoints.action_center import router as action_center_router

# Root API router — all service routers mount here
api_router = APIRouter(prefix="/api/v1")

api_router.include_router(advanced_analytics_router, prefix="/analytics", tags=["advanced-analytics"])
api_router.include_router(ai_ops_router, prefix="/ai-ops", tags=["ai-ops"])
api_router.include_router(ai_quality_router, prefix="/ai-quality", tags=["ai-quality"])
api_router.include_router(ai_resilience_router, prefix="/ai-resilience", tags=["ai-resilience"])
api_router.include_router(scraping_scaling_router, prefix="/scraping", tags=["scraping-scaling"])
api_router.include_router(communication_reliability_router, prefix="/communication-reliability", tags=["communication-reliability"])
api_router.include_router(health_router, tags=["health"])
api_router.include_router(scale_router, prefix="/scale", tags=["scale"])
api_router.include_router(tenants_router, prefix="/tenants", tags=["tenants"])
api_router.include_router(identity_router, prefix="/identity", tags=["identity"])
api_router.include_router(clients_router, prefix="/clients", tags=["clients"])
api_router.include_router(campaigns_router, prefix="/campaigns", tags=["campaigns"])
api_router.include_router(approvals_router, prefix="/approvals", tags=["approvals"])
api_router.include_router(plans_router, prefix="/plans", tags=["plans"])
api_router.include_router(keywords_router, prefix="/keywords", tags=["keywords"])
api_router.include_router(kill_switches_router, prefix="/kill-switches", tags=["kill-switches"])
api_router.include_router(reports_router, prefix="/citations", tags=["citation-reports"])
# api_router.include_router(citations_router, prefix="/citations", tags=["citations"])  # OLD: uses phantom columns
api_router.include_router(citation_projects_router, prefix="/citations", tags=["citation-projects"])
api_router.include_router(citation_sites_router, prefix="/citations/sites", tags=["citation-sites"])
api_router.include_router(citation_submissions_router, prefix="/citations", tags=["citation-submissions"])
api_router.include_router(citation_export_router, prefix="/citations", tags=["citation-export"])

# Phase 2: Citation automation (browser-based form filling)
from seo_platform.api.endpoints.citation_automation import router as citation_automation_router
api_router.include_router(citation_automation_router, prefix="/citations/automation", tags=["citation-automation"])

# Phase 3: Email verification automation
from seo_platform.api.endpoints.citation_verification import router as citation_verification_router
api_router.include_router(citation_verification_router, prefix="/citations/verification", tags=["citation-verification"])

# Phase 4: Credential Vault
from seo_platform.api.endpoints.credentials import router as credentials_router
api_router.include_router(credentials_router, prefix="/credentials", tags=["credential-vault"])

# Phase 5: Rate Limiting + Proxy Rotation
from seo_platform.api.endpoints.proxies import router as proxies_router
api_router.include_router(proxies_router, prefix="/proxies", tags=["proxy-pool"])

# Phase 7: Smart Site Recommendations
from seo_platform.api.endpoints.recommendations import router as recommendations_router
api_router.include_router(recommendations_router, prefix="/citations", tags=["recommendations"])

api_router.include_router(infrastructure_intelligence_router, prefix="/infrastructure", tags=["infrastructure"])
api_router.include_router(intelligence_router, prefix="/intelligence", tags=["intelligence"])
api_router.include_router(observability_router, prefix="/observability", tags=["observability"])
api_router.include_router(seo_intelligence_router, prefix="/seo-intelligence", tags=["seo-intelligence"])
api_router.include_router(keyword_intelligence_router, prefix="/seo-intelligence", tags=["keyword-intelligence"])
api_router.include_router(serp_intelligence_router, prefix="/serp-intelligence", tags=["serp-intelligence"])
api_router.include_router(intelligence_queries_router, prefix="/intelligence-queries", tags=["intelligence-queries"])
api_router.include_router(backlink_intelligence_router, prefix="/backlink-intelligence", tags=["backlink-intelligence"])
api_router.include_router(outreach_intelligence_router, prefix="/outreach-intelligence", tags=["outreach-intelligence"])
api_router.include_router(prospect_graph_router, prefix="/prospect-graph", tags=["prospect-graph"])
api_router.include_router(prospects_router, tags=["prospects"])  # Phase 1.5: /prospects, /prospects/stats (root level)
api_router.include_router(event_lineage_router, tags=["event-lineage"])
api_router.include_router(realtime_router, prefix="/realtime", tags=["realtime"])
api_router.include_router(operational_realtime_router, prefix="/realtime", tags=["realtime"])
api_router.include_router(sse_router, tags=["sse"])
api_router.include_router(local_seo_router, prefix="/local-seo", tags=["local-seo"])
api_router.include_router(recommendations_router, prefix="/recommendations", tags=["recommendations"])
api_router.include_router(semantic_memory_router, prefix="/semantic-memory", tags=["semantic-memory"])
api_router.include_router(event_infrastructure_router, tags=["event-infrastructure"])
api_router.include_router(sre_observability_router, tags=["sre-observability"])
api_router.include_router(workflow_status_router, prefix="/workflow", tags=["workflow-status"])
api_router.include_router(workflow_resilience_router, prefix="/workflow-resilience", tags=["workflow-resilience"])
api_router.include_router(distributed_hardening_router, prefix="/distributed", tags=["distributed-hardening"])
api_router.include_router(overload_protection_router, prefix="/overload", tags=["overload-protection"])
api_router.include_router(deployment_router, prefix="/deployment", tags=["deployment"])
api_router.include_router(complexity_management_router, prefix="/ops", tags=["complexity-management"])
api_router.include_router(seo_strategic_router, prefix="/seo-strategic", tags=["seo-strategic"])
api_router.include_router(backlink_acquisition_router, prefix="/backlink-acquisition", tags=["backlink-acquisition"])
api_router.include_router(infrastructure_self_analysis_router, tags=["infrastructure-self-analysis"])
api_router.include_router(anomaly_prediction_router, tags=["anomaly-prediction"])
api_router.include_router(operational_assistant_router, prefix="/operational-assistant", tags=["operational-assistant"])
api_router.include_router(predictive_intelligence_router, prefix="/predictive", tags=["predictive-intelligence"])
api_router.include_router(adaptive_optimization_router, prefix="/adaptive-optimization", tags=["adaptive-optimization"])
api_router.include_router(enterprise_cognition_router, prefix="/enterprise-cognition", tags=["enterprise-cognition"])
api_router.include_router(orchestration_intelligence_router, prefix="/orchestration-intelligence", tags=["orchestration-intelligence"])
api_router.include_router(autonomy_orchestrator_router, prefix="/autonomy", tags=["autonomy"])
api_router.include_router(agents_router, prefix="/autonomous-agents", tags=["autonomous-agents"])
api_router.include_router(goals_router, prefix="/goals", tags=["goals"])
api_router.include_router(strategic_growth_router, prefix="/strategic-growth", tags=["strategic-growth"])
api_router.include_router(governance_service_router, prefix="/governance", tags=["governance"])
api_router.include_router(maintainability_service_router, prefix="/maintainability", tags=["maintainability"])
api_router.include_router(infrastructure_economics_router, prefix="/infra-economics", tags=["infrastructure-economics"])
api_router.include_router(scraping_resilience_router, prefix="/scraping-resilience", tags=["scraping-resilience"])
api_router.include_router(incident_response_router, prefix="/incident", tags=["incident-response"])
api_router.include_router(incident_intelligence_router, prefix="/incident-intelligence", tags=["incident-intelligence"])
api_router.include_router(enterprise_lifecycle_router, prefix="/enterprise-lifecycle", tags=["enterprise-lifecycle"])
api_router.include_router(advanced_sre_router, prefix="/advanced-sre", tags=["advanced-sre"])
api_router.include_router(global_infrastructure_router, prefix="/global-infra", tags=["global-infrastructure"])
api_router.include_router(global_orchestration_router, prefix="/global-orchestration", tags=["global-orchestration"])
api_router.include_router(enterprise_ecosystem_router, prefix="/enterprise-ecosystem", tags=["enterprise-ecosystem"])
api_router.include_router(cross_tenant_intelligence_router, prefix="/cross-tenant", tags=["cross-tenant"])
api_router.include_router(autonomous_coordination_router, prefix="/autonomous-coordination", tags=["autonomous-coordination"])
api_router.include_router(strategic_seo_cognition_router, prefix="/strategic-seo", tags=["strategic-seo-cognition"])
api_router.include_router(operational_lifecycle_router, prefix="/operational-lifecycle", tags=["operational-lifecycle"])
api_router.include_router(maintainability_dominance_router, prefix="/maintainability-dominance", tags=["maintainability-dominance"])
api_router.include_router(operational_evolution_router, prefix="/operational-evolution", tags=["operational-evolution"])
api_router.include_router(production_economics_router, prefix="/production-economics", tags=["production-economics"])
api_router.include_router(organizational_intelligence_router, prefix="/organizational-intelligence", tags=["organizational-intelligence"])
api_router.include_router(extreme_scale_orchestration_router, prefix="/extreme-scale-orchestration", tags=["extreme-scale-orchestration"])
api_router.include_router(incident_evolution_router, prefix="/incident-evolution", tags=["incident-evolution"])
api_router.include_router(ecosystem_maturity_router, prefix="/ecosystem-maturity", tags=["ecosystem-maturity"])
api_router.include_router(platform_stewardship_router, prefix="/platform-stewardship", tags=["platform-stewardship"])
api_router.include_router(realtime_telemetry_router, prefix="/queue-telemetry", tags=["realtime-telemetry"])
api_router.include_router(operations_feed_router, prefix="/operations", tags=["operations-feed"])
api_router.include_router(business_intelligence_router, prefix="/business-intelligence", tags=["business-intelligence"])
api_router.include_router(provider_health_router, tags=["provider-health"])
api_router.include_router(demo_scenarios_router, tags=["demo-scenarios"])
api_router.include_router(campaign_timeline_router, tags=["campaign-timeline"])
api_router.include_router(search_router, prefix="/search", tags=["search"])
api_router.include_router(providers_router, prefix="/providers")
api_router.include_router(providers_unified_router, prefix="/providers", tags=["providers-unified"])
api_router.include_router(webhooks_router)

# Workstream E: Link verification endpoints
api_router.include_router(
    link_verification_router,
    prefix="/link-verification",
    tags=["link-verification"],
)
api_router.include_router(seo_tasks_router, prefix="/tasks", tags=["seo-tasks"])
api_router.include_router(inbound_webhooks_router)

# Phase 12B Communication Studio routers
from seo_platform.api.endpoints.communication_templates import router as communication_templates_router
from seo_platform.api.endpoints.email_scheduling import router as email_scheduling_router
from seo_platform.api.endpoints.email_drafts import router as email_drafts_router
from seo_platform.api.endpoints.email_attachments import router as email_attachments_router

api_router.include_router(communication_templates_router, prefix="/communication-templates", tags=["communication-templates"])
api_router.include_router(email_scheduling_router, prefix="/email-scheduling", tags=["email-scheduling"])
api_router.include_router(email_drafts_router, prefix="/email-drafts", tags=["email-drafts"])
api_router.include_router(email_attachments_router, prefix="/attachments", tags=["email-attachments"])

# Phase 12C Campaign Portfolio routers
from seo_platform.api.endpoints.campaign_portfolio import router as campaign_portfolio_router

api_router.include_router(campaign_portfolio_router, prefix="/portfolio", tags=["campaign-portfolio"])

# Phase 12D Executive Control Center routers
from seo_platform.api.endpoints.executive import router as executive_router

api_router.include_router(executive_router, prefix="/executive", tags=["executive"])

# Phase 12E Automation Engine routers
from seo_platform.api.endpoints.automation import router as automation_router

api_router.include_router(automation_router, prefix="/automation", tags=["automation"])

# Phase 12F Unified Customer Workspace
from seo_platform.api.endpoints.customers import router as customers_router

api_router.include_router(customers_router, prefix="/customers", tags=["customers"])

# Phase 12F.10 Global Search for CMD+K Command Bar
from seo_platform.api.endpoints.search_global import router as search_global_router

api_router.include_router(search_global_router, tags=["search-global"])

# Phase 12G.2 Alerting System
from seo_platform.api.endpoints.alerting import router as alerting_router

api_router.include_router(alerting_router, prefix="/alerts", tags=["alerting"])

# Phase 13.1 Knowledge Graph
from seo_platform.api.endpoints.knowledge import router as knowledge_router

api_router.include_router(knowledge_router, prefix="/knowledge", tags=["knowledge"])

# Phase 13.2 Semantic Search
from seo_platform.api.endpoints.semantic import router as semantic_router

api_router.include_router(semantic_router, prefix="/semantic", tags=["semantic"])

# Phase 13.3 Natural Language Query Engine
from seo_platform.api.endpoints.ai_query import router as ai_query_router

api_router.include_router(ai_query_router, prefix="/ai", tags=["ai-query"])

# Phase 13.4 Forecasting Platform
from seo_platform.api.endpoints.forecasting import router as forecasting_router

api_router.include_router(forecasting_router, prefix="/forecast", tags=["forecast"])

# Phase 13.5 AI Recommendation Engine
from seo_platform.api.endpoints.ai_recommendations import router as ai_recommendations_router

api_router.include_router(ai_recommendations_router, prefix="/recommendations", tags=["recommendations"])

# Phase 13.6 Autonomous Campaign Agent
from seo_platform.api.endpoints.campaign_agent import router as campaign_agent_router

api_router.include_router(campaign_agent_router, prefix="/agents", tags=["agents"])

# Phase 13.7 Executive Copilot
from seo_platform.api.endpoints.copilot import router as copilot_router

api_router.include_router(copilot_router, prefix="/ai/copilot", tags=["copilot"])

# Phase 14 - Action Registry
from seo_platform.api.endpoints.action_registry import router as action_registry_router
api_router.include_router(action_registry_router, prefix="/actions", tags=["actions"])

# Phase 14 - Execution Engine
from seo_platform.api.endpoints.execution import router as execution_router
api_router.include_router(execution_router, prefix="/executions", tags=["executions"])

# Recovery — failure recovery interface
api_router.include_router(recovery_router, prefix="/recovery", tags=["recovery"])

# Phase 14 - Approvals (v2)
from seo_platform.api.endpoints.approvals_v2 import router as approvals_v2_router
api_router.include_router(approvals_v2_router, prefix="/approvals/v2", tags=["approvals-v2"])



# Phase 2 Final — Audit Ledger (exposed as /audit/ledger)
from seo_platform.api.endpoints.audit_ledger import router as audit_ledger_router
api_router.include_router(audit_ledger_router, prefix="/audit", tags=["audit"])

# Phase 11.5 — Operational Infrastructure
from seo_platform.api.endpoints.temporal_ops import router as temporal_ops_router
from seo_platform.api.endpoints.system_health import router as system_health_router
from seo_platform.api.endpoints.provider_management import router as provider_management_router

api_router.include_router(temporal_ops_router, tags=["temporal-ops"])
api_router.include_router(system_health_router, tags=["system-health"])
api_router.include_router(provider_management_router, tags=["provider-management"])

# Phase 12 — SEO Capability Engine
from seo_platform.api.endpoints.competitor_intelligence import router as competitor_intelligence_router
from seo_platform.api.endpoints.keyword_priority import router as keyword_priority_router
from seo_platform.api.endpoints.copilot_v2 import router as copilot_v2_router
from seo_platform.api.endpoints.seo_health import router as seo_health_router
from seo_platform.api.endpoints.outreach_quality import router as outreach_quality_router

api_router.include_router(competitor_intelligence_router, prefix="/competitor-intelligence", tags=["competitor-intelligence"])
api_router.include_router(keyword_priority_router, prefix="/keyword-priority", tags=["keyword-priority"])
api_router.include_router(copilot_v2_router, prefix="/copilot-v2", tags=["copilot-v2"])
api_router.include_router(seo_health_router, prefix="/seo-health", tags=["seo-health"])
api_router.include_router(outreach_quality_router, prefix="/outreach-quality", tags=["outreach-quality"])

# Phase 12F/G/H — Local SEO, Citation Intelligence, Recommendation Engine V2
from seo_platform.api.endpoints.citation_intelligence import router as citation_intelligence_router
from seo_platform.api.endpoints.recommendations_v2 import router as recommendations_v2_router

api_router.include_router(citation_intelligence_router, prefix="/citation-intelligence", tags=["citation-intelligence"])
api_router.include_router(recommendations_v2_router, prefix="/recommendations-v2", tags=["recommendations-v2"])

# Action Center V2 — unified "What needs attention?" view
api_router.include_router(action_center_router, prefix="/action-center", tags=["action-center"])

# Campaign Operations Engine — single-page unified campaign view
from seo_platform.api.endpoints.campaign_operations import router as campaign_operations_router
api_router.include_router(campaign_operations_router, prefix="/campaign-operations", tags=["campaign-operations"])

# Outreach Operations Engine
from seo_platform.api.endpoints.outreach_operations import router as outreach_operations_router
api_router.include_router(outreach_operations_router, prefix="/outreach-operations", tags=["outreach-operations"])

# Citation Operations Engine
from seo_platform.api.endpoints.citation_operations import router as citation_operations_router
api_router.include_router(citation_operations_router, prefix="/citation-operations", tags=["citation-operations"])

# Approval Workflow Engine — dashboard, approve/reject/escalate, bulk, analytics
from seo_platform.api.endpoints.approval_workflow import router as approval_workflow_router
api_router.include_router(approval_workflow_router, prefix="/approval-workflow", tags=["approval-workflow"])

# Workflow Automation Engine — scan-and-create-tasks, rules, audit
from seo_platform.api.endpoints.workflow_automation import router as workflow_automation_router
api_router.include_router(workflow_automation_router, prefix="/workflow-automation", tags=["workflow-automation"])

