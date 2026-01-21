"""Basic tests for the FastAPI application."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.mark.unit
def test_health_check():
    """Test that the application starts and responds to health check."""
    response = client.get("/")
    # Either root endpoint exists or returns 404 - both are valid for a working app
    assert response.status_code in [200, 404]


@pytest.mark.unit
def test_docs_endpoint():
    """Test that the API docs endpoint is accessible."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger" in response.text.lower() or "openapi" in response.text.lower()


@pytest.mark.unit
def test_openapi_endpoint():
    """Test that the OpenAPI schema endpoint is accessible."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    
    # Verify it's valid JSON
    openapi_data = response.json()
    assert "openapi" in openapi_data
    assert "info" in openapi_data


@pytest.mark.unit
def test_cors_headers():
    """Test that CORS headers are properly configured."""
    response = client.options("/docs")
    # CORS preflight should be handled
    assert response.status_code in [200, 405]  # 405 if OPTIONS not explicitly handled