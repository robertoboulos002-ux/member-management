# Tests for member CRUD and search endpoints.
# Uses a separate SQLite test database so runs don't touch members.db.

import os
import sys
import warnings

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.database import Base, get_db

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
def setup_and_teardown():
    """Create fresh tables before each test and drop them after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)

SAMPLE_MEMBER = {
    "firstname": "John",
    "lastname": "Doe",
    "father_name": "Michael Doe",
    "mother_name": "Sarah Doe",
    "intercessor_name": "Pastor James",
    "date_of_birth": "1990-05-14",
}


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_member():
    response = client.post("/members", json=SAMPLE_MEMBER)
    assert response.status_code == 201
    data = response.json()
    assert data["firstname"] == "John"
    assert data["date_of_birth"] == "1990-05-14"
    assert "id" in data


def test_create_member_missing_field_returns_422():
    incomplete = {k: v for k, v in SAMPLE_MEMBER.items() if k != "lastname"}
    response = client.post("/members", json=incomplete)
    assert response.status_code == 422


def test_get_member():
    created = client.post("/members", json=SAMPLE_MEMBER).json()
    response = client.get(f"/members/{created['id']}")
    assert response.status_code == 200
    assert response.json()["firstname"] == "John"


def test_get_nonexistent_member_returns_404():
    response = client.get("/members/9999")
    assert response.status_code == 404


def test_list_members():
    client.post("/members", json=SAMPLE_MEMBER)
    response = client.get("/members")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_search_members_by_firstname():
    client.post("/members", json=SAMPLE_MEMBER)
    response = client.get("/members", params={"firstname": "Jo"})
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = client.get("/members", params={"firstname": "Zzz"})
    assert response.status_code == 200
    assert len(response.json()) == 0


def test_update_member():
    created = client.post("/members", json=SAMPLE_MEMBER).json()
    updated_data = {**SAMPLE_MEMBER, "lastname": "Smith"}
    response = client.put(f"/members/{created['id']}", json=updated_data)
    assert response.status_code == 200
    assert response.json()["lastname"] == "Smith"


def test_update_nonexistent_member_returns_404():
    response = client.put("/members/9999", json=SAMPLE_MEMBER)
    assert response.status_code == 404


def test_delete_member():
    created = client.post("/members", json=SAMPLE_MEMBER).json()
    response = client.delete(f"/members/{created['id']}")
    assert response.status_code == 204

    response = client.get(f"/members/{created['id']}")
    assert response.status_code == 404


def test_delete_nonexistent_member_returns_404():
    response = client.delete("/members/9999")
    assert response.status_code == 404