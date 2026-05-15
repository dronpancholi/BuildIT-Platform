"""
SEO Platform — Real-Time Queue & Infrastructure Telemetry
===========================================================
Exposes live operational metrics from Temporal, Kafka, and workers.
All data originates from real infrastructure state — no simulation.
"""

from __future__ import annotations

import subprocess
import time
from typing import Any

from fastapi import APIRouter

router = APIRouter()


@router.get("/test")
async def test_endpoint() -> dict[str, Any]:
    """Simple test endpoint to verify routing works."""
    return {"success": True, "message": "Telemetry routing works"}


async def _get_temporal_workflows() -> dict[str, Any]:
    """Get workflow counts via Temporal Python SDK."""
    from temporalio.client import Client

    from seo_platform.config import get_settings

    print("DEBUG: Starting _get_temporal_workflows", flush=True)
    settings = get_settings()
    print(f"DEBUG: Settings loaded, target={settings.temporal.target}", flush=True)
    try:
        print("DEBUG: Connecting to Temporal...", flush=True)
        client = await Client.connect(settings.temporal.target, namespace=settings.temporal.namespace)
        print("DEBUG: Connected to Temporal", flush=True)

        workflow_types: dict[str, int] = {}
        status_counts: dict[str, int] = {}
        queue_workflows: dict[str, int] = {}
        count = 0

        print("DEBUG: Listing workflows...", flush=True)
        async for wf in client.list_workflows():
            count += 1
            if count > 100:
                break
            status = wf.status.name
            status_counts[status] = status_counts.get(status, 0) + 1
            if status == "RUNNING":
                workflow_types[wf.workflow_type] = workflow_types.get(wf.workflow_type, 0) + 1
                if wf.task_queue:
                    queue_workflows[wf.task_queue] = queue_workflows.get(wf.task_queue, 0) + 1

        print(f"DEBUG: Listed {count} workflows, {status_counts.get('RUNNING', 0)} running", flush=True)

        return {
            "success": True,
            "data": {
                "running_workflows": status_counts.get("RUNNING", 0),
                "completed_workflows": status_counts.get("COMPLETED", 0),
                "failed_workflows": status_counts.get("FAILED", 0),
                "workflow_types": workflow_types,
                "queue_workflows": queue_workflows,
                "timestamp": time.time(),
            },
        }
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"DEBUG: WORKFLOW LIST FAILED: {e}", flush=True)
        print(f"DEBUG: TRACEBACK: {tb}", flush=True)
        return {
            "success": False,
            "error": str(e)[:200],
            "data": {"running_workflows": 0, "completed_workflows": 0, "failed_workflows": 0, "workflow_types": {}, "queue_workflows": {}},
        }


@router.get("/queue-telemetry")
async def get_queue_telemetry() -> dict[str, Any]:
    """
    Real Temporal queue telemetry from the server.
    """
    workflows = await _get_temporal_workflows()
    if not workflows.get("success"):
        return workflows

    data = workflows["data"]
    known_queues = [
        "onboarding",
        "seo-intelligence",
        "backlink-engine",
        "communication",
        "reporting",
        "ai-orchestration",
    ]

    # Map task queues to short names
    queue_map = {
        "seo-platform-onboarding": "onboarding",
        "seo-platform-seo-intelligence": "seo-intelligence",
        "seo-platform-backlink-engine": "backlink-engine",
        "seo-platform-communication": "communication",
        "seo-platform-reporting": "reporting",
        "seo-platform-ai-orchestration": "ai-orchestration",
    }

    queues = {q: {"depth": 0, "active_workflows": 0, "pending_activities": 0} for q in known_queues}

    for full_queue, count in data.get("queue_workflows", {}).items():
        short_name = queue_map.get(full_queue, full_queue.replace("seo-platform-", ""))
        if short_name in queues:
            queues[short_name]["active_workflows"] = count
            queues[short_name]["depth"] = count

    return {
        "success": True,
        "data": {
            "queues": queues,
            "total_active_workflows": data.get("running_workflows", 0),
            "timestamp": time.time(),
        },
    }


@router.get("/kafka-telemetry")
async def get_kafka_telemetry() -> dict[str, Any]:
    """
    Real Kafka consumer group telemetry from the broker.
    """
    try:
        result = subprocess.run(
            [
                "docker", "exec", "seo-kafka",
                "/usr/bin/kafka-consumer-groups",
                "--describe",
                "--group", "seo-platform-workflow-workers",
                "--bootstrap-server", "localhost:9092",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        topics = {}
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if line.startswith("GROUP") or line.startswith("Error") or not line.strip():
                    continue
                parts = line.split()
                if len(parts) >= 6:
                    try:
                        topic = parts[1]
                        current_offset = int(parts[3]) if parts[3] != "-" else 0
                        log_end_offset = int(parts[4]) if parts[4] != "-" else 0
                        lag = int(parts[5]) if parts[5] != "-" else 0
                        topics[topic] = {
                            "current_offset": current_offset,
                            "log_end_offset": log_end_offset,
                            "lag": lag,
                        }
                    except (ValueError, IndexError):
                        continue
    except Exception as e:
        return {
            "success": False,
            "error": str(e)[:200],
            "data": {"topics": {}, "consumer_groups": [], "total_lag": 0},
        }

    try:
        result = subprocess.run(
            [
                "docker", "exec", "seo-kafka",
                "/usr/bin/kafka-consumer-groups",
                "--list",
                "--bootstrap-server", "localhost:9092",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        consumer_groups = [g.strip() for g in result.stdout.strip().split("\n") if g.strip()]
    except Exception:
        consumer_groups = []

    return {
        "success": True,
        "data": {
            "topics": topics,
            "consumer_groups": consumer_groups,
            "total_lag": sum(t.get("lag", 0) for t in topics.values()),
            "timestamp": time.time(),
        },
    }


@router.get("/worker-telemetry")
async def get_worker_telemetry() -> dict[str, Any]:
    """
    Real worker telemetry from Temporal.
    """
    return await _get_temporal_workflows()
