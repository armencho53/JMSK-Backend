"""
Unit tests for PreciousMetalAPIClient

Tests the metal price API client functionality including:
- Metal code to category mapping
- Price fetching with mocked API responses
- Error handling (timeout, network errors, invalid responses)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from requests.exceptions import Timeout, RequestException

from app.infrastructure.metal_price_api import PreciousMetalAPIClient


class TestPreciousMetalAPIClient:
    """Test suite for PreciousMetalAPIClient"""
    
    @pytest.fixture
    def api_client(self):
        """Create API client instance for testing"""
        with patch('app.infrastructure.metal_price_api.settings') as mock_settings:
            mock_settings.METAL_PRICE_API_URL = "https://api.example.com"
            mock_settings.METAL_PRICE_API_KEY = "test_api_key"
            return PreciousMetalAPIClient()
    
    def test_metal_code_to_category_mapping_gold(self, api_client):
        """Test mapping of gold variants to GOLD category"""
        assert api_client._map_metal_code_to_category("GOLD_24K") == "GOLD"
        assert api_client._map_metal_code_to_category("GOLD_22K") == "GOLD"
        assert api_client._map_metal_code_to_category("GOLD_18K") == "GOLD"
        assert api_client._map_metal_code_to_category("GOLD_14K") == "GOLD"
        assert api_client._map_metal_code_to_category("gold_24k") == "GOLD"
    
    def test_metal_code_to_category_mapping_silver(self, api_client):
        """Test mapping of silver variants to SILVER category"""
        assert api_client._map_metal_code_to_category("SILVER_925") == "SILVER"
        assert api_client._map_metal_code_to_category("SILVER") == "SILVER"
        assert api_client._map_metal_code_to_category("silver_925") == "SILVER"
    
    def test_metal_code_to_category_mapping_platinum(self, api_client):
        """Test mapping of platinum to PLATINUM category"""
        assert api_client._map_metal_code_to_category("PLATINUM") == "PLATINUM"
        assert api_client._map_metal_code_to_category("platinum") == "PLATINUM"
    
    def test_metal_code_to_category_mapping_unknown(self, api_client):
        """Test mapping of unknown metal codes returns the code itself"""
        assert api_client._map_metal_code_to_category("COPPER") == "COPPER"
        assert api_client._map_metal_code_to_category("BRONZE") == "BRONZE"
    
    @patch('app.infrastructure.metal_price_api.requests.get')
    def test_get_gold_price_success(self, mock_get, api_client):
        """Test successful gold price fetch"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"price_per_gram": 65.50}
        mock_get.return_value = mock_response
        
        price = api_client.get_gold_price_per_gram()
        
        assert price == 65.50
        mock_get.assert_called_once()
        assert "gold" in mock_get.call_args[0][0]
    
    @patch('app.infrastructure.metal_price_api.requests.get')
    def test_get_silver_price_success(self, mock_get, api_client):
        """Test successful silver price fetch"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"price_per_gram": 0.85}
        mock_get.return_value = mock_response
        
        price = api_client.get_silver_price_per_gram()
        
        assert price == 0.85
        mock_get.assert_called_once()
        assert "silver" in mock_get.call_args[0][0]
    
    @patch('app.infrastructure.metal_price_api.requests.get')
    def test_get_platinum_price_success(self, mock_get, api_client):
        """Test successful platinum price fetch"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"price_per_gram": 32.75}
        mock_get.return_value = mock_response
        
        price = api_client.get_platinum_price_per_gram()
        
        assert price == 32.75
        mock_get.assert_called_once()
        assert "platinum" in mock_get.call_args[0][0]
    
    @patch('app.infrastructure.metal_price_api.requests.get')
    def test_api_timeout_returns_none(self, mock_get, api_client):
        """Test that API timeout returns None gracefully"""
        mock_get.side_effect = Timeout()
        
        price = api_client.get_gold_price_per_gram()
        
        assert price is None
    
    @patch('app.infrastructure.metal_price_api.requests.get')
    def test_network_error_returns_none(self, mock_get, api_client):
        """Test that network errors return None gracefully"""
        mock_get.side_effect = RequestException("Network error")
        
        price = api_client.get_gold_price_per_gram()
        
        assert price is None
    
    @patch('app.infrastructure.metal_price_api.requests.get')
    def test_api_401_unauthorized_returns_none(self, mock_get, api_client):
        """Test that 401 Unauthorized returns None"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        price = api_client.get_gold_price_per_gram()
        
        assert price is None
    
    @patch('app.infrastructure.metal_price_api.requests.get')
    def test_api_429_rate_limit_returns_none(self, mock_get, api_client):
        """Test that 429 Rate Limit returns None"""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_get.return_value = mock_response
        
        price = api_client.get_gold_price_per_gram()
        
        assert price is None
    
    @patch('app.infrastructure.metal_price_api.requests.get')
    def test_api_500_server_error_returns_none(self, mock_get, api_client):
        """Test that 500 Server Error returns None"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        price = api_client.get_gold_price_per_gram()
        
        assert price is None
    
    @patch('app.infrastructure.metal_price_api.requests.get')
    def test_missing_price_field_returns_none(self, mock_get, api_client):
        """Test that missing price_per_gram field returns None"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"other_field": "value"}
        mock_get.return_value = mock_response
        
        price = api_client.get_gold_price_per_gram()
        
        assert price is None
    
    @patch('app.infrastructure.metal_price_api.requests.get')
    def test_invalid_json_returns_none(self, mock_get, api_client):
        """Test that invalid JSON response returns None"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response
        
        price = api_client.get_gold_price_per_gram()
        
        assert price is None
    
    @patch('app.infrastructure.metal_price_api.requests.get')
    def test_timeout_configuration(self, mock_get, api_client):
        """Test that timeout is configured correctly"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"price_per_gram": 65.50}
        mock_get.return_value = mock_response
        
        api_client.get_gold_price_per_gram()
        
        # Verify timeout parameter is passed
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs['timeout'] == 5
    
    @patch('app.infrastructure.metal_price_api.requests.get')
    def test_api_key_in_headers(self, mock_get, api_client):
        """Test that API key is included in request headers"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"price_per_gram": 65.50}
        mock_get.return_value = mock_response
        
        api_client.get_gold_price_per_gram()
        
        # Verify API key in headers
        call_kwargs = mock_get.call_args[1]
        assert 'headers' in call_kwargs
        assert 'Authorization' in call_kwargs['headers']
        assert 'Bearer test_api_key' in call_kwargs['headers']['Authorization']
