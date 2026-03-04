"""
MetalPriceService - Domain service for precious metal price management

This service provides metal price lookup with caching to minimize external API calls.
It integrates with the PreciousMetalAPIClient for fetching current prices and uses
MetalPriceRepository for caching with configurable TTL.

Requirements: 8.1, 8.2, 8.3, 8.4, 8.8
"""

import logging
from typing import Optional
from sqlalchemy.orm import Session

from app.data.repositories.metal_price_repository import MetalPriceRepository
from app.infrastructure.metal_price_api import PreciousMetalAPIClient

logger = logging.getLogger(__name__)


class MetalPriceService:
    """
    Domain service for managing precious metal price lookups with caching.
    
    This service implements a cache-first strategy for metal price lookups:
    1. Check if cached price exists and is not expired
    2. If valid cache exists, return cached price
    3. If cache expired or missing, fetch from external API
    4. Cache the fetched price with TTL (default: 15 minutes)
    5. Return None on API failure (non-blocking, allows manual entry)
    
    The service handles all API errors gracefully to ensure price lookup
    failures don't block user workflows.
    
    Requirements: 8.1, 8.2, 8.3, 8.4, 8.8
    """
    
    def __init__(self, db: Session):
        """
        Initialize the service with database session.
        
        Creates instances of MetalPriceRepository for caching and
        PreciousMetalAPIClient for external API communication.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.price_repo = MetalPriceRepository(db)
        self.api_client = PreciousMetalAPIClient()
        self.cache_ttl_minutes = 15  # Default cache TTL
    
    def get_current_price(
        self,
        metal_code: str,
        tenant_id: int
    ) -> Optional[float]:
        """
        Get current price per gram for a metal with caching logic.
        
        Implements cache-first strategy:
        1. Map metal code to category (e.g., GOLD_24K -> GOLD)
        2. Check cache for existing price
        3. If cached and not expired, return cached price
        4. If expired or missing, fetch from API and cache
        5. Return None on API failure (non-blocking)
        
        Args:
            metal_code: Specific metal code (e.g., GOLD_24K, SILVER_925)
            tenant_id: Tenant ID (for logging/audit purposes, prices are global)
        
        Returns:
            Current price per gram in USD, or None if unavailable
        
        Requirements: 8.1, 8.2, 8.3, 8.4, 8.8
        """
        # Map metal code to category for API lookup
        metal_category = self.api_client._map_metal_code_to_category(metal_code)
        
        logger.info(
            f"Price lookup for metal_code={metal_code}, "
            f"category={metal_category}, tenant_id={tenant_id}"
        )
        
        # Check cache first
        cached_price = self.price_repo.get_current_price(metal_category)
        
        if cached_price and not self.price_repo.is_expired(cached_price):
            logger.info(
                f"Cache hit for {metal_category}: ${cached_price.price_per_gram}/gram "
                f"(expires at {cached_price.expires_at})"
            )
            return cached_price.price_per_gram
        
        # Cache miss or expired - fetch from API
        if cached_price:
            logger.info(
                f"Cache expired for {metal_category}, fetching fresh price"
            )
        else:
            logger.info(
                f"No cached price for {metal_category}, fetching from API"
            )
        
        return self.fetch_and_cache_price(metal_category)
    
    def fetch_and_cache_price(
        self,
        metal_category: str
    ) -> Optional[float]:
        """
        Fetch price from external API and cache for TTL duration.
        
        Calls the appropriate API method based on metal category,
        caches the result if successful, and returns the price.
        
        On API failure, returns None to allow graceful degradation
        (user can proceed with manual price entry).
        
        Args:
            metal_category: Metal category (GOLD, SILVER, PLATINUM)
        
        Returns:
            Current price per gram in USD, or None if API unavailable
        
        Requirements: 8.1, 8.2, 8.3, 8.4, 8.8
        """
        # Fetch price from external API based on category
        price = None
        
        if metal_category == "GOLD":
            price = self.api_client.get_gold_price_per_gram()
        elif metal_category == "SILVER":
            price = self.api_client.get_silver_price_per_gram()
        elif metal_category == "PLATINUM":
            price = self.api_client.get_platinum_price_per_gram()
        else:
            logger.warning(
                f"Unknown metal category: {metal_category}. "
                "Cannot fetch price."
            )
            return None
        
        # Handle API failure gracefully
        if price is None:
            logger.warning(
                f"Failed to fetch price for {metal_category} from API. "
                "User can proceed with manual entry."
            )
            return None
        
        # Cache the fetched price
        try:
            cached_price = self.price_repo.save_price(
                metal_category=metal_category,
                price_per_gram=price,
                ttl_minutes=self.cache_ttl_minutes
            )
            logger.info(
                f"Cached {metal_category} price: ${price}/gram "
                f"(expires at {cached_price.expires_at})"
            )
            return price
        
        except Exception as e:
            logger.error(
                f"Error caching price for {metal_category}: {str(e)}. "
                "Returning fetched price without caching."
            )
            # Return the fetched price even if caching fails
            return price
