"""Unit tests for PreciousMetalAPIClient."""
import pytest
from unittest.mock import Mock, patch
from requests.exceptions import Timeout, RequestException
from app.infrastructure.metal_price_api import PreciousMetalAPIClient


@pytest.fixture
def api_client():
    with patch('app.infrastructure.metal_price_api.settings') as mock_settings:
        mock_settings.METAL_PRICE_API_URL = "https://api.example.com"
        mock_settings.METAL_PRICE_API_KEY = "test_api_key"
        yield PreciousMetalAPIClient()


class TestMetalCodeMapping:
    def test_gold_variants(self, api_client):
        for code in ["GOLD_24K", "GOLD_22K", "GOLD_18K", "GOLD_14K", "gold_24k"]:
            assert api_client._map_metal_code_to_category(code) == "GOLD"

    def test_silver(self, api_client):
        assert api_client._map_metal_code_to_category("SILVER_925") == "SILVER"

    def test_platinum(self, api_client):
        assert api_client._map_metal_code_to_category("PLATINUM") == "PLATINUM"

    def test_unknown(self, api_client):
        assert api_client._map_metal_code_to_category("COPPER") == "COPPER"


class TestPriceFetching:
    @patch('app.infrastructure.metal_price_api.requests.get')
    def test_success(self, mock_get, api_client):
        mock_resp = Mock(status_code=200)
        mock_resp.json.return_value = {"price_per_gram": 65.50}
        mock_get.return_value = mock_resp
        assert api_client.get_gold_price_per_gram() == 65.50

    @patch('app.infrastructure.metal_price_api.requests.get')
    def test_timeout_returns_none(self, mock_get, api_client):
        mock_get.side_effect = Timeout()
        assert api_client.get_gold_price_per_gram() is None

    @patch('app.infrastructure.metal_price_api.requests.get')
    def test_network_error_returns_none(self, mock_get, api_client):
        mock_get.side_effect = RequestException("fail")
        assert api_client.get_gold_price_per_gram() is None

    @patch('app.infrastructure.metal_price_api.requests.get')
    def test_http_error_returns_none(self, mock_get, api_client):
        mock_get.return_value = Mock(status_code=500)
        assert api_client.get_gold_price_per_gram() is None

    @patch('app.infrastructure.metal_price_api.requests.get')
    def test_missing_price_field_returns_none(self, mock_get, api_client):
        mock_resp = Mock(status_code=200)
        mock_resp.json.return_value = {"other": "value"}
        mock_get.return_value = mock_resp
        assert api_client.get_gold_price_per_gram() is None

    @patch('app.infrastructure.metal_price_api.requests.get')
    def test_sends_auth_header(self, mock_get, api_client):
        mock_resp = Mock(status_code=200)
        mock_resp.json.return_value = {"price_per_gram": 65.50}
        mock_get.return_value = mock_resp
        api_client.get_gold_price_per_gram()
        headers = mock_get.call_args[1]['headers']
        assert 'Bearer test_api_key' in headers['Authorization']
