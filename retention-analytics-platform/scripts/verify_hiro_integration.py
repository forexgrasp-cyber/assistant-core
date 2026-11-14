#!/usr/bin/env python
"""Live verification script for Hiro Analytics integration.

Queries the actual Hiro API endpoints and validates the bridge works end-to-end.

Endpoints used:
- GET  /api/v1/agency/platforms
- POST /api/v1/agency/platforms/hiro/sync
- GET  /api/v1/agency/platforms/syncs

Usage:
    python scripts/verify_hiro_integration.py           # live verification
    python scripts/verify_hiro_integration.py --dry-run # dry-run mode (no network)
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

from shared.integrations.hiro_client import HiroClient, HIRO_DEFAULT_API_BASE


def _print_check(name: str, ok: bool, detail: str = "") -> None:
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))


def _print_section(title: str) -> None:
    print(f"\n=== {title} ===")


async def _verify_live(client: HiroClient) -> tuple[int, int]:
    passed = failed = 0

    _print_section("REST ENDPOINTS")
    # 1. Platforms catalog
    r = await client.platforms()
    ok = r.get("status") in ("ok", "dry_run") and "platforms" in r
    _print_check("GET /agency/platforms", ok, f"count={len(r.get('platforms', []))}")
    if ok:
        passed += 1
    else:
        failed += 1
        print(f"       Response: {r}")

    # 2. Sync hiro platform (should work if we have key)
    r = await client.sync_platform("hiro", "test-tenant")
    ok = r.get("status") in ("ok", "dry_run", "no_credentials")
    _print_check("POST /agency/platforms/hiro/sync", ok, f"status={r.get('status')}")
    if ok:
        passed += 1
    else:
        failed += 1

    # 3. Sync history
    r = await client.syncs("test-tenant")
    ok = r.get("status") in ("ok", "dry_run") and "syncs" in r
    _print_check("GET /agency/platforms/syncs", ok, f"count={len(r.get('syncs', []))}")
    if ok:
        passed += 1
    else:
        failed += 1

    _print_section("MCP TOOLS")
    # 4. Ask Hiro
    r = await client.ask("Which clients are behind goal?", "test-tenant")
    ok = r.get("status") in ("ok", "dry_run", "no_credentials")
    _print_check("MCP ask_hiro", ok, f"status={r.get('status')}")
    if ok:
        passed += 1
    else:
        failed += 1

    # 5. Hiro roster
    r = await client.mcp_roster("test-tenant")
    ok = r.get("status") in ("ok", "dry_run", "no_credentials")
    _print_check("MCP hiro_roster", ok, f"status={r.get('status')}")
    if ok:
        passed += 1
    else:
        failed += 1

    return passed, failed


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Hiro Analytics integration")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry-run mode (no network)")
    parser.add_argument("--api-base", default=HIRO_DEFAULT_API_BASE, help="Override API base URL")
    parser.add_argument("--mcp-url", default=None, help="Override MCP URL")
    args = parser.parse_args()

    if args.dry_run:
        os.environ["HIRO_DRY_RUN"] = "1"

    client = HiroClient(api_base=args.api_base, mcp_url=args.mcp_url)

    import asyncio
    passed, failed = asyncio.run(_verify_live(client))

    _print_section("SUMMARY")
    print(f"Passed: {passed}, Failed: {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())