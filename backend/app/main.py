import json
import logging
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.upload_limit import ImportBodyLimit
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.expenses import router as expenses_router
from app.api.v1.foundation import router as foundation_router
from app.api.v1.health import router as health_router
from app.api.v1.imports import router as imports_router
from app.api.v1.market import router as market_router
from app.api.v1.ready import router as ready_router
from app.api.v1.regions import router as regions_router
from app.core.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or get_settings()
    application = FastAPI(
        title="Stay Insight API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url=None,
        openapi_url="/api/v1/openapi.json",
        swagger_ui_oauth2_redirect_url=None,
    )
    application.add_middleware(ImportBodyLimit)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "Authorization", "X-Organization-Id"],
    )

    @application.middleware("http")
    async def private_api_responses(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        try:
            response = await call_next(request)
        except Exception:
            if config.app_env not in {"staging", "production"}:
                raise
            # Never emit driver exceptions, query parameters, tokens or request bodies.
            logging.getLogger("uvicorn.error").error("request_failed")
            response = JSONResponse({"detail": "Internal server error"}, status_code=500)
        if config.app_env in {"staging", "production"}:
            route = getattr(request.scope.get("route"), "path", "unmatched")
            logging.getLogger("uvicorn.error").info(
                json.dumps(
                    {
                        "event": "request",
                        "route": route,
                        "status": response.status_code,
                    }
                )
            )
        if request.url.path.startswith("/api/v1/"):
            response.headers["Cache-Control"] = "private, no-store"
        return response

    application.include_router(health_router, prefix="/api/v1")
    application.include_router(ready_router, prefix="/api/v1")
    application.include_router(foundation_router, prefix="/api/v1")
    application.include_router(imports_router, prefix="/api/v1")
    application.include_router(expenses_router, prefix="/api/v1")
    application.include_router(dashboard_router, prefix="/api/v1")
    application.include_router(market_router, prefix="/api/v1")
    application.include_router(regions_router, prefix="/api/v1")
    return application


app = create_app()
