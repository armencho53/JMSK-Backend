"""Unit tests for Address Pydantic schemas."""
import pytest
from pydantic import ValidationError
from datetime import datetime
from app.schemas.address import (
    AddressBase, AddressCreate, AddressUpdate, AddressResponse,
    AddressListResponse, CompanySummary,
)


class TestAddressCreate:
    def test_valid_address(self):
        addr = AddressCreate(
            street_address="123 Main St", city="New York",
            state="NY", zip_code="10001", company_id=1,
        )
        assert addr.street_address == "123 Main St"
        assert addr.country == "USA"  # default
        assert addr.is_default is False  # default

    def test_strips_whitespace(self):
        addr = AddressCreate(
            street_address="  789 Pine Rd  ", city="  Chicago  ",
            state="  IL  ", zip_code="  60601  ", company_id=1,
        )
        assert addr.street_address == "789 Pine Rd"
        assert addr.city == "Chicago"

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            AddressCreate(city="Boston", state="MA", zip_code="02101", company_id=1)

    def test_empty_fields_rejected(self):
        with pytest.raises(ValidationError):
            AddressCreate(
                street_address="   ", city="Boston",
                state="MA", zip_code="02101", company_id=1,
            )

    def test_zip_code_too_short(self):
        with pytest.raises(ValidationError):
            AddressCreate(
                street_address="123 Main St", city="Boston",
                state="MA", zip_code="123", company_id=1,
            )

    def test_invalid_company_id(self):
        with pytest.raises(ValidationError):
            AddressCreate(
                street_address="123 Main St", city="NY",
                state="NY", zip_code="10001", company_id=0,
            )


class TestAddressUpdate:
    def test_partial_update(self):
        addr = AddressUpdate(street_address="789 Pine Rd")
        assert addr.street_address == "789 Pine Rd"
        assert addr.city is None

    def test_empty_update(self):
        addr = AddressUpdate()
        assert addr.street_address is None

    def test_empty_field_rejected(self):
        with pytest.raises(ValidationError):
            AddressUpdate(street_address="   ")


class TestAddressResponse:
    def test_from_dict(self):
        addr = AddressResponse(
            id=1, tenant_id=100, company_id=5,
            street_address="123 Main St", city="New York",
            state="NY", zip_code="10001", country="USA",
            is_default=True, created_at=datetime(2024, 1, 1),
        )
        assert addr.id == 1
        assert addr.company is None

    def test_with_company(self):
        addr = AddressResponse(
            id=1, tenant_id=100, company_id=5,
            street_address="123 Main St", city="New York",
            state="NY", zip_code="10001", country="USA",
            is_default=True, created_at=datetime(2024, 1, 1),
            company={"id": 5, "name": "Acme Corp"},
        )
        assert addr.company.name == "Acme Corp"
