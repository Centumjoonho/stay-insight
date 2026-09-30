"""Hosted entrypoint. Never echo configuration values or driver exceptions."""

import json
import os
import re

import uvicorn
from sqlalchemy.engine import make_url

from app.core.config import Settings, get_settings


def validate_runtime(settings: Settings) -> None:
    if settings.app_env not in {"staging", "production"}:
        raise ValueError("APP_ENV must identify a hosted environment")
    url = make_url(settings.database_url.get_secret_value())
    if not settings.supabase_url or not settings.cors_origins:
        raise ValueError("SUPABASE_URL and CORS_ORIGINS are required")
    if any(not origin.startswith("https://") for origin in settings.cors_origins):
        raise ValueError("Hosted CORS origins require HTTPS")
    if url.query.get("sslmode") not in {"require", "verify-ca", "verify-full"}:
        raise ValueError("Hosted DATABASE_URL requires TLS")
    if url.port == 6543:
        raise ValueError("Use verified direct or session-mode connections")
    if settings.app_env == "staging" and not settings.staging_allowed_user_ids:
        raise ValueError("STAGING_ALLOWED_USER_IDS is required")


def main() -> int:
    try:
        settings = get_settings()
        validate_runtime(settings)
        port = int(os.environ.get("PORT", "8000"))
        if not 1 <= port <= 65535:
            raise ValueError("Invalid port")
    except Exception:
        print(json.dumps({"event": "startup_failed", "code": "INVALID_HOSTED_CONFIGURATION"}))
        return 1
    revision = os.environ.get("DEPLOYMENT_VERSION") or os.environ.get(
        "RENDER_GIT_COMMIT", "unknown"
    )
    revision = revision if re.fullmatch(r"[A-Za-z0-9._-]{1,80}", revision) else "unknown"
    print(json.dumps({"event": "startup", "environment": settings.app_env, "revision": revision}))
    # One process per small staging instance; scaling is a platform concern.
    # Access logging is replaced by safe route-template/status logging in the application.
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, access_log=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
