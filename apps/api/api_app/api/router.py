from fastapi import APIRouter

from api_app.features.system.router import router as system_router

api_router = APIRouter()
api_router.include_router(system_router)
