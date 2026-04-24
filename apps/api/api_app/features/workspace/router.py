from fastapi import APIRouter
from archyve_common.settings import get_settings
from api_app.features.workspace.schemas import WorkspaceContextRead

router = APIRouter()


@router.get("/bootstrap", response_model=WorkspaceContextRead)
def get_workspace_context() -> WorkspaceContextRead:
    settings = get_settings()
    return WorkspaceContextRead(
        app_name=settings.app_name,
        auth_enabled=settings.auth0_configured,
    )
