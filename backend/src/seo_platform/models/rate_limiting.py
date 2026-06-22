"""
SEO Platform — Rate Limiting & Proxy Models
=============================================
SQLAlchemy models for proxy pools and rate limit configurations.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from seo_platform.core.database import Base
from seo_platform.models.base import TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class ProxyType(str, enum.Enum):
    RESIDENTIAL = "residential"
    DATACENTER = "datacenter"
    MOBILE = "mobile"
    SHARED = "shared"


class ProxyStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXPIRED = "expired"


class ProxyProtocol(str, enum.Enum):
    HTTP = "http"
    HTTPS = "https"
    SOCKS5 = "socks5"
    SOCKS4 = "socks4"


class RateLimitTargetType(str, enum.Enum):
    SITE = "site"
    CREDENTIAL = "credential"
    SITE_GROUP = "site_group"
    GLOBAL = "global"


class ProxyPool(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """Proxy pool with health tracking."""

    __tablename__ = "proxy_pools"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    proxy_type: Mapped[str] = mapped_column(
        Enum("residential", "datacenter", "mobile", "shared", name="proxy_type_enum"),
        nullable=False,
    )

    # Connection
    proxy_host: Mapped[str] = mapped_column(String(255), nullable=False)
    proxy_port: Mapped[int] = mapped_column(Integer, nullable=False)
    proxy_protocol: Mapped[str] = mapped_column(
        Enum("http", "https", "socks5", "socks4", name="proxy_protocol_enum"),
        nullable=False,
        server_default="http",
    )
    proxy_auth_username: Mapped[str | None] = mapped_column(String(255))
    proxy_auth_password_encrypted: Mapped[str | None] = mapped_column(Text)

    # Status
    status: Mapped[str] = mapped_column(
        Enum("active", "suspended", "expired", name="proxy_status_enum"),
        nullable=False,
        server_default="active",
    )
    health_score: Mapped[int] = mapped_column(Integer, default=100, server_default="100")

    # Usage
    total_requests: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    successful_requests: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    failed_requests: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Assignment
    assigned_sites: Mapped[dict | None] = mapped_column(JSONB, server_default="[]")

    __table_args__ = ({"schema": None},)


class RateLimitConfig(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """Rate limit configuration per target."""

    __tablename__ = "rate_limit_configs"

    target_type: Mapped[str] = mapped_column(
        Enum("site", "credential", "site_group", "global", name="rate_limit_target_type"),
        nullable=False,
    )
    target_id: Mapped[str | None] = mapped_column(String(100))

    # Limits
    requests_per_minute: Mapped[int] = mapped_column(Integer, default=10, server_default="10")
    requests_per_hour: Mapped[int] = mapped_column(Integer, default=100, server_default="100")
    requests_per_day: Mapped[int] = mapped_column(Integer, default=500, server_default="500")

    # Retry
    max_retries: Mapped[int] = mapped_column(Integer, default=3, server_default="3")
    backoff_multiplier: Mapped[float] = mapped_column(Float, default=2.0, server_default="2.0")

    # CAPTCHA
    max_captchas_before_skip: Mapped[int] = mapped_column(Integer, default=3, server_default="3")

    __table_args__ = ({"schema": None},)
