"""One-off migration: add place_of_birth, godfather_name and godmother_name
to the members table.

The same fix-up now runs automatically when the app starts (see
app/migrate.py), so a normal deploy repairs an existing database. This script
stays for running the migration by hand — e.g. against a database the app is
not currently pointed at, or to confirm the change before deploying.

Run from the backend directory, with DATABASE_URL pointing at the target DB
(or unset, to migrate the local SQLite file):

    python migrations/001_add_birthplace_and_godparents.py

The script is idempotent: columns that already exist are skipped.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SQLALCHEMY_DATABASE_URL, engine
from app.migrate import ensure_member_columns


def main() -> int:
    added = ensure_member_columns(engine)

    if not added:
        print("Nothing to do — columns already present, or no 'members' table yet.")
        return 0

    for name in added:
        print(f"Added column: {name}")

    print(f"Migrated {SQLALCHEMY_DATABASE_URL.split('@')[-1]} — {len(added)} column(s) added.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
