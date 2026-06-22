"""
SEO Platform — Proxy Manager Service
======================================
Manages proxy pool with health tracking and automatic rotation.
"""

from __future__ import annotations

import random
import uuid
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from seo_platform.core.database import get_session
from seo_platform.core.encryption import encryption_service
from seo_platform.core.logging import get_logger
from seo_platform.models.rate_limiting import ProxyPool

logger = get_logger(__name__)


class ProxyConfig:
    """Represents a proxy configuration for browser use."""

    def __init__(
        self,
        proxy_id: uuid.UUID,
        host: str,
        port: int,
        protocol: str,
        username: str | None = None,
        password: str | None = None,
    ):
        self.proxy_id = proxy_id
        self.host = host
        self.port = port
        self.protocol = protocol
        self.username = username
        self.password = password

    def to_playwright(self) -> dict:
        """Convert to Playwright proxy format."""
        proxy_dict = {
            "server": f"{self.protocol}://{self.host}:{self.port}",
        }
        if self.username and self.password:
            proxy_dict["username"] = self.username
            proxy_dict["password"] = self.password
        return proxy_dict

    def __str__(self) -> str:
        return f"{self.protocol}://{self.host}:{self.port}"


class ProxyManager:
    """
    Manages proxy pool with health tracking and automatic rotation.

    Features:
    - Health-based selection (prefer healthy proxies)
    - Automatic blacklist on detection
    - Sticky sessions (same proxy for same site)
    """

    async def get_proxy(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        site_slug: str | None = None,
        prefer_residential: bool = True,
    ) -> Optional[ProxyConfig]:
        """
        Get best available proxy for a site.

        Selection logic:
        1. Filter by assigned_sites (if configured)
        2. Filter by status=active
        3. Sort by health_score DESC
        4. Pick randomly from top 3 (load distribution)
        """
        result = await session.execute(
            select(ProxyPool).where(
                ProxyPool.tenant_id == tenant_id,
                ProxyPool.status == "active",
            )
        )
        proxies = list(result.scalars().all())

        if not proxies:
            logger.warning("no_proxies_available")
            return None

        # Filter by site assignment
        if site_slug:
            assigned = [
                p for p in proxies
                if not p.assigned_sites or site_slug in (p.assigned_sites or [])
            ]
            if assigned:
                proxies = assigned

        # Prefer residential
        if prefer_residential:
            residential = [p for p in proxies if p.proxy_type == "residential"]
            if residential:
                proxies = residential

        # Sort by health score
        proxies.sort(key=lambda p: (-p.health_score, p.total_requests))

        # Pick from top 3
        top_n = proxies[:3]
        selected = random.choice(top_n)

        # Decrypt password if needed
        password = None
        if selected.proxy_auth_password_encrypted:
            try:
                password = encryption_service.decrypt(selected.proxy_auth_password_encrypted)
            except Exception as e:
                logger.error("proxy_password_decrypt_failed", proxy_id=str(selected.id))

        return ProxyConfig(
            proxy_id=selected.id,
            host=selected.proxy_host,
            port=selected.proxy_port,
            protocol=selected.proxy_protocol,
            username=selected.proxy_auth_username,
            password=password,
        )

    async def record_proxy_result(
        self,
        session: AsyncSession,
        proxy_id: uuid.UUID,
        success: bool,
        error_type: str | None = None,
    ) -> None:
        """Record result and update health score."""
        result = await session.execute(
            select(ProxyPool).where(ProxyPool.id == proxy_id)
        )
        proxy = result.scalar_one_or_none()
        if not proxy:
            return

        proxy.total_requests += 1
        proxy.last_used_at = datetime.now(UTC)

        if success:
            proxy.successful_requests += 1
        else:
            proxy.failed_requests += 1

            # Auto-suspend on high failure rate
            if proxy.total_requests > 10:
                failure_rate = proxy.failed_requests / proxy.total_requests
                if failure_rate > 0.5:
                    proxy.status = "suspended"
                    logger.warning(
                        "proxy_auto_suspended",
                        proxy_id=str(proxy_id),
                        failure_rate=failure_rate,
                    )

        # Update health score
        if proxy.total_requests > 0:
            success_rate = proxy.successful_requests / proxy.total_requests
            proxy.health_score = int(success_rate * 100)

        await session.commit()

    async def blacklist_proxy(
        self,
        session: AsyncSession,
        proxy_id: uuid.UUID,
        reason: str,
    ) -> bool:
        """Temporarily blacklist a proxy."""
        result = await session.execute(
            select(ProxyPool).where(ProxyPool.id == proxy_id)
        )
        proxy = result.scalar_one_or_none()
        if not proxy:
            return False

        proxy.status = "suspended"
        proxy.health_score = 0
        await session.commit()

        logger.info("proxy_blacklisted", proxy_id=str(proxy_id), reason=reason)
        return True

    # === CRUD ===

    async def add_proxy(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        name: str,
        proxy_type: str,
        proxy_host: str,
        proxy_port: int,
        proxy_protocol: str = "http",
        proxy_auth_username: str | None = None,
        proxy_auth_password: str | None = None,
        assigned_sites: list[str] | None = None,
    ) -> ProxyPool:
        """Add new proxy to pool."""
        encrypted_password = None
        if proxy_auth_password:
            encrypted_password = encryption_service.encrypt(proxy_auth_password)

        proxy = ProxyPool(
            tenant_id=tenant_id,
            name=name,
            proxy_type=proxy_type,
            proxy_host=proxy_host,
            proxy_port=proxy_port,
            proxy_protocol=proxy_protocol,
            proxy_auth_username=proxy_auth_username,
            proxy_auth_password_encrypted=encrypted_password,
            assigned_sites=assigned_sites or [],
        )
        session.add(proxy)
        await session.commit()
        await session.refresh(proxy)

        logger.info("proxy_added", proxy_id=str(proxy.id), name=name)
        return proxy

    async def list_proxies(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        status: str | None = None,
        proxy_type: str | None = None,
    ) -> list[ProxyPool]:
        """List all proxies with optional filters."""
        stmt = select(ProxyPool).where(ProxyPool.tenant_id == tenant_id)
        if status:
            stmt = stmt.where(ProxyPool.status == status)
        if proxy_type:
            stmt = stmt.where(ProxyPool.proxy_type == proxy_type)
        stmt = stmt.order_by(ProxyPool.created_at.desc())
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_proxy_by_id(
        self,
        session: AsyncSession,
        proxy_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Optional[ProxyPool]:
        """Get proxy by ID."""
        result = await session.execute(
            select(ProxyPool).where(
                ProxyPool.id == proxy_id,
                ProxyPool.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def delete_proxy(
        self,
        session: AsyncSession,
        proxy_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> bool:
        """Remove proxy from pool."""
        proxy = await self.get_proxy_by_id(session, proxy_id, tenant_id)
        if not proxy:
            return False
        await session.delete(proxy)
        await session.commit()
        return True

    async def get_proxy_summary(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> dict:
        """Get summary stats for proxy pool dashboard."""
        proxies = await self.list_proxies(session, tenant_id)
        total = len(proxies)
        active = sum(1 for p in proxies if p.status == "active")
        suspended = sum(1 for p in proxies if p.status == "suspended")
        expired = sum(1 for p in proxies if p.status == "expired")
        avg_health = sum(p.health_score for p in proxies) // total if total > 0 else 0

        total_requests = sum(p.total_requests for p in proxies)
        successful = sum(p.successful_requests for p in proxies)
        success_rate = (successful / total_requests * 100) if total_requests > 0 else 0

        return {
            "total": total,
            "active": active,
            "suspended": suspended,
            "expired": expired,
            "avg_health": avg_health,
            "total_requests": total_requests,
            "success_rate": round(success_rate, 1),
        }


proxy_manager = ProxyManager()
