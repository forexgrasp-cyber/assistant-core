#!/usr/bin/env python
"""Watch Hiro Analytics site for platform catalog changes.

Fetches hiroanalytics.com/#integrations, parses the listed platforms,
and compares against our PLATFORMS catalog to detect drift.

Usage:
    python scripts/watch_hiro_site.py               # live check
    python scripts/watch_hiro_site.py --save        # save snapshot to docs/HIRO_SITE_SNAPSHOT.json
    python scripts/watch_hiro_site.py --dry-run     # dry-run mode (no network)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any
from urllib.request import urlopen

from shared.integrations.hiro_client import HiroClient


HRO_INTEGRATIONS_URL = "https://hiroanalytics.com/#integrations"


def _print_check(name: str, ok: bool, detail: str = "") -> None:
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))


async def _fetch_site(dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return {
            "status": "dry_run",
            "url": HRO_INTEGRATIONS_URL,
            "platforms": [
                "klaviyo", "attentive", "postscript", "omnisend", "sendlane",
                "shopify", "recharge", "skio", "loop", "stayai", "ordergroove", "alia",
                "stripe", "mailchimp", "braze"
            ]
        }
    try:
        with urlopen(HRO_INTEGRATIONS_URL, timeout=10) as resp:
            html = resp.read().decode("utf-8")
        # Simple extraction: look for known platform names in the page
        known = [
            "klaviyo", "attentive", "postscript", "omnisend", "sendlane",
            "shopify", "recharge", "skio", "loop", "stayai", "ordergroove", "alia",
            "stripe", "mailchimp", "braze"
        ]
        found = [p for p in known if p in html.lower()]
        return {"status": "ok", "url": HRO_INTEGRATIONS_URL, "platforms": found, "raw_length": len(html)}
    except Exception as exc:
        return {"status": "error", "url": HRO_INTEGRATIONS_URL, "error": str(exc)}


def _compare_with_catalog(site_platforms: list[str]) -> dict[str, Any]:
    from retention_analytics_advanced_processing.agency_connectors import PLATFORMS
    our = set(PLATFORMS.keys())
    theirs = set(site_platforms)
    missing_in_ours = sorted(theirs - our)
    extra_in_ours = sorted(our - theirs)
    return {
        "our_count": len(our),
        "their_count": len(theirs),
        "parity": missing_in_ours == [] and extra_in_ours == [],
        "missing_in_ours": missing_in_ours,
        "extra_in_ours": extra_in_ours,
    }


async def main() -> int:
    parser = argparse.ArgumentParser(description="Watch Hiro site for platform catalog changes")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry-run mode (no network)")
    parser.add_argument("--save", action="store_true", help="Save snapshot to docs/HIRO_SITE_SNAPSHOT.json")
    args = parser.parse_args()

    print("=== HIRO SITE WATCH ===\n")

    site_data = await _fetch_site(args.dry_run)
    if site_data["status"] == "error":
        print(f"[FAIL] Failed to fetch site: {site_data['error']}")
        return 1

    platforms = site_data.get("platforms", [])
    print(f"Fetched {len(platforms)} platforms from {HRO_INTEGRATIONS_URL}")

    comparison = _compare_with_catalog(platforms)
    _print_check("Platform catalog parity", comparison["parity"],
                 f"ours={comparison['our_count']} theirs={comparison['their_count']}")
    if comparison["missing_in_ours"]:
        print(f"  Missing in our catalog: {comparison['missing_in_ours']}")
    if comparison["extra_in_ours"]:
        print(f"  Extra in our catalog: {comparison['extra_in_ours']}")

    # Also test HiroClient endpoints
    client = HiroClient()
    r = await client.platforms()
    _print_check("HiroClient.platforms()", r.get("status") in ("ok", "dry_run"),
                 f"status={r.get('status')}")

    if args.save:
        os.makedirs("docs", exist_ok=True)
        snapshot = {
            "site": site_data,
            "catalog": comparison,
            "hiro_client": r,
        }
        with open("docs/HIRO_SITE_SNAPSHOT.json", "w") as f:
            json.dump(snapshot, f, indent=2, default=str)
        print(f"\n[OK] Snapshot saved to docs/HIRO_SITE_SNAPSHOT.json")

    return 0 if comparison["parity"] else 1


if __name__ == "__main__":
    import asyncio
    sys.exit(asyncio.run(main()))