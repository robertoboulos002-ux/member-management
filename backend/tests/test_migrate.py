# Tests for the startup schema fix-up in app/migrate.py.
# Uses its own throwaway SQLite file so it can create a deliberately outdated
# `members` table without disturbing the other tests' database.

import os
import sys

import pytest
from sqlalchemy import create_engine, inspect, text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.migrate import MEMBER_COLUMNS_ADDED_AFTER_RELEASE, ensure_member_columns
from app.models import Member

# The members table as it existed before place_of_birth and the godparent
# fields were added — the shape the live database was left in.
PRE_RELEASE_MEMBERS_TABLE = """
CREATE TABLE members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    firstname VARCHAR NOT NULL,
    lastname VARCHAR NOT NULL,
    father_name VARCHAR NOT NULL,
    mother_name VARCHAR NOT NULL,
    intercessor_name VARCHAR NOT NULL,
    date_of_birth DATE NOT NULL
)
"""


@pytest.fixture
def outdated_engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'outdated.db'}")
    with engine.begin() as connection:
        connection.execute(text(PRE_RELEASE_MEMBERS_TABLE))
    yield engine
    engine.dispose()


def test_adds_the_columns_missing_from_an_outdated_table(outdated_engine):
    added = ensure_member_columns(outdated_engine)

    assert sorted(added) == sorted(MEMBER_COLUMNS_ADDED_AFTER_RELEASE)
    columns = {c["name"] for c in inspect(outdated_engine).get_columns("members")}
    assert set(MEMBER_COLUMNS_ADDED_AFTER_RELEASE) <= columns


def test_querying_an_outdated_table_works_after_the_fix_up(outdated_engine):
    """The live symptom: selecting the model's columns 500s until migrated."""
    with pytest.raises(Exception):
        with outdated_engine.connect() as connection:
            connection.execute(Member.__table__.select()).all()

    ensure_member_columns(outdated_engine)

    with outdated_engine.connect() as connection:
        assert connection.execute(Member.__table__.select()).all() == []


def test_is_idempotent(outdated_engine):
    ensure_member_columns(outdated_engine)
    assert ensure_member_columns(outdated_engine) == []


def test_no_members_table_is_a_no_op(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'empty.db'}")
    try:
        assert ensure_member_columns(engine) == []
    finally:
        engine.dispose()
