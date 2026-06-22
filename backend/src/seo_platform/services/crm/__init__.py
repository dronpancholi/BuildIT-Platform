"""
SEO Platform — CRM Service
==============================
Contact management, deal pipeline, and activity tracking.
"""

from __future__ import annotations

from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


class CRMService:
    """Contact and relationship management. Consumes events from backlink/communication services."""

    async def upsert_contact(self, tenant_id: str, client_id: str, email: str, name: str) -> dict:
        """Create or update a contact for the given tenant and client.

        The domain is derived from the email address.
        """
        import uuid
        from seo_platform.core.database import get_tenant_session
        from seo_platform.models.contact import Contact
        from sqlalchemy import select

        logger.info("contact_upserted", email_domain=email.split("@")[-1], tenant_id=tenant_id)
        domain = email.split("@")[-1]
        async with get_tenant_session(uuid.UUID(tenant_id)) as session:
            stmt = select(Contact).where(Contact.email == email, Contact.tenant_id == uuid.UUID(tenant_id))
            result = await session.execute(stmt)
            contact = result.scalar_one_or_none()
            if contact:
                contact.name = name
                contact.domain = domain
                await session.flush()
                return {"id": str(contact.id), "status": "updated"}
            else:
                new_contact = Contact(
                    tenant_id=uuid.UUID(tenant_id),
                    client_id=uuid.UUID(client_id),
                    email=email,
                    name=name,
                    domain=domain,
                )
                session.add(new_contact)
                await session.flush()
                await session.refresh(new_contact)
                return {"id": str(new_contact.id), "status": "created"}



crm_service = CRMService()
