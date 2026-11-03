"""L4 Playwright browser journey tests.

Tests the user-facing product works in a real browser. Per TESTING_STANDARDS.md
§2 (L4): every user-facing flow requires at least one Playwright journey.

These tests require Playwright to be installed:
    pip install playwright && playwright install chromium

Run with:
    pytest tests/e2e/ -m e2e
"""

from __future__ import annotations

import pytest


@pytest.mark.e2e
async def test_dashboard_loads(page, base_url):
    """Dashboard page loads; no console errors, no failed network requests."""
    console_errors: list[str] = []
    failed_requests: list[str] = []
    page.on(
        "console",
        lambda msg: console_errors.append(msg.text) if msg.type == "error" else None,
    )
    page.on("requestfailed", lambda req: failed_requests.append(req.url))

    await page.goto(f"{base_url}/dashboard")
    await page.wait_for_load_state("networkidle")

    assert not console_errors, f"Console errors: {console_errors}"
    assert not failed_requests, f"Failed requests: {failed_requests}"


@pytest.mark.e2e
async def test_services_page_reachable(page, base_url):
    """Services page lists registered services (email, sms present)."""
    await page.goto(f"{base_url}/api/v1/services")
    await page.wait_for_load_state("networkidle")
    body = await page.locator("body").text_content()
    assert body is not None
    assert "email" in body.lower()
    assert "sms" in body.lower()


@pytest.mark.e2e
async def test_workflows_page_reachable(page, base_url):
    """Workflows page lists registered pipelines."""
    await page.goto(f"{base_url}/api/v1/workflows")
    await page.wait_for_load_state("networkidle")
    body = await page.locator("body").text_content()
    assert body is not None
    assert "churn-prevention" in body.lower()


@pytest.mark.e2e
async def test_health_endpoint(page, base_url):
    """Health endpoint returns ok."""
    await page.goto(f"{base_url}/health")
    await page.wait_for_load_state("networkidle")
    body = await page.locator("body").text_content()
    assert body is not None
    assert "ok" in body.lower()
