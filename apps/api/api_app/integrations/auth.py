from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from archyve_common.db import get_session
from archyve_common.models import Company, CompanyMembership, User
from archyve_common.settings import get_settings


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    user_id: UUID
    company_id: UUID
    membership_role: str


def get_dev_principal(session: Session = Depends(get_session)) -> AuthenticatedPrincipal:
    """Returns a fixed dev principal, bootstrapping the default company/user if needed."""
    settings = get_settings()

    company = session.scalar(select(Company).where(Company.name == settings.default_company_name))
    if company is None:
        company = Company(name=settings.default_company_name, status="active")
        session.add(company)
        session.flush()

    user = session.scalar(select(User).where(User.email == "dev@local"))
    if user is None:
        user = User(
            email="dev@local",
            full_name="Dev User",
            last_active_company_id=company.id,
            status="active",
        )
        session.add(user)
        session.flush()

    membership = session.scalar(
        select(CompanyMembership)
        .where(CompanyMembership.company_id == company.id)
        .where(CompanyMembership.user_id == user.id)
    )
    if membership is None:
        membership = CompanyMembership(
            company_id=company.id,
            user_id=user.id,
            role="admin",
            status="active",
        )
        session.add(membership)

    session.commit()
    return AuthenticatedPrincipal(
        user_id=user.id,
        company_id=company.id,
        membership_role=membership.role,
    )
