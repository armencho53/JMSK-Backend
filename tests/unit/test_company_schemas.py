"""Unit tests for Company Pydantic schemas."""
import pytest
from pydantic import ValidationError
from datetime import datetime
from decimal import Decimal
from app.schemas.company import (
    CompanyBase, CompanyCreate, CompanyUpdate, CompanyResponse,
    ContactSummary, AddressSummary,
)


class TestCompanyCreate:
    def test_valid_company(self):
        c = CompanyCreate(name="Acme Corp", email="info@acme.com")
        assert c.name == "Acme Corp"

    def test_minimal(self):
        c = CompanyCreate(name="Minimal Corp")
        assert c.address is None

    def test_missing_name(self):
        with pytest.raises(ValidationError):
            CompanyCreate()

    def test_empty_name(self):
        with pytest.raises(ValidationError):
            CompanyCreate(name="")

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            CompanyCreate(name="Test", email="invalid-email")


class TestCompanyUpdate:
    def test_all_optional(self):
        c = CompanyUpdate()
        assert c.name is None

    def test_partial(self):
        c = CompanyUpdate(name="Updated")
        assert c.name == "Updated"
        assert c.email is None

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            CompanyUpdate(email="not-an-email")


class TestCompanyResponse:
    def test_basic(self):
        now = datetime.utcnow()
        c = CompanyResponse(
            id=1, tenant_id=1, name="Corp",
            created_at=now, updated_at=now,
        )
        assert c.contacts is None
        assert c.total_balance is None

    def test_with_relationships(self):
        now = datetime.utcnow()
        c = CompanyResponse(
            id=1, tenant_id=1, name="Corp",
            created_at=now, updated_at=now,
            contacts=[ContactSummary(id=1, name="John")],
            addresses=[AddressSummary(
                id=1, street_address="123 Main", city="NY",
                state="NY", zip_code="10001", country="USA", is_default=True,
            )],
            total_balance=Decimal("15000.50"),
        )
        assert len(c.contacts) == 1
        assert len(c.addresses) == 1
        assert c.total_balance == Decimal("15000.50")

    def test_serialization(self):
        now = datetime.utcnow()
        c = CompanyResponse(
            id=1, tenant_id=1, name="Test",
            created_at=now, updated_at=now,
            total_balance=Decimal("5000.00"),
        )
        data = c.model_dump()
        assert data["total_balance"] == Decimal("5000.00")
