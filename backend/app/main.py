# Application entry point.
# Loads environment variables, creates the FastAPI app instance, creates
# database tables on startup, and registers routers.
# Run with: uvicorn app.main:app --reload

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.migrate import ensure_member_columns
from app.routers import health, members

load_dotenv()

APP_ENV = os.getenv("APP_ENV", "development")


def get_allowed_origins() -> list[str]:
    """Return a valid CORS allowlist from the environment.

    Production deployments often set a comma-separated list of frontend origins,
    while local development is easiest with a wildcard. Accept both forms and
    trim whitespace so invalid single-string values do not break the browser.
    """
    raw_value = os.getenv("ALLOWED_ORIGIN") or os.getenv("ALLOWED_ORIGINS") or "*"
    raw_value = raw_value.strip()

    if raw_value == "*":
        return ["*"]

    origins = [origin.strip() for origin in raw_value.split(",") if origin.strip()]
    return origins or ["*"]


ALLOWED_ORIGINS = get_allowed_origins()

# Create tables if they don't already exist. Fine for SQLite/dev use;
# a migrations tool (e.g. Alembic) would replace this in production.
Base.metadata.create_all(bind=engine)

# create_all() adds missing tables but never missing *columns*, so a database
# created before a field was introduced would 500 on every query selecting it.
# Patch it up here so deploying is enough to repair an existing database.
try:
    added_columns = ensure_member_columns(engine)
    if added_columns:
        print(f"[migrate] added members column(s): {', '.join(added_columns)}")
except Exception as exc:  # noqa: BLE001 - never let this stop the app booting
    # /health and / must stay up so the failure is diagnosable from the logs.
    print(f"[migrate] could not update the members table: {exc!r}")

app = FastAPI(
    title="Member Management API",
    description="REST API for managing members (CRUD + search).",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(members.router)


@app.get("/")
def read_root() -> dict:
    """Basic root endpoint confirming the API is reachable."""
    return {"service": "member-management-api", "environment": APP_ENV}