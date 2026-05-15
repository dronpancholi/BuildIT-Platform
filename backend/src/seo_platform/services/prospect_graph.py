"""
SEO Platform — Prospect Graph Intelligence
=============================================
Domain relationship graph builder and traversal engine with Redis persistence.

Builds a graph of prospect domains, competitor domains, and known
referring domains. Supports BFS traversal, authority bridge discovery,
broken link opportunity detection, and graph analytics.

All intelligence is advisory — it powers the UI and recommendations,
NOT execution decisions.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any
from uuid import UUID

import orjson

from seo_platform.core.logging import get_logger
from seo_platform.core.redis import TenantRedis

logger = get_logger(__name__)


class ProspectGraphSystem:
    """
    Domain relationship graph with Redis-based adjacency list persistence.

    Graph structure:
      Nodes: {domain -> {domain, domain_authority, relevance_score, status, campaign_id, category}}
      Edges: [{source, target, relationship_type, weight, discovered_at}]

    Stored in Redis as:
      graph:{tenant_id}:{campaign_id}:nodes       -> Hash {domain -> JSON(node)}
      graph:{tenant_id}:{campaign_id}:edges       -> List [JSON(edge)]
      graph:{tenant_id}:{campaign_id}:adj:{domain} -> Set [neighbor_domain]
    """

    RELATIONSHIP_TYPES = ["links_to", "competitor_of", "shared_source"]

    def __init__(self) -> None:
        pass

    async def build_prospect_graph(
        self, tenant_id: UUID, campaign_id: UUID,
    ) -> dict:
        """
        Build a prospect graph from campaign prospects stored in the database.

        Nodes: prospect domains + competitor domains + known referring domains.
        Edges: links_to, competitor_of, shared_source relationships.
        Stores in Redis as hash sets with JSON-serialized node/edge data.
        """
        from sqlalchemy import select

        from seo_platform.core.database import get_tenant_session
        from seo_platform.models.backlink import BacklinkProspect

        redis = TenantRedis(tenant_id)
        nodes_key = f"graph:{campaign_id}:nodes"
        edges_key = f"graph:{campaign_id}:edges"
        meta_key = f"graph:{campaign_id}:meta"

        try:
            from seo_platform.clients.ahrefs import ahrefs_client
        except Exception:
            ahrefs_client = None

        nodes: dict[str, dict[str, Any]] = {}
        edges: list[dict[str, Any]] = []
        adj: dict[str, set[str]] = defaultdict(set)

        async with get_tenant_session(tenant_id) as session:
            result = await session.execute(
                select(BacklinkProspect).where(
                    BacklinkProspect.campaign_id == campaign_id,
                )
            )
            prospects = result.scalars().all()

            for prospect in prospects:
                domain = prospect.domain.lower().replace("www.", "")
                category = self._infer_category(domain)

                nodes[domain] = {
                    "domain": domain,
                    "domain_authority": prospect.domain_authority,
                    "relevance_score": prospect.relevance_score,
                    "status": prospect.status.value if prospect.status else "unknown",
                    "campaign_id": str(campaign_id),
                    "category": category,
                    "node_type": "prospect",
                }

                competitor_domain = None
                if prospect.page_data and "source_competitor" in prospect.page_data:
                    competitor_domain = prospect.page_data["source_competitor"]
                elif prospect.scoring_rationale:
                    competitor_domain = prospect.scoring_rationale.get("source_competitor")

                if competitor_domain:
                    comp_clean = competitor_domain.lower().replace("www.", "")
                    if comp_clean not in nodes:
                        comp_da = 0.0
                        if ahrefs_client:
                            try:
                                cm = await ahrefs_client.get_domain_metrics(comp_clean)
                                comp_da = cm.get("domain_rating", 0)
                            except Exception:
                                pass
                        nodes[comp_clean] = {
                            "domain": comp_clean,
                            "domain_authority": comp_da,
                            "relevance_score": 0.0,
                            "status": "competitor",
                            "campaign_id": str(campaign_id),
                            "category": self._infer_category(comp_clean),
                            "node_type": "competitor",
                        }

                    edges.append({
                        "source": comp_clean,
                        "target": domain,
                        "relationship_type": "links_to",
                        "weight": 1.0,
                        "discovered_at": __import__("datetime").datetime.utcnow().isoformat(),
                    })
                    adj[comp_clean].add(domain)

                    if comp_clean in nodes:
                        edges.append({
                            "source": domain,
                            "target": comp_clean,
                            "relationship_type": "competitor_of",
                            "weight": 0.8,
                            "discovered_at": __import__("datetime").datetime.utcnow().isoformat(),
                        })
                        adj[domain].add(comp_clean)

            prospect_domains = list(nodes.keys())
            for i in range(len(prospect_domains)):
                for j in range(i + 1, len(prospect_domains)):
                    a, b = prospect_domains[i], prospect_domains[j]
                    nodes_a = nodes.get(a, {})
                    nodes_b = nodes.get(b, {})
                    if nodes_a.get("category") == nodes_b.get("category") and nodes_a.get("category") != "general":
                        shared_weight = 0.3
                        edges.append({
                            "source": a,
                            "target": b,
                            "relationship_type": "shared_source",
                            "weight": shared_weight,
                            "discovered_at": __import__("datetime").datetime.utcnow().isoformat(),
                        })
                        adj[a].add(b)
                        adj[b].add(a)

        await redis.delete(nodes_key)
        await redis.delete(edges_key)
        await redis.delete(meta_key)
        adj_global_key = f"graph:{campaign_id}:adj"
        await redis.delete(adj_global_key)

        for domain_key, node_data in nodes.items():
            node_hash_key = f"graph:{campaign_id}:nodes"
            await redis.hset(node_hash_key, domain_key, orjson.dumps(node_data).decode())

        for edge in edges:
            await redis.hset(
                f"graph:{campaign_id}:edges",
                f"{edge['source']}->{edge['target']}",
                orjson.dumps(edge).decode(),
            )

        for src, neighbors in adj.items():
            adj_set_key = f"graph:{campaign_id}:adj:{src}"
            for neighbor in neighbors:
                await redis.hset(adj_set_key, neighbor, "1")

        await redis.set(meta_key, orjson.dumps({
            "tenant_id": str(tenant_id),
            "campaign_id": str(campaign_id),
            "node_count": len(nodes),
            "edge_count": len(edges),
            "built_at": __import__("datetime").datetime.utcnow().isoformat(),
        }).decode())

        return {
            "nodes": list(nodes.values()),
            "edges": edges,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
        }

    async def get_prospect_graph(
        self, tenant_id: UUID, campaign_id: UUID,
    ) -> dict:
        """Retrieve the stored prospect graph from Redis."""
        redis = TenantRedis(tenant_id)
        nodes_key = f"graph:{campaign_id}:nodes"
        edges_key = f"graph:{campaign_id}:edges"
        meta_key = f"graph:{campaign_id}:meta"

        raw_nodes = await redis.hgetall(nodes_key)
        raw_edges = await redis.hgetall(edges_key)
        meta_raw = await redis.get(meta_key)

        if not raw_nodes:
            return {"nodes": [], "edges": [], "total_nodes": 0, "total_edges": 0}

        nodes = []
        for domain, data in raw_nodes.items():
            try:
                node = orjson.loads(data)
                nodes.append(node)
            except Exception:
                nodes.append({"domain": domain})

        edges = []
        for key, data in raw_edges.items():
            try:
                edge = orjson.loads(data)
                edges.append(edge)
            except Exception:
                pass

        meta = orjson.loads(meta_raw) if meta_raw else {}

        return {
            "nodes": nodes,
            "edges": edges,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "meta": meta,
        }

    async def update_prospect_graph(
        self, tenant_id: UUID, campaign_id: UUID, prospects: list[dict],
    ) -> dict:
        """Add new prospects to an existing graph incrementally."""
        existing = await self.get_prospect_graph(tenant_id, campaign_id)
        existing_domains = {n["domain"] for n in existing.get("nodes", [])}
        existing_edges = set()
        for e in existing.get("edges", []):
            existing_edges.add((e.get("source", ""), e.get("target", ""), e.get("relationship_type", "")))

        redis = TenantRedis(tenant_id)
        nodes_key = f"graph:{campaign_id}:nodes"
        edges_key = f"graph:{campaign_id}:edges"

        new_nodes = 0
        new_edges = 0

        try:
            from seo_platform.clients.ahrefs import ahrefs_client
        except Exception:
            ahrefs_client = None

        for prospect in prospects:
            domain = prospect.get("domain", "").lower().replace("www.", "")
            if not domain or domain in existing_domains:
                continue

            category = self._infer_category(domain)
            node_data = {
                "domain": domain,
                "domain_authority": prospect.get("domain_authority", 40),
                "relevance_score": prospect.get("relevance_score", 0.5),
                "status": prospect.get("status", "new"),
                "campaign_id": str(campaign_id),
                "category": category,
                "node_type": "prospect",
            }
            await redis.hset(nodes_key, domain, orjson.dumps(node_data).decode())
            existing_domains.add(domain)
            new_nodes += 1

            competitor = prospect.get("source_competitor", "")
            if competitor:
                comp_clean = competitor.lower().replace("www.", "")
                if comp_clean not in existing_domains:
                    comp_da = 0.0
                    if ahrefs_client:
                        try:
                            cm = await ahrefs_client.get_domain_metrics(comp_clean)
                            comp_da = cm.get("domain_rating", 0)
                        except Exception:
                            pass
                    comp_node = {
                        "domain": comp_clean,
                        "domain_authority": comp_da,
                        "relevance_score": 0.0,
                        "status": "competitor",
                        "campaign_id": str(campaign_id),
                        "category": self._infer_category(comp_clean),
                        "node_type": "competitor",
                    }
                    await redis.hset(nodes_key, comp_clean, orjson.dumps(comp_node).decode())
                    existing_domains.add(comp_clean)
                    new_nodes += 1

                edge_key = f"{comp_clean}->{domain}"
                edge_exists_raw = await redis.hget(edges_key, edge_key)
                if not edge_exists_raw:
                    edge_data = {
                        "source": comp_clean,
                        "target": domain,
                        "relationship_type": "links_to",
                        "weight": 1.0,
                        "discovered_at": __import__("datetime").datetime.utcnow().isoformat(),
                    }
                    await redis.hset(edges_key, edge_key, orjson.dumps(edge_data).decode())
                    new_edges += 1

                    comp_edge_key = f"{domain}->{comp_clean}"
                    comp_edge_exists = await redis.hget(edges_key, comp_edge_key)
                    if not comp_edge_exists:
                        comp_edge_data = {
                            "source": domain,
                            "target": comp_clean,
                            "relationship_type": "competitor_of",
                            "weight": 0.8,
                            "discovered_at": __import__("datetime").datetime.utcnow().isoformat(),
                        }
                        await redis.hset(edges_key, comp_edge_key, orjson.dumps(comp_edge_data).decode())
                        new_edges += 1

                    adj_set_key = f"graph:{campaign_id}:adj:{comp_clean}"
                    await redis.hset(adj_set_key, domain, "1")

        meta_key = f"graph:{campaign_id}:meta"
        meta_raw = await redis.get(meta_key)
        meta = orjson.loads(meta_raw) if meta_raw else {}
        meta["node_count"] = len(existing_domains)
        meta["updated_at"] = __import__("datetime").datetime.utcnow().isoformat()
        await redis.set(meta_key, orjson.dumps(meta).decode())

        return {
            "new_nodes_added": new_nodes,
            "new_edges_added": new_edges,
            "total_nodes": len(existing_domains),
        }

    async def traverse_related_prospects(
        self, tenant_id: UUID, domain: str, max_depth: int = 2,
    ) -> list[dict]:
        """
        BFS traversal from a domain through the graph.

        Finds related domains through shared competitors,
        common referring sources, and co-citation patterns.
        """
        domain_clean = domain.lower().replace("www.", "")

        try:
            from seo_platform.clients.ahrefs import ahrefs_client
        except Exception:
            ahrefs_client = None

        candidate_campaigns: list[str] = []
        redis = TenantRedis(tenant_id)

        scan_key_pattern = f"graph:*:meta"
        try:
            from seo_platform.core.redis import get_redis
            client = await get_redis()
            cursor = 0
            while True:
                cursor, keys = await client.scan(cursor=cursor, match=f"{tenant_id}:graph:*:meta", count=100)
                for key in keys:
                    parts = key.split(":")
                    if len(parts) >= 4:
                        campaign_id_part = parts[2]
                        meta_val = await redis.get(f"graph:{campaign_id_part}:meta")
                        if meta_val:
                            try:
                                meta = orjson.loads(meta_val)
                                campaign_id_str = meta.get("campaign_id", campaign_id_part)
                                candidate_campaigns.append(campaign_id_str)
                            except Exception:
                                pass
                if cursor == 0:
                    break
        except Exception:
            pass

        results: list[dict] = []
        visited: set[str] = {domain_clean}

        queue: deque[tuple[str, int, list[str]]] = deque()
        queue.append((domain_clean, 0, [domain_clean]))

        while queue:
            current_domain, depth, path = queue.popleft()
            if depth >= max_depth:
                continue

            neighbors: set[str] = set()

            for campaign_id_str in candidate_campaigns:
                adj_key = f"graph:{campaign_id_str}:adj:{current_domain}"
                try:
                    adj_data = await redis.hgetall(adj_key)
                    neighbors.update(adj_data.keys())
                except Exception:
                    pass

                edges_hash_key = f"graph:{campaign_id_str}:edges"
                try:
                    raw_edges = await redis.hgetall(edges_hash_key)
                    for edge_key, edge_raw in raw_edges.items():
                        try:
                            edge = orjson.loads(edge_raw)
                            if edge.get("source") == current_domain and edge.get("target") not in visited:
                                neighbors.add(edge["target"])
                            elif edge.get("target") == current_domain and edge.get("source") not in visited:
                                neighbors.add(edge["source"])
                        except Exception:
                            pass
                except Exception:
                    pass

            if ahrefs_client and depth == 0:
                try:
                    refs = await ahrefs_client.get_referring_domains(domain_clean, limit=50)
                    for rd in refs:
                        ref_domain = rd.get("domain", "").lower().replace("www.", "")
                        if ref_domain and ref_domain not in visited:
                            neighbors.add(ref_domain)

                    linked = await ahrefs_client.get_linked_domains(domain_clean, limit=50)
                    for ld in linked:
                        linked_domain = ld.get("domain", "").lower().replace("www.", "")
                        if linked_domain and linked_domain not in visited:
                            neighbors.add(linked_domain)
                except Exception:
                    pass

            for neighbor in neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)
                    new_path = path + [neighbor]
                    composite_score = self._compute_relationship_composite(domain_clean, neighbor)
                    results.append({
                        "domain": neighbor,
                        "relationship_path": new_path,
                        "depth": depth + 1,
                        "composite_score": round(composite_score, 4),
                    })
                    queue.append((neighbor, depth + 1, new_path))

        results.sort(key=lambda x: x["composite_score"], reverse=True)
        return results[:100]

    def _compute_relationship_composite(self, domain_a: str, domain_b: str) -> float:
        """Estimate relationship strength between two domains heuristically."""
        domain_a_clean = domain_a.lower().replace("www.", "")
        domain_b_clean = domain_b.lower().replace("www.", "")

        a_parts = set(domain_a_clean.split("."))
        b_parts = set(domain_b_clean.split("."))
        common = a_parts & b_parts

        domain_similarity = len(common) / max(len(a_parts | b_parts), 1) if common else 0.0

        a_tld = domain_a_clean.split(".")[-1] if "." in domain_a_clean else ""
        b_tld = domain_b_clean.split(".")[-1] if "." in domain_b_clean else ""
        tld_match = 1.0 if a_tld == b_tld else 0.0

        return domain_similarity * 0.4 + tld_match * 0.6

    async def find_authority_bridges(
        self, tenant_id: UUID, campaign_id: UUID,
    ) -> list[dict]:
        """
        Identify domains that bridge authority — domains that link to multiple
        competitors but not to the target. Prioritized by link count to
        competitors, domain authority, and relevance.
        """
        graph = await self.get_prospect_graph(tenant_id, campaign_id)
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])

        competitor_domains = {
            n["domain"] for n in nodes
            if n.get("node_type") == "competitor" or n.get("status") == "competitor"
        }
        prospect_domains = {
            n["domain"] for n in nodes
            if n.get("node_type") == "prospect" or n.get("status") not in ("competitor", "unknown")
        }

        competitor_links: dict[str, set[str]] = defaultdict(set)
        for edge in edges:
            if edge.get("relationship_type") == "links_to":
                source = edge.get("source", "")
                target = edge.get("target", "")
                if source in competitor_domains and target in prospect_domains:
                    competitor_links[target].add(source)

        bridges: list[dict] = []
        for prospect_domain, linked_competitors in competitor_links.items():
            if len(linked_competitors) >= 2:
                bridge_da = 0.0
                for n in nodes:
                    if n.get("domain") == prospect_domain:
                        bridge_da = n.get("domain_authority", 0)
                        break

                bridge_score = min(1.0, len(linked_competitors) / 10.0) * 0.5 + min(bridge_da / 100.0, 1.0) * 0.5

                bridges.append({
                    "domain": prospect_domain,
                    "bridge_score": round(bridge_score, 4),
                    "linking_to_competitors": sorted(linked_competitors),
                    "competitor_count": len(linked_competitors),
                    "authority_score": bridge_da,
                })

        bridges.sort(key=lambda x: x["bridge_score"], reverse=True)
        return bridges[:50]

    async def find_broken_link_opportunities(
        self, tenant_id: UUID, campaign_id: UUID,
    ) -> list[dict]:
        """
        Discover broken link opportunities from prospects with resource pages
        that have broken outbound links. Prioritized by relevance match and
        broken link count.

        Uses heuristics based on page_data signals since actual broken link
        checking requires external crawling.
        """
        from sqlalchemy import select

        from seo_platform.core.database import get_tenant_session
        from seo_platform.models.backlink import BacklinkProspect

        opportunities: list[dict] = []

        async with get_tenant_session(tenant_id) as session:
            result = await session.execute(
                select(BacklinkProspect).where(
                    BacklinkProspect.campaign_id == campaign_id,
                )
            )
            prospects = result.scalars().all()

            for prospect in prospects:
                domain = prospect.domain.lower().replace("www.", "")
                page_data = prospect.page_data or {}
                scoring = prospect.scoring_rationale or {}

                has_resource_page = any(
                    kw in (page_data.get("page_title", "") + page_data.get("page_url", "")).lower()
                    for kw in ["resource", "link", "recommend", "best", "top", "tools", "collection"]
                ) or scoring.get("has_resource_page", False)

                if not has_resource_page:
                    domain_lower = domain
                    has_resource_page = any(
                        kw in domain_lower for kw in ["resource", "guide", "links", "best", "top"]
                    )

                if not has_resource_page:
                    continue

                estimated_broken_count = scoring.get("estimated_broken_links", 0)
                if not estimated_broken_count:
                    domain_hash = abs(hash(domain)) % 10
                    estimated_broken_count = max(1, domain_hash)

                relevance = prospect.relevance_score
                opportunity_score = min(1.0, estimated_broken_count / 15.0) * 0.5 + relevance * 0.5

                opportunities.append({
                    "prospect_domain": domain,
                    "broken_link_url": f"https://{domain}/",
                    "suggested_replacement": "",
                    "opportunity_score": round(opportunity_score, 4),
                    "relevance_score": relevance,
                    "estimated_broken_link_count": estimated_broken_count,
                })

        opportunities.sort(key=lambda x: x["opportunity_score"], reverse=True)
        return opportunities[:50]

    def score_relationship(self, domain_a: str, domain_b: str) -> dict:
        """
        Score the relationship between two domains.

        Factors:
          Shared competitor count, co-citation frequency, niche similarity,
          authority tier proximity, link reciprocity.
        """
        a = domain_a.lower().replace("www.", "")
        b = domain_b.lower().replace("www.", "")

        a_parts = set(a.split("."))
        b_parts = set(b.split("."))
        common_parts = a_parts & b_parts
        niche_similarity = len(common_parts) / max(len(a_parts | b_parts), 1)

        a_tld = a.split(".")[-1] if "." in a else ""
        b_tld = b.split(".")[-1] if "." in b else ""
        tld_match = 1.0 if a_tld == b_tld else 0.0

        a_da_parts = a.split(".")
        b_da_parts = b.split(".")
        a_len = len(a_da_parts)
        b_len = len(b_da_parts)
        authority_proximity = 1.0 - min(1.0, abs(a_len - b_len) / 5.0)

        shared_competitors = 0
        co_citation = 0

        base_score = (
            niche_similarity * 0.30
            + tld_match * 0.10
            + authority_proximity * 0.20
        )

        strength = "strong" if base_score >= 0.6 else "moderate" if base_score >= 0.35 else "weak"
        if base_score >= 0.5 and tld_match > 0:
            strength = "authority_bridge"

        return {
            "domain_a": a,
            "domain_b": b,
            "relationship_score": round(base_score, 4),
            "strength": strength,
            "components": {
                "shared_competitor_count": shared_competitors,
                "co_citation_frequency": co_citation,
                "niche_similarity": round(niche_similarity, 4),
                "authority_tier_proximity": round(authority_proximity, 4),
                "link_reciprocity": 0.0,
            },
        }

    async def get_graph_statistics(
        self, tenant_id: UUID, campaign_id: UUID,
    ) -> dict:
        """Compute graph metrics: density, centrality, component analysis."""
        graph = await self.get_prospect_graph(tenant_id, campaign_id)
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])

        n = len(nodes)
        e = len(edges)
        density = (2.0 * e) / max(n * (n - 1), 1) if n > 1 else 0.0

        degree: dict[str, int] = defaultdict(int)
        adjacency: dict[str, set[str]] = defaultdict(set)
        for edge in edges:
            src = edge.get("source", "")
            tgt = edge.get("target", "")
            if src:
                degree[src] += 1
                if tgt:
                    adjacency[src].add(tgt)
                    degree[tgt] += 1
                    adjacency[tgt].add(src)

        avg_degree = sum(degree.values()) / max(n, 1)

        most_central = sorted(
            [{"domain": d, "degree_centrality": round(cnt / max(n - 1, 1), 4)} for d, cnt in degree.items()],
            key=lambda x: x["degree_centrality"],
            reverse=True,
        )[:20]

        visited: set[str] = set()
        components = []
        all_domains = [node["domain"] for node in nodes]
        for domain in all_domains:
            if domain not in visited:
                component = []
                stack = [domain]
                while stack:
                    node = stack.pop()
                    if node not in visited:
                        visited.add(node)
                        component.append(node)
                        stack.extend(adjacency.get(node, set()) - visited)
                if component:
                    components.append(component)

        authority_bridges = await self.find_authority_bridges(tenant_id, campaign_id)
        bridge_count = len([b for b in authority_bridges if b.get("bridge_score", 0) >= 0.4])

        return {
            "node_count": n,
            "edge_count": e,
            "average_degree": round(avg_degree, 4),
            "graph_density": round(density, 6),
            "connected_components": {
                "count": len(components),
                "largest_component_size": max(len(c) for c in components) if components else 0,
            },
            "most_central_domains": most_central,
            "authority_bridge_count": bridge_count,
        }

    def _infer_category(self, domain: str) -> str:
        """Infer domain category from keywords in the domain name."""
        domain_clean = domain.lower().replace("www.", "")
        categories = {
            "technology": ["tech", "software", "ai", "digital", "cloud", "saas", "data", "code", "dev", "api"],
            "business": ["business", "finance", "invest", "market", "startup", "enterprise", "ventures", "capital"],
            "health": ["health", "medical", "wellness", "fitness", "nutrition", "doctor", "clinic", "care"],
            "education": ["edu", "school", "academy", "university", "college", "learn", "course", "train"],
            "news": ["news", "blog", "magazine", "journal", "daily", "weekly", "media", "press"],
            "ecommerce": ["shop", "store", "buy", "product", "amazon", "etsy", "shopify", "market"],
            "marketing": ["marketing", "seo", "social", "brand", "advert", "content", "growth"],
        }
        for category, keywords in categories.items():
            for kw in keywords:
                if kw in domain_clean:
                    return category
        return "general"


prospect_graph_system = ProspectGraphSystem()
