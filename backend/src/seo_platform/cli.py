"""
SEO Platform — CLI Entry Point
==================================
Management commands for database, workflows, and operations.
"""

from __future__ import annotations

import asyncio

import click

from seo_platform.core.logging import get_logger, setup_logging

logger = get_logger(__name__)


@click.group()
def main() -> None:
    """SEO Operations Platform CLI."""
    setup_logging()


@main.command()
def db_init() -> None:
    """Initialize database and verify connectivity."""
    from seo_platform.core.database import init_database
    asyncio.run(init_database())
    click.echo("✅ Database initialized and connected.")


@main.command()
@click.option("--head", is_flag=True, default=True, help="Migrate to head")
def db_migrate(head: bool) -> None:
    """Run database migrations."""
    import subprocess
    result = subprocess.run(["alembic", "upgrade", "head"], capture_output=True, text=True)
    click.echo(result.stdout)
    if result.returncode != 0:
        click.echo(f"❌ Migration failed:\n{result.stderr}", err=True)
        raise SystemExit(1)
    click.echo("✅ Migrations complete.")


@main.command()
@click.argument("task_queue", default="seo-platform-onboarding")
def worker(task_queue: str) -> None:
    """Start a Temporal worker for a specific task queue."""
    from seo_platform.workflows.worker import run_worker
    click.echo(f"🚀 Starting Temporal worker for queue: {task_queue}")
    asyncio.run(run_worker(task_queue))


@main.command()
@click.option("--host", default="0.0.0.0", help="Bind host")
@click.option("--port", default=8000, help="Bind port")
@click.option("--reload", is_flag=True, default=True, help="Enable hot reload")
def serve(host: str, port: int, reload: bool) -> None:
    """Start the API server."""
    import uvicorn
    click.echo(f"🚀 Starting API server on {host}:{port}")
    uvicorn.run(
        "seo_platform.main:app",
        host=host,
        port=port,
        reload=reload,
    )


@main.command()
@click.argument("switch_key")
@click.option("--reason", "-r", required=True, help="Reason for activation")
@click.option("--ttl", default=None, type=int, help="Auto-reset after N seconds")
def kill_switch_on(switch_key: str, reason: str, ttl: int | None) -> None:
    """Activate a kill switch."""
    from seo_platform.core.kill_switch import kill_switch_service
    asyncio.run(kill_switch_service.activate(switch_key, reason, "cli-admin", ttl))
    click.echo(f"🛑 Kill switch activated: {switch_key}")


@main.command()
@click.argument("switch_key")
def kill_switch_off(switch_key: str) -> None:
    """Deactivate a kill switch."""
    from seo_platform.core.kill_switch import kill_switch_service
    asyncio.run(kill_switch_service.deactivate(switch_key, "cli-admin"))
    click.echo(f"✅ Kill switch deactivated: {switch_key}")


@main.command()
def kill_switch_list() -> None:
    """List all active kill switches."""
    from seo_platform.core.kill_switch import kill_switch_service
    switches = asyncio.run(kill_switch_service.list_active())
    if not switches:
        click.echo("No active kill switches.")
    else:
        for s in switches:
            click.echo(f"  🛑 {s['key']} — {s.get('reason', 'N/A')}")


@main.command()
def health() -> None:
    """Check platform health."""
    import httpx
    try:
        resp = httpx.get("http://localhost:8000/api/v1/health", timeout=5.0)
        data = resp.json()
        status = data.get("status", "unknown")
        icon = "✅" if status == "healthy" else "⚠️" if status == "degraded" else "❌"
        click.echo(f"{icon} Platform status: {status}")
        for comp in data.get("components", []):
            c_icon = "✅" if comp["status"] == "healthy" else "❌"
            click.echo(f"  {c_icon} {comp['name']}: {comp['status']} ({comp.get('latency_ms', '?')}ms)")
    except Exception as e:
        click.echo(f"❌ Could not reach API: {e}", err=True)


if __name__ == "__main__":
    main()
