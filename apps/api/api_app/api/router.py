from fastapi import APIRouter

from api_app.features.documents.router import router as documents_router
from api_app.features.system.router import router as system_router

api_router = APIRouter()
api_router.include_router(system_router)
api_router.include_router(documents_router)
