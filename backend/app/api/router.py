"""Root API v1 router aggregator (`/api/v1`)."""

from fastapi import APIRouter

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.billing import router as billing_router
from app.api.customer import router as customer_router
from app.api.health import router as health_router
from app.api.kitchen import router as kitchen_router
from app.api.notifications import router as notifications_router
from app.api.public_qr import router as public_qr_router
from app.api.waiter import router as waiter_router
from app.api.ws import router as ws_router

api_v1_router = APIRouter()
api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(public_qr_router)
api_v1_router.include_router(admin_router)
api_v1_router.include_router(customer_router)
api_v1_router.include_router(kitchen_router)
api_v1_router.include_router(waiter_router)
api_v1_router.include_router(billing_router)
api_v1_router.include_router(notifications_router)
api_v1_router.include_router(ws_router)
