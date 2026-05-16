"""
SEO Platform — Configuration System
=====================================
Environment-driven configuration using Pydantic Settings.
All configuration is loaded from environment variables with strong typing,
validation, and sensible defaults for development.

Design principle: Configuration is infrastructure. Every configurable value
is typed, validated, and documented. No magic strings in application code.
"""

from __future__ import annotations

import enum
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, enum.Enum):
    """Application deployment environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class LogLevel(str, enum.Enum):
    """Structured logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DatabaseSettings(BaseSettings):
    """PostgreSQL database configuration."""

    model_config = SettingsConfigDict(env_prefix="POSTGRES_")

    host: str = "localhost"
    port: int = 5432
    db: str = "seo_platform"
    user: str = "seo_platform"
    password: str = "seo_platform_dev"

    # Connection pool settings (PgBouncer-aware)
    pool_size: int = Field(default=20, description="SQLAlchemy connection pool size")
    max_overflow: int = Field(default=10, description="Max connections beyond pool_size")
    pool_timeout: int = Field(default=30, description="Seconds to wait for pool connection")
    pool_recycle: int = Field(default=1800, description="Recycle connections after N seconds")
    echo: bool = Field(default=False, description="Echo SQL queries to log (dev only)")

    @property
    def async_url(self) -> str:
        """Async database URL for SQLAlchemy + asyncpg."""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"

    @property
    def sync_url(self) -> str:
        """Sync database URL for Alembic migrations."""
        return f"postgresql+psycopg2://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"


class RedisSettings(BaseSettings):
    """Redis configuration."""

    model_config = SettingsConfigDict(env_prefix="REDIS_")

    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str | None = None
    max_connections: int = Field(default=50, description="Max connections in pool")
    socket_timeout: float = Field(default=5.0, description="Socket timeout in seconds")
    socket_connect_timeout: float = Field(default=5.0, description="Connect timeout")
    decode_responses: bool = True

    @property
    def url(self) -> str:
        """Redis connection URL."""
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"


class KafkaSettings(BaseSettings):
    """Apache Kafka configuration."""

    model_config = SettingsConfigDict(env_prefix="KAFKA_")

    bootstrap_servers: str = "localhost:9092"
    consumer_group_prefix: str = "seo-platform"
    auto_offset_reset: str = "earliest"
    enable_auto_commit: bool = False
    max_poll_records: int = 100
    session_timeout_ms: int = 30000
    heartbeat_interval_ms: int = 10000

    @property
    def bootstrap_servers_list(self) -> list[str]:
        """Parse comma-separated bootstrap servers."""
        return [s.strip() for s in self.bootstrap_servers.split(",")]


class TemporalSettings(BaseSettings):
    """Temporal.io workflow orchestration configuration."""

    model_config = SettingsConfigDict(env_prefix="TEMPORAL_")

    host: str = "localhost"
    port: int = 7233
    namespace: str = "default"
    task_queue_prefix: str = "seo-platform"

    # Worker pool configuration
    max_concurrent_activities: int = 50
    max_concurrent_workflows: int = 200

    @property
    def target(self) -> str:
        """Temporal gRPC target address."""
        return f"{self.host}:{self.port}"


class QdrantSettings(BaseSettings):
    """Qdrant vector database configuration."""

    model_config = SettingsConfigDict(env_prefix="QDRANT_")

    host: str = "localhost"
    port: int = 6333
    grpc_port: int = 6334
    api_key: str | None = None
    prefer_grpc: bool = True


class NvidiaSettings(BaseSettings):
    """NVIDIA NIM API configuration for LLM inference."""

    model_config = SettingsConfigDict(env_prefix="NVIDIA_NIM_")

    api_url: str = "https://integrate.api.nvidia.com/v1"
    api_key: str = "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"

    # Enterprise NIM Model Fleet
    orchestration_model: str = "DeepSeek-V4-Pro"
    seo_model: str = "meta/llama-3.1-8b-instruct"
    memory_model: str = "MiniMax M2.7"
    infra_model: str = "NVIDIA-Nemotron-3-Super-120B-A12B"
    embedding_model: str = "nvidia/nv-embedqa-e5-v5"

    # Inference defaults
    default_temperature: float = 0.7
    default_max_tokens: int = 2048
    request_timeout: float = 45.0
    max_retries: int = 3


class AuthSettings(BaseSettings):
    """Authentication and authorization configuration."""

    model_config = SettingsConfigDict(env_prefix="AUTH_")

    provider: str = "clerk"  # clerk | auth0 | internal
    secret_key: str = "change-me-to-a-secure-random-string"
    issuer_url: str = ""
    audience: str = "seo-platform-api"

    # JWT
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 7
    algorithm: str = "HS256"


class SendGridSettings(BaseSettings):
    """SendGrid email configuration."""

    model_config = SettingsConfigDict(env_prefix="SENDGRID_")

    api_key: str = ""
    sender_email: str = "noreply@seoplatform.io"
    sender_name: str = "SEO Platform"


class DataForSEOSettings(BaseSettings):
    """DataForSEO API configuration for keyword research and SERP data."""

    model_config = SettingsConfigDict(env_prefix="DATAFORSEO_")

    login: str = ""
    password: str = ""


class AhrefsSettings(BaseSettings):
    """Ahrefs API configuration for backlink data."""

    model_config = SettingsConfigDict(env_prefix="AHREFS_")

    api_key: str = ""


class HunterSettings(BaseSettings):
    """Hunter.io API configuration for email discovery."""

    model_config = SettingsConfigDict(env_prefix="HUNTER_")

    api_key: str = ""


class MailgunSettings(BaseSettings):
    """Mailgun API configuration for email delivery."""

    model_config = SettingsConfigDict(env_prefix="MAILGUN_")

    api_key: str = ""
    domain: str = ""
    webhook_signing_key: str = ""


class ResendSettings(BaseSettings):
    """Resend API configuration for email delivery."""

    model_config = SettingsConfigDict(env_prefix="RESEND_")

    api_key: str = ""
    webhook_signing_key: str = ""


class ObservabilitySettings(BaseSettings):
    """OpenTelemetry and observability configuration."""

    model_config = SettingsConfigDict(env_prefix="OTEL_")

    exporter_otlp_endpoint: str = "http://localhost:4317"
    service_name: str = "seo-platform-api"

    # Sampling
    trace_sample_rate: float = Field(default=1.0, description="1.0 = 100% sampling in dev")
    error_sample_rate: float = Field(default=1.0, description="Always sample errors")

    # Prometheus
    prometheus_port: int = 9090


class Settings(BaseSettings):
    """
    Root application settings.

    Aggregates all subsystem configurations into a single typed settings object.
    Environment variables are loaded automatically via pydantic-settings.
    """

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent.parent.parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    app_env: Environment = Environment.DEVELOPMENT
    app_debug: bool = True
    app_log_level: LogLevel = LogLevel.DEBUG
    app_secret_key: str = "change-me-to-a-secure-random-string"
    app_name: str = "SEO Operations Platform"
    app_version: str = "0.1.0"

    # --- CORS ---
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
        "http://localhost:8000"
    ]

    # --- Subsystem Settings ---
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    kafka: KafkaSettings = Field(default_factory=KafkaSettings)
    temporal: TemporalSettings = Field(default_factory=TemporalSettings)
    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)
    nvidia: NvidiaSettings = Field(default_factory=NvidiaSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)
    sendgrid: SendGridSettings = Field(default_factory=SendGridSettings)
    dataforseo: DataForSEOSettings = Field(default_factory=DataForSEOSettings)
    ahrefs: AhrefsSettings = Field(default_factory=AhrefsSettings)
    hunter: HunterSettings = Field(default_factory=HunterSettings)
    mailgun: MailgunSettings = Field(default_factory=MailgunSettings)
    resend: ResendSettings = Field(default_factory=ResendSettings)

    # --- Email / SMTP (MailHog for dev) ---
    smtp_host: str = "localhost"
    smtp_port: int = 1025

    # Shared webhook signing key (used by Mailgun/Resend webhook verification)
    email_webhook_signing_key: str = Field(default="", description="HMAC key for email webhook signature verification")

    # --- Operational Modes (Zero-Cost / Production Toggles) ---
    use_mock_providers: bool = Field(default=True, description="Toggle between local scrapers and paid APIs")
    dev_auth_bypass: bool = Field(default=True, description="Bypass auth enforcement for local development")
    test_mode: bool = Field(default=False, description="Enable deterministic test behaviors")

    @property
    def is_production(self) -> bool:
        return self.app_env == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        return self.app_env == Environment.DEVELOPMENT

    @property
    def is_testing(self) -> bool:
        return self.app_env == Environment.TESTING


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Singleton settings factory.

    Returns a cached Settings instance. The cache is invalidated only
    on process restart. This prevents re-reading .env on every request.
    """
    return Settings()
