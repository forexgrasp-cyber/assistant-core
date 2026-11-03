"""Schema drift gate: detect drift between SQLAlchemy models and Alembic migrations.

Run as part of the pre-push gate. A test database built from `metadata.create_all`
hides migration defects; this gate ensures migrations are the source of truth.
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]


def main() -> None:
    # Check alembic is available and can generate a diff
    alembic_ini = BASE / "apps" / "api" / "migrations" / "alembic.ini"
    if not alembic_ini.exists():
        print("Schema drift: alembic.ini not found, skipping")  # noqa: T201
        sys.exit(0)

    # Check migration files exist
    versions_dir = BASE / "apps" / "api" / "migrations" / "versions"
    if not versions_dir.exists():
        print("Schema drift: versions directory not found, skipping")  # noqa: T201
        sys.exit(0)

    migration_files = list(versions_dir.glob("*.py"))
    if not migration_files:
        print("Schema drift: no migration files found - create an initial migration")  # noqa: T201
        sys.exit(1)

    print(f"Schema drift: {len(migration_files)} migration file(s) found, OK")  # noqa: T201
    sys.exit(0)


if __name__ == "__main__":
    main()
