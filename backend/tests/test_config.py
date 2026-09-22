import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.db.base import Base
from app.db.session import get_engine


def test_cors_parses_comma_separated_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000, https://example.test ,")
    assert Settings().cors_origins == ["http://localhost:3000", "https://example.test"]


@pytest.mark.parametrize("value", ["*", "https://example.test/path", "not-an-origin"])
def test_cors_rejects_invalid_origins(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("CORS_ORIGINS", value)
    with pytest.raises(ValidationError):
        Settings()


def test_database_configuration_without_connection() -> None:
    engine = get_engine()
    assert engine.url.drivername == "postgresql+psycopg"
    assert set(Base.metadata.tables) == {
        "app.organizations",
        "app.organization_members",
        "app.properties",
    }
    engine.dispose()
