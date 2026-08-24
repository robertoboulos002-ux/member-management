# Shared test setup: admin credentials, the test database, and per-test cleanup.
#
# All of this lives here rather than in a single test module because more than
# one module needs it, and because the environment has to be set before any app
# code reads it - regardless of which file pytest happens to collect first.

import os
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

TEST_ADMIN_PASSWORD = "test-admin-password"

# Fixed values, and set before the imports below: tokens minted in one test
# must verify in another, and a developer's real .env must not change how the
# suite behaves.
os.environ["ADMIN_PASSWORD"] = TEST_ADMIN_PASSWORD
os.environ["ADMIN_SESSION_SECRET"] = "test-session-secret"

from app.auth import reset_throttle
from app.database import Base, get_db
from app.main import app

# A separate SQLite file so runs never touch members.db.
TEST_DATABASE_URL = "sqlite:///./test_members.db"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def fresh_database():
    """Create fresh tables before each test and drop them after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def clean_login_throttle():
    """Keep each test's failed-login count from leaking into the next one."""
    reset_throttle()
    yield
    reset_throttle()
