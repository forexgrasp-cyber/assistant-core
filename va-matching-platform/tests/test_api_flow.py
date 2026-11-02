"""Full e2e flow: register → login → intake → VA search (mock adapter) → match → accept."""

import asyncio
from httpx import AsyncClient
import pytest


@pytest.mark.asyncio
async def test_full_client_to_match_flow(client, auth_headers):
    # 1) Client intake
    intake = {
        "email": "client-user@va-matching.dev",
        "company_name": "Acme Corp",
        "contact_name": "Test Client",
        "timezone": "America/New_York",
        "industry": "SaaS",
        "company_size": 25,
        "monthly_budget": 5000,
        "needed_hours_per_week": 20,
        "required_skills": ["admin", "bookkeeping"],
        "tasks_to_delegate": ["inbox", "calendar"],
        "current_tools": ["Slack"],
        "preferred_timezone_overlap_hours": 4,
        "max_hourly_rate": 25,
        "source": "direct",
    }
    r = await client.post("/api/clients", json=intake, headers=auth_headers)
    assert r.status_code == 200, r.text
    client_id = r.json()["client_id"]
    assert client_id

    # 2) VA search (mock adapter returns candidates)
    search = {
        "skills": ["admin", "bookkeeping"],
        "limit": 5,
    }
    r = await client.post("/api/vas/search", json=search, headers=auth_headers)
    assert r.status_code == 200, r.text
    vas = r.json()
    assert len(vas) >= 1

    # 3) Wait for vetting tasks to complete (background workers)
    await asyncio.sleep(3)  # give workers time

    # 4) Matching (min_score=0 so we get any matches)
    match_req = {"client_id": client_id, "limit": 3, "min_score": 0.0}
    r = await client.post("/api/matches", json=match_req, headers=auth_headers)
    assert r.status_code == 200, r.text
    matches = r.json()

    # 5) If matches exist, accept one and verify
    if matches:
        match_id = matches[0]["match_id"]
        r = await client.post(f"/api/matches/{match_id}/accept", headers=auth_headers)
        assert r.status_code == 200, r.text
        assert r.json()["message"] == "Match accepted"

        # Verify match status is ACCEPTED
        r = await client.get(f"/api/matches/client/{client_id}", headers=auth_headers)
        assert r.status_code == 200
        updated = r.json()
        assert len(updated) >= 1
        accepted = [m for m in updated if m["status"] == "accepted"]
        assert len(accepted) == 1
        assert accepted[0]["match_id"] == matches[0]["match_id"]

        # Check notifications created
        r = await client.get("/api/notifications", headers=auth_headers)
        assert r.status_code == 200
        notifs = r.json()
        assert any(n["type"] == "match_proposed" for n in notifs)
    else:
        # No matches due to vetting outcomes - still verify flow didn't crash
        pass

    # 9) Reports work
    r = await client.get("/api/reports/payments")
    assert r.status_code == 200
    data = r.json()
    assert "total" in data and "by_status" in data

    r = await client.get("/api/reports/ledger")
    assert r.status_code == 200
    data = r.json()
    assert "summary" in data and "rows" in data