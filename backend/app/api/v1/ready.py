from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.db.session import get_engine
from app.services.readiness import ready

router = APIRouter()


@router.get("/ready", response_model=None)
def readiness() -> JSONResponse:
    available = ready(get_engine())
    return JSONResponse(
        {"status": "ready" if available else "unavailable"}, status_code=200 if available else 503
    )
