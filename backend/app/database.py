# Database engine and session setup using SQLAlchemy.
# Uses DATABASE_URL when set (e.g. PostgreSQL on Render) and falls back to a
# local SQLite file, so the same code runs in both environments.

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Loaded here as well as in main.py: this module is imported before main.py
# calls load_dotenv(), so a DATABASE_URL in .env would otherwise be missed.
load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./members.db")

# Render hands out postgres:// URLs; SQLAlchemy 2.x only accepts postgresql://.
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace(
        "postgres://", "postgresql://", 1
    )

# check_same_thread=False is required for SQLite when used with FastAPI's
# threaded request handling. It is not a valid PostgreSQL connect arg.
connect_args = (
    {"check_same_thread": False}
    if SQLALCHEMY_DATABASE_URL.startswith("sqlite")
    else {}
)

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and closes it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()