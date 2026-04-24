from uuid import uuid4

from archyve_common.db import get_session
from archyve_common.models import User

from api_app.features.auth import router as auth_router
from api_app.features.auth.service import (
    AuthenticatedContext,
    SessionMembership,
    get_authenticated_context,
)


def build_context(
    *,
    active_company: bool = True,
    memberships: tuple[SessionMembership, ...] | None = None,
) -> AuthenticatedContext:
    user = User(
        id=uuid4(),
        auth0_user_id="auth0|user-1",
        email="person@example.com",
        full_name="Person Example",
        status="active",
    )
    membership_records = memberships or (
        SessionMembership(
            company_id=uuid4(),
            company_name="Acme",
            role="admin",
            status="active",
        ),
    )
    active_membership = membership_records[0] if active_company and membership_records else None
    return AuthenticatedContext(
        user=user,
        memberships=membership_records,
        active_membership=active_membership,
        permissions=("documents:read", "documents:write"),
        needs_company_setup=False,
        company_selection_required=not active_company and bool(membership_records),
    )


def test_get_auth_session_serializes_context(api_client) -> None:
    api_client.app.dependency_overrides[get_authenticated_context] = build_context

    response = api_client.get("/auth/session")

    assert response.status_code == 200
    assert response.json()["user"]["auth0_user_id"] == "auth0|user-1"
    assert response.json()["active_company"]["name"] == "Acme"
    assert response.json()["permissions"] == ["documents:read", "documents:write"]


def test_get_auth_session_requires_authentication(api_client) -> None:
    response = api_client.get("/auth/session")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "missing_token"


def test_create_onboarding_company_returns_updated_session(api_client, monkeypatch) -> None:
    session = object()
    base_context = AuthenticatedContext(
        user=User(
            id=uuid4(),
            auth0_user_id="auth0|user-2",
            email="new@example.com",
            full_name="New User",
            status="active",
        ),
        memberships=(),
        active_membership=None,
        permissions=(),
        needs_company_setup=True,
        company_selection_required=False,
    )
    created_context = build_context()

    api_client.app.dependency_overrides[get_session] = lambda: session
    api_client.app.dependency_overrides[get_authenticated_context] = lambda: base_context
    monkeypatch.setattr(
        auth_router,
        "create_company_for_user",
        lambda current_session, *, user, company_name: created_context,
    )

    response = api_client.post(
        "/auth/onboarding/create-company",
        json={"name": "Acme"},
    )

    assert response.status_code == 200
    assert response.json()["active_company"]["name"] == "Acme"
    assert response.json()["needs_company_setup"] is False


def test_create_onboarding_company_rejects_blank_names(api_client) -> None:
    base_context = AuthenticatedContext(
        user=User(
            id=uuid4(),
            auth0_user_id="auth0|user-3",
            email="blank@example.com",
            full_name="Blank User",
            status="active",
        ),
        memberships=(),
        active_membership=None,
        permissions=(),
        needs_company_setup=True,
        company_selection_required=False,
    )
    api_client.app.dependency_overrides[get_session] = lambda: object()
    api_client.app.dependency_overrides[get_authenticated_context] = lambda: base_context

    response = api_client.post(
        "/auth/onboarding/create-company",
        json={"name": "   "},
    )

    assert response.status_code == 422


def test_select_company_returns_updated_session(api_client, monkeypatch) -> None:
    session = object()
    company_id = uuid4()
    base_context = build_context(active_company=False)
    selected_context = build_context(
        memberships=(
            SessionMembership(
                company_id=company_id,
                company_name="Beta",
                role="member",
                status="active",
            ),
        )
    )

    api_client.app.dependency_overrides[get_session] = lambda: session
    api_client.app.dependency_overrides[get_authenticated_context] = lambda: base_context
    monkeypatch.setattr(
        auth_router,
        "select_company_for_user",
        lambda current_session, *, user, company_id: selected_context,
    )

    response = api_client.post(
        "/auth/session/select-company",
        json={"company_id": str(company_id)},
    )

    assert response.status_code == 200
    assert response.json()["active_company"]["id"] == str(company_id)
    assert response.json()["active_company"]["role"] == "member"
