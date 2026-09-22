from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_swagger_and_explicit_response_schema() -> None:
    with TestClient(app) as client:
        assert client.get("/docs").status_code == 200
        schema = client.get("/api/v1/openapi.json").json()
    response_schema = schema["paths"]["/api/v1/health"]["get"]["responses"]["200"]
    reference = response_schema["content"]["application/json"]["schema"]["$ref"]
    assert reference.endswith("HealthResponse")


def test_cors_allows_configured_origin_only() -> None:
    with TestClient(app) as client:
        allowed = client.get("/api/v1/health", headers={"Origin": "http://localhost:3000"})
        denied = client.get("/api/v1/health", headers={"Origin": "https://untrusted.example"})
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "access-control-allow-origin" not in denied.headers


def test_bearer_and_tenant_preflight() -> None:
    with TestClient(app) as client:
        response = client.options(
            "/api/v1/properties",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "PATCH",
                "Access-Control-Request-Headers": "authorization,x-organization-id,content-type",
            },
        )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
