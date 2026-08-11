# Application entry point.
# Loads environment variables, creates the FastAPI app instance, creates
# database tables on startup, and registers routers.
# Run with: uvicorn app.main:app --reload

import os

from dotenv import load_dotenv
from fastapi import FastAPI

from app.database import Base, engine
from app.routers import health, members

load_dotenv()

APP_ENV = os.getenv("APP_ENV", "development")

# Set ALLOWED_ORIGIN to the deployed frontend URL in production; defaults to
# "*" so local development keeps working without extra config.
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "*")

# Create tables if they don't already exist. Fine for SQLite/dev use;
# a migrations tool (e.g. Alembic) would replace this in production.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Member Management API",
    description="REST API for managing members (CRUD + search).",
    version="0.1.0",
)
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(members.router)


@app.get("/")
def read_root() -> dict:
    """Basic root endpoint confirming the API is reachable."""
    return {"service": "member-management-api", "environment": APP_ENV}