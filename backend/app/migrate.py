"""Schema fix-ups the app applies to itself on startup.

Base.metadata.create_all() only creates *missing tables* — it never adds
columns to a table that already exists. A database created before a column was
introduced therefore keeps serving 500s on every query that selects it, which
is exactly what happened to the live deployment when place_of_birth and the
godparent fields were added.

Running the fix-up at startup means a plain deploy repairs the database; no
one-off shell on the host is needed. Everything here must stay idempotent, so
it is a no-op on an already-correct database.
"""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

# Columns added to `members` after the first release. Nullable with no default:
# rows created before they existed have no value to backfill with, and the API
# layer is what enforces them on create/update.
MEMBER_COLUMNS_ADDED_AFTER_RELEASE = (
    "place_of_birth",
    "godfather_name",
    "godmother_name",
)


def ensure_member_columns(engine: Engine) -> list[str]:
    """Add any missing late-addition columns to `members`.

    Returns the columns that were added, so callers can log or print them. If
    the table does not exist yet there is nothing to migrate: create_all()
    builds it with the current schema.
    """
    inspector = inspect(engine)

    if "members" not in inspector.get_table_names():
        return []

    existing = {column["name"] for column in inspector.get_columns("members")}
    missing = [
        name for name in MEMBER_COLUMNS_ADDED_AFTER_RELEASE if name not in existing
    ]

    if not missing:
        return []

    with engine.begin() as connection:
        for name in missing:
            connection.execute(
                text(f"ALTER TABLE members ADD COLUMN {name} VARCHAR(100) NULL")
            )

    return missing
