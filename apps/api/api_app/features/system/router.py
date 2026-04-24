from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from archyve_common.db import get_session
from archyve_common.settings import get_settings

router = APIRouter()


@router.get("/healthz")
def healthcheck(session: Session = Depends(get_session)) -> dict[str, str]:
    settings = get_settings()
    session.execute(text("SELECT 1"))
    return {"status": "ok", "db": "ok", "storage_root": str(settings.storage_root_path)}
