from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError, PyJWKClientError

from archyve_common.settings import get_settings


bearer_scheme = HTTPBearer(auto_error=False)


ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "member": ("documents:read", "documents:write"),
    "admin": (
        "documents:read",
        "documents:write",
        "company:manage",
        "memberships:manage",
    ),
}


@dataclass(frozen=True)
class TokenIdentity:
    auth0_user_id: str
    email: str | None
    full_name: str | None
    email_verified: bool | None
    claims: dict[str, Any]


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    user_id: UUID
    auth0_user_id: str
    company_id: UUID
    membership_role: str
    permissions: tuple[str, ...] = ()


class Auth0TokenVerifier:
    def __init__(self, *, jwks_url: str, audience: str, issuer: str) -> None:
        self._audience = audience
        self._issuer = issuer
        self._jwks_client = PyJWKClient(
            jwks_url,
            cache_jwk_set=True,
            cache_keys=True,
            lifespan=300,
            max_cached_keys=32,
        )

    def decode_access_token(self, token: str) -> TokenIdentity:
        signing_key = self._get_signing_key(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=self._audience,
            issuer=self._issuer,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
        )

        return TokenIdentity(
            auth0_user_id=str(claims["sub"]),
            email=self._extract_claim(claims, "email"),
            full_name=self._extract_claim(claims, "name"),
            email_verified=self._extract_boolean_claim(claims, "email_verified"),
            claims=claims,
        )

    def _get_signing_key(self, token: str):
        try:
            return self._jwks_client.get_signing_key_from_jwt(token)
        except PyJWKClientError:
            self._jwks_client.get_jwk_set(refresh=True)
            return self._jwks_client.get_signing_key_from_jwt(token)

    @staticmethod
    def _extract_claim(claims: dict[str, Any], claim_name: str) -> str | None:
        value = claims.get(claim_name)
        if isinstance(value, str) and value.strip():
            return value.strip()

        suffix = f"/{claim_name}"
        for key, candidate in claims.items():
            if key.endswith(suffix) and isinstance(candidate, str) and candidate.strip():
                return candidate.strip()

        return None

    @staticmethod
    def _extract_boolean_claim(claims: dict[str, Any], claim_name: str) -> bool | None:
        value = claims.get(claim_name)
        if isinstance(value, bool):
            return value

        suffix = f"/{claim_name}"
        for key, candidate in claims.items():
            if key.endswith(suffix) and isinstance(candidate, bool):
                return candidate

        return None


@lru_cache(maxsize=1)
def get_auth0_token_verifier() -> Auth0TokenVerifier:
    settings = get_settings()
    if not settings.auth0_configured:
        raise RuntimeError("Auth0 is not fully configured.")

    return Auth0TokenVerifier(
        jwks_url=settings.resolved_auth0_jwks_url or "",
        audience=settings.auth0_audience or "",
        issuer=settings.resolved_auth0_issuer or "",
    )


def get_bearer_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "missing_token", "message": "Authentication is required."},
        )

    return credentials.credentials


def get_token_identity(token: str = Depends(get_bearer_token)) -> TokenIdentity:
    try:
        return get_auth0_token_verifier().decode_access_token(token)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "auth_not_configured", "message": str(exc)},
        ) from exc
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_token", "message": "The access token is invalid."},
        ) from exc


def permissions_for_role(role: str | None) -> tuple[str, ...]:
    if role is None:
        return ()

    return ROLE_PERMISSIONS.get(role, ())
