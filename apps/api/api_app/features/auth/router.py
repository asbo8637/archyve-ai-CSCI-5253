from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from archyve_common.db import get_session

from api_app.features.auth.schemas import (
    ActiveCompanyRead,
    AuthSessionMembershipRead,
    AuthSessionRead,
    AuthSessionUserRead,
    CreateCompanyRequest,
    SelectCompanyRequest,
)
from api_app.features.auth.service import (
    AuthenticatedContext,
    create_company_for_user,
    get_authenticated_context,
    select_company_for_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/session", response_model=AuthSessionRead)
def get_auth_session(
    context: AuthenticatedContext = Depends(get_authenticated_context),
) -> AuthSessionRead:
    return serialize_auth_session(context)


@router.post("/onboarding/create-company", response_model=AuthSessionRead)
def create_onboarding_company(
    payload: CreateCompanyRequest,
    session: Session = Depends(get_session),
    context: AuthenticatedContext = Depends(get_authenticated_context),
) -> AuthSessionRead:
    next_context = create_company_for_user(
        session,
        user=context.user,
        company_name=payload.name,
    )
    return serialize_auth_session(next_context)


@router.post("/session/select-company", response_model=AuthSessionRead)
def select_company(
    payload: SelectCompanyRequest,
    session: Session = Depends(get_session),
    context: AuthenticatedContext = Depends(get_authenticated_context),
) -> AuthSessionRead:
    next_context = select_company_for_user(
        session,
        user=context.user,
        company_id=payload.company_id,
    )
    return serialize_auth_session(next_context)


def serialize_auth_session(context: AuthenticatedContext) -> AuthSessionRead:
    active_company = None
    if context.active_membership is not None:
        active_company = ActiveCompanyRead(
            id=context.active_membership.company_id,
            name=context.active_membership.company_name,
            role=context.active_membership.role,
        )

    return AuthSessionRead(
        user=AuthSessionUserRead(
            id=context.user.id,
            auth0_user_id=context.user.auth0_user_id or "",
            email=context.user.email,
            full_name=context.user.full_name,
            status=context.user.status,
        ),
        memberships=[
            AuthSessionMembershipRead(
                company_id=membership.company_id,
                company_name=membership.company_name,
                role=membership.role,
                status=membership.status,
            )
            for membership in context.memberships
        ],
        active_company=active_company,
        permissions=list(context.permissions),
        needs_company_setup=context.needs_company_setup,
        company_selection_required=context.company_selection_required,
    )
