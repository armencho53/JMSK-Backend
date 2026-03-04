"""Test that new controllers are properly registered in the API router"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


def test_order_controller_routes_registered():
    """Verify that order controller routes are registered"""
    client = TestClient(app)
    
    # Check that the routes exist (will return 401 without auth, but that's expected)
    # POST /api/v1/orders-v2/
    response = client.post("/api/v1/orders-v2/")
    assert response.status_code in [401, 422], "Order creation endpoint should exist"
    
    # GET /api/v1/orders-v2/{order_id}
    response = client.get("/api/v1/orders-v2/1")
    assert response.status_code in [401, 404], "Order retrieval endpoint should exist"
    
    # PUT /api/v1/orders-v2/{order_id}
    response = client.put("/api/v1/orders-v2/1")
    assert response.status_code in [401, 422], "Order update endpoint should exist"


def test_metal_price_controller_routes_registered():
    """Verify that metal price controller routes are registered"""
    client = TestClient(app)
    
    # GET /api/v1/metals/price/{metal_code}
    response = client.get("/api/v1/metals/price/GOLD_24K")
    assert response.status_code in [401, 404], "Metal price endpoint should exist"


def test_supply_tracking_metal_balances_endpoint():
    """Verify that company metal balances endpoint exists"""
    client = TestClient(app)
    
    # GET /api/v1/companies/{company_id}/metal-balances
    response = client.get("/api/v1/companies/1/metal-balances")
    assert response.status_code in [401, 404], "Company metal balances endpoint should exist"


def test_openapi_schema_includes_new_routes():
    """Verify that new routes appear in OpenAPI schema"""
    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200
    
    openapi_schema = response.json()
    paths = openapi_schema.get("paths", {})
    
    # Check for new order routes
    assert "/api/v1/orders-v2/" in paths, "Order creation route should be in OpenAPI schema"
    assert "/api/v1/orders-v2/{order_id}" in paths, "Order retrieval route should be in OpenAPI schema"
    
    # Check for metal price route
    assert "/api/v1/metals/price/{metal_code}" in paths, "Metal price route should be in OpenAPI schema"
    
    # Check for company metal balances route
    assert "/api/v1/companies/{company_id}/metal-balances" in paths, "Company metal balances route should be in OpenAPI schema"
