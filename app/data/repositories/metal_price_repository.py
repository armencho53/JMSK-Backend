"""MetalPrice repository for data access

This repository manages cached precious metal prices from external APIs.
It provides methods to retrieve current prices, save new prices with expiration,
and check if cached prices have expired.

Requirements: 8.7, 8.8
"""
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.data.models.metal_price import MetalPrice


class MetalPriceRepository:
    """
    Repository for metal price caching operations.
    
    This repository manages the metal_prices table for caching precious metal
    prices from external APIs. It handles price retrieval, caching with TTL,
    and expiration checking.
    
    Note: This repository does NOT extend BaseRepository because MetalPrice
    is not tenant-specific (prices are global) and has specialized caching logic.
    
    Methods:
        get_current_price: Get current cached price for a metal category
        save_price: Save/update cached price with expiration
        is_expired: Check if a cached price has expired
    
    Requirements: 8.7, 8.8
    """
    
    def __init__(self, db: Session):
        """
        Initialize the repository with a database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def get_current_price(
        self,
        metal_category: str
    ) -> Optional[MetalPrice]:
        """
        Get current cached price for a metal category.
        
        Retrieves the cached price for the specified metal category
        (GOLD, SILVER, PLATINUM). Returns None if no price exists
        for the category.
        
        Note: This method does NOT check expiration. Use is_expired()
        to determine if the returned price is still valid.
        
        Args:
            metal_category: Metal category identifier (GOLD, SILVER, PLATINUM)
        
        Returns:
            MetalPrice object if found, None otherwise
        
        Requirements: 8.7, 8.8
        """
        return self.db.query(MetalPrice).filter(
            MetalPrice.metal_category == metal_category
        ).first()
    
    def save_price(
        self,
        metal_category: str,
        price_per_gram: float,
        ttl_minutes: int = 15
    ) -> MetalPrice:
        """
        Save or update cached price with expiration.
        
        Creates a new price record or updates an existing one for the
        specified metal category. Sets expiration time based on TTL.
        
        The unique constraint on metal_category ensures only one price
        per category exists. If a price already exists, it is updated
        with the new price and expiration time.
        
        Args:
            metal_category: Metal category identifier (GOLD, SILVER, PLATINUM)
            price_per_gram: Current market price per gram
            ttl_minutes: Time-to-live in minutes (default: 15)
        
        Returns:
            MetalPrice object (newly created or updated)
        
        Requirements: 8.7, 8.8
        """
        now = datetime.utcnow()
        expires_at = now + timedelta(minutes=ttl_minutes)
        
        # Check if price already exists for this category
        existing_price = self.get_current_price(metal_category)
        
        if existing_price:
            # Update existing price
            existing_price.price_per_gram = price_per_gram
            existing_price.fetched_at = now
            existing_price.expires_at = expires_at
            self.db.commit()
            self.db.refresh(existing_price)
            return existing_price
        else:
            # Create new price record
            new_price = MetalPrice(
                metal_category=metal_category,
                price_per_gram=price_per_gram,
                fetched_at=now,
                expires_at=expires_at
            )
            self.db.add(new_price)
            self.db.commit()
            self.db.refresh(new_price)
            return new_price
    
    def is_expired(self, price: MetalPrice) -> bool:
        """
        Check if a cached price has expired.
        
        Compares the price's expiration timestamp with the current time
        to determine if the cached price is still valid.
        
        Args:
            price: MetalPrice object to check
        
        Returns:
            True if price has expired, False if still valid
        
        Requirements: 8.8
        """
        return datetime.utcnow() > price.expires_at
