"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
def test_api_v1_router_exists(client: TestClient):
    """Test that the API v1 router is properly mounted."""
    response = client.get("/docs")
    assert response.status_code == 200


@pytest.mark.api
def test_auth_endpoints_exist(client: TestClient):
    """Test that authentication endpoints are available."""
    # Test login endpoint exists (should return 422 for missing data, not 404)
    response = client.post("/api/v1/auth/login")
    assert response.status_code != 404
    
    # Test register endpoint exists
    response = client.post("/api/v1/auth/register")
    assert response.status_code != 404


@pytest.mark.integration
def test_database_connection(db_session):
    """Test that database connection works in test environment."""
    from sqlalchemy import text
    result = db_session.execute(text("SELECT 1 as test_value"))
    row = result.fetchone()
    assert row[0] == 1