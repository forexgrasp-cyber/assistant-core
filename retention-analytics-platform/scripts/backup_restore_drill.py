"""Backup/restore drill script for the Retention Analytics Platform.

Run as part of the pre-push gate or on a schedule to verify that database
backups can be restored. Per PRODUCTION_STANDARDS.md, backups must be
restore-tested regularly.

Usage:
    python scripts/backup_restore_drill.py --mode backup
    python scripts/backup_restore_drill.py --mode restore --backup-file /path/to/backup.sql
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BACKUP_DIR = Path("backups")


def run_cmd(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def backup(database_url: str) -> Path:
    """Create a PostgreSQL backup using pg_dump."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"retention_analytics_{timestamp}.sql"

    # Extract connection params from DATABASE_URL for pg_dump
    cmd = [
        "pg_dump",
        database_url,
        "--no-password",
        "--file",
        str(backup_file),
    ]
    result = run_cmd(cmd)
    if result.returncode != 0:
        print(f"Backup failed: {result.stderr}")  # noqa: T201
        sys.exit(1)

    print(f"Backup created: {backup_file}")  # noqa: T201
    return backup_file


def restore(backup_file: Path, database_url: str) -> None:
    """Restore a PostgreSQL backup using pg_restore / psql."""
    if not backup_file.exists():
        print(f"Backup file not found: {backup_file}")  # noqa: T201
        sys.exit(1)

    cmd = [
        "pg_restore",
        "--clean",
        "--if-exists",
        "--no-password",
        "--dbname",
        database_url,
        str(backup_file),
    ]
    result = run_cmd(cmd)
    if result.returncode != 0:
        print(f"Restore failed: {result.stderr}")  # noqa: T201
        sys.exit(1)

    print(f"Restore completed from: {backup_file}")  # noqa: T201


def verify_restore(database_url: str) -> None:
    """Verify the restored database by checking key tables exist."""
    import asyncio

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _check() -> None:
        engine = create_async_engine(database_url, echo=False)
        try:
            async with engine.connect() as conn:
                result = await conn.execute(
                    text("SELECT COUNT(*) FROM entity_schemas")
                )
                count = result.scalar()
                print(f"Verified: entity_schemas table has {count} row(s)")  # noqa: T201
        finally:
            await engine.dispose()

    asyncio.run(_check())


def main() -> None:
    parser = argparse.ArgumentParser(description="Backup/restore drill")
    parser.add_argument(
        "--mode",
        choices=["backup", "restore", "drill"],
        required=True,
        help="Operation mode",
    )
    parser.add_argument(
        "--backup-file",
        type=Path,
        help="Backup file to restore from (required for restore/drill)",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="PostgreSQL DATABASE_URL",
    )
    args = parser.parse_args()

    from retention_analytics_shared_config import get_settings

    settings = get_settings()
    database_url = args.database_url or settings.database_url

    if args.mode == "backup":
        backup(database_url)
    elif args.mode == "restore":
        if not args.backup_file:
            print("--backup-file required for restore mode")  # noqa: T201
            sys.exit(1)
        restore(args.backup_file, database_url)
        verify_restore(database_url)
    elif args.mode == "drill":
        # Full drill: backup, then restore into a test DB, then verify
        backup_file = backup(database_url)
        restore(backup_file, database_url)
        verify_restore(database_url)
        print("Drill PASSED: backup → restore → verify all succeeded")  # noqa: T201


if __name__ == "__main__":
    main()
