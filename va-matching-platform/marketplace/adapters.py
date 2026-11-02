"""
VA Source Adapters
==================
Adapters for VA sources: Upwork, Fiverr, Toptal, Direct applications.

Uses real OAuth 2.0 implementations from shared.oauth for Upwork, Fiverr, Toptal.
Direct applications use simple API key authentication.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import urllib.parse
import urllib.request
import urllib.error
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from .base import VAProfile, VASkill, VAStatus, VASourceAdapter
from .adapters_oauth import (
    UpworkOAuthAdapter,
    FiverrOAuthAdapter,
    ToptalOAuthAdapter,
    create_oauth_adapters,
)

log = logging.getLogger(__name__)


class DirectAdapter(VASourceAdapter):
    """Direct application VA source adapter (no OAuth needed)."""

    @property
    def source_name(self) -> str:
        return "direct"

    def __init__(self, applications_db: list[dict] | None = None):
        self.applications_db = applications_db or []

    async def search_vas(
        self,
        skills: list[str],
        min_hourly_rate: float | None = None,
        max_hourly_rate: float | None = None,
        min_rating: float | None = None,
        timezone: str | None = None,
        availability_hours: int | None = None,
        limit: int = 50,
    ) -> list[VAProfile]:
        log.info(f"Searching direct applications for skills: {skills}")

        results = []
        for app in self.applications_db:
            va = VAProfile(
                id=f"direct_{uuid4().hex[:8]}",
                email=app.get("email", ""),
                full_name=app.get("full_name", ""),
                timezone=app.get("timezone", "UTC"),
                hourly_rate=app.get("hourly_rate", 0),
                availability_hours_per_week=app.get("availability_hours", 0),
                skills=[VASkill(name=s, category="general", proficiency=3) for s in app.get("skills", [])],
                languages=app.get("languages", ["English"]),
                location=app.get("location", ""),
                bio=app.get("bio", ""),
                portfolio_url=app.get("portfolio_url", ""),
                linkedin_url=app.get("linkedin_url", ""),
                status=VAStatus.PENDING,
                source="direct",
                source_profile_url="",
            )
            # Filter by criteria
            if min_hourly_rate and va.hourly_rate < min_hourly_rate:
                continue
            if max_hourly_rate and va.hourly_rate > max_hourly_rate:
                continue
            if timezone and va.timezone != timezone:
                continue
            if availability_hours and va.availability_hours_per_week < availability_hours:
                continue
            results.append(va)
            if len(results) >= limit:
                break
        return results

    async def get_va_details(self, va_id: str) -> VAProfile | None:
        for app in self.applications_db:
            if app.get("id") == va_id:
                return VAProfile(
                    id=va_id,
                    email=app.get("email", ""),
                    full_name=app.get("full_name", ""),
                    timezone=app.get("timezone", "UTC"),
                    hourly_rate=app.get("hourly_rate", 0),
                    availability_hours_per_week=app.get("availability_hours", 0),
                    skills=[VASkill(name=s, category="general", proficiency=3) for s in app.get("skills", [])],
                    languages=app.get("languages", ["English"]),
                    location=app.get("location", ""),
                    bio=app.get("bio", ""),
                    portfolio_url=app.get("portfolio_url", ""),
                    linkedin_url=app.get("linkedin_url", ""),
                    status=VAStatus.PENDING,
                    source="direct",
                    source_profile_url="",
                )
        return None

    async def get_va_reviews(self, va_id: str) -> list[dict]:
        return []

    async def invite_va(self, va_id: str, message: str) -> bool:
        log.info(f"Inviting direct VA {va_id}")
        return True

    def add_application(self, application: dict):
        """Add a direct application."""
        application["id"] = application.get("id", str(uuid4()))
        application["submitted_at"] = datetime.now(UTC).isoformat()
        application["status"] = "pending_review"
        self.applications_db.append(application)
        return application["id"]


class VAAdapterRegistry:
    """Registry for managing VA source adapters."""

    DEFAULT_INVIDIOUS_HOSTS = [
        "https://yt.chocolatemoo53.com",
        "https://inv.nadeko.net",
        "https://invidious.nerdvpn.de",
        "https://inv.us.projectsegfau.lt",
        "https://invidious.privacyredirect.com",
        "https://inv.tux.pizza",
        "https://invidious.jing.rocks",
        "https://invidious.f5.si",
        "https://invidious.protokolla.fi",
        "https://iv.ggtyler.dev",
        "https://invidious.jing.rocks",
    ]

    def __init__(self, tenant_id: str | None = None, db_session: Any | None = None, dry_run: bool = False):
        self.adapters: dict[str, VASourceAdapter] = {}
        self._working_hosts: list[str] = []
        self._host_index = 0
        self._host_last_failure: dict[str, float] = {}
        self._host_failure_count: dict[str, int] = {}
        self.request_timeout = 30
        self.max_retries = 3
        
        # Initialize OAuth-based adapters
        upwork, fiverr, toptal = create_oauth_adapters(tenant_id=None, db_session=None, dry_run=True)
        self.register(upwork)
        self.register(fiverr)
        self.register(toptal)
        self.register(DirectAdapter())

    def register(self, adapter: VASourceAdapter):
        self.adapters[adapter.source_name] = adapter

    def get(self, source_name: str) -> VASourceAdapter | None:
        return self.adapters.get(source_name)

    def get_all(self) -> list[VASourceAdapter]:
        return list(self.adapters.values())

    async def discover_working_instances(self, test_video_id: str = "test") -> list[str]:
        """Discover working Invidious instances by testing caption API."""
        instances = await self._fetch_instance_list()
        working = []

        async def test_instance(host: str) -> tuple[str, bool]:
            try:
                url = f"{host.rstrip('/')}/api/v1/captions/{test_video_id}"
                data = await self._fetch_json(url)
                if data and data.get("captions"):
                    return host, True
            except Exception:
                pass
            return host, False

        semaphore = asyncio.Semaphore(5)

        async def test_with_sem(h):
            async with semaphore:
                return await test_instance(h)

        results = await asyncio.gather(*[test_with_sem(h) for h in instances], return_exceptions=True)
        for r in results:
            if isinstance(r, tuple) and r[1]:
                working.append(r[0])

        self._working_hosts = working or self.DEFAULT_INVIDIOUS_HOSTS[:2]
        log.info(f"Discovered {len(working)} working instances")
        return working

    async def _fetch_instance_list(self) -> list[str]:
        try:
            data = await self._fetch_json("https://api.invidious.io/instances.json?sort_by=type,users")
            if not data:
                return self.DEFAULT_INVIDIOUS_HOSTS

            hosts = []
            for name, meta in data:
                uri = meta.get("uri", "")
                if uri.startswith("https://") and meta.get("api"):
                    hosts.append(uri)
                elif uri.startswith("https://"):
                    hosts.append(uri)
            return hosts or self.DEFAULT_INVIDIOUS_HOSTS
        except Exception as e:
            log.warning(f"Failed to fetch instance list: {e}")
            return self.DEFAULT_INVIDIOUS_HOSTS

    def _next_host(self) -> str:
        if not self._working_hosts:
            self._working_hosts = self.DEFAULT_INVIDIOUS_HOSTS[:]
        host = self._working_hosts[self._host_index % len(self._working_hosts)]
        self._host_index += 1
        return host

    def _mark_host_failure(self, host: str):
        now = time.time()
        self._host_last_failure[host] = now
        self._host_failure_count[host] = self._host_failure_count.get(host, 0) + 1
        if self._host_failure_count[host] >= 3:
            if host in self._working_hosts:
                self._working_hosts.remove(host)
                log.warning(f"Removed failing host: {host}")

    async def _fetch_with_failover(self, path: str, timeout: int | None = None):
        if not self._working_hosts:
            await self.discover_working_instances()

        timeout = timeout or self.request_timeout
        last_error = None

        for attempt in range(self.max_retries * len(self._working_hosts)):
            host = self._next_host()
            url = f"{host.rstrip('/')}{path}"

            try:
                data = await self._fetch_json(url, timeout=timeout)
                if data:
                    return data
            except Exception as e:
                last_error = e
                self._mark_host_failure(host)
                await asyncio.sleep(0.5 * (attempt + 1))

        log.error(f"All hosts failed for {path}: {last_error}")
        return None

    async def _fetch_json(self, url: str, timeout: int | None = None):
        timeout = timeout or self.request_timeout
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; VAAdapterRegistry/2026.10)"}
            )
            loop = asyncio.get_running_loop()
            def _fetch():
                with urllib.request.urlopen(req, timeout=timeout or self.request_timeout) as resp:
                    return resp.read().decode("utf-8", "ignore")
            body = await loop.run_in_executor(None, _fetch)
            return json.loads(body)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise
        except Exception as e:
            log.debug(f"Fetch failed for {url}: {e}")
            raise

    async def search_all_sources(
        self,
        skills: list[str],
        min_hourly_rate: float | None = None,
        max_hourly_rate: float | None = None,
        min_rating: float | None = None,
        timezone: str | None = None,
        availability_hours: int | None = None,
        limit: int = 50,
    ) -> list[VAProfile]:
        """Search across all registered sources concurrently."""
        tasks = []
        for adapter in self.adapters.values():
            tasks.append(adapter.search_vas(
                skills=skills,
                min_hourly_rate=min_hourly_rate,
                max_hourly_rate=max_hourly_rate,
                min_rating=min_rating,
                timezone=timezone,
                availability_hours=availability_hours,
                limit=limit,
            ))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        all_profiles = []
        for result in results:
            if isinstance(result, list):
                all_profiles.extend(result)
            elif isinstance(result, Exception):
                log.error(f"Adapter search failed: {result}")

        # Sort by source rating descending
        all_profiles.sort(key=lambda v: v.source_rating, reverse=True)
        return all_profiles[:limit]


# Default registry instance (lazy initialization for dry-run)
default_registry = None

def get_default_registry(tenant_id: str | None = None, db_session: Any | None = None, dry_run: bool = True) -> VAAdapterRegistry:
    """Get or create the default registry with OAuth adapters."""
    global default_registry
    if default_registry is None:
        default_registry = VAAdapterRegistry(tenant_id=tenant_id, db_session=None, dry_run=dry_run)
    return default_registry


# Register platform OAuth clients on import
from .adapters_oauth import create_oauth_adapters

# Backward compatibility aliases
UpworkAdapter = UpworkOAuthAdapter
FiverrAdapter = FiverrOAuthAdapter
ToptalAdapter = ToptalOAuthAdapter

# Note: Actual OAuth adapters are created via get_default_registry() with proper config