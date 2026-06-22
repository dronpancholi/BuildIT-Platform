"""
SEO Platform — Phase 14 Service: Action Registry
===================================================
Provides CRUD operations for ActionDefinition catalog and helper methods.
"""

from __future__ import annotations

import uuid
from typing import List, Mapping

from sqlalchemy import select

from seo_platform.core.database import get_tenant_session
from seo_platform.models.action import ActionDefinition

class ActionRegistryService:
    """Service managing ActionDefinition records.

    All methods operate within a tenant-isolated DB session.
    """

    async def list_actions(self, tenant_id: uuid.UUID) -> List[ActionDefinition]:
        async with get_tenant_session(tenant_id) as session:
            result = await session.execute(select(ActionDefinition).where(ActionDefinition.tenant_id == tenant_id))
            return result.scalars().all()

    async def get_action(self, tenant_id: uuid.UUID, action_id: uuid.UUID) -> ActionDefinition | None:
        async with get_tenant_session(tenant_id) as session:
            action = await session.get(ActionDefinition, action_id)
            if action and action.tenant_id != tenant_id:
                return None
            return action

    async def create_action(self, tenant_id: uuid.UUID, data: Mapping) -> ActionDefinition:
        async with get_tenant_session(tenant_id) as session:
            action = ActionDefinition(tenant_id=tenant_id, **data)
            session.add(action)
            await session.flush()
            await session.refresh(action)
            return action

    async def update_action(self, tenant_id: uuid.UUID, action_id: uuid.UUID, data: Mapping) -> ActionDefinition:
        async with get_tenant_session(tenant_id) as session:
            action = await session.get(ActionDefinition, action_id)
            if not action or action.tenant_id != tenant_id:
                raise ValueError("Action not found")
            for key, value in data.items():
                if hasattr(action, key):
                    setattr(action, key, value)
            await session.flush()
            await session.refresh(action)
            return action

    async def disable_action(self, tenant_id: uuid.UUID, action_id: uuid.UUID) -> ActionDefinition:
        return await self.update_action(tenant_id, action_id, {"is_enabled": False})

# Export a singleton instance for DI
action_registry_service = ActionRegistryService()
