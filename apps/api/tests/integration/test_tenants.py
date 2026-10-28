"""
Integration tests for tenant management endpoints.

Covers critical paths:
- Create → List → Get → Update → Delete agencies
"""

import pytest
from httpx import AsyncClient


class TestTenants:
    """Tenant management integration tests."""

    async def test_create_and_list_agencies(self, async_client: AsyncClient, test_user, async_client_auth_header):
        """Test creating and listing agencies."""
        # Create an agency
        create_response = await async_client.post(
            "/api/v1/tenants/",
            json={
                "name": "Test Agency Inc",
                "slug": "test-agency-inc",
            },
            headers={"Authorization": f"Bearer {async_client_auth_header}"},
        )
        assert create_response.status_code == 201, f"Create agency failed: {create_response.text}"
        agency_data = create_response.json()
        assert agency_data["name"] == "Test Agency Inc"
        assert agency_data["slug"] == "test-agency-inc"

        # List agencies
        list_response = await async_client.get(
            "/api/v1/tenants/",
            headers={"Authorization": f"Bearer {async_client_auth_header}"},
        )
        assert list_response.status_code == 200, f"List agencies failed: {list_response.text}"
        agencies = list_response.json()
        assert len(agencies) >= 1

    async def test_get_agency_by_id(self, async_client: AsyncClient, test_user):
        """Test getting a specific agency by ID."""
        # First create an agency
        create_response = await async_client.post(
            "/api/v1/tenants/",
            json={
                "name": "Test Agency for Get",
                "slug": "test-agency-get",
            },
            headers={"Authorization": f"Bearer {async_client_auth_header}"},
        )
        assert create_response.status_code == 201
        agency_id = create_response.json()["id"]

        # Get the agency
        get_response = await async_client.get(
            f"/api/v1/tenants/{agency_id}",
            headers={"Authorization": f"Bearer {async_client_auth_header}"},
        )
        assert get_response.status_code == 200
        assert get_response.json()["id"] == agency_id
        assert get_response.json()["name"] == "Test Agency for Get"

    async def test_update_agency(self, async_client: AsyncClient, test_user):
        """Test updating an agency."""
        create_response = await async_client.post(
            "/api/v1/tenants/",
            json={
                "name": "Original Agency Name",
                "slug": "original-agency",
            },
            headers={"Authorization": f"Bearer {async_client_auth_header}"},
        )
        agency_id = create_response.json()["id"]

        # Update the agency
        update_response = await async_client.patch(
            f"/api/v1/tenants/{agency_id}",
            json={"name": "Updated Agency Name"},
            headers={"Authorization": f"Bearer {async_client_auth_header}"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "Updated Agency Name"

    async def test_delete_agency(self, async_client: AsyncClient, test_user):
        """Test deleting an agency."""
        create_response = await async_client.post(
            "/api/v1/tenants/",
            json={
                "name": "To Be Deleted Agency",
                "slug": "to-be-deleted",
            },
            headers={"Authorization": f"Bearer {async_client_auth_header}"},
        )
        agency_id = create_response.json()["id"]

        # Delete the agency
        delete_response = await async_client.delete(
            f"/api/v1/tenants/{agency_id}",
            headers={"Authorization": f"Bearer {async_client_auth_header}"},
        )
        assert delete_response.status_code == 204

        # Verify deletion
        get_response = await async_client.get(
            f"/api/v1/tenants/{agency_id}",
            headers={"Authorization": f"Bearer {async_client_auth_header}"},
        )
        assert get_response.status_code == 404

    async def test_unauthenticated_access_denied(self, async_client: AsyncClient):
        """Test that unauthenticated requests are rejected."""
        response = await async_client.get("/api/v1/tenants/")
        assert response.status_code == 401

    async def test_create_agency_without_auth(self, async_client: AsyncClient):
        """Test that creating an agency without auth is rejected."""
        response = await async_client.post(
            "/api/v1/tenants/",
            json={"name": "Unauthorized Agency", "slug": "unauth-agency"},
        )
        assert response.status_code == 401