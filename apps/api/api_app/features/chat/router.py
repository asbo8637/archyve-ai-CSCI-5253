from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from archyve_common.db import get_session

from api_app.features.auth.service import get_current_principal
from api_app.integrations.auth import AuthenticatedPrincipal
from api_app.features.chat.schemas import AskRequest, AskResponse
from api_app.features.chat.service import answer_question

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/ask", response_model=AskResponse)
async def ask(
    request: AskRequest,
    session: Session = Depends(get_session),
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> AskResponse:
    result = answer_question(session, company_id=principal.company_id, question=request.question)
    return AskResponse(answer=result.answer, sources=list(result.cited_sources))
