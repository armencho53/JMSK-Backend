"""Basic tests for the FastAPI application startup and core endpoints."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_docs_accessible():
    response = client.get("/docs")
    assert response.status_code == 200


def test_openapi_schema():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert "info" in data


def test_auth_endpoints_exist():
    assert client.post("/api/v1/auth/login").status_code != 404
    assert client.post("/api/v1/auth/register").status_code != 404
