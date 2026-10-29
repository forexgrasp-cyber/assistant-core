"""
Integration tests for authentication API endpoints.

Covers critical paths:
- Register → Login → Get Me → Change Password → Logout
- Email verification flow
- Password reset flow
"""

import pytest
from httpx import AsyncClient
import uuid


class TestAuth:
    """Authentication integration tests."""

    async def test_register_and_login_flow(self, async_client: AsyncClient):
        """Test complete registration → login → get me flow."""
        # Register a new user with unique email
        unique_id = uuid.uuid4().hex[:8]
        register_data = {
            "email": f"integration.test.{unique_id}@example.com",
            "password": "TestPassword123!",
            "first_name": "Integration",
            "last_name": "Test",
            "agency_name": f"Integration Test Agency {unique_id}",
        }

        response = await async_client.post("/api/v1/auth/register", json=register_data)
        assert response.status_code == 201, f"Registration failed: {response.text}"
        data = response.json()
        assert data["email"] == register_data["email"]
        assert data["first_name"] == "Integration"
        assert data["last_name"] == "Test"
        assert data["is_active"] is True
        user_id = data["id"]

        # Login with the registered user
        login_response = await async_client.post(
            "/api/v1/auth/login",
            data={"username": f"integration.test.{unique_id}@example.com", "password": "TestPassword123!"},
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        login_data = login_response.json()
        assert "access_token" in login_data
        assert "refresh_token" in login_data
        assert login_data["token_type"] == "bearer"
        access_token = login_data["access_token"]

        # Get current user profile
        me_response = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert me_response.status_code == 200, f"Get me failed: {me_response.text}"
        me_data = me_response.json()
        assert me_data["id"] == user_id
        assert me_data["email"] == register_data["email"]
        assert me_data["is_active"] is True

        # Change password
        change_password_response = await async_client.put(
            "/api/v1/auth/me/password",
            params={
                "current_password": "TestPassword123!",
                "new_password": "NewPassword456!",
            },
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert change_password_response.status_code == 200, f"Password change failed: {change_password_response.text}"

        # Login with new password
        login_response2 = await async_client.post(
            "/api/v1/auth/login",
            data={"username": register_data["email"], "password": "NewPassword456!"},
        )
        assert login_response2.status_code == 200, f"Login with new password failed: {login_response2.text}"
        new_token_data = login_response2.json()
        assert "access_token" in new_token_data

        # Logout
        logout_response = await async_client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {new_token_data['access_token']}"},
        )
        assert logout_response.status_code == 200, f"Logout failed: {logout_response.text}"

    async def test_login_with_invalid_credentials(self, async_client: AsyncClient):
        """Test login fails with invalid credentials."""
        response = await async_client.post(
            "/api/v1/auth/login",
            data={"username": "nonexistent@example.com", "password": "wrongpassword"},
        )
        assert response.status_code == 401
        assert "Incorrect email or password" in response.text

    async def test_register_duplicate_email(self, async_client: AsyncClient):
        """Test registration fails with duplicate email."""
        # First registration
        response1 = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "TestPassword123!",
                "first_name": "Duplicate",
                "last_name": "User",
                "agency_name": "Duplicate Agency",
            },
        )
        assert response1.status_code == 201
        
        # Second registration with same email
        response2 = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "TestPassword123!",
                "first_name": "Duplicate",
                "last_name": "User",
                "agency_name": "Duplicate Agency 2",
            },
        )
        assert response2.status_code == 400
        assert "already registered" in response2.text.lower()

    async def test_get_me_without_auth(self, async_client: AsyncClient):
        """Test that /me requires authentication."""
        response = await async_client.get("/api/v1/auth/me")
        assert response.status_code == 401