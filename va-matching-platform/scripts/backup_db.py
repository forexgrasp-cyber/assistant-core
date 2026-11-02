#!/usr/bin/env python3
"""
Backup script for VA Matching Platform database.

Creates a compressed PostgreSQL dump of the application database.
"""

from __future__ import annotations

import argparse
import gzip
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def create_backup(
    db_url: str,
    output_dir: Path,
    compress: bool = True,
    schema_only: bool = False,
    data_only: bool = False,
) -> Path:
    """
    Create a PostgreSQL database backup.
    
    Args:
        db_url: PostgreSQL connection URL
        output_dir: Directory to save backup file
        compress: Whether to gzip the backup
        schema_only: Only dump schema (no data)
        data_only: Only dump data (no schema)
    
    Returns:
        Path to the backup file
    """
    # Parse database URL
    # postgresql+asyncpg://user:pass@host:port/dbname
    # or postgresql://user:pass@host:port/dbname
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    
    # Extract connection parameters
    import urllib.parse
    parsed = urllib.parse.urlparse(db_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    username = parsed.username or "postgres"
    password = parsed.password or "postgres"
    dbname = parsed.path.lstrip("/") if parsed.path else "va_matching"
    
    # Generate backup filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = ".sql"
    if compress:
        suffix += ".gz"
    
    if schema_only:
        filename = f"backup_schema_{timestamp}{suffix}"
    elif data_only:
        filename = f"backup_data_{timestamp}{suffix}"
    else:
        filename = f"backup_full_{timestamp}{suffix}"
    
    output_path = output_dir / filename
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Build pg_dump command
    cmd = [
        "pg_dump",
        "-h", host,
        "-p", str(port),
        "-U", username,
        "-d", dbname,
        "--no-owner",
        "--no-privileges",
    ]
    
    if schema_only:
        cmd.append("--schema-only")
    elif data_only:
        cmd.append("--data-only")
    
    # Set password via environment
    env = os.environ.copy()
    env["PGPASSWORD"] = password
    
    print(f"Creating backup: {output_path}")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        if compress:
            # Use pg_dump and pipe through gzip
            proc = subprocess.run(cmd, capture_output=True, env=env, check=True)
            with gzip.open(output_path, "wb") as f_out:
                f_out.write(proc.stdout)
        else:
            with open(output_path, "wb") as f_out:
                proc = subprocess.run(cmd, stdout=f_out, env=env, check=True)
        
        print(f"Backup created successfully: {output_path}")
        print(f"Size: {output_path.stat().st_size / 1024 / 1024:.2f} MB")
        return output_path
    
    except subprocess.CalledProcessError as e:
        print(f"Backup failed with exit code {e.returncode}")
        if output_path.exists():
            output_path.unlink()
        raise
    except FileNotFoundError:
        print("Error: pg_dump not found. Please install PostgreSQL client tools.")
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="VA Matching Platform database backup")
    parser.add_argument(
        "--db-url",
        default=os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/va_matching"),
        help="Database URL (default: DATABASE_URL env var)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./backups"),
        help="Output directory for backups",
    )
    parser.add_argument(
        "--no-compress",
        action="store_true",
        help="Don't compress the backup",
    )
    parser.add_argument(
        "--schema-only",
        action="store_true",
        help="Only dump schema (no data)",
    )
    parser.add_argument(
        "--data-only",
        action="store_true",
        help="Only dump data (no schema)",
    )
    
    args = parser.parse_args()
    
    try:
        backup_path = create_backup(
            db_url=args.db_url,
            output_dir=args.output_dir,
            compress=not args.no_compress,
            schema_only=args.schema_only,
            data_only=args.data_only,
        )
        print(f"✅ Backup completed: {backup_path}")
        return 0
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())