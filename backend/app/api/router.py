"""Root API v1 router aggregator (`/api/v1`)."""

from fastapi import APIRouter

from app.api.health import router as health_router

api_v1_router = APIRouter()
api_v1_router.include_router(health_router)
