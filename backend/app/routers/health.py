# Router for health-check related endpoints.
# Isolated in its own router so future routers (e.g. members) can be added
# without growing main.py.

from datetime import datetime, timezone

from fastapi import APIRouter

from app.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, status_code=200)
def get_health() -> HealthResponse:
    """Return service status and the current UTC timestamp in ISO 8601 format."""
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )