"""
SEO Platform — Link Monitoring Workflow (Workstream F)
=========================================================
Temporal activity and workflow that drives scheduled re-verification
of every previously-VERIFIED_LIVE acquired link.

This module wraps ``LinkMonitoringService.monitor_all_links`` in a
durable Temporal surface so the platform scheduler can register it
on a weekly cron without blocking on the underlying network I/O.

For environments without Temporal, the same activity entry point can
be called directly from APScheduler (see ``workflows/scheduler.py``).
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID

from temporalio import activity, workflow

from seo_platform.core.logging import get_logger
from seo_platform.workflows import RetryPreset, TaskQueue

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Activity: scheduled link monitor
# ---------------------------------------------------------------------------
@activity.defn(name="monitor_links_activity")
async def monitor_links_activity(
    tenant_id: str | None = None,
    campaign_id: str | None = None,
) -> dict[str, Any]:
    """
    Run a single monitoring sweep.

    Parameters
    ----------
    tenant_id:
        Optional UUID string restricting the sweep to a single tenant.
        When ``None`` (the default — used by the platform-wide cron)
        the sweep runs across every tenant that has acquired links.
    campaign_id:
        Optional UUID string restricting the sweep to a single campaign.
    """
    from seo_platform.services.link_monitoring import (
        link_monitoring_service,
    )

    parsed_tenant = UUID(tenant_id) if tenant_id else None
    parsed_campaign = UUID(campaign_id) if campaign_id else None

    logger.info(
        "monitor_links_activity_started",
        tenant_id=str(parsed_tenant) if parsed_tenant else "all",
        campaign_id=str(parsed_campaign) if parsed_campaign else "all",
    )

    summary = await link_monitoring_service.monitor_all_links(
        tenant_id=parsed_tenant,
        campaign_id=parsed_campaign,
    )
    logger.info(
        "monitor_links_activity_complete",
        checked=summary.get("checked", 0),
        changed=summary.get("changed", 0),
        duration_ms=summary.get("duration_ms"),
    )
    return summary


# ---------------------------------------------------------------------------
# Workflow: weekly scheduled link monitor
# ---------------------------------------------------------------------------
@workflow.defn(name="ScheduledLinkMonitor")
class ScheduledLinkMonitor:
    """
    Durable wrapper around ``monitor_links_activity``.

    Designed to be started by a Temporal Schedule (cron) at 9 AM every
    Monday. A single workflow run can be re-launched cheaply.
    """

    @workflow.run
    async def run(self, input_json: str = "") -> str:
        import json as _json

        try:
            payload = _json.loads(input_json) if input_json else {}
        except Exception:
            payload = {}

        tenant_id = payload.get("tenant_id")
        campaign_id = payload.get("campaign_id")

        summary = await workflow.execute_activity(
            monitor_links_activity,
            args=[tenant_id, campaign_id],
            task_queue=TaskQueue.BACKLINK_ENGINE,
            start_to_close_timeout=timedelta(minutes=30),
            retry_policy=RetryPreset.EXTERNAL_API,
        )
        return _json.dumps(summary)
