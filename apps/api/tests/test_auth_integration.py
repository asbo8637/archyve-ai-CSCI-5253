from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from jwt.exceptions import InvalidAudienceError, InvalidIssuerError, InvalidTokenError

from api_app import integrations
from api_app.integrations.auth import Auth0TokenVerifier


def build_private_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def build_token(private_key, *, audience: str, issuer: str, claims: dict | None = None) -> str:
    payload = {
        "aud": audience,
        "exp": 4_102_444_800,
        "iat": 1_700_000_000,
        "iss": issuer,
        "sub": f"auth0|{uuid4()}",
    }
    payload.update(claims or {})
    return jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": "test-kid"})


def test_auth0_token_verifier_decodes_valid_token_with_namespaced_claims(monkeypatch) -> None:
    private_key = build_private_key()
    public_key = private_key.public_key()
    verifier = Auth0TokenVerifier(
        jwks_url="https://tenant.example.com/.well-known/jwks.json",
        audience="https://api.example.com",
        issuer="https://tenant.example.com/",
    )
    token = build_token(
        private_key,
        audience="https://api.example.com",
        issuer="https://tenant.example.com/",
        claims={
            "https://archyve.ai/email": "person@example.com",
            "https://archyve.ai/name": "Person Example",
            "https://archyve.ai/email_verified": True,
        },
    )
    monkeypatch.setattr(
        verifier,
        "_get_signing_key",
        lambda _token: SimpleNamespace(key=public_key),
    )

    identity = verifier.decode_access_token(token)

    assert identity.auth0_user_id.startswith("auth0|")
    assert identity.email == "person@example.com"
    assert identity.full_name == "Person Example"
    assert identity.email_verified is True


@pytest.mark.parametrize(
    ("audience", "issuer", "expected_exception"),
    [
        ("https://wrong-audience.example.com", "https://tenant.example.com/", InvalidAudienceError),
        ("https://api.example.com", "https://wrong-issuer.example.com/", InvalidIssuerError),
    ],
)
def test_auth0_token_verifier_rejects_invalid_claims(
    monkeypatch,
    audience: str,
    issuer: str,
    expected_exception,
) -> None:
    private_key = build_private_key()
    public_key = private_key.public_key()
    verifier = Auth0TokenVerifier(
        jwks_url="https://tenant.example.com/.well-known/jwks.json",
        audience="https://api.example.com",
        issuer="https://tenant.example.com/",
    )
    token = build_token(
        private_key,
        audience=audience,
        issuer=issuer,
    )
    monkeypatch.setattr(
        verifier,
        "_get_signing_key",
        lambda _token: SimpleNamespace(key=public_key),
    )

    with pytest.raises(expected_exception):
        verifier.decode_access_token(token)


def test_get_bearer_token_requires_credentials() -> None:
    with pytest.raises(HTTPException) as exc_info:
        integrations.auth.get_bearer_token(None)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["code"] == "missing_token"


def test_get_token_identity_translates_invalid_token(monkeypatch) -> None:
    class InvalidVerifier:
        def decode_access_token(self, token: str):
            raise InvalidTokenError(token)

    monkeypatch.setattr(integrations.auth, "get_auth0_token_verifier", lambda: InvalidVerifier())

    with pytest.raises(HTTPException) as exc_info:
        integrations.auth.get_token_identity("bad-token")

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["code"] == "invalid_token"


def test_get_token_identity_translates_missing_auth0_config(monkeypatch) -> None:
    def raise_not_configured():
        raise RuntimeError("Auth0 is not fully configured.")

    monkeypatch.setattr(integrations.auth, "get_auth0_token_verifier", raise_not_configured)

    with pytest.raises(HTTPException) as exc_info:
        integrations.auth.get_token_identity("token")

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail["code"] == "auth_not_configured"


def test_permissions_for_unknown_role_returns_no_permissions() -> None:
    assert integrations.auth.permissions_for_role("unknown") == ()
