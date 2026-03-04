"""MetalPrice data model for caching precious metal prices from external APIs

This model stores cached precious metal prices to reduce external API calls
and improve performance. Prices are cached per metal category (GOLD, SILVER, PLATINUM)
with configurable expiration times.

Requirements: 8.7, 8.8
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, UniqueConstraint
from datetime import datetime
from app.data.database import Base


class MetalPrice(Base):
    """
    MetalPrice model for caching precious metal prices from external APIs.
    
    This model stores current market prices for precious metal categories
    (GOLD, SILVER, PLATINUM) with expiration timestamps to enable cache
    invalidation. The unique constraint on metal_category ensures only
    one active price per metal category.
    
    Attributes:
        id: Primary key
        metal_category: Metal category identifier (GOLD, SILVER, PLATINUM)
        price_per_gram: Current market price per gram
        currency: Currency code (default: USD)
        fetched_at: Timestamp when price was fetched from API
        expires_at: Timestamp when cached price expires
    
    Constraints:
        - Unique constraint on metal_category (only one price per category)
    
    Requirements: 8.7, 8.8
    """
    __tablename__ = "metal_prices"
    __table_args__ = (
        UniqueConstraint("metal_category", name="uq_metal_category"),
    )

    id = Column(Integer, primary_key=True, index=True)
    metal_category = Column(String(20), nullable=False, index=True)
    price_per_gram = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    fetched_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False, index=True)
