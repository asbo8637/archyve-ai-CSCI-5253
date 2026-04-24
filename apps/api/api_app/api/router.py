from fastapi import APIRouter

from api_app.features.auth.router import router as auth_router
from api_app.features.documents.router import router as documents_router
from api_app.features.system.router import router as system_router
from api_app.features.workspace.router import router as workspace_router

api_router = APIRouter()
api_router.include_router(system_router)
api_router.include_router(auth_router)
api_router.include_router(workspace_router)
api_router.include_router(documents_router)
