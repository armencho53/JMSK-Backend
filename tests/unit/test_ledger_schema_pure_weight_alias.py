"""Test LedgerEntryResponse schema pure_weight alias for backward compatibility"""
import pytest
from datetime import date, datetime
from app.schemas.ledger import LedgerEntryResponse


class TestLedgerEntryResponsePureWeightAlias:
    """Test that pure_weight field aliases fine_weight for backward compatibility"""

    def test_pure_weight_aliases_fine_weight(self):
        """Test that pure_weight field is populated from fine_weight database column"""
        # Simulate ORM object data with fine_weight
        data = {
            "id": 1,
            "tenant_id": 1,
            "date": date(2024, 1, 15),
            "department_id": 1,
            "order_id": 1,
            "order_number": "ORD-001",
            "metal_id": 1,
            "metal_code": "GOLD_24K",
            "metal_name": "Gold 24K",
            "direction": "IN",
            "quantity": 10,
            "weight": 100.0,
            "fine_weight": 95.5,  # Database column name
            "notes": "Test entry",
            "is_archived": False,
            "created_by": 1,
            "created_at": datetime(2024, 1, 15, 10, 0, 0),
            "updated_at": datetime(2024, 1, 15, 10, 0, 0),
        }

        # Create response schema
        response = LedgerEntryResponse.model_validate(data)

        # Both fine_weight and pure_weight should be accessible
        assert response.fine_weight == 95.5
        assert response.pure_weight == 95.5

    def test_populate_by_name_allows_both_field_names(self):
        """Test that populate_by_name=True allows reading from either fine_weight or pure_weight"""
        # Test with fine_weight (database column name) - primary use case
        data_with_fine = {
            "id": 1,
            "tenant_id": 1,
            "date": date(2024, 1, 15),
            "department_id": 1,
            "order_id": 1,
            "order_number": "ORD-001",
            "metal_id": 1,
            "metal_code": "GOLD_24K",
            "metal_name": "Gold 24K",
            "direction": "IN",
            "quantity": 10,
            "weight": 100.0,
            "fine_weight": 95.5,
            "notes": None,
            "is_archived": False,
            "created_by": 1,
            "created_at": datetime(2024, 1, 15, 10, 0, 0),
            "updated_at": datetime(2024, 1, 15, 10, 0, 0),
        }

        response1 = LedgerEntryResponse.model_validate(data_with_fine)

        # Both fields should be accessible
        assert response1.fine_weight == 95.5
        assert response1.pure_weight == 95.5

    def test_json_serialization_includes_both_fields(self):
        """Test that JSON serialization includes both fine_weight and pure_weight"""
        data = {
            "id": 1,
            "tenant_id": 1,
            "date": date(2024, 1, 15),
            "department_id": 1,
            "order_id": 1,
            "order_number": "ORD-001",
            "metal_id": 1,
            "metal_code": "GOLD_24K",
            "metal_name": "Gold 24K",
            "direction": "IN",
            "quantity": 10,
            "weight": 100.0,
            "fine_weight": 95.5,
            "notes": None,
            "is_archived": False,
            "created_by": 1,
            "created_at": datetime(2024, 1, 15, 10, 0, 0),
            "updated_at": datetime(2024, 1, 15, 10, 0, 0),
        }

        response = LedgerEntryResponse.model_validate(data)
        json_data = response.model_dump()

        # Both fields should be in the serialized output
        assert "fine_weight" in json_data
        assert "pure_weight" in json_data
        assert json_data["fine_weight"] == 95.5
        assert json_data["pure_weight"] == 95.5
