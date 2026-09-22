from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError

from app.core.config import get_settings

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: UUID


@lru_cache
def get_jwks_client(url: str) -> PyJWKClient:
    return PyJWKClient(url, cache_jwk_set=True, lifespan=300, timeout=5)


def verify_access_token(token: str) -> AuthenticatedUser:
    try:
        header = jwt.get_unverified_header(token)
        # The header only selects a permitted key/algorithm; it never authorizes a user.
        if header.get("alg") not in {"RS256", "ES256"} or not header.get("kid"):
            raise jwt.InvalidTokenError()
        settings = get_settings()
        if not settings.supabase_url:
            raise HTTPException(503, "Authentication is not configured")
        issuer = settings.supabase_url.rstrip("/") + "/auth/v1"
        key = get_jwks_client(issuer + "/.well-known/jwks.json").get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            key.key,
            algorithms=["RS256", "ES256"],
            audience=settings.supabase_jwt_audience,
            issuer=issuer,
            options={"require": ["exp", "iat", "sub", "iss", "aud", "role"]},
        )
        if claims["role"] != "authenticated" or claims.get("is_anonymous", False):
            raise jwt.InvalidTokenError()
        return AuthenticatedUser(UUID(claims["sub"]))
    except PyJWKClientConnectionError as error:
        raise HTTPException(503, "Authentication provider is unavailable") from error
    except (jwt.PyJWTError, ValueError, TypeError, KeyError) as error:
        raise HTTPException(
            401, "Invalid or expired access token", headers={"WWW-Authenticate": "Bearer"}
        ) from error


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(401, "Authentication required", headers={"WWW-Authenticate": "Bearer"})
    return verify_access_token(credentials.credentials)
