from uuid import uuid4

import pytest
from fastapi import HTTPException

from archyve_common.models import Company, CompanyMembership, User

from api_app.features.auth import service as auth_service
from api_app.integrations.auth import TokenIdentity


class RecordingSession:
    def __init__(self, existing_user: User | None = None) -> None:
        self.added = []
        self.commits = 0
        self.existing_user = existing_user
        self.refreshed = []

    def add(self, obj) -> None:
        self.added.append(obj)

    def commit(self) -> None:
        self.commits += 1

    def refresh(self, obj) -> None:
        self.refreshed.append(obj)

    def scalar(self, _statement):
        return self.existing_user


def test_sync_user_from_identity_creates_user() -> None:
    session = RecordingSession()

    user = auth_service.sync_user_from_identity(
        session,
        TokenIdentity(
            auth0_user_id="auth0|abc",
            email="PERSON@EXAMPLE.COM ",
            full_name="Person Example",
            email_verified=True,
            claims={},
        ),
    )

    assert user.auth0_user_id == "auth0|abc"
    assert user.email == "person@example.com"
    assert user.full_name == "Person Example"
    assert session.commits == 1
    assert session.refreshed == [user]


def test_sync_user_from_identity_updates_existing_user() -> None:
    existing_user = User(
        id=uuid4(),
        auth0_user_id="auth0|abc",
        email="old@example.com",
        full_name="Old Name",
        status="active",
    )
    session = RecordingSession(existing_user=existing_user)

    user = auth_service.sync_user_from_identity(
        session,
        TokenIdentity(
            auth0_user_id="auth0|abc",
            email="NEW@EXAMPLE.COM",
            full_name="New Name",
            email_verified=True,
            claims={},
        ),
    )

    assert user.email == "new@example.com"
    assert user.full_name == "New Name"
    assert session.commits == 1
    assert session.refreshed == [user]


def test_resolve_active_membership_sets_single_membership_as_active() -> None:
    user = User(
        id=uuid4(),
        auth0_user_id="auth0|single",
        email="single@example.com",
        full_name="Single User",
        status="active",
    )
    membership = auth_service.SessionMembership(
        company_id=uuid4(),
        company_name="Acme",
        role="admin",
        status="active",
    )
    session = RecordingSession(existing_user=user)

    active_membership = auth_service.resolve_active_membership(session, user, (membership,))

    assert active_membership == membership
    assert user.last_active_company_id == membership.company_id
    assert session.commits == 1
    assert session.refreshed == [user]


def test_get_current_principal_requires_company_membership() -> None:
    context = auth_service.AuthenticatedContext(
        user=User(
            id=uuid4(),
            auth0_user_id="auth0|nomembership",
            email=None,
            full_name=None,
            status="active",
        ),
        memberships=(),
        active_membership=None,
        permissions=(),
        needs_company_setup=True,
        company_selection_required=False,
    )

    with pytest.raises(HTTPException) as exc_info:
        auth_service.get_current_principal(context)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "membership_required"


def test_get_current_principal_requires_company_selection() -> None:
    context = auth_service.AuthenticatedContext(
        user=User(
            id=uuid4(),
            auth0_user_id="auth0|multicompany",
            email=None,
            full_name=None,
            status="active",
        ),
        memberships=(
            auth_service.SessionMembership(
                company_id=uuid4(),
                company_name="Acme",
                role="admin",
                status="active",
            ),
            auth_service.SessionMembership(
                company_id=uuid4(),
                company_name="Beta",
                role="member",
                status="active",
            ),
        ),
        active_membership=None,
        permissions=(),
        needs_company_setup=False,
        company_selection_required=True,
    )

    with pytest.raises(HTTPException) as exc_info:
        auth_service.get_current_principal(context)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "company_selection_required"


def test_create_company_for_user_sets_admin_membership(monkeypatch) -> None:
    user = User(
        id=uuid4(),
        auth0_user_id="auth0|onboarding",
        email="owner@example.com",
        full_name="Owner",
        status="active",
    )
    session = RecordingSession(existing_user=user)
    company = Company(id=uuid4(), name="Acme", status="active")

    monkeypatch.setattr(auth_service, "load_memberships", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(auth_service, "create_company", lambda *_args, **_kwargs: company)
    monkeypatch.setattr(
        auth_service,
        "build_user_context",
        lambda *_args, **_kwargs: auth_service.AuthenticatedContext(
            user=user,
            memberships=(
                auth_service.SessionMembership(
                    company_id=company.id,
                    company_name=company.name,
                    role="admin",
                    status="active",
                ),
            ),
            active_membership=auth_service.SessionMembership(
                company_id=company.id,
                company_name=company.name,
                role="admin",
                status="active",
            ),
            permissions=("documents:read", "documents:write"),
            needs_company_setup=False,
            company_selection_required=False,
        ),
    )

    context = auth_service.create_company_for_user(
        session,
        user=user,
        company_name="Acme",
    )

    membership = next(item for item in session.added if isinstance(item, CompanyMembership))
    assert membership.role == "admin"
    assert membership.company_id == company.id
    assert user.last_active_company_id == company.id
    assert context.active_membership is not None


def test_select_company_for_user_rejects_unknown_membership(monkeypatch) -> None:
    user = User(
        id=uuid4(),
        auth0_user_id="auth0|member",
        email="member@example.com",
        full_name="Member",
        status="active",
    )
    session = RecordingSession(existing_user=user)
    company_id = uuid4()
    monkeypatch.setattr(
        auth_service,
        "load_memberships",
        lambda *_args, **_kwargs: [
            auth_service.SessionMembership(
                company_id=uuid4(),
                company_name="Other",
                role="member",
                status="active",
            )
        ],
    )

    with pytest.raises(HTTPException) as exc_info:
        auth_service.select_company_for_user(session, user=user, company_id=company_id)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "membership_required"
