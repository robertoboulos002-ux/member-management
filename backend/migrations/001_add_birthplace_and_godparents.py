"""One-off migration: add place_of_birth, godfather_name and godmother_name
to the members table.

The app creates tables with Base.metadata.create_all(), which only creates
missing *tables* — it never adds columns to a table that already exists. So an
already-deployed database needs this script run once before the new code is
served, or every /members request will fail on the unknown columns.

Run from the backend directory, with DATABASE_URL pointing at the target DB
(or unset, to migrate the local SQLite file):

    python migrations/001_add_birthplace_and_godparents.py

The script is idempotent: columns that already exist are skipped.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import inspect, text

from app.database import SQLALCHEMY_DATABASE_URL, engine

NEW_COLUMNS = ["place_of_birth", "godfather_name", "godmother_name"]


def main() -> int:
    inspector = inspect(engine)

    if "members" not in inspector.get_table_names():
        print("No 'members' table yet — nothing to migrate; the app will create it.")
        return 0

    existing = {column["name"] for column in inspector.get_columns("members")}
    missing = [name for name in NEW_COLUMNS if name not in existing]

    if not missing:
        print("All columns already present — nothing to do.")
        return 0

    # Nullable with no default: existing rows have no value to backfill with,
    # and the API layer is what enforces the fields on create/update.
    with engine.begin() as connection:
        for name in missing:
            connection.execute(
                text(f"ALTER TABLE members ADD COLUMN {name} VARCHAR(100) NULL")
            )
            print(f"Added column: {name}")

    print(f"Migrated {SQLALCHEMY_DATABASE_URL.split('@')[-1]} — {len(missing)} column(s) added.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
