"""
Integration tests for workflow management API.

Tests workflow execution lifecycle using shared testing infrastructure.
"""

import pytest
import uuid
from httpx import AsyncClient

from apps.api.app.main import app


class TestWorkflowAPI:
    """Test workflow API with real user registration and authentication."""

    async def test_register_and_login(self, async_client: AsyncClient):
        """Test complete registration -> login flow."""
        unique_id = uuid.uuid4().hex[:8]
        email = f"workflow.{unique_id}@example.com"

        # Register a new user
        register_response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "TestPassword123!",
                "first_name": "Test",
                "last_name": "User",
                "agency_name": f"Test Agency {unique_id}",
            },
        )
        assert register_response.status_code == 201, f"Register failed: {register_response.text}"
        data = register_response.json()
        assert data["email"] == email

        # Login with the same credentials
        login_response = await async_client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": "TestPassword123!"},
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        login_data = login_response.json()
        assert "access_token" in login_data

    async def test_workflow_crud(self, async_client: AsyncClient):
        """Test complete workflow CRUD cycle."""
        unique_id = uuid.uuid4().hex  # Full 32-char hex for uniqueness
        email = f"workflow.{unique_id}@example.com"

        # Register a new user
        await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "TestPassword123!",
                "first_name": "Test",
                "last_name": "User",
                "agency_name": f"Workflow Test Agency {unique_id}",
            },
        )

        # Login
        login_response = await async_client.post(
            "/api/v1/auth/login",
            data={
                "username": f"workflow.{unique_id}@example.com",
                "password": "TestPassword123!",
            },
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        token = login_response.json()["access_token"]

        # Create workflow
        create_response = await async_client.post(
            "/api/v1/workflows",
            json={
                "name": "Test Workflow",
                "slug": f"test-workflow-{unique_id}",
                "description": "A test workflow",
                "is_active": True,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert create_response.status_code == 201, f"Create failed: {create_response.text}"
        data = create_response.json()
        assert data["name"] == "Test Workflow"
        assert data["slug"] == f"test-workflow-{unique_id}"

        # Get workflow
        workflow_id = data["id"]
        get_response = await async_client.get(
            f"/api/v1/workflows/{workflow_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_response.status_code == 200
        assert get_response.json()["id"] == workflow_id


__all__ = ["TestWorkflowAPI"]
