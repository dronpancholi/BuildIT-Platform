from fastapi import APIRouter

from .events import router as realtime_router

# Combine routers
api_router = APIRouter()
api_router.include_router(realtime_router, prefix="/realtime", tags=["realtime"])
