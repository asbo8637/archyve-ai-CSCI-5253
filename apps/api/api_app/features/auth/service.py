from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from archyve_common.db import get_session
from archyve_common.models import Company, CompanyMembership, User

from api_app.features.companies.service import create_company
from api_app.integrations.auth import (
    AuthenticatedPrincipal,
    TokenIdentity,
    get_token_identity,
    permissions_for_role,
)


@dataclass(frozen=True)
class SessionMembership:
    company_id: UUID
    company_name: str
    role: str
    status: str


@dataclass(frozen=True)
class AuthenticatedContext:
    user: User
    memberships: tuple[SessionMembership, ...]
    active_membership: SessionMembership | None
    permissions: tuple[str, ...]
    needs_company_setup: bool
    company_selection_required: bool


def get_authenticated_context(
    session: Session = Depends(get_session),
    token_identity: TokenIdentity = Depends(get_token_identity),
) -> AuthenticatedContext:
    user = sync_user_from_identity(session, token_identity)
    return build_user_context(session, user)


def get_current_principal(
    context: AuthenticatedContext = Depends(get_authenticated_context),
) -> AuthenticatedPrincipal:
    if context.needs_company_setup:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "membership_required",
                "message": "Create or join a company to continue.",
            },
        )

    if context.company_selection_required or context.active_membership is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "company_selection_required",
                "message": "Select a company to continue.",
            },
        )

    return AuthenticatedPrincipal(
        user_id=context.user.id,
        auth0_user_id=context.user.auth0_user_id or "",
        company_id=context.active_membership.company_id,
        membership_role=context.active_membership.role,
        permissions=context.permissions,
    )


def require_company_role(role: str):
    def dependency(
        principal: AuthenticatedPrincipal = Depends(get_current_principal),
    ) -> AuthenticatedPrincipal:
        if principal.membership_role != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "insufficient_role",
                    "message": f"The '{role}' role is required for this action.",
                },
            )

        return principal

    return dependency


def sync_user_from_identity(session: Session, token_identity: TokenIdentity) -> User:
    user = session.scalar(
        select(User).where(User.auth0_user_id == token_identity.auth0_user_id)
    )
    normalized_email = normalize_email(token_identity.email)

    if user is None:
        user = User(
            auth0_user_id=token_identity.auth0_user_id,
            email=normalized_email,
            full_name=token_identity.full_name,
            status="active",
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    has_changes = False
    if normalized_email and normalized_email != user.email:
        user.email = normalized_email
        has_changes = True

    if token_identity.full_name and token_identity.full_name != user.full_name:
        user.full_name = token_identity.full_name
        has_changes = True

    if has_changes:
        session.commit()
        session.refresh(user)

    return user


def build_user_context(session: Session, user: User) -> AuthenticatedContext:
    memberships = tuple(load_memberships(session, user.id))
    active_membership = resolve_active_membership(session, user, memberships)
    return AuthenticatedContext(
        user=user,
        memberships=memberships,
        active_membership=active_membership,
        permissions=permissions_for_role(active_membership.role if active_membership else None),
        needs_company_setup=len(memberships) == 0,
        company_selection_required=len(memberships) > 1 and active_membership is None,
    )


def create_company_for_user(
    session: Session,
    *,
    user: User,
    company_name: str,
) -> AuthenticatedContext:
    existing_memberships = load_memberships(session, user.id)
    if existing_memberships:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "company_already_exists_for_user",
                "message": "This user already belongs to a company.",
            },
        )

    company = create_company(session, name=company_name)
    membership = CompanyMembership(
        company_id=company.id,
        user_id=user.id,
        role="admin",
        status="active",
    )
    user.last_active_company_id = company.id
    session.add(membership)
    session.commit()
    session.refresh(user)
    return build_user_context(session, user)


def select_company_for_user(
    session: Session,
    *,
    user: User,
    company_id: UUID,
) -> AuthenticatedContext:
    memberships = load_memberships(session, user.id)
    if all(membership.company_id != company_id for membership in memberships):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "membership_required",
                "message": "You do not have access to that company.",
            },
        )

    if user.last_active_company_id != company_id:
        user.last_active_company_id = company_id
        session.commit()
        session.refresh(user)

    return build_user_context(session, user)


def load_memberships(session: Session, user_id: UUID) -> list[SessionMembership]:
    statement = (
        select(CompanyMembership, Company)
        .join(Company, Company.id == CompanyMembership.company_id)
        .where(CompanyMembership.user_id == user_id)
        .where(CompanyMembership.status == "active")
        .where(Company.status == "active")
        .order_by(Company.name.asc())
    )
    rows = session.execute(statement).all()
    return [
        SessionMembership(
            company_id=membership.company_id,
            company_name=company.name,
            role=membership.role,
            status=membership.status,
        )
        for membership, company in rows
    ]


def resolve_active_membership(
    session: Session,
    user: User,
    memberships: tuple[SessionMembership, ...],
) -> SessionMembership | None:
    if not memberships:
        if user.last_active_company_id is not None:
            user.last_active_company_id = None
            session.commit()
            session.refresh(user)
        return None

    memberships_by_company = {
        membership.company_id: membership for membership in memberships
    }
    if user.last_active_company_id is not None:
        active_membership = memberships_by_company.get(user.last_active_company_id)
        if active_membership is not None:
            return active_membership

        user.last_active_company_id = None
        session.commit()
        session.refresh(user)

    if len(memberships) == 1:
        only_membership = memberships[0]
        user.last_active_company_id = only_membership.company_id
        session.commit()
        session.refresh(user)
        return only_membership

    return None


def normalize_email(email: str | None) -> str | None:
    if email is None:
        return None

    normalized = email.strip().lower()
    return normalized or None
