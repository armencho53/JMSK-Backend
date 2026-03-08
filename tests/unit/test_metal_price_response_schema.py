"""Unit tests for MetalPriceResponse schema."""
from datetime import datetime
from app.schemas.metal import MetalPriceResponse


def test_metal_price_response():
    now = datetime.utcnow()
    r = MetalPriceResponse(
        metal_code="GOLD_24K", price_per_gram=75.50,
        fetched_at=now, cached=False,
    )
    assert r.metal_code == "GOLD_24K"
    assert r.currency == "USD"  # default
    assert r.cached is False
    data = r.model_dump()
    assert data["price_per_gram"] == 75.50
