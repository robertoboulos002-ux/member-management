"""Migration: add the members columns introduced after the first release.

Started as place_of_birth, godfather_name and godmother_name; it now also
covers the baptism fields (baptizing_priest, place_of_baptism,
date_of_baptism), because it applies whatever app/migrate.py lists as a
late addition rather than a fixed set of its own.

The same fix-up now runs automatically when the app starts (see
app/migrate.py), so a normal deploy repairs an existing database. This script
stays for running the migration by hand — e.g. against a database the app is
not currently pointed at, or to confirm the change before deploying.

Run from the backend directory, with DATABASE_URL pointing at the target DB
(or unset, to migrate the local SQLite file):

    python migrations/001_add_birthplace_and_godparents.py

Pass --check to report what the database looks like without changing anything.
Exits 1 when columns are missing, so it also works as a deployment check:

    python migrations/001_add_birthplace_and_godparents.py --check

The script is idempotent: columns that already exist are skipped.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import inspect

from app.database import SQLALCHEMY_DATABASE_URL, engine
from app.migrate import MEMBER_COLUMNS_ADDED_AFTER_RELEASE, ensure_member_columns


def describe() -> int:
    """Print the target database's schema without modifying it."""
    inspector = inspect(engine)
    print(f"Database: {SQLALCHEMY_DATABASE_URL.split('@')[-1]}")

    if "members" not in inspector.get_table_names():
        print("No 'members' table - the app will create it with the current schema.")
        return 0

    present = {column["name"] for column in inspector.get_columns("members")}
    missing = [c for c in MEMBER_COLUMNS_ADDED_AFTER_RELEASE if c not in present]

    print(f"members columns ({len(present)}): {', '.join(sorted(present))}")

    if missing:
        print(f"MISSING: {', '.join(missing)}")
        print("Every /members request will fail until these are added. Re-run "
              "without --check to add them.")
        return 1

    print("All expected columns present.")
    return 0


def main() -> int:
    if "--check" in sys.argv[1:]:
        return describe()

    added = ensure_member_columns(engine)

    if not added:
        print("Nothing to do — columns already present, or no 'members' table yet.")
        return 0

    for name in added:
        print(f"Added column: {name}")

    print(f"Migrated {SQLALCHEMY_DATABASE_URL.split('@')[-1]} - {len(added)} column(s) added.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
