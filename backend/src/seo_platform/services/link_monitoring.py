"""
SEO Platform — Link Monitoring Service (Workstream F)
=======================================================
Scheduled re-verification of every previously-verified acquired link.

Iterates over every AcquiredLink with status ``VERIFIED_LIVE`` (the
result of a prior successful verification) and re-runs the real
network check from ``LinkVerificationService``. When the new outcome
indicates the link has been removed, redirected off-domain, or has
become unreachable the service:

1. Emits a ``backlink.link_status_changed`` domain event.
2. Flips the parent prospect from ``link_acquired`` → ``link_lost``
   when applicable.
3. Recomputes the campaign's ``acquired_link_count`` and
   ``acquisition_rate`` so the dashboard reflects reality.
4. Writes an immutable audit_log row via the existing
   ``AuditService`` so compliance/forensics see the regression.
5. Best-effort dispatches a notification (if a notification service
   is available) without blocking the monitoring loop.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from seo_platform.core.logging import get_logger
from seo_platform.services.link_verification import (
    LinkVerificationService,
    VerificationOutcome,
    link_verification_service,
)

logger = get_logger(__name__)


class MonitoringSummary(BaseModel):
    """Result returned from a single ``monitor_all_links`` invocation."""

    checked: int = 0
    verified: int = 0
    missing: int = 0
    redirected: int = 0
    broken: int = 0
    errors: int = 0
    changed: int = 0
    campaigns_affected: int = 0
    started_at: datetime
    finished_at: datetime | None = None
    duration_ms: float | None = None


class LinkMonitoringService:
    """
    Orchestrates re-verification of every previously-VERIFIED_LIVE link.

    Uses a single ``LinkVerificationService`` for the actual network
    work so it shares the same 10s timeout, classifier, and persistence
    semantics as manual verification.
    """

    # How many links to verify concurrently inside one tenant sweep.
    BATCH_SIZE: int = 50

    def __init__(
        self,
        verification_service: LinkVerificationService | None = None,
    ) -> None:
        self._verifier = verification_service or link_verification_service

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def monitor_all_links(
        self,
        tenant_id: UUID | None = None,
        campaign_id: UUID | None = None,
        link_ids: list[UUID] | None = None,
    ) -> dict[str, Any]:
        """
        Re-verify every link previously known to be live.

        Parameters
        ----------
        tenant_id:
            Restrict the sweep to a single tenant. ``None`` means
            cross-tenant — used by the global scheduler.
        campaign_id:
            Optional further restriction to a single campaign.
        link_ids:
            Optional explicit subset of acquired link UUIDs.
        """
        import asyncio
        import time
        from collections import defaultdict

        from sqlalchemy import select

        from seo_platform.core.database import (
            get_session,
            get_tenant_session,
        )
        from seo_platform.models.backlink import (
            AcquiredLink,
            BacklinkCampaign,
            BacklinkProspect,
            LinkStatus,
            ProspectStatus,
        )

        started_at = datetime.now(UTC)
        t0 = time.monotonic()
        summary = MonitoringSummary(started_at=started_at)

        # ------------------------------------------------------------------
        # 1. Load candidate link IDs (cross-tenant safe via get_session).
        # ------------------------------------------------------------------
        if link_ids is not None:
            target_ids = list(link_ids)
        else:
            target_ids = await self._collect_candidate_link_ids(
                tenant_id=tenant_id,
                campaign_id=campaign_id,
            )

        if not target_ids:
            summary.finished_at = datetime.now(UTC)
            summary.duration_ms = round((time.monotonic() - t0) * 1000, 2)
            return summary.model_dump()

        # Group IDs by tenant so we can run the verifier under a tenant
        # session (matches RLS policy requirements for every write).
        # The AcquiredLink table has tenant_id, so we look it up once
        # with a cross-tenant session and then route the verification
        # to per-tenant sessions.
        per_tenant: dict[UUID, list[UUID]] = defaultdict(list)
        async with get_session() as session:
            rows = await session.execute(
                select(AcquiredLink.id, AcquiredLink.tenant_id).where(
                    AcquiredLink.id.in_(target_ids)
                )
            )
            for link_id, link_tenant in rows.all():
                per_tenant[link_tenant].append(link_id)

        # ------------------------------------------------------------------
        # 2. Run real verifications in bounded concurrency.
        # ------------------------------------------------------------------
        semaphore = asyncio.Semaphore(self.BATCH_SIZE)

        async def _run_one(t_id: UUID, l_id: UUID) -> dict[str, Any]:
            async with semaphore:
                try:
                    return await self._verifier.verify_link(
                        acquired_link_id=l_id, tenant_id=t_id,
                    )
                except Exception as exc:  # never break the sweep
                    logger.warning(
                        "link_monitor_verify_failed",
                        acquired_link_id=str(l_id),
                        error=str(exc),
                    )
                    return {
                        "acquired_link_id": str(l_id),
                        "tenant_id": str(t_id),
                        "outcome": VerificationOutcome.ERROR.value,
                        "matched": False,
                        "previous_status": "",
                        "error": str(exc),
                    }

        tasks: list[asyncio.Task[Any]] = []
        for t_id, ids in per_tenant.items():
            for l_id in ids:
                tasks.append(asyncio.create_task(_run_one(t_id, l_id)))

        results: list[dict[str, Any]] = await asyncio.gather(*tasks, return_exceptions=False)

        # ------------------------------------------------------------------
        # 3. Tally, detect status changes, fire events + audit + prospect
        #    flips + campaign metric recomputation.
        # ------------------------------------------------------------------
        affected_campaigns: set[UUID] = set()
        for res in results:
            summary.checked += 1
            outcome = (res.get("outcome") or "").lower()
            if outcome == VerificationOutcome.VERIFIED.value:
                summary.verified += 1
            elif outcome == VerificationOutcome.MISSING.value:
                summary.missing += 1
            elif outcome == VerificationOutcome.REDIRECTED.value:
                summary.redirected += 1
            elif outcome == VerificationOutcome.BROKEN.value:
                summary.broken += 1
            else:
                summary.errors += 1

            previous = (res.get("previous_status") or "").lower()
            new_status = (res.get("link_status") or "").lower()
            if previous == LinkStatus.VERIFIED_LIVE.value and new_status and new_status != LinkStatus.VERIFIED_LIVE.value:
                summary.changed += 1
                try:
                    link_tenant = UUID(res["tenant_id"])
                except (KeyError, ValueError):
                    link_tenant = None
                if link_tenant is not None:
                    await self._on_link_regression(
                        tenant_id=link_tenant,
                        verification=res,
                        previous_status=previous,
                        new_status=new_status,
                        affected_campaigns=affected_campaigns,
                    )

        # ------------------------------------------------------------------
        # 4. Recompute campaign metrics for every affected campaign.
        # ------------------------------------------------------------------
        for camp_tenant, camp_id in {(await self._tenant_for_campaign(c)) for c in affected_campaigns if c}:
            try:
                async with get_tenant_session(camp_tenant) as session:
                    await self._recompute_campaign_metrics(session, camp_id)
            except Exception as exc:
                logger.warning(
                    "link_monitor_campaign_metric_recompute_failed",
                    campaign_id=str(camp_id),
                    error=str(exc),
                )

        # ------------------------------------------------------------------
        # 5. Publish a single monitoring summary event (best-effort).
        # ------------------------------------------------------------------
        await self._publish_monitoring_event(summary, results)

        summary.campaigns_affected = len(affected_campaigns)
        summary.finished_at = datetime.now(UTC)
        summary.duration_ms = round((time.monotonic() - t0) * 1000, 2)
        return summary.model_dump()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    async def _collect_candidate_link_ids(
        self,
        tenant_id: UUID | None,
        campaign_id: UUID | None,
    ) -> list[UUID]:
        from sqlalchemy import select

        from seo_platform.core.database import get_session
        from seo_platform.models.backlink import AcquiredLink, LinkStatus

        stmt = select(AcquiredLink.id).where(
            AcquiredLink.status == LinkStatus.VERIFIED_LIVE
        )
        if tenant_id is not None:
            stmt = stmt.where(AcquiredLink.tenant_id == tenant_id)
        if campaign_id is not None:
            stmt = stmt.where(AcquiredLink.campaign_id == campaign_id)

        async with get_session() as session:
            rows = await session.execute(stmt)
            return [row[0] for row in rows.all()]

    async def _on_link_regression(
        self,
        tenant_id: UUID,
        verification: dict[str, Any],
        previous_status: str,
        new_status: str,
        affected_campaigns: set[UUID],
    ) -> None:
        """Handle a single VERIFIED_LIVE → anything-else transition."""
        from sqlalchemy import select

        from seo_platform.core.database import get_tenant_session
        from seo_platform.models.backlink import (
            AcquiredLink,
            BacklinkProspect,
            ProspectStatus,
        )

        try:
            link_uuid = UUID(verification["acquired_link_id"])
        except (KeyError, ValueError):
            return

        async with get_tenant_session(tenant_id) as session:
            result = await session.execute(
                select(AcquiredLink).where(
                    AcquiredLink.id == link_uuid,
                    AcquiredLink.tenant_id == tenant_id,
                )
            )
            link = result.scalar_one_or_none()
            if link is None:
                return

            affected_campaigns.add(link.campaign_id)
            prospect_id = link.prospect_id

            if prospect_id is not None:
                prospect = await session.get(BacklinkProspect, prospect_id)
                if prospect is not None and prospect.status == ProspectStatus.LINK_ACQUIRED:
                    prospect.status = ProspectStatus.LINK_LOST

        # Fire event (outside the DB transaction — never blocks commit).
        await self._publish_status_change_event(
            tenant_id=tenant_id,
            link_id=link_uuid,
            campaign_id=link.campaign_id,
            prospect_id=prospect_id,
            previous_status=previous_status,
            new_status=new_status,
            verification=verification,
        )

        # Best-effort audit + notification — never break the loop.
        await self._write_audit_entry(
            tenant_id=tenant_id,
            link_id=link_uuid,
            campaign_id=link.campaign_id,
            previous_status=previous_status,
            new_status=new_status,
            verification=verification,
        )
        await self._send_notification_best_effort(
            tenant_id=tenant_id,
            link_id=link_uuid,
            campaign_id=link.campaign_id,
            previous_status=previous_status,
            new_status=new_status,
            verification=verification,
        )

    async def _recompute_campaign_metrics(self, session, campaign_id: UUID) -> None:
        from sqlalchemy import func, select

        from seo_platform.models.backlink import (
            AcquiredLink,
            BacklinkCampaign,
            LinkStatus,
        )

        campaign = await session.get(BacklinkCampaign, campaign_id)
        if campaign is None:
            return

        live_count = await session.execute(
            select(func.count())
            .select_from(AcquiredLink)
            .where(
                AcquiredLink.campaign_id == campaign_id,
                AcquiredLink.status == LinkStatus.VERIFIED_LIVE,
            )
        )
        live = int(live_count.scalar() or 0)

        # acquired_link_count tracks links that are currently live
        # (a link that was verified and later lost should no longer
        # count as an acquisition).
        campaign.acquired_link_count = live
        if campaign.target_link_count and campaign.target_link_count > 0:
            campaign.acquisition_rate = round(
                live / campaign.target_link_count, 4
            )

    async def _tenant_for_campaign(self, campaign_id: UUID) -> tuple[UUID, UUID]:
        from sqlalchemy import select

        from seo_platform.core.database import get_session
        from seo_platform.models.backlink import BacklinkCampaign

        async with get_session() as session:
            row = await session.execute(
                select(BacklinkCampaign.tenant_id, BacklinkCampaign.id).where(
                    BacklinkCampaign.id == campaign_id,
                )
            )
            record = row.first()
            if record is None:
                # Return a sentinel that won't match a real tenant.
                return (campaign_id, campaign_id)
            return (record.tenant_id, record.id)

    async def _publish_status_change_event(
        self,
        tenant_id: UUID,
        link_id: UUID,
        campaign_id: UUID,
        prospect_id: UUID | None,
        previous_status: str,
        new_status: str,
        verification: dict[str, Any],
    ) -> None:
        try:
            from seo_platform.core.events import DomainEvent

            event = DomainEvent(
                event_type="backlink.link_status_changed",
                tenant_id=tenant_id,
                source_service="link_monitoring",
                payload={
                    "acquired_link_id": str(link_id),
                    "campaign_id": str(campaign_id),
                    "prospect_id": str(prospect_id) if prospect_id else None,
                    "previous_status": previous_status,
                    "new_status": new_status,
                    "outcome": verification.get("outcome"),
                    "http_status": verification.get("http_status"),
                    "anchor_text": verification.get("anchor_text"),
                    "final_url": verification.get("final_url"),
                    "error": verification.get("error"),
                },
            )
            # EventPublisher may not be started in all environments
            # (e.g. worker entry points). Failures are logged, not raised.
            try:
                from seo_platform.core.events import event_publisher  # type: ignore

                await event_publisher.publish(event)
            except Exception as inner:
                logger.info(
                    "link_status_event_publish_skipped",
                    event_type=event.event_type,
                    reason=str(inner),
                )
        except Exception as exc:
            logger.warning(
                "link_status_event_publish_failed",
                error=str(exc),
                acquired_link_id=str(link_id),
            )

    async def _publish_monitoring_event(
        self,
        summary: MonitoringSummary,
        results: list[dict[str, Any]],
    ) -> None:
        try:
            from seo_platform.core.events import DomainEvent

            # Multi-tenant summary: we use the zero UUID as a synthetic
            # "platform" tenant — downstream consumers that need
            # per-tenant splits can read individual results.
            event = DomainEvent(
                event_type="backlink.monitoring_cycle_complete",
                tenant_id=UUID(int=0),
                source_service="link_monitoring",
                payload={
                    "checked": summary.checked,
                    "verified": summary.verified,
                    "missing": summary.missing,
                    "redirected": summary.redirected,
                    "broken": summary.broken,
                    "errors": summary.errors,
                    "changed": summary.changed,
                    "campaigns_affected": summary.campaigns_affected,
                    "duration_ms": summary.duration_ms,
                },
            )
            try:
                from seo_platform.core.events import event_publisher  # type: ignore

                await event_publisher.publish(event)
            except Exception:
                pass
        except Exception as exc:
            logger.warning("link_monitoring_event_publish_failed", error=str(exc))

    async def _write_audit_entry(
        self,
        tenant_id: UUID,
        link_id: UUID,
        campaign_id: UUID,
        previous_status: str,
        new_status: str,
        verification: dict[str, Any],
    ) -> None:
        try:
            from seo_platform.core.audit import AuditEntry, audit_service

            await audit_service.record(
                AuditEntry(
                    tenant_id=tenant_id,
                    event_type="link.status_changed",
                    entity_type="AcquiredLink",
                    entity_id=link_id,
                    actor_type="system",
                    actor_id="link_monitoring",
                    before_state={"status": previous_status},
                    after_state={
                        "status": new_status,
                        "outcome": verification.get("outcome"),
                        "http_status": verification.get("http_status"),
                        "anchor_text": verification.get("anchor_text"),
                        "final_url": verification.get("final_url"),
                    },
                    metadata={
                        "campaign_id": str(campaign_id),
                        "link_type": verification.get("link_type"),
                        "error": verification.get("error"),
                    },
                )
            )
        except Exception as exc:
            logger.warning(
                "link_monitoring_audit_failed",
                error=str(exc),
                acquired_link_id=str(link_id),
            )

    async def _send_notification_best_effort(
        self,
        tenant_id: UUID,
        link_id: UUID,
        campaign_id: UUID,
        previous_status: str,
        new_status: str,
        verification: dict[str, Any],
    ) -> None:
        """Best-effort notification dispatch — never raises."""
        try:
            from seo_platform.core.alerting import (
                Severity,
                alert_manager,
            )

            alert_manager.raise_alert(
                alert_type="link_status_regression",
                severity=Severity.MEDIUM,
                title=f"Backlink regressed: {verification.get('source_url', '')}",
                message=(
                    f"Acquired link {link_id} moved from {previous_status} → {new_status} "
                    f"(outcome={verification.get('outcome')}, http={verification.get('http_status')})."
                ),
                source="link_monitoring",
                tenant_id=str(tenant_id),
                metadata={
                    "acquired_link_id": str(link_id),
                    "campaign_id": str(campaign_id),
                    "previous_status": previous_status,
                    "new_status": new_status,
                    "outcome": verification.get("outcome"),
                    "http_status": verification.get("http_status"),
                    "final_url": verification.get("final_url"),
                    "anchor_text": verification.get("anchor_text"),
                },
            )
        except Exception as exc:
            # Some deployments don't register an alert_manager; swallow
            # the error so the monitoring loop continues.
            logger.info(
                "link_monitoring_notification_skipped",
                error=str(exc),
                acquired_link_id=str(link_id),
            )


link_monitoring_service = LinkMonitoringService()
