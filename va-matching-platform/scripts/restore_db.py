#!/usr/bin/env python3
"""
Restore script for VA Matching Platform database.

Restores a PostgreSQL database from a backup file.
"""

from __future__ import annotations

import argparse
import gzip
import os
import subprocess
import sys
from pathlib import Path


def restore_backup(
    backup_path: Path,
    db_url: str,
    clean: bool = False,
    schema_only: bool = False,
    data_only: bool = False,
) -> None:
    """
    Restore a PostgreSQL database from a backup file.
    
    Args:
        backup_path: Path to the backup file (.sql or .sql.gz)
        db_url: PostgreSQL connection URL
        clean: Drop existing objects before restoring
        schema_only: Only restore schema (no data)
        data_only: Only restore data (no schema)
    """
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_path}")
    
    # Parse database URL
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    
    import urllib.parse
    parsed = urllib.parse.urlparse(db_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    username = parsed.username or "postgres"
    password = parsed.password or "postgres"
    dbname = parsed.path.lstrip("/") if parsed.path else "va_matching"
    
    # Check if backup is compressed
    is_compressed = backup_path.suffix == ".gz"
    
    # Build psql command
    cmd = [
        "psql",
        "-h", host,
        "-p", str(port),
        "-U", username,
        "-d", dbname,
        "-v", "ON_ERROR_STOP=1",
    ]
    
    if clean:
        cmd.append("--clean")
    if schema_only:
        cmd.append("--schema-only")
    elif data_only:
        cmd.append("--data-only")
    
    # Set password via environment
    env = os.environ.copy()
    env["PGPASSWORD"] = password
    
    print(f"Restoring from: {backup_path}")
    print(f"Target database: {dbname} on {host}:{port}")
    print(f"Clean mode: {clean}")
    
    try:
        if backup_path.suffix == ".gz":
            # Decompress and pipe to psql
            with gzip.open(backup_path, "rb") as f_in:
                proc = subprocess.run(
                    cmd,
                    stdin=subprocess.PIPE,
                    env=env,
                    check=True,
                    capture_output=True,
                    text=True,
                    input=f_in.read().decode('utf-8')
                )
        else:
            with open(backup_path, "rb") as f_in:
                proc = subprocess.run(
                    cmd,
                    stdin=f_in,
                    env=env,
                    check=True,
                    capture_output=True,
                    text=True
                )
        
        print("✅ Restore completed successfully!")
        if proc.stdout:
            print(proc.stdout)
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Restore failed with exit code {e.returncode}")
        if e.stdout:
            print(f"STDOUT: {e.stdout}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        raise
    except FileNotFoundError:
        print("Error: psql not found. Please install PostgreSQL client tools.")
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="VA Matching Platform database restore")
    parser.add_argument(
        "backup_file",
        type=Path,
        help="Path to backup file (.sql or .sql.gz)",
    )
    parser.add_argument(
        "--db-url",
        default=os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/va_matching"),
        help="Database URL (default: DATABASE_URL env var)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Drop existing objects before restoring",
    )
    parser.add_argument(
        "--schema-only",
        action="store_true",
        help="Only restore schema (no data)",
    )
    parser.add_argument(
        "--data-only",
        action="store_true",
        help="Only restore data (no schema)",
    )
    
    args = parser.parse_args()
    
    try:
        restore_backup(
            backup_path=args.backup_file,
            db_url=args.db_url,
            clean=args.clean,
            schema_only=args.schema_only,
            data_only=args.data_only,
        )
        print("✅ Restore completed successfully!")
        return 0
    except Exception as e:
        print(f"❌ Restore failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())