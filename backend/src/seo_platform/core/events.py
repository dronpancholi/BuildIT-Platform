"""
SEO Platform — Event Bus Foundation
======================================
Typed domain event system with Kafka-backed async publishing.

Design principles:
- All events are strongly typed Pydantic models
- Events carry tenant_id, trace_id, and timestamps
- Topic naming: {domain}.{entity}.{event}
- Partition by tenant_id for per-tenant ordering
- Consumer groups per service (bounded context isolation)
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import orjson
from pydantic import BaseModel, Field

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Domain Event Schema
# ---------------------------------------------------------------------------
class DomainEvent(BaseModel):
    """
    Base schema for all domain events in the platform.

    Every event published to Kafka extends this schema, ensuring
    consistent metadata, traceability, and tenant isolation.
    """

    event_id: UUID = Field(default_factory=uuid4, description="Unique event identifier")
    event_type: str = Field(..., description="Event type: {domain}.{entity}.{action}")
    schema_version: str = Field(default="v1", description="Event schema version for migration")
    tenant_id: UUID = Field(..., description="Owning tenant — used as Kafka partition key")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source_service: str = Field(default="", description="Service that emitted this event")
    correlation_id: str | None = Field(default=None, description="Workflow run ID for tracing")
    causation_id: str | None = Field(default=None, description="Event ID that caused this event")
    trace_id: str | None = Field(default=None, description="OpenTelemetry trace ID")
    payload: dict[str, Any] = Field(default_factory=dict, description="Event-specific data")

    def to_kafka_key(self) -> bytes:
        """Partition key: tenant_id ensures per-tenant ordering."""
        return str(self.tenant_id).encode("utf-8")

    def to_kafka_value(self) -> bytes:
        """Serialize event to JSON bytes for Kafka."""
        return orjson.dumps(self.model_dump(mode="json"))

    @classmethod
    def from_kafka_value(cls, data: bytes) -> DomainEvent:
        """Deserialize event from Kafka message value."""
        return cls.model_validate_json(data)


# ---------------------------------------------------------------------------
# Typed Event Definitions
# ---------------------------------------------------------------------------
class ClientOnboardedEvent(DomainEvent):
    """Emitted when a new client completes onboarding."""

    event_type: str = "client.onboarded"


class KeywordResearchCompletedEvent(DomainEvent):
    """Emitted when keyword research workflow completes."""

    event_type: str = "seo.keyword_research.completed"


class ClusterApprovedEvent(DomainEvent):
    """Emitted when keyword clusters are approved."""

    event_type: str = "seo.cluster.approved"


class ProspectDiscoveredEvent(DomainEvent):
    """Emitted when new backlink prospects are discovered."""

    event_type: str = "backlink.prospect.discovered"


class ProspectScoredEvent(DomainEvent):
    """Emitted when prospects are scored and ranked."""

    event_type: str = "backlink.prospect.scored"


class OutreachEmailSentEvent(DomainEvent):
    """Emitted when an outreach email is sent."""

    event_type: str = "backlink.outreach.email_sent"


class OutreachReplyReceivedEvent(DomainEvent):
    """Emitted when a reply to outreach is received."""

    event_type: str = "backlink.outreach.reply_received"


class LinkAcquiredEvent(DomainEvent):
    """Emitted when a backlink is acquired and verified."""

    event_type: str = "backlink.link_acquired"


class ApprovalRequestCreatedEvent(DomainEvent):
    """Emitted when a new approval request is created."""

    event_type: str = "approval.request.created"


class ApprovalDecidedEvent(DomainEvent):
    """Emitted when an approval decision is made."""

    event_type: str = "approval.request.decided"


class CampaignStartedEvent(DomainEvent):
    """Emitted when a campaign is launched."""

    event_type: str = "workflow.campaign.started"


class CampaignCompletedEvent(DomainEvent):
    """Emitted when a campaign reaches terminal state."""

    event_type: str = "workflow.campaign.completed"


# ---------------------------------------------------------------------------
# Event Publisher (Kafka Producer Abstraction)
# ---------------------------------------------------------------------------
class EventPublisher:
    """
    Async Kafka event publisher.

    Abstracts Kafka producer behind a typed interface.
    All domain events are published through this service.

    Usage:
        publisher = EventPublisher()
        await publisher.publish(ClientOnboardedEvent(
            tenant_id=tenant_id,
            payload={"client_id": str(client_id)},
        ))
    """

    def __init__(self) -> None:
        self._producer: Any | None = None

    async def start(self) -> None:
        """Initialize the Kafka producer."""
        from aiokafka import AIOKafkaProducer

        from seo_platform.config import get_settings

        settings = get_settings()
        self._producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka.bootstrap_servers,
            value_serializer=lambda v: v,  # Events pre-serialized
            key_serializer=lambda k: k,    # Keys pre-serialized
            acks="all",                     # Wait for all replicas
            enable_idempotence=True,        # Exactly-once semantics
            max_request_size=1048576,       # 1MB max message
            compression_type="gzip",        # Efficient compression (lz4 has C lib issues)
        )
        await self._producer.start()
        logger.info("event_publisher_started")

    async def stop(self) -> None:
        """Flush and stop the Kafka producer."""
        if self._producer:
            await self._producer.stop()
            logger.info("event_publisher_stopped")

    async def publish(self, event: DomainEvent) -> None:
        """
        Publish a domain event to Kafka.

        Topic is derived from event_type: dots replaced with periods.
        Partition key is tenant_id for per-tenant ordering.
        """
        if self._producer is None:
            logger.warning("event_publisher_not_started", event_type=event.event_type)
            return

        topic = event.event_type.replace(".", "_")  # Kafka topic naming
        try:
            await self._producer.send_and_wait(
                topic=topic,
                key=event.to_kafka_key(),
                value=event.to_kafka_value(),
            )
            logger.info(
                "event_published",
                event_type=event.event_type,
                event_id=str(event.event_id),
                tenant_id=str(event.tenant_id),
                topic=topic,
            )
        except Exception as e:
            logger.error(
                "event_publish_failed",
                event_type=event.event_type,
                error=str(e),
                tenant_id=str(event.tenant_id),
            )
            raise


# ---------------------------------------------------------------------------
# Event Consumer Base
# ---------------------------------------------------------------------------
EventHandler = Callable[[DomainEvent], Coroutine[Any, Any, None]]


class EventConsumer:
    """
    Async Kafka event consumer base class.

    Domain services inherit from this to consume events from specific topics.

    Usage:
        consumer = EventConsumer(
            topics=["client_onboarded", "seo_keyword_research_completed"],
            group_id="backlink-engine-workers",
        )
        consumer.register_handler("client.onboarded", handle_client_onboarded)
        await consumer.start()
    """

    def __init__(self, topics: list[str], group_id: str) -> None:
        self.topics = topics
        self.group_id = group_id
        self._handlers: dict[str, EventHandler] = {}
        self._consumer: Any | None = None

    def register_handler(self, event_type: str, handler: EventHandler) -> None:
        """Register an async handler for a specific event type."""
        self._handlers[event_type] = handler

    async def start(self) -> None:
        """Start consuming messages from registered topics."""
        from aiokafka import AIOKafkaConsumer

        from seo_platform.config import get_settings

        settings = get_settings()
        self._consumer = AIOKafkaConsumer(
            *self.topics,
            bootstrap_servers=settings.kafka.bootstrap_servers,
            group_id=f"{settings.kafka.consumer_group_prefix}-{self.group_id}",
            auto_offset_reset=settings.kafka.auto_offset_reset,
            enable_auto_commit=settings.kafka.enable_auto_commit,
            max_poll_records=settings.kafka.max_poll_records,
            session_timeout_ms=settings.kafka.session_timeout_ms,
            heartbeat_interval_ms=settings.kafka.heartbeat_interval_ms,
        )
        await self._consumer.start()
        logger.info("event_consumer_started", topics=self.topics, group_id=self.group_id)

    async def stop(self) -> None:
        """Stop the consumer."""
        if self._consumer:
            await self._consumer.stop()
            logger.info("event_consumer_stopped")

    async def consume(self) -> None:
        """Main consumption loop — call in an asyncio task."""
        if self._consumer is None:
            raise RuntimeError("Consumer not started")

        async for message in self._consumer:
            try:
                event = DomainEvent.from_kafka_value(message.value)

                from seo_platform.core.reliability import idempotency_store
                event_idem_key = f"event:{event.event_id}"
                if await idempotency_store.exists(event_idem_key):
                    await self._consumer.commit()
                    continue

                handler = self._handlers.get(event.event_type)
                if handler:
                    await handler(event)
                    await idempotency_store.store(event_idem_key, "processed", ttl=86400)
                    await self._consumer.commit()
                    logger.info(
                        "event_processed",
                        event_type=event.event_type,
                        event_id=str(event.event_id),
                    )
                else:
                    logger.warning("no_handler_for_event", event_type=event.event_type)
            except Exception as e:
                logger.error(
                    "event_processing_failed",
                    error=str(e),
                    topic=message.topic,
                    offset=message.offset,
                )
                raise
