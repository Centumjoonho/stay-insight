import time
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.core.auth import jwt as auth
from app.core.config import get_settings
from app.main import app


@pytest.fixture
def signing(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = jwt.algorithms.RSAAlgorithm.to_jwk(private.public_key(), as_dict=True)
    public.update({"kid": "test-key", "alg": "RS256", "use": "sig"})
    client = jwt.PyJWKClient("https://auth.example.test/auth/v1/.well-known/jwks.json")
    monkeypatch.setattr(client, "fetch_data", lambda: {"keys": [public]})
    monkeypatch.setattr(auth, "get_jwks_client", lambda _url: client)
    monkeypatch.setenv("SUPABASE_URL", "https://auth.example.test")
    get_settings.cache_clear()
    claims = {
        "sub": str(uuid4()),
        "iss": "https://auth.example.test/auth/v1",
        "aud": "authenticated",
        "role": "authenticated",
        "iat": int(time.time()),
        "exp": int(time.time()) + 300,
    }
    yield_value = SimpleNamespace(private=private, claims=claims)
    return yield_value


def test_valid_signed_token(signing: SimpleNamespace) -> None:
    token = jwt.encode(
        signing.claims, signing.private, algorithm="RS256", headers={"kid": "test-key"}
    )
    assert str(auth.verify_access_token(token).user_id) == signing.claims["sub"]


@pytest.mark.parametrize(
    "change",
    [
        {"exp": 1},
        {"iss": "https://wrong.example/auth/v1"},
        {"aud": "wrong"},
        {"sub": "not-a-uuid"},
        {"role": "service_role"},
        {"is_anonymous": True},
        {"iat": int(time.time()) + 3600},
    ],
)
def test_rejects_invalid_claims(signing: SimpleNamespace, change: dict[str, object]) -> None:
    token = jwt.encode(
        signing.claims | change, signing.private, algorithm="RS256", headers={"kid": "test-key"}
    )
    with TestClient(app) as client:
        result = client.get("/api/v1/me", headers={"Authorization": "Bearer " + token})
    assert result.status_code == 401


def test_invalid_signature(signing: SimpleNamespace) -> None:
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = jwt.encode(signing.claims, other, algorithm="RS256", headers={"kid": "test-key"})
    with TestClient(app) as client:
        assert (
            client.get("/api/v1/me", headers={"Authorization": "Bearer " + token}).status_code
            == 401
        )


@pytest.mark.parametrize("authorization", [None, "Bearer invalid", "Basic abc"])
def test_unauthenticated_endpoint(authorization: str | None) -> None:
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/me", headers=({"Authorization": authorization} if authorization else {})
        )
    assert response.status_code == 401


def test_rejects_unknown_key_and_unsigned_tokens(signing: SimpleNamespace) -> None:
    tokens = [
        jwt.encode(signing.claims, signing.private, algorithm="RS256", headers={"kid": "unknown"}),
        jwt.encode(signing.claims, "", algorithm="none"),
    ]
    with TestClient(app) as client:
        for token in tokens:
            assert (
                client.get("/api/v1/me", headers={"Authorization": "Bearer " + token}).status_code
                == 401
            )
