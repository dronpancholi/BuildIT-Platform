"""Stub qdrant_client module for testing.
Provides minimal AsyncQdrantClient and related model classes to satisfy imports.
"""

from __future__ import annotations

# Export a placeholder AsyncQdrantClient that implements the async methods used.

class AsyncQdrantClient:
    def __init__(self, *args, **kwargs):
        pass

    async def collection_exists(self, collection_name: str) -> bool:
        return False

    async def create_collection(self, collection_name: str, vectors_config):
        return None

    async def upsert(self, collection_name: str, points):
        return None

    async def retrieve(self, collection_name: str, ids, **kwargs):
        return []

    async def search(self, collection_name: str, query_vector, query_filter, limit: int):
        return []

# Export the models submodule
from . import models
