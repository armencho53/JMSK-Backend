"""Unit tests for MetalPriceResponse schema"""
import pytest
from datetime import datetime
from app.schemas.metal import MetalPriceResponse


def test_metal_price_response_creation():
    """Test creating a MetalPriceResponse with all required fields"""
    now = datetime.utcnow()
    response = MetalPriceResponse(
        metal_code="GOLD_24K",
        price_per_gram=75.50,
        currency="USD",
        fetched_at=now,
        cached=False
    )
    
    assert response.metal_code == "GOLD_24K"
    assert response.price_per_gram == 75.50
    assert response.currency == "USD"
    assert response.fetched_at == now
    assert response.cached is False


def test_metal_price_response_default_currency():
    """Test that currency defaults to USD"""
    now = datetime.utcnow()
    response = MetalPriceResponse(
        metal_code="SILVER_925",
        price_per_gram=0.85,
        fetched_at=now,
        cached=True
    )
    
    assert response.currency == "USD"


def test_metal_price_response_cached_flag():
    """Test cached flag for both cached and fresh prices"""
    now = datetime.utcnow()
    
    # Cached price
    cached_response = MetalPriceResponse(
        metal_code="GOLD_18K",
        price_per_gram=56.75,
        fetched_at=now,
        cached=True
    )
    assert cached_response.cached is True
    
    # Fresh price
    fresh_response = MetalPriceResponse(
        metal_code="GOLD_18K",
        price_per_gram=56.75,
        fetched_at=now,
        cached=False
    )
    assert fresh_response.cached is False


def test_metal_price_response_serialization():
    """Test that MetalPriceResponse can be serialized to dict"""
    now = datetime.utcnow()
    response = MetalPriceResponse(
        metal_code="PLATINUM",
        price_per_gram=95.00,
        currency="USD",
        fetched_at=now,
        cached=False
    )
    
    data = response.model_dump()
    assert data["metal_code"] == "PLATINUM"
    assert data["price_per_gram"] == 95.00
    assert data["currency"] == "USD"
    assert data["fetched_at"] == now
    assert data["cached"] is False
