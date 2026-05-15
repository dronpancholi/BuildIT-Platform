from __future__ import annotations

from fastapi import APIRouter, Body, Query

from seo_platform.services.scraping.scaling import scraping_scale

router = APIRouter()


@router.get("/scraping/browser-pool")
async def get_browser_pool() -> dict:
    status = await scraping_scale.get_browser_pool_status()
    return {"success": True, "data": status.model_dump()}


@router.post("/scraping/scale-browsers")
async def scale_browsers(
    target_size: int = Body(..., embed=True),
) -> dict:
    config = await scraping_scale.scale_browser_pool(target_size)
    return {"success": True, "data": config.model_dump()}


@router.get("/scraping/queue-status")
async def get_queue_status() -> dict:
    status = await scraping_scale.get_scrape_queue_depth()
    return {"success": True, "data": status.model_dump()}


@router.post("/scraping/requeue-failed")
async def requeue_failed() -> dict:
    count = await scraping_scale.requeue_failed_scrapes()
    return {"success": True, "data": {"requeue_count": count}}


@router.get("/scraping/anti-bot")
async def get_anti_bot_status() -> dict:
    status = await scraping_scale.check_anti_bot_status()
    return {"success": True, "data": status.model_dump()}


@router.post("/scraping/rotate-session")
async def rotate_session(
    engine_name: str = Body(..., embed=True),
) -> dict:
    session_id = await scraping_scale.rotate_session(engine_name)
    return {"success": True, "data": {"new_session_id": session_id}}


@router.get("/scraping/extraction-quality")
async def get_extraction_quality(
    time_window_hours: int = Query(24, description="Time window in hours"),
) -> dict:
    report = await scraping_scale.get_extraction_quality(time_window_hours)
    return {"success": True, "data": report.model_dump()}


@router.get("/scraping/selector-degradation")
async def get_selector_degradation(
    time_window_hours: int = Query(24, description="Time window in hours"),
) -> dict:
    report = await scraping_scale.detect_selector_degradation(time_window_hours)
    return {"success": True, "data": report.model_dump()}


@router.post("/scraping/recover-failures")
async def recover_failures() -> dict:
    report = await scraping_scale.recover_scraping_failures()
    return {"success": True, "data": report.model_dump()}


@router.get("/scraping/worker-status")
async def get_worker_status() -> dict:
    workers = await scraping_scale.get_scraping_worker_status()
    return {
        "success": True,
        "data": [w.model_dump() for w in workers],
        "count": len(workers),
    }
