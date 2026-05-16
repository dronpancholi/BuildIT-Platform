"""
SEO Platform — Qdrant Vector Store
=====================================
Asynchronous vector store for prospect content and keyword cluster embeddings.
Calculates cosine similarity for topical relevance matching.

Uses NVIDIA NIM nv-embedqa-e5-v5 for embeddings (1024-dim).
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from qdrant_client import AsyncQdrantClient, models

from seo_platform.config import get_settings
from seo_platform.core.logging import get_logger

logger = get_logger(__name__)

VECTOR_SIZE = 1024  # nv-embedqa-e5-v5 output dimension


class QdrantVectorStoreError(Exception):
    """Base exception for Qdrant vector store errors."""


class QdrantVectorStore:
    """
    Asynchronous Qdrant vector store for prospect content and keyword clusters.

    Collections:
    - prospect_content: embeddings of scraped prospect markdown
    - client_keywords: embeddings of keyword cluster summaries
    """

    PROSPECT_COLLECTION = "prospect_content"
    KEYWORD_COLLECTION = "client_keywords"

    def __init__(self) -> None:
        settings = get_settings()
        self._client: AsyncQdrantClient | None = None
        self._qdrant_host = settings.qdrant.host
        self._qdrant_port = settings.qdrant.port
        self._qdrant_api_key = settings.qdrant.api_key or None
        self._initialized = False

    async def _get_client(self) -> AsyncQdrantClient:
        if self._client is None:
            self._client = AsyncQdrantClient(
                host=self._qdrant_host,
                port=self._qdrant_port,
                api_key=self._qdrant_api_key,
                prefer_grpc=True,
            )
        return self._client

    async def initialize(self) -> None:
        """Ensure required collections exist with correct vector config."""
        if self._initialized:
            return
        client = await self._get_client()
        for collection in (self.PROSPECT_COLLECTION, self.KEYWORD_COLLECTION):
            try:
                existing = await client.collection_exists(collection)
                if not existing:
                    await client.create_collection(
                        collection_name=collection,
                        vectors_config=models.VectorParams(
                            size=VECTOR_SIZE,
                            distance=models.Distance.COSINE,
                        ),
                    )
                    logger.info("qdrant_collection_created", collection=collection)
            except Exception as e:
                logger.warning("qdrant_collection_init_failed", collection=collection, error=str(e))
        self._initialized = True

    async def _generate_embedding(self, text: str) -> list[float]:
        """
        Generate embedding vector for text using NVIDIA NIM embedding API.
        Returns 1024-dim float vector. Falls back to zero vector when API is unavailable.
        """
        settings = get_settings()
        api_key = settings.nvidia.api_key
        api_url = settings.nvidia.api_url.rstrip("/")
        model = settings.nvidia.embedding_model

        if not api_key:
            logger.info("embedding_skipped_no_nim_key")
            return [0.0] * VECTOR_SIZE

        try:
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{api_url}/embeddings",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "input": text[:8000],
                        "model": model,
                    },
                )
                if response.status_code in (401, 403):
                    logger.warning("nim_embedding_auth_failed")
                    return [0.0] * VECTOR_SIZE
                response.raise_for_status()
                data = response.json()
                embedding = data["data"][0]["embedding"]
                if len(embedding) != VECTOR_SIZE:
                    embedding = self._pad_or_truncate(embedding, VECTOR_SIZE)
                return embedding
        except Exception as e:
            logger.warning("embedding_generation_failed", error=str(e))
            return [0.0] * VECTOR_SIZE

    def _pad_or_truncate(self, vec: list[float], size: int) -> list[float]:
        if len(vec) > size:
            return vec[:size]
        return vec + [0.0] * (size - len(vec))

    async def _point_exists(self, collection: str, point_id: str) -> bool:
        """Check if a point with given ID exists in the collection."""
        client = await self._get_client()
        try:
            points = await client.retrieve(
                collection_name=collection,
                ids=[point_id],
            )
            return len(points) > 0
        except Exception:
            return False

    async def upsert_prospect_content(
        self,
        tenant_id: UUID,
        domain: str,
        markdown_content: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Generate embedding for scraped prospect content and upsert into Qdrant.

        Args:
            tenant_id: Tenant UUID
            domain: Prospect domain (used as point ID)
            markdown_content: Scraped markdown body
            metadata: Additional metadata to store

        Returns:
            True if upsert succeeded, False otherwise.
        """
        await self.initialize()
        point_id = f"{tenant_id}:{domain}"

        if not markdown_content.strip():
            logger.info("skipping_empty_prospect_content", domain=domain)
            return False

        embedding = await self._generate_embedding(markdown_content[:8000])
        payload: dict[str, Any] = {
            "tenant_id": str(tenant_id),
            "domain": domain,
            **(metadata or {}),
        }

        client = await self._get_client()
        try:
            await client.upsert(
                collection_name=self.PROSPECT_COLLECTION,
                points=[
                    models.PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload=payload,
                    )
                ],
            )
            logger.info("prospect_content_upserted", domain=domain)
            return True
        except Exception as e:
            logger.warning("prospect_upsert_failed", domain=domain, error=str(e))
            return False

    async def upsert_keyword_cluster(
        self,
        tenant_id: UUID,
        cluster_id: str,
        keywords: list[str],
    ) -> bool:
        """
        Generate embedding for keyword cluster and upsert into Qdrant.

        Args:
            tenant_id: Tenant UUID
            cluster_id: Keyword cluster identifier
            keywords: List of keywords in the cluster

        Returns:
            True if upsert succeeded, False otherwise.
        """
        await self.initialize()
        point_id = f"{tenant_id}:{cluster_id}"
        text = ", ".join(keywords)

        if not text.strip():
            return False

        embedding = await self._generate_embedding(text)

        client = await self._get_client()
        try:
            await client.upsert(
                collection_name=self.KEYWORD_COLLECTION,
                points=[
                    models.PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload={
                            "tenant_id": str(tenant_id),
                            "cluster_id": cluster_id,
                            "keywords_count": len(keywords),
                        },
                    )
                ],
            )
            logger.info("keyword_cluster_upserted", cluster_id=cluster_id, keywords=len(keywords))
            return True
        except Exception as e:
            logger.warning("keyword_cluster_upsert_failed", cluster_id=cluster_id, error=str(e))
            return False

    async def calculate_topical_relevance(
        self,
        tenant_id: UUID,
        prospect_domain: str,
        keyword_cluster_id: str,
    ) -> float:
        """
        Calculate cosine similarity between prospect content and keyword cluster.

        Returns 0.0–1.0 similarity score. Returns 0.5 (neutral) if either
        vector is not found or computation fails.
        """
        await self.initialize()
        client = await self._get_client()

        prospect_point_id = f"{tenant_id}:{prospect_domain}"
        keyword_point_id = f"{tenant_id}:{keyword_cluster_id}"

        try:
            prospect_points = await client.retrieve(
                collection_name=self.PROSPECT_COLLECTION,
                ids=[prospect_point_id],
                with_vectors=True,
            )
            keyword_points = await client.retrieve(
                collection_name=self.KEYWORD_COLLECTION,
                ids=[keyword_point_id],
                with_vectors=True,
            )

            if not prospect_points or not keyword_points:
                logger.info(
                    "topical_relevance_vectors_missing",
                    prospect_domain=prospect_domain,
                    keyword_cluster_id=keyword_cluster_id,
                )
                return 0.5

            p_vec = prospect_points[0].vector
            k_vec = keyword_points[0].vector
            if not p_vec or not k_vec:
                return 0.5

            # Cosine similarity
            import math
            dot = sum(a * b for a, b in zip(p_vec, k_vec, strict=False))
            norm_p = math.sqrt(sum(a * a for a in p_vec))
            norm_k = math.sqrt(sum(b * b for b in k_vec))
            if norm_p == 0 or norm_k == 0:
                return 0.5

            similarity = dot / (norm_p * norm_k)
            # Clamp to [0, 1] from [-1, 1]
            clamped = max(0.0, min(1.0, similarity))
            logger.info(
                "topical_relevance_calculated",
                prospect_domain=prospect_domain,
                score=round(clamped, 4),
            )
            return round(clamped, 4)

        except Exception as e:
            logger.warning("topical_relevance_failed", error=str(e))
            return 0.5

    async def search_similar_prospects(
        self,
        tenant_id: UUID,
        query_text: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Search prospect content by semantic similarity.

        Args:
            tenant_id: Tenant filter
            query_text: Natural language query
            limit: Max results

        Returns:
            List of matching prospect payloads with scores.
        """
        await self.initialize()
        client = await self._get_client()
        query_vector = await self._generate_embedding(query_text)

        try:
            results = await client.search(
                collection_name=self.PROSPECT_COLLECTION,
                query_vector=query_vector,
                query_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="tenant_id",
                            match=models.MatchValue(value=str(tenant_id)),
                        )
                    ],
                ),
                limit=limit,
            )
            return [
                {
                    "domain": hit.payload.get("domain", ""),
                    "score": round(hit.score, 4),
                    **(hit.payload or {}),
                }
                for hit in results
            ]
        except Exception as e:
            logger.warning("prospect_search_failed", error=str(e))
            return []


qdrant_vector_store = QdrantVectorStore()
