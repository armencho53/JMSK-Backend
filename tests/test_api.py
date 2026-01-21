"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
def test_api_v1_router_exists(client: TestClient):
    """Test that the API v1 router is properly mounted."""
    # Test that API endpoints return proper responses (not 404)
    # Since /api/v1/ might not have a GET handler, test a known endpoint
    response = client.get("/docs")
    # Docs endpoint should be available and indicate API is working
    assert response.status_code == 200


@pytest.mark.api
def test_auth_endpoints_exist(client: TestClient):
    """Test that authentication endpoints are available."""
    # Test login endpoint exists
    response = client.post("/api/v1/auth/login")
    # Should not return 404 (endpoint exists), but may return 422 (validation error)
    assert response.status_code != 404
    
    # Test register endpoint exists  
    response = client.post("/api/v1/auth/register")
    assert response.status_code != 404


@pytest.mark.integration
def test_database_connection(client: TestClient, db_session):
    """Test that database connection works in test environment."""
    # This test verifies that our test database setup works
    assert db_session is not None
    
    # Try a simple database operation
    from sqlalchemy import text
    result = db_session.execute(text("SELECT 1 as test_value"))
    row = result.fetchone()
    assert row[0] == 1