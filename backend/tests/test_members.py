# Tests for member CRUD and search endpoints.
# Uses a separate SQLite test database so runs don't touch members.db.

import os
import sys
import warnings
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app, get_allowed_origins
from app.database import Base, get_db
from app.models import Member

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
    "godfather_name": "Peter Doe",
    "godmother_name": "Mary Doe",
    "date_of_birth": "1990-05-14",
    "place_of_birth": "Beirut",
}


def test_get_allowed_origins_supports_comma_separated_values(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGIN", "https://app.example.com, https://admin.example.com")
    assert get_allowed_origins() == [
        "https://app.example.com",
        "https://admin.example.com",
    ]


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
    assert data["place_of_birth"] == "Beirut"
    assert data["godfather_name"] == "Peter Doe"
    assert data["godmother_name"] == "Mary Doe"
    assert "id" in data


def test_create_member_missing_field_returns_422():
    incomplete = {k: v for k, v in SAMPLE_MEMBER.items() if k != "lastname"}
    response = client.post("/members", json=incomplete)
    assert response.status_code == 422


@pytest.mark.parametrize(
    "missing", ["place_of_birth", "godfather_name", "godmother_name"]
)
def test_create_member_missing_new_field_returns_422(missing):
    incomplete = {k: v for k, v in SAMPLE_MEMBER.items() if k != missing}
    response = client.post("/members", json=incomplete)
    assert response.status_code == 422


def test_update_member_replaces_new_fields():
    created = client.post("/members", json=SAMPLE_MEMBER).json()
    updated_data = {
        **SAMPLE_MEMBER,
        "place_of_birth": "Cairo",
        "godfather_name": "Paul Doe",
        "godmother_name": "Martha Doe",
    }
    response = client.put(f"/members/{created['id']}", json=updated_data)
    assert response.status_code == 200
    data = response.json()
    assert data["place_of_birth"] == "Cairo"
    assert data["godfather_name"] == "Paul Doe"
    assert data["godmother_name"] == "Martha Doe"


def test_legacy_member_without_new_fields_is_returned():
    """Rows stored before the new columns existed must still serialize."""
    db = TestingSessionLocal()
    try:
        legacy = Member(
            firstname="Old",
            lastname="Record",
            father_name="Father",
            mother_name="Mother",
            intercessor_name="Pastor James",
            date_of_birth=date(1980, 1, 1),
        )
        db.add(legacy)
        db.commit()
        legacy_id = legacy.id
    finally:
        db.close()

    response = client.get(f"/members/{legacy_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["place_of_birth"] is None
    assert data["godfather_name"] is None
    assert data["godmother_name"] is None


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
    response = client.get("/members", params={"firstname": "Joh"})
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = client.get("/members", params={"firstname": "Zzz"})
    assert response.status_code == 200
    assert len(response.json()) == 0


def test_search_members_by_lastname():
    client.post("/members", json=SAMPLE_MEMBER)
    response = client.get("/members", params={"lastname": "Doe"})
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = client.get("/members", params={"lastname": "Zzz"})
    assert response.status_code == 200
    assert len(response.json()) == 0


def test_search_members_by_intercessor_name():
    client.post("/members", json=SAMPLE_MEMBER)
    response = client.get("/members", params={"intercessor_name": "James"})
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = client.get("/members", params={"intercessor_name": "Zzz"})
    assert response.status_code == 200
    assert len(response.json()) == 0


def test_search_combines_filters_with_and():
    client.post("/members", json=SAMPLE_MEMBER)
    client.post("/members", json={**SAMPLE_MEMBER, "firstname": "Jane", "intercessor_name": "Pastor Mary"})

    # All three filters matching the same member.
    response = client.get(
        "/members",
        params={"firstname": "John", "lastname": "Doe", "intercessor_name": "James"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["firstname"] == "John"

    # Name and intercessor each match a member, but not the same one.
    response = client.get("/members", params={"firstname": "John", "intercessor_name": "Mary"})
    assert response.status_code == 200
    assert len(response.json()) == 0

    # Lastname alone is shared by both members.
    response = client.get("/members", params={"lastname": "Doe"})
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_search_ignores_blank_filters():
    client.post("/members", json=SAMPLE_MEMBER)
    response = client.get(
        "/members",
        params={"firstname": "  ", "lastname": "", "intercessor_name": " "},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


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

def test_database_health_reports_the_live_schema():
    """The diagnostic must answer even when /members cannot."""
    response = client.get("/health/database")
    assert response.status_code == 200
    data = response.json()
    assert data["reachable"] is True
    assert data["error"] is None
    assert "members" in data["tables"]
    assert "place_of_birth" in data["expected_members_columns"]
    assert data["missing_members_columns"] == []
