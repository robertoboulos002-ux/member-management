# Router for health-check related endpoints.
# Isolated in its own router so future routers (e.g. members) can be added
# without growing main.py.

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Member
from app.schemas import DatabaseHealthResponse, HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, status_code=200)
def get_health() -> HealthResponse:
    """Return service status and the current UTC timestamp in ISO 8601 format."""
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/health/database", response_model=DatabaseHealthResponse, status_code=200)
def get_database_health(db: Session = Depends(get_db)) -> DatabaseHealthResponse:
    """Report what the database actually looks like.

    /members failing with a bare 500 gives nothing to work from when the logs
    are not to hand: the cause could be an outdated table, an unreachable
    database, or a deploy that never landed. This reports the live schema so the
    difference is visible from a single request. It exposes column names only -
    the same names /docs already publishes - and never any row data.

    Always answers 200, including when the database is unreachable: a
    diagnostic that fails the same way as the endpoint being diagnosed is no
    help at all.
    """
    expected = sorted(column.name for column in Member.__table__.columns)

    try:
        # Inspect the session's own connection rather than the module-level
        # engine, so this reports on whichever database is actually serving
        # /members - the point of the diagnostic.
        inspector = inspect(db.get_bind())
        tables = sorted(inspector.get_table_names())
    except Exception as exc:  # noqa: BLE001 - the failure *is* the answer here
        return DatabaseHealthResponse(
            reachable=False,
            error=repr(exc),
            expected_members_columns=expected,
        )

    if "members" not in tables:
        return DatabaseHealthResponse(
            reachable=True,
            tables=tables,
            expected_members_columns=expected,
            missing_members_columns=expected,
        )

    present = sorted(column["name"] for column in inspector.get_columns("members"))

    return DatabaseHealthResponse(
        reachable=True,
        tables=tables,
        members_columns=present,
        expected_members_columns=expected,
        missing_members_columns=sorted(set(expected) - set(present)),
    )
