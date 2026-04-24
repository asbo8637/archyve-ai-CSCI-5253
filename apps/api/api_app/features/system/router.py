from fastapi import APIRouter

from archyve_common.settings import get_settings

router = APIRouter()


@router.get("/healthz")
def healthcheck() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "storage_root": str(settings.storage_root_path)}
