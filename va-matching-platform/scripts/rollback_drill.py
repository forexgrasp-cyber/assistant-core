#!/usr/bin/env python3
"""
Rollback drill script for VA Matching Platform.

Performs a complete rollback test:
1. Creates a backup of current database
2. Applies a migration (upgrade)
3. Verifies the migration worked
4. Rolls back the migration (downgrade)
5. Verifies the rollback worked
5. Restores the original backup
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], env: dict[str, str] | None = None, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    
    return subprocess.run(
        cmd,
        env=env or os.environ,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def run_alembic_upgrade(revision: str = "head", cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run alembic upgrade to specified revision."""
    cmd = ["alembic", "upgrade", revision]
    return run_command(cmd, cwd=cwd)


def run_alembic_downgrade(revision: str = "-1", cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run alembic downgrade to specified revision."""
    cmd = ["alembic", "downgrade", revision]
    return run_command(cmd, cwd=cwd)


def run_alembic_current(cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Get current alembic revision."""
    cmd = ["alembic", "current"]
    return run_command(cmd, cwd=cwd)


def run_alembic_history(cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Show alembic migration history."""
    cmd = ["alembic", "history", "--verbose"]
    return run_command(cmd, cwd=cwd)


def create_backup(db_url: str, output_dir: Path) -> Path:
    """Create a database backup."""
    from scripts.backup_db import create_backup
    return create_backup(db_url, output_dir)


def restore_backup(backup_path: Path, db_url: str) -> None:
    """Restore database from backup."""
    from scripts.restore_db import restore_backup
    restore_backup(backup_path, db_url, clean=True)


def run_rollback_drill(
    db_url: str,
    backup_dir: Path,
    steps: int = 1,
) -> bool:
    """
    Run a complete rollback drill.
    
    Args:
        db_url: Database connection URL
        backup_dir: Directory to store backups
        steps: Number of migration steps to test rollback for
    
    Returns:
        True if drill passed, False otherwise
    """
    project_root = Path(__file__).parent.parent
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("🚀 Starting Rollback Drill")
    print("=" * 60)
    
    # Step 1: Show current migration status
    print("\n📋 Step 1: Current migration status")
    result = run_alembic_current(cwd=project_root)
    print(result.stdout)
    if result.stderr:
        print(f"STDERR: {result.stderr}")
    
    # Step 2: Show migration history
    print("\n📜 Step 2: Migration history")
    result = run_alembic_history(cwd=project_root)
    print(result.stdout)
    
    # Step 3: Create pre-drill backup
    print("\n💾 Step 3: Creating pre-drill backup...")
    backup_path = create_backup(db_url, backup_dir / "pre_drill")
    print(f"✅ Backup created: {backup_path}")
    
    # Step 4: Get current revision
    result = run_alembic_current(cwd=project_root)
    current_rev = result.stdout.strip().split()[0] if result.stdout else "unknown"
    print(f"\n📍 Current revision: {current_rev}")
    
    # Step 5: Upgrade (if not at head)
    print(f"\n⬆️ Step 4: Upgrading {steps} step(s)...")
    for i in range(steps):
        result = run_alembic_upgrade("+1", cwd=project_root)
        if result.returncode != 0:
            print(f"❌ Upgrade failed: {result.stderr}")
            return False
        print(result.stdout)
    
    # Step 5: Verify upgrade
    print("\n✅ Step 5: Verifying upgrade...")
    result = run_alembic_current(cwd=project_root)
    new_rev = result.stdout.strip().split()[0] if result.stdout else "unknown"
    print(f"New revision: {new_rev}")
    
    if new_rev == current_rev:
        print("⚠️ Revision didn't change - may already be at head")
    
    # Step 6: Create post-upgrade backup
    print("\n💾 Step 6: Creating post-upgrade backup...")
    backup_path2 = create_backup(db_url, backup_dir / "post_upgrade")
    print(f"✅ Backup created: {backup_path2}")
    
    # Step 7: Downgrade
    print(f"\n⬇️ Step 7: Downgrading {steps} step(s)...")
    for i in range(steps):
        result = run_alembic_downgrade("-1", cwd=project_root)
        if result.returncode != 0:
            print(f"❌ Downgrade failed: {result.stderr}")
            return False
        print(result.stdout)
    
    # Step 8: Verify rollback
    print("\n✅ Step 8: Verifying rollback...")
    result = run_alembic_current(cwd=project_root)
    rolled_back_rev = result.stdout.strip().split()[0] if result.stdout else "unknown"
    print(f"Rolled back to: {rolled_back_rev}")
    
    if rolled_back_rev != current_rev:
        print(f"❌ Rollback verification failed! Expected {current_rev}, got {rolled_back_rev}")
        return False
    
    print("✅ Rollback verified - revision matches original")
    
    # Step 9: Restore original backup
    print("\n🔄 Step 9: Restoring original backup...")
    restore_backup(backup_path, os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/va_matching"))
    print("✅ Original backup restored")
    
    # Step 10: Final verification
    print("\n✅ Step 10: Final verification...")
    result = run_alembic_current(cwd=project_root)
    final_rev = result.stdout.strip().split()[0] if result.stdout else "unknown"
    print(f"Final revision: {final_rev}")
    
    if final_rev == current_rev:
        print("✅ Full rollback drill PASSED!")
        return True
    else:
        print(f"❌ Final verification failed! Expected {current_rev}, got {final_rev}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="VA Matching Platform rollback drill")
    parser.add_argument(
        "--db-url",
        default=os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/va_matching"),
        help="Database URL (default: DATABASE_URL env var)",
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=Path("./backups/rollback_drill"),
        help="Directory for drill backups",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=1,
        help="Number of migration steps to test",
    )
    parser.add_argument(
        "--skip-backup",
        action="store_true",
        help="Skip backup creation (use existing backup)",
    )
    
    args = parser.parse_args()
    
    print("🎯 VA Matching Platform Rollback Drill")
    print(f"Database: {args.db_url}")
    print(f"Backup dir: {args.backup_dir}")
    print(f"Steps: {args.steps}")
    
    try:
        success = run_rollback_drill(args.db_url, args.backup_dir, args.steps)
        if success:
            print("\n🎉 Rollback drill COMPLETED SUCCESSFULLY!")
            return 0
        else:
            print("\n❌ Rollback drill FAILED!")
            return 1
    except Exception as e:
        print(f"\n💥 Rollback drill crashed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())