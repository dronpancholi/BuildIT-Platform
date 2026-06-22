"""
SEO Platform — Phase 14 Model: Contact
===================================================
Stores CRM contact records linked to a client.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from seo_platform.core.database import Base
from seo_platform.models.base import TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin

class Contact(Base, UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin):
    """CRM contact record.

    Email is unique per tenant. Domain is derived from email.
    """
    __tablename__ = "contacts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_contact_tenant_email"),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)

    client: Mapped["Client"] = relationship("Client", back_populates="contacts")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Contact {self.tenant_id}:{self.email}>"
