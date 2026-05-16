"""
SEO Platform — Temporal Worker Bootstrap
==========================================
Worker process that runs Temporal activities and workflows.

ARCHITECTURE: All task queues must be served by workers. Each queue
corresponds to a bounded context with dedicated worker pools.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor

from temporalio.client import Client as TemporalClient
from temporalio.worker import Worker
from temporalio.worker.workflow_sandbox import SandboxedWorkflowRunner, SandboxRestrictions

from seo_platform.config import get_settings
from seo_platform.core.logging import get_logger, setup_logging
from seo_platform.workflows import TaskQueue


async def run_event_consumers() -> None:
    """Start Kafka event consumers for workflow-related events."""
    try:
        from seo_platform.core.events import EventConsumer

        consumer = EventConsumer(
            topics=[
                "approval_request_decided",
                "workflow_campaign_started",
                "workflow_campaign_completed",
                "seo_keyword_research_completed",
            ],
            group_id="workflow-workers",
        )

        async def on_approval_decided(event):
            logger.info("approval_decided_event_received", event_id=str(event.event_id))
            from seo_platform.api.endpoints.realtime.sse import emit_approval_event
            payload = event.payload
            await emit_approval_event(
                event.tenant_id,
                payload.get("request_id", ""),
                payload.get("decision", "unknown"),
            )

        async def on_campaign_event(event):
            logger.info("campaign_event_received", event_type=event.event_type, correlation_id=event.correlation_id)
            from seo_platform.api.endpoints.realtime.sse import emit_campaign_event
            await emit_campaign_event(
                event.tenant_id,
                event.payload.get("campaign_id", ""),
                event.payload.get("status", "unknown"),
            )

        async def on_workflow_event(event):
            logger.info("workflow_event_received", event_type=event.event_type, correlation_id=event.correlation_id)
            from seo_platform.api.endpoints.realtime.sse import emit_workflow_event
            await emit_workflow_event(
                event.tenant_id,
                event.event_type,
                event.payload.get("status", "running"),
                event.payload,
            )

        consumer.register_handler("approval.request.decided", on_approval_decided)
        consumer.register_handler("workflow.campaign.started", on_campaign_event)
        consumer.register_handler("workflow.campaign.completed", on_campaign_event)
        consumer.register_handler("workflow.keyword.research.completed", on_workflow_event)

        logger.info("event_consumer_starting", group_id="workflow-workers")
        await consumer.start()
        await consumer.consume()
    except Exception as e:
        logger.warning("event_consumer_skipped", error=str(e))


async def run_worker(task_queue: str | None = None) -> None:
    """
    Start a Temporal worker for the specified task queue.

    Each task queue corresponds to a bounded context / service domain.
    Workers are scaled independently per queue based on load.
    """
    setup_logging()
    settings = get_settings()

    queue = task_queue or TaskQueue.ONBOARDING
    logger.info("temporal_worker_starting", task_queue=queue, namespace=settings.temporal.namespace)

    consumer_task = asyncio.create_task(run_event_consumers())

    client = await TemporalClient.connect(
        settings.temporal.target,
        namespace=settings.temporal.namespace,
    )

    workflows, activities = get_workflows_and_activities(queue)

    # Configure sandbox to allow structlog (uses threading.Lock but is safe for logging)
    base_restrictions = SandboxRestrictions.default
    custom_restrictions = SandboxRestrictions(
        passthrough_modules=base_restrictions.passthrough_modules | {"structlog"},
        invalid_modules=base_restrictions.invalid_modules,
        invalid_module_members=base_restrictions.invalid_module_members,
    )

    workflow_runner = SandboxedWorkflowRunner(restrictions=custom_restrictions)

    worker = Worker(
        client,
        task_queue=queue,
        workflows=workflows,
        activities=activities,
        max_concurrent_activities=settings.temporal.max_concurrent_activities,
        max_concurrent_workflow_tasks=settings.temporal.max_concurrent_workflows,
        activity_executor=ThreadPoolExecutor(max_workers=20),
        workflow_runner=workflow_runner,
    )

    logger.info(
        "temporal_worker_started",
        task_queue=queue,
        workflows=[w.__name__ for w in workflows],
        activities=[a.__name__ for a in activities],
    )

    try:
        await worker.run()
    finally:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass


def get_workflows_and_activities(task_queue: str) -> tuple[list, list]:
    """
    Get all workflows and activities for a given task queue.
    
    This ensures EVERY workflow is registered with the worker,
    preventing dead queues and ensuring real execution.
    """
    from seo_platform.workflows import (
        OnboardingWorkflow,
        discover_competitors,
        enrich_business_profile,
        generate_keyword_ideas,
        validate_client_domain,
    )
    from seo_platform.workflows.backlink_campaign import (
        BacklinkCampaignWorkflow,
        OutreachThreadWorkflow,
        create_approval_request_activity,
        discover_contacts_activity,
        discover_prospects_activity,
        fallback_prospects_activity,
        generate_outreach_emails_activity,
        score_prospects_activity,
        send_outreach_batch_activity,
        send_single_email_activity,
        update_campaign_status_activity,
    )
    from seo_platform.workflows.citation import (
        CitationSubmissionWorkflow,
        create_citation_approval,
        execute_directory_submission,
        governance_scan_activity,
        validate_business_profile,
        verify_citation_listing,
    )
    from seo_platform.workflows.keyword_research import (
        KeywordResearchWorkflow as FullKeywordResearchWorkflow,
    )
    from seo_platform.workflows.keyword_research import (
        cluster_keywords_activity,
        enrich_keywords_activity,
        expand_keywords,
        generate_keyword_embeddings,
        generate_seed_keywords,
        name_clusters_activity,
        persist_keyword_data,
    )

    workflows = []
    activities = []

    if task_queue == TaskQueue.ONBOARDING:
        workflows = [
            OnboardingWorkflow,
        ]
        activities = [
            validate_client_domain,
            enrich_business_profile,
            discover_competitors,
            generate_keyword_ideas,
        ]

    elif task_queue == TaskQueue.AI_ORCHESTRATION:
        from seo_platform.workflows.reporting import generate_ai_summary
        from seo_platform.workflows.scheduler import (
            OperationalHealthScan,
            OperationalLoopEngine,
            AutonomousDiscovery,
            gather_active_campaigns,
            check_campaign_health,
            create_operational_event,
            scan_backlink_opportunities,
            generate_platform_recommendation,
        )
        workflows = [
            FullKeywordResearchWorkflow,
            BacklinkCampaignWorkflow,
            CitationSubmissionWorkflow,
            OperationalHealthScan,
            OperationalLoopEngine,
            AutonomousDiscovery,
        ]
        activities = [
            generate_seed_keywords,
            expand_keywords,
            enrich_keywords_activity,
            generate_keyword_embeddings,
            cluster_keywords_activity,
            name_clusters_activity,
            generate_outreach_emails_activity,
            generate_keyword_ideas,
            governance_scan_activity,
            generate_ai_summary,
            gather_active_campaigns,
            check_campaign_health,
            create_operational_event,
            scan_backlink_opportunities,
            generate_platform_recommendation,
        ]

    elif task_queue == TaskQueue.SEO_INTELLIGENCE:
        workflows = [
            FullKeywordResearchWorkflow,
            CitationSubmissionWorkflow,
        ]
        activities = [
            generate_seed_keywords,
            expand_keywords,
            enrich_keywords_activity,
            cluster_keywords_activity,
            persist_keyword_data,
            create_approval_request_activity,
            validate_business_profile,
            execute_directory_submission,
            verify_citation_listing,
            create_citation_approval,
        ]

    elif task_queue == TaskQueue.BACKLINK_ENGINE:
        workflows = [
            BacklinkCampaignWorkflow,
        ]
        activities = [
            discover_prospects_activity,
            fallback_prospects_activity,
            score_prospects_activity,
            discover_contacts_activity,
            create_approval_request_activity,
            update_campaign_status_activity,
        ]

    elif task_queue == TaskQueue.COMMUNICATION:
        workflows = [
            OutreachThreadWorkflow,
        ]
        activities = [
            send_outreach_batch_activity,
            send_single_email_activity,
            update_campaign_status_activity,
        ]

    elif task_queue == TaskQueue.REPORTING:
        from seo_platform.workflows.reporting import (
            ReportGenerationWorkflow,
            gather_report_data,
            generate_ai_summary,
            persist_report,
        )
        workflows = [ReportGenerationWorkflow]
        activities = [
            gather_report_data,
            generate_ai_summary,
            persist_report,
        ]

    return workflows, activities


logger = get_logger(__name__)


def main() -> None:
    """Entry point for the worker process."""
    import sys
    raw = sys.argv[1] if len(sys.argv) > 1 else None
    if raw:
        task_queue = getattr(TaskQueue, raw.upper(), raw)
    else:
        task_queue = TaskQueue.ONBOARDING
    asyncio.run(run_worker(task_queue))


if __name__ == "__main__":
    main()
