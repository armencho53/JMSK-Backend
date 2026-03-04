"""
Precious Metal Price API Client

This module provides integration with external precious metal price APIs
to fetch current market prices for gold, silver, and platinum.
"""

import logging
from typing import Optional
import requests
from requests.exceptions import RequestException, Timeout

from app.infrastructure.config import settings

logger = logging.getLogger(__name__)


class PreciousMetalAPIClient:
    """
    Client for fetching precious metal prices from external API.
    
    Handles API communication with timeout and error handling.
    Returns None on failure to allow graceful degradation.
    """
    
    def __init__(self):
        """Initialize the API client with configuration from settings."""
        self.base_url = settings.METAL_PRICE_API_URL
        self.api_key = settings.METAL_PRICE_API_KEY
        self.timeout = 5  # seconds
    
    def get_gold_price_per_gram(self) -> Optional[float]:
        """
        Fetch current gold price per gram.
        
        Returns:
            Current gold price per gram in USD, or None if unavailable.
        """
        return self._fetch_price("GOLD")
    
    def get_silver_price_per_gram(self) -> Optional[float]:
        """
        Fetch current silver price per gram.
        
        Returns:
            Current silver price per gram in USD, or None if unavailable.
        """
        return self._fetch_price("SILVER")
    
    def get_platinum_price_per_gram(self) -> Optional[float]:
        """
        Fetch current platinum price per gram.
        
        Returns:
            Current platinum price per gram in USD, or None if unavailable.
        """
        return self._fetch_price("PLATINUM")
    
    def _map_metal_code_to_category(self, metal_code: str) -> str:
        """
        Map specific metal codes to their base category for API queries.
        
        Examples:
            GOLD_24K, GOLD_22K, GOLD_18K, GOLD_14K -> GOLD
            SILVER_925 -> SILVER
            PLATINUM -> PLATINUM
        
        Args:
            metal_code: Specific metal code from the metals table
        
        Returns:
            Base metal category (GOLD, SILVER, or PLATINUM)
        """
        metal_code_upper = metal_code.upper()
        
        if metal_code_upper.startswith("GOLD"):
            return "GOLD"
        elif metal_code_upper.startswith("SILVER"):
            return "SILVER"
        elif metal_code_upper.startswith("PLATINUM"):
            return "PLATINUM"
        else:
            # Default to the code itself if no mapping found
            return metal_code_upper
    
    def _fetch_price(self, metal_category: str) -> Optional[float]:
        """
        Fetch price from external API for a given metal category.
        
        Args:
            metal_category: Metal category (GOLD, SILVER, PLATINUM)
        
        Returns:
            Price per gram in USD, or None if fetch fails
        """
        try:
            # Construct API request URL
            url = f"{self.base_url}/price/{metal_category.lower()}"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Make API request with timeout
            response = requests.get(
                url,
                headers=headers,
                timeout=self.timeout
            )
            
            # Check for successful response
            if response.status_code == 200:
                data = response.json()
                # Assuming API returns price_per_gram field
                price = data.get("price_per_gram")
                
                if price is not None:
                    logger.info(
                        f"Successfully fetched {metal_category} price: ${price}/gram"
                    )
                    return float(price)
                else:
                    logger.warning(
                        f"API response missing price_per_gram field for {metal_category}"
                    )
                    return None
            
            elif response.status_code == 401:
                logger.error(
                    f"API authentication failed for {metal_category} price lookup. "
                    "Check API key configuration."
                )
                return None
            
            elif response.status_code == 429:
                logger.warning(
                    f"API rate limit exceeded for {metal_category} price lookup"
                )
                return None
            
            else:
                logger.warning(
                    f"API returned status {response.status_code} for {metal_category}"
                )
                return None
        
        except Timeout:
            logger.warning(
                f"API request timeout ({self.timeout}s) for {metal_category} price"
            )
            return None
        
        except RequestException as e:
            logger.warning(
                f"Network error fetching {metal_category} price: {str(e)}"
            )
            return None
        
        except (ValueError, KeyError) as e:
            logger.error(
                f"Error parsing API response for {metal_category}: {str(e)}"
            )
            return None
        
        except Exception as e:
            logger.error(
                f"Unexpected error fetching {metal_category} price: {str(e)}"
            )
            return None
