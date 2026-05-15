"""
SEO Platform — Kill Switch Service
=====================================
Hierarchical emergency stops stored in Redis for near-zero latency checks.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


class KillSwitchCheck(BaseModel):
    blocked: bool
    switch_key: str | None = None
    reason: str | None = None


class KillSwitchService:
    """
    Kill switches are the fastest path to stopping a bad operation.
    Stored in Redis with near-zero read latency. All critical execution
    paths check kill switches before proceeding.

    Hierarchy:
      platform.all_outreach     — Stops ALL email/SMS sends platform-wide
      platform.all_llm_calls    — Stops ALL LLM inference
      platform.all_scraping     — Stops ALL browser automation
      provider.{name}           — Stops specific provider
      tenant.{id}.outreach      — Stops outreach for specific tenant
      campaign.{id}             — Stops specific campaign
    """

    async def activate(self, switch_key: str, reason: str, activated_by: str,
                       auto_reset_seconds: int | None = None) -> None:
        from seo_platform.core.redis import get_redis
        redis = await get_redis()
        mapping: dict[str, str] = {
            "active": "1",
            "reason": reason,
            "activated_by": activated_by,
            "activated_at": datetime.now(UTC).isoformat(),
        }
        if auto_reset_seconds:
            reset_at = datetime.now(UTC) + timedelta(seconds=auto_reset_seconds)
            mapping["auto_reset_at"] = reset_at.isoformat()
        await redis.hset(f"kill_switch:{switch_key}", mapping=mapping)
        if auto_reset_seconds:
            await redis.expire(f"kill_switch:{switch_key}", auto_reset_seconds)
        logger.warning("kill_switch_activated", switch_key=switch_key, reason=reason, activated_by=activated_by)

    async def deactivate(self, switch_key: str, deactivated_by: str) -> None:
        from seo_platform.core.redis import get_redis
        redis = await get_redis()
        await redis.delete(f"kill_switch:{switch_key}")
        logger.info("kill_switch_deactivated", switch_key=switch_key, deactivated_by=deactivated_by)

    async def is_blocked(self, operation_type: str, tenant_id: UUID | None = None,
                         campaign_id: UUID | None = None, provider: str | None = None) -> KillSwitchCheck:
        from seo_platform.core.redis import get_redis
        redis = await get_redis()
        keys_to_check = [f"platform.{operation_type}"]
        if tenant_id:
            keys_to_check.append(f"tenant.{tenant_id}.{operation_type}")
        if campaign_id:
            keys_to_check.append(f"campaign.{campaign_id}")
        if provider:
            keys_to_check.append(f"provider.{provider}")

        for key in keys_to_check:
            active = await redis.hget(f"kill_switch:{key}", "active")
            if active == "1":
                reason = await redis.hget(f"kill_switch:{key}", "reason") or "No reason provided"
                return KillSwitchCheck(blocked=True, switch_key=key, reason=reason)
        return KillSwitchCheck(blocked=False)

    async def list_active(self) -> list[dict[str, Any]]:
        from seo_platform.core.redis import get_redis
        redis = await get_redis()
        keys = []
        async for key in redis.scan_iter("kill_switch:*"):
            data = await redis.hgetall(key)
            if data.get("active") == "1":
                keys.append({"key": key.replace("kill_switch:", ""), **data})
        return keys


kill_switch_service = KillSwitchService()
